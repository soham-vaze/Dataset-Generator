import pandas as pd
import os
from typing import List
import json
from datetime import datetime
import requests
import math
import re

OLLAMA_URL = "http://10.30.1.34:11434/api/generate"


# =====================================================
# UTIL: SAVE DATASET
# =====================================================

def save_dataset(df: pd.DataFrame, output_path: str):

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
# UTIL: EXTRACT JSON FROM MODEL OUTPUT
# =====================================================

def extract_json(text: str):

    text = text.strip()

    # Remove markdown blocks
    text = text.replace("```json", "").replace("```", "")

    # Extract JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError("No JSON object found in model output")

    json_text = match.group(0)

    return json.loads(json_text)


# =====================================================
# UTIL: CALL OLLAMA API
# =====================================================

def query_model(prompt: str, model: str, temperature: float):

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }

    response = requests.post(
        OLLAMA_URL,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    return data["response"]


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
):

    labels_str = ", ".join(class_labels)

    print(f"Generating classification dataset for: {task_description}")

    batch_size = min(20, num_samples)

    total_batches = math.ceil(num_samples / batch_size)

    print(f"Using batch size {batch_size} ({total_batches} batches)")

    generated_total = 0

    for batch in range(total_batches):

        current_batch = min(batch_size, num_samples - generated_total)

        print(f"\nBatch {batch+1}/{total_batches} → generating {current_batch}")

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

        try:

            raw_output = query_model(prompt, model, temperature)

            # Debug print (helps diagnose bad responses)
            print("\n--- RAW MODEL OUTPUT ---")
            print(raw_output[:500])
            print("------------------------\n")

            data = extract_json(raw_output)

            df = pd.DataFrame(data["samples"])

        except Exception as e:

            print("⚠️ Failed to parse model output:", e)
            print("Model output was:\n", raw_output)
            continue

        df = df[df["label"].isin(class_labels)]

        df["task"] = task_description
        df["created_at"] = datetime.utcnow().isoformat()

        save_dataset(df, output_path)

        generated_total += len(df)

        print(f"Saved {len(df)} samples. Total so far: {generated_total}")

        if generated_total >= num_samples:
            break

    print(f"\n✅ Dataset generation completed. Total samples saved: {generated_total}")


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