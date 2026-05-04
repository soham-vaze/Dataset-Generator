"""Shared utilities for all dataset generators — eliminates duplication across generator files."""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Module-level API URL — set at app startup via configure().
_api_url: str = "http://localhost:11434/api/generate"


def configure(api_url: str) -> None:
    """Set the LLM API URL. Called once during application startup."""
    global _api_url
    _api_url = api_url


class ModelNotFoundError(Exception):
    """Raised when the requested model is not available in Ollama."""
    pass


def get_api_url() -> str:
    """Return the configured Ollama API URL."""
    return _api_url


def call_model(
    prompt: str,
    model: str,
    temperature: float = 0.7,
    timeout: int = 180,
    num_predict: int = 2000,
) -> str:
    """Call the remote LLM API and return the response text."""
    api_url = get_api_url()

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }

    response = requests.post(
        api_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )

    if response.status_code == 404:
        raise ModelNotFoundError(f"Model '{model}' not found. Pull it with: ollama pull {model}")

    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

    data = response.json()

    if "response" not in data:
        raise ValueError(f"Invalid response format: {data}")

    return data["response"]


def extract_json(text: str) -> Dict[str, Any]:
    """Extract a JSON object from model output, handling markdown fences and noise."""
    text = re.sub(r"```json|```", "", text).strip()

    # Try direct parsing
    try:
        return json.loads(text)  # type: ignore[return-value]
    except (json.JSONDecodeError, ValueError):
        pass

    # Extract largest JSON block
    matches = re.findall(r"\{[\s\S]*\}", text)
    for match in reversed(matches):
        try:
            return json.loads(match)  # type: ignore[return-value]
        except (json.JSONDecodeError, ValueError):
            continue

    raise ValueError(f"JSON parsing failed:\n{text[:500]}")


def extract_json_array(text: str) -> List[Dict[str, Any]]:
    """Extract a JSON array from model output."""
    text = re.sub(r"```json|```", "", text).strip()

    # Try direct parse
    try:
        return json.loads(text)  # type: ignore[return-value]
    except (json.JSONDecodeError, ValueError):
        pass

    # Extract JSON array
    match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())  # type: ignore[return-value]

    raise ValueError(f"JSON array extraction failed:\n{text[:500]}")


def normalize_text(text: str) -> str:
    """Normalize text for deduplication (lowercase, collapse whitespace)."""
    return " ".join(text.lower().split())


def save_dataset(rows: List[Dict[str, Any]], output_path: str) -> None:
    """Append rows to CSV and JSONL files."""
    df = pd.DataFrame(rows)

    file_exists = os.path.isfile(output_path)

    df.to_csv(
        output_path,
        mode="a",
        index=False,
        header=not file_exists,
    )

    jsonl_path = output_path.replace(".csv", ".jsonl")

    df.to_json(
        jsonl_path,
        orient="records",
        lines=True,
        mode="a",
    )


def save_dataframe(df: pd.DataFrame, output_path: str) -> None:
    """Append a DataFrame to CSV and JSONL files."""
    file_exists = os.path.exists(output_path)

    df.to_csv(
        output_path,
        mode="a",
        index=False,
        header=not file_exists,
    )

    jsonl_path = output_path.replace(".csv", ".jsonl")

    df.to_json(
        jsonl_path,
        orient="records",
        lines=True,
        mode="a",
    )
