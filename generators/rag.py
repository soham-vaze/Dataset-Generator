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

from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)

# =====================================================
# GLOBAL EMBEDDING CACHE
# =====================================================

EMBEDDING_CACHE = {}

# =====================================================
# 1️⃣ CHUNKING
# =====================================================

def chunk_text(
    text: str,
    sentences_per_chunk: int = 5,
    overlap: int = 2
) -> List[str]:

    logger.info("Chunking text")

    sentences = sent_tokenize(text)

    if not sentences:
        return []

    chunks = []
    start = 0

    while start < len(sentences):

        end = start + sentences_per_chunk
        chunk_sentences = sentences[start:end]

        # Include even small final chunk
        if len(chunk_sentences) == 0:
            break

        chunk = " ".join(chunk_sentences).strip()

        if chunk:
            chunks.append(chunk)

        start += max(1, sentences_per_chunk - overlap)

    logger.info("Generated %d chunks", len(chunks))

    return chunks


# =====================================================
# 2️⃣ DIFFICULTY PROMPT
# =====================================================

def build_prompt_by_difficulty(difficulty: str) -> str:

    logger.info("Building prompt for %s level", difficulty)

    if difficulty == "easy":
        return (
            "Generate ONE factual question whose answer is directly "
            "present in the context."
        )

    elif difficulty == "medium":
        return (
            "Generate ONE reasoning question that combines "
            "information from multiple sentences."
        )

    elif difficulty == "hard":
        return (
            "Generate ONE analytical or inferential question "
            "requiring deeper reasoning from the context."
        )

    raise ValueError("Difficulty must be easy | medium | hard")


# =====================================================
# 3️⃣ SAFE JSON EXTRACTION
# =====================================================

def safe_json_parse(raw_output: str):

    raw_output = raw_output.strip()

    # Remove markdown fences
    raw_output = re.sub(r"```json|```", "", raw_output).strip()

    try:
        return extract_json_array(raw_output)

    except Exception:

        # Try regex extraction
        matches = re.findall(r"\[[\s\S]*\]", raw_output)

        if matches:

            for match in matches:

                try:
                    return json.loads(match)
                except Exception:
                    continue

    raise ValueError("Failed to parse JSON response")


# =====================================================
# 4️⃣ QA GENERATION
# =====================================================

def generate_qa_batch(
    contexts: List[str],
    model: str,
    difficulty: str,
    temperature: float = 0.5
) -> List[Dict[str, Any]]:

    logger.info("Generating QA batch")

    instruction = build_prompt_by_difficulty(difficulty)

    joined_context = ""

    for i, ctx in enumerate(contexts):
        joined_context += f"\n\nCONTEXT_{i+1}:\n{ctx}"

    prompt = f"""
You are a STRICT JSON generator.

TASK:
{instruction}

Generate EXACTLY {len(contexts)} question-answer pairs.

RULES:
- Output ONLY valid JSON
- No markdown
- No explanations
- No comments
- No trailing commas
- Each QA must be unique
- Questions must NOT repeat

FORMAT:
[
  {{
    "question": "...",
    "answer": "...",
    "context_id": 1
  }}
]

{joined_context}
"""

    raw_output = call_model(
        prompt=prompt,
        model=model,
        temperature=temperature,
    )

    if not raw_output or not raw_output.strip():
        raise ValueError("Empty model response")

    logger.debug("Raw output: %s", raw_output[:500])

    qa_list = safe_json_parse(raw_output)

    if not isinstance(qa_list, list):
        raise ValueError("Model did not return a list")

    validated = []

    for item in qa_list:

        if not isinstance(item, dict):
            continue

        question = item.get("question")
        answer = item.get("answer")
        context_id = item.get("context_id", 1)

        if not question or not answer:
            continue

        validated.append({
            "question": str(question).strip(),
            "answer": str(answer).strip(),
            "context_id": int(context_id),
        })

    return validated


# =====================================================
# 5️⃣ VALIDATION — OVERLAP
# =====================================================

def grounding_overlap_check(
    answer: str,
    context: str,
    threshold: float = 0.50
) -> bool:

    answer_words = set(re.findall(r"\w+", answer.lower()))
    context_words = set(re.findall(r"\w+", context.lower()))

    if not answer_words:
        return False

    overlap_ratio = len(answer_words & context_words) / len(answer_words)

    logger.debug("Overlap ratio: %.3f", overlap_ratio)

    return overlap_ratio >= threshold


# =====================================================
# 6️⃣ EMBEDDING CACHE
# =====================================================

def get_embedding(
    text: str,
    embedding_model: str = "nomic-embed-text"
):

    cache_key = f"{embedding_model}:{text}"

    if cache_key not in EMBEDDING_CACHE:

        EMBEDDING_CACHE[cache_key] = ollama.embeddings(
            model=embedding_model,
            prompt=text
        )["embedding"]

    return EMBEDDING_CACHE[cache_key]


# =====================================================
# 7️⃣ SEMANTIC VALIDATION
# =====================================================

def semantic_similarity_check(
    question: str,
    answer: str,
    context: str,
    threshold: float = 0.55,
    embedding_model: str = "nomic-embed-text"
) -> bool:

    qa_text = f"{question} {answer}"

    qa_emb = get_embedding(qa_text, embedding_model)
    context_emb = get_embedding(context, embedding_model)

    similarity = cosine_similarity(
        [qa_emb],
        [context_emb]
    )[0][0]

    logger.debug("Semantic similarity: %.4f", similarity)

    return similarity >= threshold


