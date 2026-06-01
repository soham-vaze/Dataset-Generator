"""Multilingual Fine-Tuning Dataset Generator.

Generates high-quality multilingual translation datasets specifically designed
for LoRA/QLoRA fine-tuning of multilingual LLMs.

Output format (JSONL):
    {"instruction": "Translate English to Hindi", "input": "How are you?", "output": "आप कैसे हैं?"}

Key features:
    - Dynamic language pair configuration (any pair, any direction)
    - Semantic anchor groups via pivot language for cross-lingual alignment
    - Bidirectional translation support
    - Paraphrase generation for semantic diversity
    - Domain-based diverse sentence generation
    - Near-duplicate filtering (Jaccard similarity)
    - Balanced samples across translation directions
    - Train / validation / test / zero-shot splitting
    - Zero-shot evaluation pairs (never appear in training)
    - Configurable semantic domains, sizes, temperature

Architecture:
    1. Choose a pivot language (English if available, else first source)
    2. Generate diverse sentences in pivot language across configured domains
    3. Optionally generate paraphrases for additional diversity
    4. Translate all sentences to every required language via NLLB-200
    5. Build instruction-input-output records for each configured pair
    6. Deduplicate, balance, split, and save
"""

import logging
import random
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

import pandas as pd

from generators.multilingual import LANGUAGE_MAP, get_language_code
from generators.translation_engine import TranslationEngine
from generators.utils import ModelNotFoundError, call_model, normalize_text, save_dataframe

logger = logging.getLogger(__name__)


# =====================================================
# DEFAULT CONFIGURATION
# =====================================================

DEFAULT_DOMAINS = [
    "daily conversation",
    "navigation",
    "weather",
    "reminders",
    "entertainment",
    "technical instructions",
    "emergency assistance",
    "scheduling",
    "device control",
]

DEFAULT_SPLIT_RATIO = (0.8, 0.1, 0.1)


# =====================================================
# INPUT PARSING
# =====================================================

def parse_language_pairs(pairs_str: str) -> List[Tuple[str, str]]:
    """Parse comma-separated directed language pairs.

    Input format:  ``"English-Hindi, Hindi-English, English-Marathi"``
    Returns:       ``[("English", "Hindi"), ("Hindi", "English"), ("English", "Marathi")]``

    Raises:
        ValueError: If a pair is malformed or contains empty language names.
    """
    if not pairs_str or not pairs_str.strip():
        return []

    pairs: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()

    for pair in pairs_str.split(","):
        pair = pair.strip()
        if not pair:
            continue

        parts = pair.split("-", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid language pair format: '{pair}'. "
                "Expected 'SourceLanguage-TargetLanguage' (e.g. 'English-Hindi')."
            )

        src = parts[0].strip()
        tgt = parts[1].strip()

        if not src or not tgt:
            raise ValueError(f"Empty language name in pair: '{pair}'")

        key = (src.lower(), tgt.lower())
        if key not in seen:
            seen.add(key)
            pairs.append((src, tgt))

    return pairs


# =====================================================
# INTERNAL HELPERS
# =====================================================

def _collect_unique_languages(
    training_pairs: List[Tuple[str, str]],
    zero_shot_pairs: List[Tuple[str, str]],
) -> List[str]:
    """Collect all unique languages mentioned across all pairs (order-preserving)."""
    seen: Set[str] = set()
    languages: List[str] = []

    for src, tgt in training_pairs + zero_shot_pairs:
        for lang in (src, tgt):
            key = lang.strip().lower()
            if key not in seen:
                seen.add(key)
                languages.append(lang.strip())

    return languages


def _choose_pivot_language(languages: List[str]) -> str:
    """Choose the pivot language for base sentence generation.

    Prefers English if available (best LLM generation quality), otherwise
    falls back to the first language in the list.
    """
    for lang in languages:
        if lang.lower() == "english":
            return lang
    return languages[0]


