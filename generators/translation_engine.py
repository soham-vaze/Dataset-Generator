"""Production-grade NLLB-200 translation engine with singleton pattern and batch support."""

import logging
import threading
import time
from typing import List, Optional

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

logger = logging.getLogger(__name__)

_MODEL_NAME = "facebook/nllb-200-distilled-600M"
_MAX_LENGTH = 512
_BATCH_SIZE = 16


class TranslationEngine:
    """Thread-safe singleton NLLB-200 translation engine with lazy model loading.

    The model is loaded once on first use and shared across all subsequent calls.
    Supports both CPU and CUDA inference with automatic device detection.
    """

    _instance: Optional["TranslationEngine"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._model = None
        self._tokenizer = None
        self._device: Optional[str] = None
        self._model_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "TranslationEngine":
        """Return the singleton engine instance (double-checked locking)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_loaded(self) -> None:
        """Lazy-load the NLLB model and tokenizer on first use."""
        if self._model is not None:
            return

        with self._model_lock:
            if self._model is not None:
                return

            start = time.time()
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if self._device == "cuda" else torch.float32

            logger.info(
                "Loading NLLB translation model '%s' on device='%s' (dtype=%s)...",
                _MODEL_NAME, self._device, dtype,
            )

            self._tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                _MODEL_NAME, dtype=dtype
            ).to(self._device)
            self._model.eval()

            elapsed = time.time() - start
            logger.info(
                "NLLB translation model loaded successfully in %.2fs (device=%s)",
                elapsed, self._device,
            )

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate a single sentence from source_lang to target_lang.

        Args:
            text: The sentence to translate.
            source_lang: NLLB flores200 source language code (e.g. 'eng_Latn').
            target_lang: NLLB flores200 target language code (e.g. 'hin_Deva').

        Returns:
            Translated text string.
        """
        results = self.translate_batch([text], source_lang, target_lang)
        return results[0]

    def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        batch_size: int = _BATCH_SIZE,
    ) -> List[str]:
        """Translate a batch of sentences with internal chunking.

        Args:
            texts: List of sentences to translate.
            source_lang: NLLB flores200 source language code.
            target_lang: NLLB flores200 target language code.
            batch_size: Number of sentences per inference batch.

        Returns:
            List of translated strings (same length and order as input).
        """
        self._ensure_loaded()

        self._tokenizer.src_lang = source_lang
        all_translations: List[str] = []

        for i in range(0, len(texts), batch_size):
            chunk = texts[i: i + batch_size]

            with self._model_lock:
                inputs = self._tokenizer(
                    chunk,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=_MAX_LENGTH,
                ).to(self._device)

                target_token_id = self._tokenizer.convert_tokens_to_ids(target_lang)

                try:
                    with torch.no_grad():
                        outputs = self._model.generate(
                            **inputs,
                            forced_bos_token_id=target_token_id,
                            max_new_tokens=_MAX_LENGTH,
                        )
                except torch.cuda.OutOfMemoryError:
                    logger.warning(
                        "GPU OOM during translation batch (size=%d). "
                        "Retrying with smaller max_new_tokens...",
                        len(chunk),
                    )
                    torch.cuda.empty_cache()
                    with torch.no_grad():
                        outputs = self._model.generate(
                            **inputs,
                            forced_bos_token_id=target_token_id,
                            max_new_tokens=256,
                        )

                decoded = self._tokenizer.batch_decode(outputs, skip_special_tokens=True)
                all_translations.extend(decoded)

        return all_translations
