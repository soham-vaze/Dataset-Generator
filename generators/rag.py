import os
import re
import json
import requests
import ollama
import pandas as pd
import nltk
from datetime import datetime
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity

nltk.download("punkt")
from nltk.tokenize import sent_tokenize


# =====================================================
# REMOTE SLM CONFIG
# =====================================================

SLM_API = "http://10.30.1.34:11434/api/generate"


def call_remote_slm(prompt: str,
                    model: str,
                    temperature: float = 0.7) -> str:

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }

    response = requests.post(
        SLM_API,
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    # response.raise_for_status()

    # return response.json()["response"]

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text}")

    data = response.json()

    if "response" not in data:
        raise Exception(f"Invalid response format: {data}")

    return data["response"]

# =====================================================
# 1️⃣ CHUNKING
# =====================================================

def chunk_text(text: str,
               sentences_per_chunk: int = 6,
               overlap: int = 2) -> List[str]:

    print("Chunking text")

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
# 2️⃣ DIFFICULTY PROMPT
# =====================================================

def build_prompt_by_difficulty(difficulty: str) -> str:

    print(f"Building prompt for {difficulty} level")

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
        raise ValueError("Difficulty must be easy | medium | hard")


# =====================================================
# 3️⃣ BATCH QA GENERATION
# =====================================================

def extract_json_array(text: str):

    text = re.sub(r"```json|```", "", text).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except:
        pass

    # Extract JSON array
    match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)

    if match:
        return json.loads(match.group())

    raise ValueError(f"JSON extraction failed:\n{text[:500]}")

def generate_qa_batch(contexts: List[str],
                      model: str,
                      difficulty: str,
                      temperature: float = 0.7) -> List[Dict]:

    print("Generating QA batch")

    instruction = build_prompt_by_difficulty(difficulty)

    joined_context = ""

    for i, ctx in enumerate(contexts):
        joined_context += f"\n\nCONTEXT_{i+1}:\n{ctx}"

    prompt = f"""
You are a STRICT JSON generator.

Generate EXACTLY {len(contexts)} question-answer pairs.

Rules:
- Output ONLY valid JSON
- NO explanations
- NO markdown
- NO extra text
- Ensure valid syntax

Format:
[
  {{"question":"...","answer":"...","context_id":1}},
  {{"question":"...","answer":"...","context_id":2}}
]

{joined_context}
"""

    raw_output = call_remote_slm(
        prompt=prompt,
        model=model,
        temperature=temperature
    )

    if not raw_output or raw_output.strip() == "":
        raise ValueError("Empty response from model")

    print("\n----- RAW OUTPUT START -----")
    print(raw_output[:1000])
    print("----- RAW OUTPUT END -----\n")

    raw_output = raw_output.strip()
    try:
        qa_list = extract_json_array(raw_output)
    except:
        raw_output = re.sub(r"```json|```", "", raw_output)
        qa_list = json.loads(raw_output)

    return qa_list


# =====================================================
# 4️⃣ VALIDATION LAYER 1: Overlap
# =====================================================

def grounding_overlap_check(answer: str,
                            context: str,
                            threshold: float = 0.3) -> bool:

    print("Entering validation layer 1 overlap")

    answer_words = set(re.findall(r"\w+", answer.lower()))
    context_words = set(re.findall(r"\w+", context.lower()))

    if not answer_words:
        return False

    overlap_ratio = len(answer_words & context_words) / len(answer_words)

    print(f"Overlap ratio: {overlap_ratio}")

    return overlap_ratio >= threshold


# =====================================================
# 5️⃣ VALIDATION LAYER 2: Length
# =====================================================

def length_check(answer: str,
                 min_chars: int = 40) -> bool:

    print("Entering validation layer 2")

    return len(answer.strip()) >= min_chars


# =====================================================
# 6️⃣ VALIDATION LAYER 3: LLM Judge
# =====================================================

def llm_consistency_check(context: str,
                          question: str,
                          answer: str,
                          model: str) -> bool:

    print("Entering validation layer 3")

    judge_prompt = (
        "Given the context, question, and answer below:\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        f"Answer:\n{answer}\n\n"
        "Is the answer fully supported by the context and does it "
        "correctly answer the question?\n"
        "Reply with YES or NO only."
    )

    response = call_remote_slm(
        prompt=judge_prompt,
        model=model,
        temperature=0
    )

    verdict = response.strip().upper()

    return "YES" in verdict


# =====================================================
# 7️⃣ VALIDATION LAYER 4: Embedding Similarity
# =====================================================

def semantic_similarity_check(answer: str,
                              context: str,
                              threshold: float = 0.50,
                              embedding_model: str = "nomic-embed-text") -> bool:

    print("Entering validation layer 4")

    answer_emb = ollama.embeddings(
        model=embedding_model,
        prompt=answer
    )["embedding"]

    context_emb = ollama.embeddings(
        model=embedding_model,
        prompt=context
    )["embedding"]

    similarity = cosine_similarity(
        [answer_emb],
        [context_emb]
    )[0][0]

    print(f"Similarity obtained: {similarity}")

    return similarity >= threshold


# =====================================================
# 8️⃣ SAVE DATASET
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
# 9️⃣ MAIN ENGINE
# =====================================================

def generate_rag_dataset(document_text: str,
                         output_path: str,
                         model: str,
                         difficulty: str = "medium",
                         max_pairs: int = 10):

    print("Generating RAG dataset")

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

    BATCH_SIZE = 4

    for i in range(0, len(chunks), BATCH_SIZE):

        if len(dataset_rows) >= max_pairs:
            break

        batch_chunks = chunks[i:i + BATCH_SIZE]

        try:

            qa_list = generate_qa_batch(
                contexts=batch_chunks,
                model=model,
                difficulty=difficulty
            )

            for qa in qa_list:

                context_id = qa.get("context_id", 1) - 1

                if context_id >= len(batch_chunks):
                    continue

                chunk = batch_chunks[context_id]

                question = qa["question"].strip()
                answer = qa["answer"].strip()

                normalized_question = question.lower()

                if normalized_question in existing_questions:
                    print("⚠ Duplicate question")
                    continue

                if not grounding_overlap_check(answer, chunk):
                    print("⚠ Failed overlap")
                    continue

                # if not length_check(answer):
                #     print("⚠ Failed length")
                #     continue

                if not semantic_similarity_check(answer, chunk):
                    print("⚠ Failed semantic similarity")
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

        print(f"\n🎯 Saved {len(dataset_rows)} QA pairs")

    else:

        print("\n❌ No valid QA pairs generated")


# =====================================================
# 🔥 EXAMPLE USAGE
# =====================================================

if __name__ == "__main__":

    with open("../data/document.txt", "r") as f:
        text = f.read()

    generate_rag_dataset(
        document_text=text,
        output_path="../datasets/rag_dataset_v2.csv",
        model="gemma3:4b",
        difficulty="medium",
        max_pairs=8
    )

    generate_rag_dataset(
        document_text=text,
        output_path="../datasets/rag_dataset_v2.csv",
        model="gemma3:4b",
        difficulty="easy",
        max_pairs=8
    )