import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

import nltk
import ollama
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from generators.utils import call_model, extract_json_array, save_dataset

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)

from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)

# =====================================================
# 1️⃣ CHUNKING
# =====================================================

def chunk_text(text: str,
               sentences_per_chunk: int = 6,
               overlap: int = 2) -> List[str]:

    logger.info("Chunking text")

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

    logger.info("Building prompt for %s level", difficulty)

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
# 3️⃣ BATCH QA GENERATION — uses extract_json_array from generators.utils
# =====================================================

def generate_qa_batch(contexts: List[str],
                      model: str,
                      difficulty: str,
                      temperature: float = 0.7) -> List[Dict[str, Any]]:

    logger.info("Generating QA batch")

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

    raw_output = call_model(
        prompt=prompt,
        model=model,
        temperature=temperature,
    )

    if not raw_output or raw_output.strip() == "":
        raise ValueError("Empty response from model")

    logger.debug("Raw LLM output: %s", raw_output[:500])

    raw_output = raw_output.strip()
    try:
        qa_list = extract_json_array(raw_output)
    except (json.JSONDecodeError, ValueError):
        raw_output = re.sub(r"```json|```", "", raw_output)
        qa_list = json.loads(raw_output)

    return qa_list


# =====================================================
# 4️⃣ VALIDATION LAYER 1: Overlap
# =====================================================

def grounding_overlap_check(answer: str,
                            context: str,
                            threshold: float = 0.3) -> bool:

    logger.debug("Entering validation layer 1 overlap")

    answer_words = set(re.findall(r"\w+", answer.lower()))
    context_words = set(re.findall(r"\w+", context.lower()))

    if not answer_words:
        return False

    overlap_ratio = len(answer_words & context_words) / len(answer_words)

    logger.debug("Overlap ratio: %.3f", overlap_ratio)

    return overlap_ratio >= threshold


# =====================================================
# 5️⃣ VALIDATION LAYER 2: Length
# =====================================================

def length_check(answer: str,
                 min_chars: int = 40) -> bool:

    logger.debug("Entering validation layer 2")

    return len(answer.strip()) >= min_chars


# =====================================================
# 6️⃣ VALIDATION LAYER 3: LLM Judge
# =====================================================

def llm_consistency_check(context: str,
                          question: str,
                          answer: str,
                          model: str) -> bool:

    logger.debug("Entering validation layer 3")

    judge_prompt = (
        "Given the context, question, and answer below:\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        f"Answer:\n{answer}\n\n"
        "Is the answer fully supported by the context and does it "
        "correctly answer the question?\n"
        "Reply with YES or NO only."
    )

    response = call_model(
        prompt=judge_prompt,
        model=model,
        temperature=0,
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

    logger.debug("Entering validation layer 4")

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

    logger.debug("Similarity obtained: %.4f", similarity)

    return similarity >= threshold


# =====================================================
# 8️⃣ SAVE DATASET — Uses shared save_dataset from generators.utils
# =====================================================


# =====================================================
# 9️⃣ MAIN ENGINE
# =====================================================

def generate_rag_dataset(document_text: str,
                         output_path: str,
                         model: str,
                         difficulty: str = "medium",
                         max_pairs: int = 10) -> None:

    logger.info("Generating RAG dataset")

    chunks = chunk_text(document_text)

    existing_questions: Set[str] = set()
    dataset_rows: List[Dict[str, str]] = []

    if os.path.exists(output_path):

        existing_df = pd.read_csv(output_path)

        if "question" in existing_df.columns:

            existing_questions = set(
                existing_df["question"].str.lower().str.strip()
            )

    logger.info("Total Chunks: %d", len(chunks))

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
                    logger.debug("Duplicate question")
                    continue

                if not grounding_overlap_check(answer, chunk):
                    logger.debug("Failed overlap check")
                    continue

                # if not length_check(answer):
                #     logger.debug("Failed length check")
                #     continue

                if not semantic_similarity_check(answer, chunk):
                    logger.debug("Failed semantic similarity")
                    continue

                dataset_rows.append({
                    "context": chunk,
                    "question": question,
                    "answer": answer,
                    "difficulty": difficulty,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })

                existing_questions.add(normalized_question)

                logger.info("Added (%d/%d)", len(dataset_rows), max_pairs)

        except Exception as e:

            logger.error("Error during QA generation: %s", e)

    if dataset_rows:

        save_dataset(dataset_rows, output_path)

        logger.info("Saved %d QA pairs", len(dataset_rows))

    else:

        logger.warning("No valid QA pairs generated")


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