# =====================================================
# 8️⃣ MAIN ENGINE
# =====================================================

def generate_rag_dataset(
    document_text: str,
    output_path: str,
    model: str,
    difficulty: str = "medium",
    max_pairs: int = 10
) -> None:

    logger.info("Generating RAG dataset")

    word_count = len(document_text.split())

    # Adaptive QA limits
    estimated_max = max(
        3,
        min(max_pairs, word_count // 80)
    )

    if estimated_max < max_pairs:

        logger.warning(
            "Reducing max_pairs from %d to %d due to limited content",
            max_pairs,
            estimated_max
        )

        max_pairs = estimated_max

    # Auto-adjust difficulty for tiny docs
    if word_count < 300 and difficulty == "hard":

        logger.warning(
            "Document too small for hard difficulty — downgrading to medium"
        )

        difficulty = "medium"

    chunks = chunk_text(document_text)

    if not chunks:

        logger.warning("No chunks generated")
        return

    logger.info("Total Chunks: %d", len(chunks))

    existing_questions: Set[str] = set()
    dataset_rows: List[Dict[str, str]] = []

    if os.path.exists(output_path):

        existing_df = pd.read_csv(output_path)

        if "question" in existing_df.columns:

            existing_questions = set(
                existing_df["question"]
                .astype(str)
                .str.lower()
                .str.strip()
            )

    BATCH_SIZE = min(4, len(chunks))

    max_attempts = max_pairs * 3

    attempts = 0
    stagnant_attempts = 0

    total_generated_raw = 0
    total_duplicates = 0
    total_failed_overlap = 0
    total_failed_similarity = 0
    total_errors = 0

    used_chunk_sets = set()

    while len(dataset_rows) < max_pairs and attempts < max_attempts:

        attempts += 1

        chunk_start = ((attempts - 1) * BATCH_SIZE) % len(chunks)

        batch_chunks = []

        for j in range(BATCH_SIZE):

            idx = (chunk_start + j) % len(chunks)
            batch_chunks.append(chunks[idx])

        chunk_signature = tuple(batch_chunks)

        if chunk_signature in used_chunk_sets:

            stagnant_attempts += 1

            if stagnant_attempts >= 5:

                logger.warning(
                    "Stopping due to repeated chunk stagnation"
                )

                break

        used_chunk_sets.add(chunk_signature)

        logger.info(
            "Attempt %d/%d — using %d chunks (have %d/%d pairs)",
            attempts,
            max_attempts,
            len(batch_chunks),
            len(dataset_rows),
            max_pairs
        )

        added_this_round = 0

        try:

            qa_list = generate_qa_batch(
                contexts=batch_chunks,
                model=model,
                difficulty=difficulty,
            )

            total_generated_raw += len(qa_list)

            for qa in qa_list:

                if len(dataset_rows) >= max_pairs:
                    break

                context_id = qa.get("context_id", 1) - 1

                if context_id >= len(batch_chunks):
                    continue

                chunk = batch_chunks[context_id]

                question = qa["question"].strip()
                answer = qa["answer"].strip()

                normalized_question = question.lower().strip()

                if normalized_question in existing_questions:

                    total_duplicates += 1
                    continue

                if not grounding_overlap_check(answer, chunk):

                    total_failed_overlap += 1
                    continue

                if not semantic_similarity_check(
                    question,
                    answer,
                    chunk
                ):

                    total_failed_similarity += 1
                    continue

                dataset_rows.append({
                    "context": chunk,
                    "question": question,
                    "answer": answer,
                    "difficulty": difficulty,
                    "created_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                })

                existing_questions.add(normalized_question)

                added_this_round += 1

                logger.info(
                    "Added (%d/%d)",
                    len(dataset_rows),
                    max_pairs
                )

            if added_this_round == 0:
                stagnant_attempts += 1
            else:
                stagnant_attempts = 0

            if stagnant_attempts >= 5:

                logger.warning(
                    "Stopping due to no new QA generation"
                )

                break

        except Exception as e:

            logger.error(
                "Error during QA generation: %s",
                e
            )

            total_errors += 1

    # =====================================================
    # SAVE
    # =====================================================

    if dataset_rows:

        save_dataset(dataset_rows, output_path)

        logger.info(
            "Saved %d QA pairs",
            len(dataset_rows)
        )

    else:

        logger.warning("No valid QA pairs generated")

    # =====================================================
    # SUMMARY
    # =====================================================

    logger.info("===== RAG Generation Summary =====")
    logger.info("Requested: %d", max_pairs)
    logger.info("Generated (raw): %d", total_generated_raw)
    logger.info("Valid saved: %d", len(dataset_rows))
    logger.info("Duplicates skipped: %d", total_duplicates)
    logger.info("Failed overlap check: %d", total_failed_overlap)
    logger.info("Failed similarity check: %d", total_failed_similarity)
    logger.info("Generation errors: %d", total_errors)
    logger.info("Attempts used: %d/%d", attempts, max_attempts)

    fulfillment = (
        (len(dataset_rows) / max_pairs) * 100
        if max_pairs > 0 else 0
    )

    logger.info("Fulfillment: %.1f%%", fulfillment)
    logger.info("==================================")


# =====================================================
# EXAMPLE USAGE
# =====================================================

if __name__ == "__main__":

    with open("../data/document.txt", "r") as f:
        text = f.read()

    generate_rag_dataset(
        document_text=text,
        output_path="../datasets/rag_dataset_v3.csv",
        model="gemma3:4b",
        difficulty="medium",
        max_pairs=8
    )