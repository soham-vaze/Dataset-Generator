import logging
import math
import os
from datetime import datetime, timezone
from typing import List

import pandas as pd

from generators.utils import ModelNotFoundError, call_model, extract_json, save_dataframe

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

    total_batches = math.ceil(num_samples / batch_size)

    logger.info("Using batch size %d (%d batches)", batch_size, total_batches)

    generated_total = 0

    for batch in range(total_batches):

        current_batch = min(batch_size, num_samples - generated_total)

        logger.info("Batch %d/%d — generating %d", batch + 1, total_batches, current_batch)

        prompt = f"""
Generate {current_batch} examples for a text classification dataset.

Task:
{task_description}

Possible labels:
{labels_str}

Return ONLY valid JSON in the format:

{{
 "samples": [
   {{"text": "...", "label": "..."}}
 ]
}}

Ensure balanced labels.
"""

        raw_output = ""
        try:

            raw_output = call_model(prompt, model, temperature=temperature, timeout=120)

            logger.debug("Raw model output: %s", raw_output[:500])

            data = extract_json(raw_output)

            df = pd.DataFrame(data["samples"])

        except ModelNotFoundError:
            raise
        except Exception as e:

            logger.warning("Failed to parse model output: %s", e)
            if raw_output:
                logger.debug("Model output was: %s", raw_output[:500])
            continue

        df = df[df["label"].isin(class_labels)]

        df["task"] = task_description
        df["created_at"] = datetime.now(timezone.utc).isoformat()

        save_dataframe(df, output_path)

        generated_total += len(df)

        logger.info("Saved %d samples. Total so far: %d", len(df), generated_total)

        if generated_total >= num_samples:
            break

    logger.info("Dataset generation completed. Total samples saved: %d", generated_total)


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