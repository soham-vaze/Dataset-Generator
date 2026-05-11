import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
from argostranslate import package, translate

from generators.utils import ModelNotFoundError, call_model, save_dataframe

logger = logging.getLogger(__name__)


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

def get_language_code(lang_name: str) -> str:
    normalized = lang_name.strip().lower()
    if normalized not in LANGUAGE_MAP:
        raise ValueError(f"Unsupported language: {lang_name}")
    return LANGUAGE_MAP[normalized]


def get_translation_model(source_lang: str, target_lang: str) -> Any:

    logger.info("Checking translation model for %s -> %s", source_lang, target_lang)

    installed_languages = translate.get_installed_languages()

    source = next((lang for lang in installed_languages if lang.code == source_lang), None)
    target = next((lang for lang in installed_languages if lang.code == target_lang), None)

    if source is None or target is None:

        logger.warning("Required language not installed. Attempting auto-install...")

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

        logger.info("Installing Argos model %s -> %s ...", source_lang, target_lang)
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

    logger.info("Translation model ready: %s -> %s", source_lang, target_lang)

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
) -> None:

    source_code = get_language_code(source_language)
    target_code = get_language_code(target_language)

    logger.info("Generating for topic %s", topic)

    # Batch logic
    batch_size = min(20, num_samples)

    logger.info("Using batch size %d, target samples: %d", batch_size, num_samples)

    all_sentences: List[str] = []
    existing_normalized: set = set()
    attempts = 0
    max_attempts = num_samples * 5
    total_generated_raw = 0
    total_duplicates = 0
    total_short_filtered = 0
    total_parse_failures = 0

    while len(all_sentences) < num_samples and attempts < max_attempts:

        attempts += 1

        remaining = num_samples - len(all_sentences)
        current_batch = min(batch_size, remaining)

        logger.info("Attempt %d/%d — generating %d (have %d/%d)",
                     attempts, max_attempts, current_batch, len(all_sentences), num_samples)

        prompt = (
            f"Generate exactly {current_batch} natural sentences about '{topic}'.\n"
            f"Language: {source_language}.\n"
            "Return one sentence per line. Do not number them."
        )

        try:

            content = call_model(prompt, model, temperature=temperature)

        except ModelNotFoundError:
            raise
        except Exception as e:

            logger.warning("Model call failed: %s", e)
            total_parse_failures += 1
            continue

        if not content:
            logger.warning("Empty model response")
            total_parse_failures += 1
            continue

        content = content.strip()

        if content.startswith("```"):
            content = content.split("```")[1].strip()

        sentences = re.split(r'\n+|(?<=[.!?])\s+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        total_generated_raw += len(sentences)

        for s in sentences:
            if len(all_sentences) >= num_samples:
                break

            # Filter short sentences
            if len(s.split()) <= 3:
                total_short_filtered += 1
                continue

            # Dedup check
            norm = " ".join(s.lower().split())
            if norm in existing_normalized:
                total_duplicates += 1
                continue

            existing_normalized.add(norm)
            all_sentences.append(s)

        logger.debug("Parsed %d valid sentences this attempt", len(sentences))

    sentences = all_sentences[:num_samples]

    logger.info("Final sentence count: %d", len(sentences))


    # =====================================================
    # TRANSLATION (UNCHANGED)
    # =====================================================

    logger.info("Starting translation for %s -> %s", source_code, target_code)

    translator = get_translation_model(source_code, target_code)

    pairs: List[Dict[str, str]] = []

    for sentence in sentences:

        translated = translator.translate(sentence)

        pairs.append({
            "source_text": sentence,
            "target_text": translated,
        })


    df = pd.DataFrame(pairs)

    df["source_language"] = source_language
    df["target_language"] = target_language
    df["topic"] = topic
    df["created_at"] = datetime.now(timezone.utc).isoformat()

    save_dataframe(df, output_path)

    logger.info("===== Multilingual Generation Summary =====")
    logger.info("Requested: %d", num_samples)
    logger.info("Generated (raw): %d", total_generated_raw)
    logger.info("Valid saved: %d", len(pairs))
    logger.info("Duplicates skipped: %d", total_duplicates)
    logger.info("Short sentences filtered: %d", total_short_filtered)
    logger.info("Parse/call failures: %d", total_parse_failures)
    logger.info("Attempts used: %d/%d", attempts, max_attempts)
    logger.info("Fulfillment: %.1f%%", (len(pairs) / num_samples * 100) if num_samples > 0 else 0)
    logger.info("============================================")


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