import logging
import os
from datetime import datetime, timezone
from typing import List, Set

import pandas as pd

from generators.utils import ModelNotFoundError, call_model, extract_json, normalize_text, save_dataframe

logger = logging.getLogger(__name__)


# =====================================================
# MAIN GENERATOR
# =====================================================

def generate_classification_dataset(
    task_description: str,
    class_labels: List[str],
    output_path: str,
    model: str,
    num_samples: int = 100,
    temperature: float = 0.8
) -> None:

    labels_str = ", ".join(class_labels)

    logger.info("Generating classification dataset for: %s", task_description)

    batch_size = min(20, num_samples)

    logger.info("Using batch size %d, target samples: %d", batch_size, num_samples)

    generated_total = 0
    attempts = 0
    max_attempts = num_samples * 5
    total_generated_raw = 0
    total_duplicates = 0
    total_invalid_label = 0
    total_parse_failures = 0

    existing_texts: Set[str] = set()

    # Load existing data for dedup
    if os.path.exists(output_path):
        existing_df = pd.read_csv(output_path)
        if "text" in existing_df.columns:
            existing_texts = set(
                existing_df["text"].astype(str).apply(normalize_text)
            )

    while generated_total < num_samples and attempts < max_attempts:

        attempts += 1

        remaining = num_samples - generated_total
        current_batch = min(batch_size, remaining)

        logger.info("Attempt %d/%d — generating %d (have %d/%d)",
                     attempts, max_attempts, current_batch, generated_total, num_samples)

        prompt = f"""You are a dataset generation engine. Generate exactly {current_batch} labeled text examples for the following classification task.

Task description:
{task_description}

Allowed labels (use ONLY these exact labels, no variations):
{labels_str}

STRICT RULES:
1. Each "label" value MUST be one of: {labels_str}
2. Do NOT invent new labels or modify the given labels.
3. Distribute examples roughly equally across all labels.
4. Each "text" must be realistic, diverse, and relevant to the task.
5. Do NOT repeat or paraphrase the same text.

Return ONLY valid JSON in this exact format:

{{
  "samples": [
    {{"text": "example text here", "label": "one_of_the_allowed_labels"}}
  ]
}}

Output ONLY the JSON object. No explanation, no markdown, no extra text.
"""

        raw_output = ""
        try:

            raw_output = call_model(prompt, model, temperature=temperature, timeout=120)

            logger.debug("Raw model output: %s", raw_output[:500])

            data = extract_json(raw_output)

            samples = data.get("samples", [])

        except ModelNotFoundError:
            raise
        except Exception as e:

            logger.warning("Failed to parse model output: %s", e)
            if raw_output:
                logger.debug("Model output was: %s", raw_output[:500])
            total_parse_failures += 1
            continue

        total_generated_raw += len(samples)
        valid_rows = []

        for item in samples:

            text = item.get("text", "").strip()
            label = item.get("label", "").strip()

            if not text or not label:
                continue

            # Label validation
            if label not in class_labels:
                total_invalid_label += 1
                continue

            # Dedup check
            norm_text = normalize_text(text)
            if norm_text in existing_texts:
                total_duplicates += 1
                logger.debug("Duplicate skipped")
                continue

            existing_texts.add(norm_text)

            valid_rows.append({
                "text": text,
                "label": label,
                "task": task_description,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

            if generated_total + len(valid_rows) >= num_samples:
                break

        if valid_rows:
            df = pd.DataFrame(valid_rows)
            save_dataframe(df, output_path)
            generated_total += len(valid_rows)
            logger.info("Saved %d samples. Total so far: %d/%d", len(valid_rows), generated_total, num_samples)

        if not valid_rows:
            logger.warning("Entire batch rejected (attempt %d)", attempts)

    logger.info("===== Classification Generation Summary =====")
    logger.info("Requested: %d", num_samples)
    logger.info("Generated (raw): %d", total_generated_raw)
    logger.info("Valid saved: %d", generated_total)
    logger.info("Duplicates skipped: %d", total_duplicates)
    logger.info("Invalid labels skipped: %d", total_invalid_label)
    logger.info("Parse failures: %d", total_parse_failures)
    logger.info("Attempts used: %d/%d", attempts, max_attempts)
    logger.info("Fulfillment: %.1f%%", (generated_total / num_samples * 100) if num_samples > 0 else 0)
    logger.info("=============================================")

    if generated_total < num_samples:
        logger.warning("Could not fulfill requested count: got %d/%d after %d attempts",
                        generated_total, num_samples, attempts)


# =====================================================
# EXAMPLE USAGE
# =====================================================

if __name__ == "__main__":

    generate_classification_dataset(
        task_description="classification of emails as genuine and fraudulent",
        class_labels=["genuine", "fraud"],
        output_path="/home/soham/dataset_generator/datasets/classification/classification_dataset_remotev1.csv",
        model="gemma3:4b",
        num_samples=100
    )