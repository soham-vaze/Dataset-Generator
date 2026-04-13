import pandas as pd
import os
import json
from datetime import datetime
from typing import List
import logging
import requests
import math
from argostranslate import translate, package

ml = logging.getLogger("multilingual")

OLLAMA_URL = "http://10.30.1.34:11434/api/generate"


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

    df.to_json(
        jsonl_path,
        orient="records",
        lines=True,
        mode="a"
    )


# =====================================================
# UTIL: MODEL CALL
# =====================================================

def query_model(prompt: str, model: str):

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(
        OLLAMA_URL,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=180
    )

    response.raise_for_status()

    data = response.json()

    return data["response"]


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
    "albanian": "sq",
    "arabic": "ar",
    "bengali": "bn",
    "bulgarian": "bg",
    "catalan": "ca",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "estonian": "et",
    "filipino": "tl",
    "finnish": "fi",
    "greek": "el",
    "hebrew": "he",
    "hungarian": "hu",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "korean": "ko",
    "latin": "la",
    "latvian": "lv",
    "lithuanian": "lt",
    "malay": "ms",
    "norwegian": "no",
    "polish": "pl",
    "romanian": "ro",
    "russian": "ru",
    "serbian": "sr",
    "slovak": "sk",
    "slovenian": "sl",
    "swedish": "sv",
    "thai": "th",
    "turkish": "tr",
    "ukrainian": "uk",
    "vietnamese": "vi"
}

def get_language_code(lang_name: str):
    normalized = lang_name.strip().lower()
    if normalized not in LANGUAGE_MAP:
        raise ValueError(f"Unsupported language: {lang_name}")
    return LANGUAGE_MAP[normalized]


def get_translation_model(source_lang: str, target_lang: str):

    print(f"🔎 Checking translation model for {source_lang} -> {target_lang}")

    installed_languages = translate.get_installed_languages()

    source = next((lang for lang in installed_languages if lang.code == source_lang), None)
    target = next((lang for lang in installed_languages if lang.code == target_lang), None)

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

        installed_languages = translate.get_installed_languages()

        source = next((lang for lang in installed_languages if lang.code == source_lang), None)
        target = next((lang for lang in installed_languages if lang.code == target_lang), None)

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

    # Batch logic
    batch_size = min(20, num_samples)
    total_batches = math.ceil(num_samples / batch_size)

    print(f"Using batch size {batch_size} ({total_batches} batches)")

    all_sentences = []

    for batch in range(total_batches):

        current_batch = min(batch_size, num_samples - len(all_sentences))

        print(f"\nBatch {batch+1}/{total_batches} → generating {current_batch}")

        prompt = (
            f"Generate exactly {current_batch} natural sentences about '{topic}'.\n"
            f"Language: {source_language}.\n"
            "Return one sentence per line. Do not number them."
        )

        try:

            content = query_model(prompt, model)

        except Exception as e:

            print("⚠ Model call failed:", e)
            continue

        if not content:
            print("⚠ Empty model response")
            continue

        content = content.strip()

        if content.startswith("```"):
            content = content.split("```")[1].strip()

        import re

        sentences = re.split(r'\n+|(?<=[.!?])\s+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        sentences = [s for s in sentences if len(s.split()) > 3]

        sentences = sentences[:current_batch]

        print("Parsed:", sentences)

        all_sentences.extend(sentences)

        if len(all_sentences) >= num_samples:
            break


    sentences = all_sentences[:num_samples]

    print("Final sentence count:", len(sentences))


    # =====================================================
    # TRANSLATION (UNCHANGED)
    # =====================================================

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
        num_samples=50
    )