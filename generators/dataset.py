import argparse
import json
import logging
import os
import re
from typing import Dict, List, Set

from generators.utils import ModelNotFoundError, call_model, extract_json

logger = logging.getLogger(__name__)

# ===============================
# CONFIG
# ===============================
DEFAULT_OUTPUT_JSONL = "datasets/qa_finetuning.jsonl"

def validate_batch(results: List[Dict[str, object]]) -> bool:
    """
    Validation 1: All 4 ACs must be distinct.
    Validation 2: Each AC must have positive, negative, and edge test cases.
    """
    if len(results) != 4:
        logger.warning("Incorrect count: Expected 4 ACs, got %d.", len(results))
        return False

    seen_acs: Set[str] = set()
    required_keys = {"positive", "negative", "edge"}

    for item in results:
        # Check Uniqueness
        raw_ac = item.get("acceptance_criteria", "")
        clean_ac = " ".join(re.sub(r'[^a-zA-Z0-9\s]', '', raw_ac).lower().split())
        if clean_ac in seen_acs:
            logger.warning("Duplicate AC detected: '%s...'", clean_ac[:30])
            return False
        seen_acs.add(clean_ac)

        # Check Test Case Presence
        test_cases = item.get("test_cases", {})
        if not all(k in test_cases for k in required_keys):
            missing = required_keys - test_cases.keys()
            logger.warning("Missing test case types: %s", missing)
            return False
            
    return True

def generate_qa_dataset(
    epic: str,
    feature: str,
    story: str,
    model: str,
    num_batches: int,
    output_path: str = DEFAULT_OUTPUT_JSONL,
) -> None:
    logger.info("Generating Gherkin-style QA Cases for Story: %s", story)
    system_content = "You are an expert QA assistant. For every Acceptance Criterion provided, you must generate atleast one Positive, one Negative, and one Edge test case in a structured JSON format."

    for b in range(num_batches):
        max_retries = 5
        success = False
        
        for attempt in range(max_retries):
            logger.info("Attempt %d/%d...", attempt + 1, max_retries)
            
            prompt = f"""
You are a strict JSON generator. Generate exactly 4 UNIQUE Acceptance Criteria in Gherkin format.
CONTEXT: Epic: {epic} | Feature: {feature} | Story: {story}

Each AC must have 3 test cases: positive, negative, and edge.
OUTPUT FORMAT:
{{
  "results": [
    {{
      "acceptance_criteria": "Given... When... Then...",
      "test_cases": {{
        "positive": {{ "test_case_id": "ID_P", "scenario": "string", "expected_result": "string" }},
        "negative": {{ "test_case_id": "ID_N", "scenario": "string", "expected_result": "string" }},
        "edge": {{ "test_case_id": "ID_E", "scenario": "string", "expected_result": "string" }}
      }}
    }}
  ]
}}
"""
            try:
                raw_response = call_model(prompt, model, temperature=0.8, num_predict=3000, timeout=300)
                data = extract_json(raw_response)
                results = data.get("results", [])

                if validate_batch(results):
                    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                    with open(output_path, "a", encoding="utf-8") as f:
                        for item in results:
                            entry = {
                                "messages": [
                                    {"role": "system", "content": system_content},
                                    {"role": "user", "content": {"context": {"epic": epic, "feature": feature, "story": story}, "acceptance_criteria": item["acceptance_criteria"]}},
                                    {"role": "assistant", "content": {"test_cases": item["test_cases"]}}
                                ]
                            }
                            f.write(json.dumps(entry) + "\n")
                    logger.info("Successfully appended 4 validated ACs.")
                    success = True
                    break
            except ModelNotFoundError:
                raise
            except Exception as e:
                logger.error("Error: %s", e)

        if not success:
            raise RuntimeError(f"Failed to generate valid data for story '{story}' after {max_retries} retries")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epic", required=True)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--story", required=True)
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--batches", type=int, default=1)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_JSONL)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    generate_qa_dataset(args.epic, args.feature, args.story, args.model, args.batches, args.output)