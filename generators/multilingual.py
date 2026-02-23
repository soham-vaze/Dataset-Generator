import pandas as pd
import os
from typing import List
import ollama
import json
from datetime import datetime

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
    df.to_json(jsonl_path, orient="records", lines=True, mode="a")



def generate_multilingual_dataset(
    topic: str,
    source_language: str,
    target_language: str,
    output_path: str,
    model: str,
    num_samples: int = 20,
    temperature: float = 0.8
):

    schema = {
        "type": "object",
        "properties": {
            "pairs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_text": {"type": "string"},
                        "target_text": {"type": "string"}
                    },
                    "required": ["source_text", "target_text"]
                }
            }
        }
    }

    prompt = (
        f"Generate {num_samples} parallel sentence pairs about '{topic}'.\n"
        f"Source language: {source_language}\n"
        f"Target language: {target_language}\n"
        "Ensure natural and accurate translations.\n"
        "Return JSON only."
    )

    response = ollama.chat(
        model=model,
        messages=[{"role": "system", "content": prompt}],
        format=schema,
        options={"temperature": temperature}
    )

    data = json.loads(response["message"]["content"])
    df = pd.DataFrame(data["pairs"])

    df["source_language"] = source_language
    df["target_language"] = target_language
    df["topic"] = topic
    df["created_at"] = datetime.utcnow().isoformat()

    save_dataset(df, output_path)
    print(f"✅ Saved {len(df)} multilingual pairs.")


if __name__ == "__main__":

    generate_multilingual_dataset(
        topic="Corporate Life",
        source_language="english",
        target_language="marathi",
        output_path="/home/soham/dataset_generator/datasets/multilingual_dataset_v1.csv",
        model="gemma3:1b",
        temperature=0.85,
        num_samples=10
    )