import pandas as pd
import os
import json
from datetime import datetime
from typing import List
import ollama
import logging
from argostranslate import translate, package

ml = logging.getLogger("multilingual")


# =====================================================
# UTIL: SAVE DATASET
# =====================================================

def save_dataset(df: pd.DataFrame, output_path: str):
    file_exists = os.path.exists(output_path)
    print("Saving the dataset")
    df.to_csv(
        output_path,
        mode="a",
        index=False,
        header=not file_exists
    )

    jsonl_path = output_path.replace(".csv", ".jsonl")
    df.to_json(jsonl_path, orient="records", lines=True, mode="a")


# =====================================================
# UTIL: LANGUAGE NAME → ISO CODE
# =====================================================

LANGUAGE_MAP = {
    "english": "en",
    "marathi": "mr",
    "hindi": "hi",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "portuguese": "pt",
    "chinese": "zh",
}

def get_language_code(lang_name: str):
    normalized = lang_name.strip().lower()
    if normalized not in LANGUAGE_MAP:
        raise ValueError(f"Unsupported language: {lang_name}")
    return LANGUAGE_MAP[normalized]

def get_translation_model(source_lang: str, target_lang: str):
    print(f"🔎 Checking translation model for {source_lang} -> {target_lang}")

    # Step 1️⃣ Check installed languages
    installed_languages = translate.get_installed_languages()

    source = next((lang for lang in installed_languages if lang.code == source_lang), None)
    target = next((lang for lang in installed_languages if lang.code == target_lang), None)

    # Step 2️⃣ If languages not installed → try installing model
    if source is None or target is None:
        print("⚠ Required language not installed. Attempting auto-install...")

        available_packages = package.get_available_packages()

        pkg = next(
            (
                p for p in available_packages
                if p.from_code == source_lang and p.to_code == target_lang
            ),
            None
        )

        if pkg is None:
            raise ValueError(
                f"❌ No Argos model available for {source_lang} -> {target_lang}"
            )

        print(f"⬇ Installing Argos model {source_lang} -> {target_lang} ...")
        package.install_from_path(pkg.download())

        # Reload installed languages after installation
        installed_languages = translate.get_installed_languages()
        source = next((lang for lang in installed_languages if lang.code == source_lang), None)
        target = next((lang for lang in installed_languages if lang.code == target_lang), None)

    # Step 3️⃣ Final validation
    if source is None or target is None:
        raise ValueError(
            f"❌ Failed to install language model for {source_lang} -> {target_lang}"
        )

    translation = source.get_translation(target)

    if translation is None:
        raise ValueError(
            f"❌ Translation pair exists but model not properly installed for {source_lang} -> {target_lang}"
        )

    print(f"✅ Translation model ready: {source_lang} -> {target_lang}")

    return translation


# =====================================================
# MAIN FUNCTION
# =====================================================

def generate_multilingual_dataset(
    topic: str,
    source_language: str,
    target_language: str,
    output_path: str,
    model: str,
    num_samples: int = 20,
    temperature: float = 0.8
):

    source_code = get_language_code(source_language)
    target_code = get_language_code(target_language)
    print(f"Generating for topic {topic}")
    # 1️⃣ Generate ONLY source language sentences
    prompt = (
        f"Generate {num_samples} natural sentences about '{topic}'.\n"
        f"Language: {source_language}\n"
        "Return JSON list like: {\"sentences\": [\"...\"]}"
    )

    schema = {
        "type": "object",
        "properties": {
            "sentences": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["sentences"]
    }

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Generate plain text only. No JSON. No explanation."
            },
            {
                "role": "user",
                "content": (
                    f"Generate exactly {num_samples} natural sentences about '{topic}'.\n"
                    f"Language: {source_language}.\n"
                    "Return one sentence per line. Do not number them."
                )
            }
        ],
        options={"temperature": 0.5}
    )

    content = response["message"]["content"]

    if not content:
        raise ValueError("Empty model response")

    # Remove markdown if any
    content = content.strip()

    if content.startswith("```"):
        content = content.split("```")[1].strip()

    # Split sentences safely
    import re

    sentences = re.split(r'\n+|(?<=[.!?])\s+', content)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Remove accidental language label lines like "हिन्दी"
    sentences = [s for s in sentences if len(s.split()) > 3]

    # Ensure correct count
    sentences = sentences[:num_samples]

    print("Final parsed sentences:", sentences)
    print("Count:", len(sentences))

    # 2️⃣ Load Argos Translation Model
    print(f"starting translation for {source_code} -> {target_code}")
    translator = get_translation_model(source_code, target_code)

    pairs = []

    for sentence in sentences:
        translated = translator.translate(sentence)

        pairs.append({
            "source_text": sentence,
            "target_text": translated
        })

    df = pd.DataFrame(pairs)

    df["source_language"] = source_language
    df["target_language"] = target_language
    df["topic"] = topic
    df["created_at"] = datetime.utcnow().isoformat()

    save_dataset(df, output_path)

    print(f"✅ Saved {len(df)} multilingual pairs using Argos Translate.")


# =====================================================
# TEST RUN
# =====================================================

if __name__ == "__main__":

    generate_multilingual_dataset(
        topic="Corporate Life",
        source_language="english",
        target_language="hindi",
        output_path="/home/soham/dataset_generator/datasets/multilingual_dataset_v2.csv",
        model="gemma3:1b",
        temperature=0.85,
        num_samples=10
    )