def _generate_domain_sentences(
    domain: str,
    language: str,
    model: str,
    count: int,
    temperature: float,
    existing_normalized: Set[str],
) -> List[str]:
    """Generate diverse sentences for a specific domain using the LLM.

    Returns deduplicated sentences that pass minimum quality checks.
    """
    sentences: List[str] = []
    batch_size = min(20, count)
    attempts = 0
    max_attempts = count * 5

    while len(sentences) < count and attempts < max_attempts:
        attempts += 1
        remaining = count - len(sentences)
        current_batch = min(batch_size, remaining)

        prompt = (
            f"Generate exactly {current_batch} diverse, natural sentences about '{domain}'.\n"
            f"Language: {language}.\n\n"
            "Requirements:\n"
            "- Each sentence must be unique in meaning and structure.\n"
            "- Mix formal and informal styles.\n"
            "- Include questions, statements, commands, and exclamations.\n"
            "- Vary sentence length from short to medium.\n"
            "- Cover different aspects and sub-topics of the domain.\n"
            "- Include emotional expressions, polite requests, and casual phrases.\n"
            "- Do NOT repeat similar sentence patterns.\n"
            "- Do NOT number the sentences.\n"
            "- One sentence per line.\n"
            "- Each sentence should be self-contained and natural.\n"
        )

        try:
            content = call_model(prompt, model, temperature=temperature)
        except ModelNotFoundError:
            raise
        except Exception as e:
            logger.warning("Model call failed for domain '%s' (attempt %d): %s", domain, attempts, e)
            continue

        if not content:
            continue

        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1].strip()

        raw_lines = re.split(r"\n+", content)
        raw_lines = [line.strip() for line in raw_lines if line.strip()]

        # Clean numbering artefacts
        cleaned: List[str] = []
        for line in raw_lines:
            line = re.sub(r"^\d+[\.\)\-:]\s*", "", line).strip()
            # Remove quotes wrapping entire sentence
            if len(line) >= 2 and line[0] in ('"', "'", "\u201c") and line[-1] in ('"', "'", "\u201d"):
                line = line[1:-1].strip()
            if line:
                cleaned.append(line)

        for s in cleaned:
            if len(sentences) >= count:
                break

            # Filter very short sentences
            if len(s.split()) <= 3:
                continue

            # Deduplication
            norm = normalize_text(s)
            if norm in existing_normalized:
                continue

            existing_normalized.add(norm)
            sentences.append(s)

    return sentences


def _generate_paraphrases(
    sentences: List[str],
    language: str,
    model: str,
    count_per_sentence: int,
    temperature: float,
    existing_normalized: Set[str],
) -> List[str]:
    """Generate semantic paraphrases of existing sentences using the LLM.

    Returns deduplicated paraphrases that differ from the originals.
    """
    if count_per_sentence <= 0 or not sentences:
        return []

    paraphrases: List[str] = []
    batch_size = min(10, len(sentences))

    for i in range(0, len(sentences), batch_size):
        batch = sentences[i : i + batch_size]
        numbered = "\n".join(f"{j + 1}. {s}" for j, s in enumerate(batch))

        prompt = (
            f"For each sentence below, generate {count_per_sentence} paraphrase(s) "
            f"that convey the same meaning using different words and structure.\n"
            f"Language: {language}.\n\n"
            f"Sentences:\n{numbered}\n\n"
            "Requirements:\n"
            "- Preserve the original meaning exactly.\n"
            "- Use different vocabulary and sentence structure.\n"
            "- Mix formal and informal rephrasing.\n"
            "- Return paraphrases only, one per line.\n"
            "- Do NOT include the original sentences.\n"
            "- Do NOT number or label the paraphrases.\n"
        )

        try:
            content = call_model(prompt, model, temperature=min(temperature + 0.1, 1.0))
        except ModelNotFoundError:
            raise
        except Exception as e:
            logger.warning("Paraphrase generation failed: %s", e)
            continue

        if not content:
            continue

        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1].strip()

        raw = re.split(r"\n+", content)
        raw = [line.strip() for line in raw if line.strip()]

        for s in raw:
            s = re.sub(r"^\d+[\.\)\-:]\s*", "", s).strip()
            if len(s) >= 2 and s[0] in ('"', "'", "\u201c") and s[-1] in ('"', "'", "\u201d"):
                s = s[1:-1].strip()

            if not s or len(s.split()) <= 3:
                continue

            norm = normalize_text(s)
            if norm in existing_normalized:
                continue

            existing_normalized.add(norm)
            paraphrases.append(s)

    return paraphrases


