import pandas as pd
import os
import json
import requests
import re
import math
from datetime import datetime
from typing import List, Dict, Set


# =====================================================
# CONFIG
# =====================================================

OLLAMA_URL = "http://10.30.1.34:11434/api/generate"


# =====================================================
# MODEL CALL
# =====================================================

def query_model(prompt: str, model: str, temperature: float = 0.8):

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
        OLLAMA_URL,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=180
    )

    response.raise_for_status()

    return response.json()["response"]


# =====================================================
# JSON EXTRACTION
# =====================================================

def extract_json(text: str) -> Dict:

    # Remove markdown
    text = re.sub(r"```json|```", "", text).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except:
        pass

    # Extract largest JSON block
    matches = re.findall(r"\{.*?\}", text, re.DOTALL)

    for match in reversed(matches):  # try biggest last
        try:
            return json.loads(match)
        except:
            continue

    # Fallback: try fixing common issues
    text_fixed = text.replace("\n", " ").replace("\t", " ")

    try:
        return json.loads(text_fixed)
    except:
        pass

    raise ValueError(f"JSON parsing failed:\n{text[:500]}")

# =====================================================
# NORMALIZATION (DEDUP)
# =====================================================

def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


# =====================================================
# SAVE
# =====================================================

def save_dataset(rows: List[Dict], output_path: str):

    df = pd.DataFrame(rows)

    file_exists = os.path.exists(output_path)

    df.to_csv(
        output_path,
        mode="a",
        index=False,
        header=not file_exists
    )

    jsonl_path = output_path.replace(".csv", ".jsonl")

    df.to_json(jsonl_path, orient="records", lines=True, mode="a")


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
):

    print(f"\n🚀 Generating dataset for {domain} ({programming_language})")

    total_batches = math.ceil(num_samples / batch_size)
    print(f"📦 Batch size: {batch_size} → {total_batches} batches")

    dataset_rows = []

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

        print(f"\n🔄 Batch attempt {attempts} | Generating {current_batch_size}")

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

        try:
            response_text = query_model(prompt, model, temperature)
            data = extract_json(response_text)
        except Exception as e:
            print("\n❌ JSON PARSE FAILED")
            print("----- RAW RESPONSE START -----")
            print(response_text[:1000])   # print first 1000 chars
            print("----- RAW RESPONSE END -----\n")
            continue

        valid_count = 0

        for item in data.get("pairs", []):

            instruction = item.get("instruction", "").strip()
            code = item.get("code", "").strip()

            norm_inst = normalize_text(instruction)

            # Dedup check
            if norm_inst in existing_instructions:
                print("⚠ Duplicate skipped")
                continue

            # Quality filter
            if not basic_quality_filter(instruction, code):
                print("⚠ Low quality skipped")
                continue

            dataset_rows.append({
                "instruction": instruction,
                "code": code,
                "domain": domain,
                "language": programming_language,
                "created_at": datetime.utcnow().isoformat()
            })

            existing_instructions.add(norm_inst)
            valid_count += 1

            print(f"✅ Accepted ({len(dataset_rows)}/{num_samples})")

            if len(dataset_rows) >= num_samples:
                break

        if valid_count == 0:
            print("⚠ Entire batch rejected")

    # SAVE
    if dataset_rows:
        save_dataset(dataset_rows, output_path)
        print(f"\n🎯 Saved {len(dataset_rows)} samples.")
    else:
        print("\n❌ No valid samples generated.")


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