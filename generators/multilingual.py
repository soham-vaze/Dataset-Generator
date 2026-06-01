import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Union

import pandas as pd

from generators.translation_engine import TranslationEngine
from generators.utils import ModelNotFoundError, call_model, save_dataframe

logger = logging.getLogger(__name__)


# =====================================================
# UTIL: LANGUAGE NAME → ISO CODE
# =====================================================

LANGUAGE_MAP = {
    # Indo-Aryan / Indic languages
    "english": "eng_Latn",
    "hindi": "hin_Deva",
    "marathi": "mar_Deva",
    "punjabi": "pan_Guru",
    "bengali": "ben_Beng",
    "gujarati": "guj_Gujr",
    "tamil": "tam_Taml",
    "telugu": "tel_Telu",
    "kannada": "kan_Knda",
    "malayalam": "mal_Mlym",
    "odia": "ory_Orya",
    "urdu": "urd_Arab",
    "assamese": "asm_Beng",
    "nepali": "npi_Deva",
    "sindhi": "snd_Arab",
    "sinhala": "sin_Sinh",
    # European languages
    "french": "fra_Latn",
    "german": "deu_Latn",
    "spanish": "spa_Latn",
    "portuguese": "por_Latn",
    "italian": "ita_Latn",
    "dutch": "nld_Latn",
    "polish": "pol_Latn",
    "romanian": "ron_Latn",
    "czech": "ces_Latn",
    "slovak": "slk_Latn",
    "hungarian": "hun_Latn",
    "bulgarian": "bul_Cyrl",
    "croatian": "hrv_Latn",
    "serbian": "srp_Cyrl",
    "slovenian": "slv_Latn",
    "albanian": "als_Latn",
    "greek": "ell_Grek",
    "swedish": "swe_Latn",
    "danish": "dan_Latn",
    "norwegian": "nob_Latn",
    "finnish": "fin_Latn",
    "estonian": "est_Latn",
    "latvian": "lvs_Latn",
    "lithuanian": "lit_Latn",
    "catalan": "cat_Latn",
    "ukrainian": "ukr_Cyrl",
    "russian": "rus_Cyrl",
    # Middle Eastern languages
    "arabic": "arb_Arab",
    "hebrew": "heb_Hebr",
    "turkish": "tur_Latn",
    "persian": "pes_Arab",
    # Asian languages
    "chinese": "zho_Hans",
    "japanese": "jpn_Jpan",
    "korean": "kor_Hang",
    "thai": "tha_Thai",
    "vietnamese": "vie_Latn",
    "indonesian": "ind_Latn",
    "malay": "zsm_Latn",
    "filipino": "tgl_Latn",
    "burmese": "mya_Mymr",
    "khmer": "khm_Khmr",
    "lao": "lao_Laoo",
}

def get_language_code(lang_name: str) -> str:
    """Resolve a human-readable language name to its NLLB flores200 code."""
    normalized = lang_name.strip().lower()
    if normalized not in LANGUAGE_MAP:
        raise ValueError(f"Unsupported language: {lang_name}")
    return LANGUAGE_MAP[normalized]


# =====================================================
# MAIN FUNCTION
# =====================================================

