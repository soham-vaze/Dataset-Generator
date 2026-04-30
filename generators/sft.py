import logging
import os
import random
from datetime import datetime, timezone
from typing import Dict, List, Set

import pandas as pd

from generators.utils import ModelNotFoundError, call_model, extract_json, normalize_text, save_dataset

logger = logging.getLogger(__name__)


# ===============================
# QUALITY FILTER
# ===============================

def quality_filter(instruction: str, response: str) -> bool:

    if len(instruction) < 20:
        return False

    if len(response) < 50:
        return False

    if "lorem ipsum" in instruction.lower():
        return False

    return True


# ===============================
# SAVE DATASET
# ===============================

# Uses shared save_dataset from generators.utils


# ===============================
# MAIN GENERATOR
# ===============================

def generate_instruction_dataset(
    topic: str,
    output_csv_path: str,
    models: List[str],
    style: str,
    num_samples: int = 50,
    batch_size: int = 5,
    language: str = "English",
    temperature: float = 0.8
) -> None:

    logger.info("Generating dataset for topic: %s, language: %s, batch_size: %d", topic, language, batch_size)

    existing_instructions: Set[str] = set()

    # Load existing dataset for deduplication
    if os.path.exists(output_csv_path):
        existing_df = pd.read_csv(output_csv_path)
        if "instruction" in existing_df.columns:
            existing_instructions = set(
                existing_df["instruction"].astype(str).apply(normalize_text)
            )

    total_added = 0

    for model in models:

        logger.info("Using model: %s", model)

        dataset_rows: List[Dict[str, str]] = []

        attempts = 0
        max_attempts = num_samples * 5

        while len(dataset_rows) < num_samples and attempts < max_attempts:

            attempts += 1

            remaining = num_samples - len(dataset_rows)
            current_batch = min(batch_size, remaining)

            logger.info("Attempt %d — generating %d samples", attempts, current_batch)

            prompt = f"""
You are a strict JSON generator.

Generate EXACTLY {current_batch} instruction-response pairs.

Topic: {topic}
Language: {language}
Style: {style}

Rules:
- Output ONLY valid JSON
- No explanations
- No markdown
- No ```json
- Ensure valid syntax

Format:
{{
  "pairs": [
    {{
      "instruction": "string",
      "response": "string"
    }}
  ]
}}
"""

            try:
                response_text = call_model(
                    prompt=prompt,
                    model=model,
                    temperature=random.uniform(0.6, 0.9),
                )

                data = extract_json(response_text)

            except ModelNotFoundError:
                raise
            except Exception as e:
                logger.warning("JSON parse failed: %s", e)
                continue

            valid_count = 0

            for item in data.get("pairs", []):

                instruction = item.get("instruction", "").strip()
                response = item.get("response", "").strip()

                norm_inst = normalize_text(instruction)

                # Dedup
                if norm_inst in existing_instructions:
                    logger.debug("Duplicate skipped")
                    continue

                # Quality filter
                if not quality_filter(instruction, response):
                    logger.debug("Low quality skipped")
                    continue

                dataset_rows.append({
                    "instruction": instruction,
                    "response": response,
                    "model": model,
                    "style": style,
                    "topic": topic,
                    "language": language,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })

                existing_instructions.add(norm_inst)
                valid_count += 1

                logger.info("Accepted (%d/%d)", len(dataset_rows), num_samples)

                if len(dataset_rows) >= num_samples:
                    break

            if valid_count == 0:
                logger.warning("Entire batch rejected")

        # SAVE per model
        if dataset_rows:
            save_dataset(dataset_rows, output_csv_path)
            logger.info("Saved %d samples for %s", len(dataset_rows), model)
            total_added += len(dataset_rows)
        else:
            logger.warning("No valid samples for %s", model)

    logger.info("TOTAL samples added: %d", total_added)


# ===============================
# RUN
# ===============================

if __name__ == "__main__":

    generate_instruction_dataset(
        topic="Quantum Computing",
        output_csv_path="/home/soham/dataset_generator/datasets/instr_response_v2.csv",
        models=["gemma3:1b"],
        style="conversational",
        num_samples=50,
        batch_size=5,
        language="English",
        temperature=0.85
    )