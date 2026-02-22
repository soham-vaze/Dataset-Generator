'''
Architecture pipeline
User uploads text document
        ↓
Chunk document
        ↓
Select chunk
        ↓
Generate question from chunk
        ↓
Generate answer strictly from chunk
        ↓
Validate answer grounding
        ↓
Store dataset

Currenty for the chunking part using sentence sliding window technique but can shift to 
semantic coherence chunking.

Difficulty Control (easy/medium/hard)

using 4 layer validation for checking that answer is grounded in context as well as answer aligns appropriately with the question: 

Layer 1: Answer must overlap context significantly

Layer 2: Answer length check

Layer 3: SLM-as-judge consistency check

Layer 4: Embedding-based semantic validation
'''

import os
import re
import json
import ollama
import pandas as pd
import nltk
from datetime import datetime
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

nltk.download("punkt")
from nltk.tokenize import sent_tokenize


# =====================================================
# 🔹 LOAD EMBEDDING MODEL (only once)
# =====================================================

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# =====================================================
# 1️⃣ CHUNKING
# =====================================================

def chunk_text(text: str,
               sentences_per_chunk: int = 6,
               overlap: int = 2) -> List[str]:

    sentences = sent_tokenize(text)

    chunks = []
    start = 0

    while start < len(sentences):
        end = start + sentences_per_chunk
        chunk_sentences = sentences[start:end]

        if len(chunk_sentences) < 3:
            break

        chunks.append(" ".join(chunk_sentences))
        start += sentences_per_chunk - overlap

    return chunks


# =====================================================
# 2️⃣ GENERATE QA PAIR (with difficulty control)
# =====================================================

def build_prompt_by_difficulty(difficulty: str) -> str:

    if difficulty == "easy":
        return (
            "Generate ONE factual question whose answer is directly "
            "stated in a single sentence from the context."
        )

    elif difficulty == "medium":
        return (
            "Generate ONE question that requires combining at least "
            "two sentences from the context."
        )

    elif difficulty == "hard":
        return (
            "Generate ONE analytical question requiring reasoning, "
            "inference, or causal understanding from multiple parts "
            "of the context."
        )

    else:
        raise ValueError("Difficulty must be: easy | medium | hard")


def generate_qa_pair(context: str,
                     model: str,
                     difficulty: str,
                     temperature: float = 0.7) -> Dict:

    instruction = build_prompt_by_difficulty(difficulty)

    schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "answer": {"type": "string"}
        },
        "required": ["question", "answer"]
    }

    system_prompt = (
        "You are a high-quality RAG dataset generator.\n"
        f"{instruction}\n"
        "Answer must be strictly grounded in the context.\n"
        "Do NOT hallucinate.\n"
        "Return JSON with 'question' and 'answer'."
    )

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ],
        format=schema,
        options={"temperature": temperature}
    )

    return json.loads(response["message"]["content"])


# =====================================================
# 3️⃣ VALIDATION LAYER 1: Overlap
# =====================================================

def grounding_overlap_check(answer: str,
                            context: str,
                            threshold: float = 0.5) -> bool:

    answer_words = set(re.findall(r"\w+", answer.lower()))
    context_words = set(re.findall(r"\w+", context.lower()))

    if not answer_words:
        return False

    overlap_ratio = len(answer_words & context_words) / len(answer_words)

    return overlap_ratio >= threshold


# =====================================================
# 4️⃣ VALIDATION LAYER 2: Minimum Length
# =====================================================

def length_check(answer: str,
                 min_chars: int = 40) -> bool:

    return len(answer.strip()) >= min_chars


# =====================================================
# 5️⃣ VALIDATION LAYER 3: LLM Judge
# =====================================================

def llm_consistency_check(context: str,
                          question: str,
                          answer: str,
                          model: str) -> bool:

    judge_prompt = (
        "Given the context, question, and answer below:\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        f"Answer:\n{answer}\n\n"
        "Is the answer fully supported by the context and does it "
        "correctly answer the question?\n"
        "Reply with YES or NO only."
    )

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": judge_prompt}],
        options={"temperature": 0}
    )

    verdict = response["message"]["content"].strip().upper()

    return "YES" in verdict


# =====================================================
# 6️⃣ VALIDATION LAYER 4: Embedding Semantic Check
# =====================================================

def semantic_similarity_check(answer: str,
                              context: str,
                              threshold: float = 0.75) -> bool:

    answer_emb = embedding_model.encode([answer])
    context_emb = embedding_model.encode([context])

    similarity = cosine_similarity(answer_emb, context_emb)[0][0]

    return similarity >= threshold


# =====================================================
# 7️⃣ SAVE DATASET
# =====================================================

def save_dataset(rows: List[Dict],
                 output_path: str):

    df = pd.DataFrame(rows)

    file_exists = os.path.exists(output_path)

    df.to_csv(
        output_path,
        mode="a",
        index=False,
        header=not file_exists
    )

    jsonl_path = output_path.replace(".csv", ".jsonl")

    df.to_json(
        jsonl_path,
        orient="records",
        lines=True,
        mode="a"
    )


# =====================================================
# 8️⃣ MAIN ENGINE
# =====================================================

def generate_rag_dataset(document_text: str,
                         output_path: str,
                         model: str,
                         difficulty: str = "medium",
                         max_pairs: int = 10):

    chunks = chunk_text(document_text)

    existing_questions = set()
    dataset_rows = []

    if os.path.exists(output_path):
        existing_df = pd.read_csv(output_path)
        if "question" in existing_df.columns:
            existing_questions = set(
                existing_df["question"].str.lower().str.strip()
            )

    print(f"Total Chunks: {len(chunks)}")

    for chunk in chunks:

        if len(dataset_rows) >= max_pairs:
            break

        try:
            qa = generate_qa_pair(
                context=chunk,
                model=model,
                difficulty=difficulty
            )

            question = qa["question"].strip()
            answer = qa["answer"].strip()

            normalized_question = question.lower()

            if normalized_question in existing_questions:
                print("⚠ Duplicate question.")
                continue

            # -------------------------
            # 🔥 4-LAYER VALIDATION
            # -------------------------

            if not grounding_overlap_check(answer, chunk):
                print("⚠ Failed overlap.")
                continue

            if not length_check(answer):
                print("⚠ Failed length.")
                continue

            if not semantic_similarity_check(answer, chunk):
                print("⚠ Failed semantic similarity.")
                continue

            if not llm_consistency_check(chunk, question, answer, model):
                print("⚠ Failed LLM judge.")
                continue

            dataset_rows.append({
                "context": chunk,
                "question": question,
                "answer": answer,
                "difficulty": difficulty,
                "created_at": datetime.utcnow().isoformat()
            })

            existing_questions.add(normalized_question)

            print(f"✅ Added ({len(dataset_rows)}/{max_pairs})")

        except Exception as e:
            print(f"❌ Error: {e}")

    if dataset_rows:
        save_dataset(dataset_rows, output_path)
        print(f"\n🎯 Saved {len(dataset_rows)} QA pairs.")
    else:
        print("\n❌ No valid QA pairs generated.")


# =====================================================
# 🔥 EXAMPLE USAGE
# =====================================================

if __name__ == "__main__":

    with open("../data/document.txt", "r") as f:
        text = f.read()

    generate_rag_dataset(
        document_text=text,
        output_path="../datasets/rag_dataset_v2.csv",
        model="gemma3:1b",
        difficulty="hard",   # easy | medium | hard
        max_pairs=8
    )