def generate_multilingual_dataset(
    topic: str,
    source_language: str,
    target_languages: Union[str, List[str]],
    output_path: str,
    model: str,
    num_samples: int = 20,
    temperature: float = 0.8,
) -> None:
    """Generate a multilingual dataset for one source language and one or more target languages.

    Source sentences are generated only once and then translated into every requested
    target language.  The resulting CSV has one row per source sentence with a dynamic
    column per target language (column name = normalised language name).

    Args:
        topic: The subject matter for sentence generation.
        source_language: Language used for generation (e.g. ``"english"``).
        target_languages: One or more target languages.  Accepts a single string
            (backward-compatible) or a list of strings.
        output_path: Destination ``.csv`` path (a ``.jsonl`` is also written alongside it).
        model: Ollama model identifier used for sentence generation.
        num_samples: Desired number of source sentences.
        temperature: Sampling temperature passed to the LLM.
    """

    # ------------------------------------------------------------------
    # 1. Normalise target_languages → deduplicated list of lowercase strs
    # ------------------------------------------------------------------
    if isinstance(target_languages, str):
        # Backward-compatible: caller may pass a single language string
        target_languages = [target_languages]

    seen_langs: set = set()
    unique_target_languages: List[str] = []
    for lang in target_languages:
        key = lang.strip().lower()
        if not key:
            continue
        if key in seen_langs:
            logger.warning("Duplicate target language ignored: '%s'", lang.strip())
            continue
        seen_langs.add(key)
        unique_target_languages.append(lang.strip())

    target_languages = unique_target_languages

    if not target_languages:
        raise ValueError("At least one target language must be specified.")

    # ------------------------------------------------------------------
    # 2. Resolve ISO codes (validates all languages upfront)
    # ------------------------------------------------------------------
    source_code = get_language_code(source_language)

    target_codes: Dict[str, str] = {}  # {normalised_lang_name: iso_code}
    for lang in target_languages:
        lang_key = lang.lower()
        target_codes[lang_key] = get_language_code(lang)

    logger.info(
        "Generating multilingual dataset | topic='%s' | source='%s' | targets=%s",
        topic, source_language, target_languages,
    )

    # ------------------------------------------------------------------
    # 3. Generate source sentences ONCE
    # ------------------------------------------------------------------
    batch_size = min(20, num_samples)
    logger.info("Batch size: %d | target samples: %d", batch_size, num_samples)

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

        logger.info(
            "Attempt %d/%d — generating %d (have %d/%d)",
            attempts, max_attempts, current_batch, len(all_sentences), num_samples,
        )

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
            logger.warning("Empty model response on attempt %d", attempts)
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

            # Deduplication
            norm = " ".join(s.lower().split())
            if norm in existing_normalized:
                total_duplicates += 1
                continue

            existing_normalized.add(norm)
            all_sentences.append(s)

        logger.debug("Parsed %d valid sentences this attempt", len(sentences))

    sentences = all_sentences[:num_samples]
    logger.info("Source sentence generation complete. Final count: %d", len(sentences))

    # ------------------------------------------------------------------
    # 4. Initialise NLLB translation engine (singleton, loaded once)
    # ------------------------------------------------------------------
    engine = TranslationEngine.get_instance()
    logger.info(
        "Translation engine ready | source=%s | targets=%s",
        source_code, list(target_codes.values()),
    )

    # ------------------------------------------------------------------
    # 5. Batch-translate all sentences into every target language
    # ------------------------------------------------------------------
    logger.info(
        "Translating %d sentence(s) into %d language(s)...",
        len(sentences), len(target_languages),
    )

    created_at = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, Any]] = []
    total_translation_failures = 0

    # Translate batch per target language for efficiency
    translations_by_lang: Dict[str, List[str]] = {}
    for lang in target_languages:
        lang_key = lang.lower()
        target_code = target_codes[lang_key]
        try:
            translations_by_lang[lang_key] = engine.translate_batch(
                sentences, source_code, target_code
            )
            logger.info(
                "Batch translated %d sentences -> %s (%s)",
                len(sentences), lang_key, target_code,
            )
        except Exception as e:
            logger.error(
                "Batch translation failed for %s -> %s: %s", source_code, target_code, e
            )
            translations_by_lang[lang_key] = [""] * len(sentences)
            total_translation_failures += len(sentences)

    # Build rows (same output schema as before)
    for idx, sentence in enumerate(sentences):
        row: Dict[str, Any] = {
            "source_text": sentence,
            "source_language": source_language.lower(),
            "topic": topic,
            "created_at": created_at,
        }

        for lang in target_languages:
            lang_key = lang.lower()
            translated = translations_by_lang[lang_key][idx]
            row[lang_key] = translated
            if translated:
                logger.debug("Translated [%s]: '%s...' -> '%s...'", lang_key, sentence[:40], translated[:40])

        rows.append(row)

    # ------------------------------------------------------------------
    # 6. Build DataFrame and persist
    # ------------------------------------------------------------------
    df = pd.DataFrame(rows)
    save_dataframe(df, output_path)

    # ------------------------------------------------------------------
    # 7. Summary logging
    # ------------------------------------------------------------------
    logger.info("===== Multilingual Generation Summary =====")
    logger.info("Topic:                   %s", topic)
    logger.info("Source language:         %s", source_language)
    logger.info("Target languages (%d):  %s", len(target_languages), target_languages)
    logger.info("Requested samples:       %d", num_samples)
    logger.info("Generated (raw):         %d", total_generated_raw)
    logger.info("Valid source sentences:  %d", len(rows))
    logger.info("Duplicates skipped:      %d", total_duplicates)
    logger.info("Short filtered:          %d", total_short_filtered)
    logger.info("LLM call failures:       %d", total_parse_failures)
    logger.info("Translation failures:    %d", total_translation_failures)
    logger.info("Attempts used:           %d/%d", attempts, max_attempts)
    logger.info(
        "Fulfillment:             %.1f%%",
        (len(rows) / num_samples * 100) if num_samples > 0 else 0,
    )
    logger.info("Output:                  %s", output_path)
    logger.info("============================================")


# =====================================================
# TEST RUN
# =====================================================

if __name__ == "__main__":

    generate_multilingual_dataset(
        topic="Corporate Life",
        source_language="english",
        target_languages=["hindi", "french", "spanish"],
        output_path="datasets/multilingual_dataset_v2.csv",
        model="gemma3:1b",
        temperature=0.85,
        num_samples=10,
    )