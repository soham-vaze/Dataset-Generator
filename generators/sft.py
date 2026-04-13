import requests
import pandas as pd
import os
import json
import re
import math
from datetime import datetime
from typing import List, Dict, Set
import random


# ===============================
# CONFIG
# ===============================

SLM_API = "http://10.30.1.34:11434/api/generate"


# ===============================
# MODEL CALL
# ===============================

def call_remote_slm(prompt: str,
                    model: str,
                    temperature: float = 0.7) -> str:

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 2000
        }
    }

    response = requests.post(
        SLM_API,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=180
    )

    # response.raise_for_status()

    # return response.json()["response"]

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text}")

    data = response.json()

    if "response" not in data:
        raise Exception(f"Invalid response format: {data}")

    return data["response"]

# ===============================
# JSON EXTRACTION (ROBUST)
# ===============================

def extract_json(text: str) -> Dict:

    text = re.sub(r"```json|```", "", text).strip()

    # Try direct parsing
    try:
        return json.loads(text)
    except:
        pass

    # Extract largest JSON block
    matches = re.findall(r"\{[\s\S]*\}", text)

    for match in reversed(matches):
        try:
            return json.loads(match)
        except:
            continue

    raise ValueError(f"JSON parsing failed:\n{text[:500]}")


# ===============================
# NORMALIZATION (DEDUP)
# ===============================

def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


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

def save_dataset(rows: List[Dict], output_path: str):

    df = pd.DataFrame(rows)

    file_exists = os.path.isfile(output_path)

    df.to_csv(
        output_path,
        mode='a',
        index=False,
        header=not file_exists
    )

    jsonl_path = output_path.replace(".csv", ".jsonl")

    df.to_json(
        jsonl_path,
        orient="records",
        lines=True,
        mode='a'
    )


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
):

    print(f"\n🚀 Generating dataset for topic: {topic}")
    print(f"Language: {language}")
    print(f"Batch size: {batch_size}\n")

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

        print(f"\n🤖 Model: {model}")

        dataset_rows = []

        attempts = 0
        max_attempts = num_samples * 5

        while len(dataset_rows) < num_samples and attempts < max_attempts:

            attempts += 1

            remaining = num_samples - len(dataset_rows)
            current_batch = min(batch_size, remaining)

            print(f"\n🔄 Attempt {attempts} → generating {current_batch}")

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
                response_text = call_remote_slm(
                    prompt=prompt,
                    model=model,
                    temperature=random.uniform(0.6, 0.9)
                )

                data = extract_json(response_text)

            except Exception as e:
                print("\n❌ JSON PARSE FAILED")
                print("----- RAW RESPONSE START -----")
                # print(response_text[:1000])
                print("----- RAW RESPONSE END -----\n")
                continue

            valid_count = 0

            for item in data.get("pairs", []):

                instruction = item.get("instruction", "").strip()
                response = item.get("response", "").strip()

                norm_inst = normalize_text(instruction)

                # Dedup
                if norm_inst in existing_instructions:
                    print("⚠ Duplicate skipped")
                    continue

                # Quality filter
                if not quality_filter(instruction, response):
                    print("⚠ Low quality skipped")
                    continue

                dataset_rows.append({
                    "instruction": instruction,
                    "response": response,
                    "model": model,
                    "style": style,
                    "topic": topic,
                    "language": language,
                    "created_at": datetime.utcnow().isoformat()
                })

                existing_instructions.add(norm_inst)
                valid_count += 1

                print(f"✅ Accepted ({len(dataset_rows)}/{num_samples})")

                if len(dataset_rows) >= num_samples:
                    break

            if valid_count == 0:
                print("⚠ Entire batch rejected")

        # SAVE per model
        if dataset_rows:
            save_dataset(dataset_rows, output_csv_path)
            print(f"\n🎯 Saved {len(dataset_rows)} samples for {model}")
            total_added += len(dataset_rows)
        else:
            print(f"\n❌ No valid samples for {model}")

    print(f"\n🚀 TOTAL samples added: {total_added}")


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