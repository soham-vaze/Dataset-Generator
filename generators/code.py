import logging
import math
import os
from datetime import datetime, timezone
from typing import Dict, List, Set

import pandas as pd

from generators.utils import ModelNotFoundError, call_model, extract_json, normalize_text, save_dataset

logger = logging.getLogger(__name__)


# =====================================================
# QUALITY FILTER (OPTIONAL HOOK)
# =====================================================

def basic_quality_filter(instruction: str, code: str) -> bool:

    if len(instruction) < 20:
        return False

    if len(code) < 40:
        return False

    if "TODO" in code or "pass" in code:
        return False

    return True


# =====================================================
# MAIN GENERATOR
# =====================================================

def generate_code_dataset(
    domain: str,
    programming_language: str,
    output_path: str,
    model: str,
    num_samples: int = 50,
    batch_size: int = 5,
    temperature: float = 0.8
) -> None:

    logger.info("Generating dataset for %s (%s)", domain, programming_language)

    total_batches = math.ceil(num_samples / batch_size)
    logger.info("Batch size: %d — %d batches", batch_size, total_batches)

    dataset_rows: List[Dict[str, str]] = []

    existing_instructions: Set[str] = set()

    # Load existing data (for dedup)
    if os.path.exists(output_path):
        existing_df = pd.read_csv(output_path)
        if "instruction" in existing_df.columns:
            existing_instructions = set(
                existing_df["instruction"].astype(str).apply(normalize_text)
            )

    attempts = 0
    max_attempts = num_samples * 5

    while len(dataset_rows) < num_samples and attempts < max_attempts:

        attempts += 1

        remaining = num_samples - len(dataset_rows)
        current_batch_size = min(batch_size, remaining)

        logger.info("Batch attempt %d — generating %d", attempts, current_batch_size)

        prompt = f"""
You are a strict JSON generator.

Generate EXACTLY {current_batch_size} programming tasks.

Domain: {domain}
Language: {programming_language}

Rules:
- Output ONLY valid JSON
- Do NOT include explanations
- Do NOT include markdown
- Do NOT include ```json
- Ensure valid syntax (no trailing commas)

Format:
{{
  "pairs": [
    {{
      "instruction": "string",
      "code": "string"
    }}
  ]
}}
"""

        response_text = ""
        try:
            response_text = call_model(prompt, model, temperature=temperature)
            data = extract_json(response_text)
        except ModelNotFoundError:
            raise
        except Exception as e:
            logger.warning("JSON parse failed: %s", e)
            if response_text:
                logger.debug("Raw response: %s", response_text[:500])
            continue

        valid_count = 0

        for item in data.get("pairs", []):

            instruction = item.get("instruction", "").strip()
            code = item.get("code", "").strip()

            norm_inst = normalize_text(instruction)

            # Dedup check
            if norm_inst in existing_instructions:
                logger.debug("Duplicate skipped")
                continue

            # Quality filter
            if not basic_quality_filter(instruction, code):
                logger.debug("Low quality skipped")
                continue

            dataset_rows.append({
                "instruction": instruction,
                "code": code,
                "domain": domain,
                "language": programming_language,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

            existing_instructions.add(norm_inst)
            valid_count += 1

            logger.info("Accepted (%d/%d)", len(dataset_rows), num_samples)

            if len(dataset_rows) >= num_samples:
                break

        if valid_count == 0:
            logger.warning("Entire batch rejected")

    # SAVE
    if dataset_rows:
        save_dataset(dataset_rows, output_path)
        logger.info("Saved %d samples.", len(dataset_rows))
    else:
        logger.warning("No valid samples generated.")


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    generate_code_dataset(
        domain="Dynamic Programming",
        programming_language="Python",
        output_path="/home/soham/dataset_generator/datasets/text_code_dataset_v2.csv",
        model="llama3.1:8b",
        num_samples=50,
        batch_size=5,
        temperature=0.85
    )