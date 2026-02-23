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



def generate_classification_dataset(
    task_description: str,
    class_labels: List[str],
    output_path: str,
    model: str,
    num_samples: int = 10,
    temperature: float = 0.8
):

    labels_str = ", ".join(class_labels)

    schema = {
        "type": "object",
        "properties": {
            "samples": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "label": {"type": "string"}
                    },
                    "required": ["text", "label"]
                }
            }
        }
    }

    prompt = (
        f"Generate {num_samples} text samples for the following classification task:\n"
        f"{task_description}\n\n"
        f"Possible class labels: {labels_str}\n"
        "Ensure balanced distribution across classes.\n"
        "Return JSON only."
    )

    response = ollama.chat(
        model=model,
        messages=[{"role": "system", "content": prompt}],
        format=schema,
        options={"temperature": temperature}
    )

    data = json.loads(response["message"]["content"])
    df = pd.DataFrame(data["samples"])

    # Keep only valid labels
    df = df[df["label"].isin(class_labels)]

    df["task"] = task_description
    df["created_at"] = datetime.utcnow().isoformat()

    save_dataset(df, output_path)
    print(f"✅ Saved {len(df)} classification samples.")


# ===============================
# 🔥 EXAMPLE USAGE
# ===============================

if __name__ == "__main__":
    generate_classification_dataset(task_description="classification of emails as genuine and fraudulent",class_labels=["genuine","fraud"],output_path="/home/soham/dataset_generator/datasets/classification_dataset_v1.csv",model="gemma3:1b")