def _near_duplicate_filter(
    records: List[Dict[str, Any]],
    threshold: float = 0.85,
) -> List[Dict[str, Any]]:
    """Remove near-duplicate records using Jaccard token-overlap on the ``input`` field.

    Two records whose input tokens have a Jaccard similarity >= *threshold*
    AND share the same translation direction are considered near-duplicates.
    The first occurrence is kept.
    """
    if not records:
        return records

    filtered: List[Dict[str, Any]] = []
    # Group by direction so that duplicates are only detected within the same pair
    seen_by_direction: Dict[str, List[Set[str]]] = defaultdict(list)

    for record in records:
        direction = record.get("_direction", "")
        input_tokens = set(normalize_text(record["input"]).split())

        is_dup = False
        for existing_tokens in seen_by_direction[direction]:
            if not input_tokens or not existing_tokens:
                continue
            intersection = input_tokens & existing_tokens
            union = input_tokens | existing_tokens
            jaccard = len(intersection) / len(union) if union else 0.0
            if jaccard >= threshold:
                is_dup = True
                break

        if not is_dup:
            seen_by_direction[direction].append(input_tokens)
            filtered.append(record)

    return filtered


def _balance_records(
    records: List[Dict[str, Any]],
    direction_key: str = "_direction",
) -> List[Dict[str, Any]]:
    """Down-sample records so that every translation direction has equal representation.

    Records within each direction are shuffled before truncation to avoid ordering bias.
    """
    by_direction: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_direction[r.get(direction_key, "")].append(r)

    if not by_direction:
        return records

    min_count = min(len(v) for v in by_direction.values())

    balanced: List[Dict[str, Any]] = []
    for recs in by_direction.values():
        random.shuffle(recs)
        balanced.extend(recs[:min_count])

    return balanced


def _split_records(
    records: List[Dict[str, Any]],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
) -> List[Dict[str, Any]]:
    """Assign a ``split`` label (train / validation / test) to each record.

    Records are shuffled before splitting so that the distribution is random.
    """
    random.shuffle(records)
    n = len(records)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)

    for i, r in enumerate(records):
        if i < train_end:
            r["split"] = "train"
        elif i < val_end:
            r["split"] = "validation"
        else:
            r["split"] = "test"

    return records


# =====================================================
# MAIN PUBLIC API
# =====================================================

