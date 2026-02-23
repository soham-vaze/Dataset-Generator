import ollama
import pandas as pd
import os
import json
from datetime import datetime
from typing import List, Dict
import random


# ===============================
# 1️⃣ MODEL CALL
# ===============================

def call_model(model: str,
               topic: str,
               style: str,
               language: str,
               num_pairs: int,
               temperature: float) -> List[Dict]:

    dataset_schema = {
        "type": "object",
        "properties": {
            "pairs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "instruction": {"type": "string"},
                        "response": {"type": "string"}
                    },
                    "required": ["instruction", "response"]
                }
            }
        },
        "required": ["pairs"]
    }

    system_msg = (
        f"You are an expert synthetic dataset generator.\n"
        f"Generate {num_pairs} high-quality instruction-response pairs "
        f"about '{topic}' in {language}.\n"
        f"Use a {style} writing style.\n"
        f"Ensure diversity and avoid repetitive phrasing.\n"
        f"Return ONLY valid JSON following the schema."
    )

    response = ollama.chat(
        model=model,
        messages=[{'role': 'system', 'content': system_msg}],
        format=dataset_schema,
        options={"temperature": temperature}
    )

    raw_data = json.loads(response['message']['content'])
    return raw_data.get("pairs", [])


# ===============================
# 2️⃣ VALIDATION
# ===============================

def validate_pairs(pairs: List[Dict],
                   min_instruction_len: int = 20,
                   min_response_len: int = 50) -> pd.DataFrame:

    df = pd.DataFrame(pairs)

    if df.empty:
        return df

    df = df[
        (df["instruction"].str.len() >= min_instruction_len) &
        (df["response"].str.len() >= min_response_len)
    ]

    df = df.dropna(subset=["instruction", "response"])

    return df


# ===============================
# 3️⃣ DEDUPLICATION (OPTIMIZED)
# ===============================

def remove_duplicates(df: pd.DataFrame,
                      existing_instructions: set) -> pd.DataFrame:

    if df.empty:
        return df

    df = df[~df["instruction"].isin(existing_instructions)]

    return df


# ===============================
# 4️⃣ SAVE DATASET
# ===============================

def save_dataset(df: pd.DataFrame,
                 output_csv_path: str):

    file_exists = os.path.isfile(output_csv_path)

    df.to_csv(
        output_csv_path,
        mode='a',
        index=False,
        header=not file_exists
    )

    # JSONL export
    jsonl_path = output_csv_path.replace(".csv", ".jsonl")
    df.to_json(jsonl_path, orient="records", lines=True, mode='a')


# ===============================
# 5️⃣ MAIN GENERATION ENGINE
# ===============================

def generate_instruction_dataset(topic: str,
                                 output_csv_path: str,
                                 models: List[str],
                                 num_pairs: int = 5,
                                 language: str = "English",
                                 temperature: float = 0.8):

    styles = [
        "highly technical",
        "beginner-friendly",
        "problem-solving oriented",
        "conversational"
    ]

    print(f"\n🚀 Generating dataset for topic: {topic}")
    print(f"Language: {language}")
    print(f"Temperature: {temperature}\n")

    # Load existing instructions once (efficient deduplication)
    existing_instructions = set()

    if os.path.exists(output_csv_path):
        existing_df = pd.read_csv(output_csv_path)
        existing_instructions = set(existing_df["instruction"].tolist())

    total_added = 0

    for model in models:
        for style in styles:   # Diversity enforcement (no randomness)

            print(f"-> Model: {model} | Style: {style}")

            try:
                pairs = call_model(
                    model=model,
                    topic=topic,
                    style=style,
                    language=language,
                    num_pairs=num_pairs,
                    temperature=random.random()
                )

                df = validate_pairs(pairs)

                df = remove_duplicates(df, existing_instructions)

                if df.empty:
                    print("⚠ No valid new pairs generated.")
                    continue

                # Metadata
                df["model"] = model
                df["style"] = style
                df["topic"] = topic
                df["language"] = language
                df["created_at"] = datetime.utcnow().isoformat()

                save_dataset(df, output_csv_path)

                # Update in-memory set for efficiency
                existing_instructions.update(df["instruction"].tolist())

                print(f"✅ Added {len(df)} rows.")
                total_added += len(df)

            except Exception as e:
                print(f"❌ Error with {model}: {e}")

    print(f"\n🎯 Total new rows added: {total_added}")


# ===============================
# 🔥 EXAMPLE USAGE
# ===============================

if __name__ == "__main__":

    generate_instruction_dataset(
        topic="Quantum Computing",
        output_csv_path="/home/soham/dataset_generator/datasets/instr_response_v1.csv",
        models=["gemma3:1b"],
        num_pairs=10,
        language="English",
        temperature=0.85
    )