def generate_multilingual_ft_dataset(
    training_pairs: List[Tuple[str, str]],
    zero_shot_pairs: List[Tuple[str, str]],
    domains: List[str],
    output_path: str,
    model: str,
    num_samples_per_pair: int = 50,
    temperature: float = 0.8,
    split_ratio: Tuple[float, float, float] = DEFAULT_SPLIT_RATIO,
) -> None:
    """Generate a multilingual fine-tuning dataset for LoRA/QLoRA training.

    The output is a CSV (with a companion JSONL) containing rows in the schema::

        instruction | input | output | source_language | target_language | domain | split | created_at

    The JSONL is directly usable for fine-tuning (instruction / input / output columns).

    Pipeline overview:
        1. Validate all languages against NLLB-200 language map.
        2. Choose a *pivot* language (English preferred) for LLM sentence generation.
        3. Generate diverse sentences across configured semantic domains.
        4. Optionally generate paraphrases for additional diversity.
        5. Translate all sentences to every required language via NLLB-200.
        6. Build ``instruction / input / output`` records for each configured pair.
        7. Deduplicate (exact + near-duplicate via Jaccard similarity).
        8. Balance records across translation directions.
        9. Split training records into train / validation / test.
        10. Mark zero-shot records separately (never appear in training).
        11. Save combined output.

    Args:
        training_pairs: Directed pairs for training, e.g.
            ``[("English", "Hindi"), ("Hindi", "English")]``.
        zero_shot_pairs: Directed pairs for evaluation only (never in training),
            e.g. ``[("Hindi", "Marathi")]``.
        domains: Semantic domains for sentence generation (e.g. ``["daily conversation"]``).
        output_path: Destination ``.csv`` path (a ``.jsonl`` is written alongside).
        model: Ollama model identifier for LLM sentence generation.
        num_samples_per_pair: Desired number of samples *per translation direction*.
        temperature: Sampling temperature for LLM calls.
        split_ratio: ``(train, validation, test)`` ratios summing to 1.0.

    Raises:
        ValueError: If no pairs are provided or a language is unsupported.
        RuntimeError: If sentence generation produces zero results.
    """
    if not training_pairs and not zero_shot_pairs:
        raise ValueError("At least one training or zero-shot language pair must be specified.")

    if not domains:
        domains = list(DEFAULT_DOMAINS)

    # ------------------------------------------------------------------
    # 1. Validate all languages
    # ------------------------------------------------------------------
    all_languages = _collect_unique_languages(training_pairs, zero_shot_pairs)
    for lang in all_languages:
        get_language_code(lang)  # raises ValueError for unsupported languages

    pivot_language = _choose_pivot_language(all_languages)
    pivot_code = get_language_code(pivot_language)

    all_pairs = training_pairs + zero_shot_pairs

    logger.info(
        "Multilingual FT | pivot='%s' | training_pairs=%d | zero_shot_pairs=%d | domains=%s",
        pivot_language, len(training_pairs), len(zero_shot_pairs), domains,
    )

    # ------------------------------------------------------------------
    # 2. Generate diverse sentences in the pivot language across domains
    # ------------------------------------------------------------------
    sentences_per_domain = max(5, num_samples_per_pair // len(domains))
    existing_normalized: Set[str] = set()
    all_base_sentences: List[str] = []
    sentence_domains: List[str] = []

    logger.info(
        "Generating ~%d sentences per domain across %d domain(s)...",
        sentences_per_domain, len(domains),
    )

    for domain in domains:
        domain_sentences = _generate_domain_sentences(
            domain=domain,
            language=pivot_language,
            model=model,
            count=sentences_per_domain,
            temperature=temperature,
            existing_normalized=existing_normalized,
        )
        all_base_sentences.extend(domain_sentences)
        sentence_domains.extend([domain] * len(domain_sentences))
        logger.info("Domain '%s': generated %d sentences", domain, len(domain_sentences))

    if not all_base_sentences:
        raise RuntimeError(
            "Failed to generate any source sentences. "
            "Check model availability and try again."
        )

    # ------------------------------------------------------------------
    # 3. Generate paraphrases for additional diversity
    # ------------------------------------------------------------------
    if len(all_base_sentences) < num_samples_per_pair:
        paraphrase_target = min(2, max(1, num_samples_per_pair // max(len(all_base_sentences), 1)))
        paraphrases = _generate_paraphrases(
            sentences=all_base_sentences,
            language=pivot_language,
            model=model,
            count_per_sentence=paraphrase_target,
            temperature=temperature,
            existing_normalized=existing_normalized,
        )
        all_base_sentences.extend(paraphrases)
        sentence_domains.extend(["paraphrase"] * len(paraphrases))
        logger.info("Generated %d paraphrases (total sentences: %d)", len(paraphrases), len(all_base_sentences))

    # ------------------------------------------------------------------
    # 4. Translate to all required languages via NLLB-200
    # ------------------------------------------------------------------
    engine = TranslationEngine.get_instance()

    # Determine which languages need translation from the pivot
    target_lang_keys: Set[str] = set()
    for src, tgt in all_pairs:
        if src.lower() != pivot_language.lower():
            target_lang_keys.add(src.lower())
        if tgt.lower() != pivot_language.lower():
            target_lang_keys.add(tgt.lower())

    # Translation matrix: {lang_key: [translated_sentences]}
    translations: Dict[str, List[str]] = {pivot_language.lower(): list(all_base_sentences)}

    for lang_key in sorted(target_lang_keys):
        target_code = get_language_code(lang_key)
        try:
            translated = engine.translate_batch(all_base_sentences, pivot_code, target_code)
            translations[lang_key] = translated
            logger.info("Translated %d sentences → %s (%s)", len(translated), lang_key, target_code)
        except Exception as e:
            logger.error("Translation to %s failed: %s", lang_key, e)
            translations[lang_key] = [""] * len(all_base_sentences)

    # ------------------------------------------------------------------
    # 5. Build instruction / input / output records
    # ------------------------------------------------------------------
    created_at = datetime.now(timezone.utc).isoformat()

    def _build_records(pairs: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for src_lang, tgt_lang in pairs:
            src_key = src_lang.strip().lower()
            tgt_key = tgt_lang.strip().lower()

            src_texts = translations.get(src_key, [])
            tgt_texts = translations.get(tgt_key, [])

            if not src_texts or not tgt_texts:
                logger.warning("Missing translations for %s → %s, skipping", src_lang, tgt_lang)
                continue

            for idx in range(min(len(src_texts), len(tgt_texts))):
                src_text = src_texts[idx]
                tgt_text = tgt_texts[idx]

                if not src_text or not tgt_text:
                    continue

                domain = sentence_domains[idx] if idx < len(sentence_domains) else "general"
                records.append({
                    "instruction": f"Translate {src_lang.strip()} to {tgt_lang.strip()}",
                    "input": src_text,
                    "output": tgt_text,
                    "source_language": src_key,
                    "target_language": tgt_key,
                    "domain": domain,
                    "_direction": f"{src_key}->{tgt_key}",
                    "created_at": created_at,
                })
        return records

    training_records = _build_records(training_pairs)
    zero_shot_records = _build_records(zero_shot_pairs)

    logger.info("Raw records — training: %d | zero-shot: %d", len(training_records), len(zero_shot_records))

    # ------------------------------------------------------------------
    # 6. Deduplicate (exact + near-duplicate)
    # ------------------------------------------------------------------
    training_records = _near_duplicate_filter(training_records)
    zero_shot_records = _near_duplicate_filter(zero_shot_records)
    logger.info("After dedup — training: %d | zero-shot: %d", len(training_records), len(zero_shot_records))

    # ------------------------------------------------------------------
    # 7. Balance across directions
    # ------------------------------------------------------------------
    training_records = _balance_records(training_records)
    logger.info("After balancing — training: %d", len(training_records))

    # ------------------------------------------------------------------
    # 8. Split training records into train / val / test
    # ------------------------------------------------------------------
    train_r, val_r, test_r = split_ratio
    training_records = _split_records(training_records, train_r, val_r, test_r)

    # Mark zero-shot records
    for r in zero_shot_records:
        r["split"] = "zero_shot"

    # ------------------------------------------------------------------
    # 9. Combine, clean internal fields, and persist
    # ------------------------------------------------------------------
    all_records = training_records + zero_shot_records

    # Remove internal bookkeeping field
    for r in all_records:
        r.pop("_direction", None)

    random.shuffle(all_records)

    if not all_records:
        raise RuntimeError(
            "No records produced after filtering. "
            "Try increasing num_samples_per_pair or adding more domains."
        )

    df = pd.DataFrame(all_records)

    # Ensure clean column order
    column_order = [
        "instruction", "input", "output",
        "source_language", "target_language",
        "domain", "split", "created_at",
    ]
    df = df[[c for c in column_order if c in df.columns]]

    save_dataframe(df, output_path)

    # ------------------------------------------------------------------
    # 10. Summary
    # ------------------------------------------------------------------
    logger.info("===== Multilingual FT Generation Summary =====")
    logger.info("Training pairs:       %s", [(s, t) for s, t in training_pairs])
    logger.info("Zero-shot pairs:      %s", [(s, t) for s, t in zero_shot_pairs])
    logger.info("Domains:              %s", domains)
    logger.info("Pivot language:       %s", pivot_language)
    logger.info("Base sentences:       %d", len(all_base_sentences))
    logger.info("Total records:        %d", len(all_records))

    if "split" in df.columns:
        split_counts = df["split"].value_counts().to_dict()
        for split_name, count in sorted(split_counts.items()):
            logger.info("  Split %-12s: %d", split_name, count)

    direction_counts = (
        df.apply(lambda r: f"{r['source_language']} → {r['target_language']}", axis=1)
        .value_counts()
        .to_dict()
    )
    for direction, count in sorted(direction_counts.items()):
        logger.info("  Direction %-20s: %d", direction, count)

    logger.info("Output:               %s", output_path)
    logger.info("===============================================")
