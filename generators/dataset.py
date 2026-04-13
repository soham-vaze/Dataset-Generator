import requests
import json
import re
import os
import argparse
from typing import List, Dict

# ===============================
# CONFIG
# ===============================
SLM_API = "http://10.30.1.34:11434/api/generate"
OUTPUT_JSONL = "/home/soham/dataset_generator/datasets/qa_finetuning_v1.jsonl"

def call_remote_slm(prompt: str, model: str) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.8, "num_predict": 3000}
    }
    response = requests.post(SLM_API, json=payload, timeout=300)
    return response.json()["response"]

def extract_json(text: str) -> Dict:
    text = re.sub(r"```json|```", "", text).strip()
    matches = re.findall(r"\{[\s\S]*\}", text)
    for match in reversed(matches):
        try:
            return json.loads(match)
        except:
            continue
    raise ValueError("JSON parsing failed")

def validate_batch(results: List[Dict]) -> bool:
    """
    Validation 1: All 4 ACs must be distinct.
    Validation 2: Each AC must have positive, negative, and edge test cases.
    """
    if len(results) != 4:
        print(f"⚠️ Incorrect count: Expected 4 ACs, got {len(results)}.")
        return False

    seen_acs = set()
    required_keys = {"positive", "negative", "edge"}

    for item in results:
        # Check Uniqueness
        raw_ac = item.get("acceptance_criteria", "")
        clean_ac = " ".join(re.sub(r'[^a-zA-Z0-9\s]', '', raw_ac).lower().split())
        if clean_ac in seen_acs:
            print(f"⚠️ Duplicate AC detected: '{clean_ac[:30]}...'")
            return False
        seen_acs.add(clean_ac)

        # Check Test Case Presence
        test_cases = item.get("test_cases", {})
        if not all(k in test_cases for k in required_keys):
            missing = required_keys - test_cases.keys()
            print(f"⚠️ Missing test case types: {missing}")
            return False
            
    return True

def generate_qa_dataset(epic, feature, story, model, num_batches):
    print(f"🚀 Generating Gherkin-style QA Cases for Story: {story}")
    system_content = "You are an expert QA assistant. For every Acceptance Criterion provided, you must generate exactly one Positive, one Negative, and one Edge test case in a structured JSON format."

    for b in range(num_batches):
        max_retries = 5 # Increased retries for stricter validation
        success = False
        
        for attempt in range(max_retries):
            print(f"🔄 Attempt {attempt+1}/{max_retries}...")
            
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
                raw_response = call_remote_slm(prompt, model)
                data = extract_json(raw_response)
                results = data.get("results", [])

                if validate_batch(results):
                    with open(OUTPUT_JSONL, "a") as f:
                        for item in results:
                            entry = {
                                "messages": [
                                    {"role": "system", "content": system_content},
                                    {"role": "user", "content": {"context": {"epic": epic, "feature": feature, "story": story}, "acceptance_criteria": item["acceptance_criteria"]}},
                                    {"role": "assistant", "content": {"test_cases": item["test_cases"]}}
                                ]
                            }
                            f.write(json.dumps(entry) + "\n")
                    print(f"✅ Successfully appended 4 validated ACs.")
                    success = True
                    break
            except Exception as e:
                print(f"❌ Error: {e}")

        if not success:
            exit(1) # Signal failure to the orchestrator

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epic", required=True)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--story", required=True)
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--batches", type=int, default=1)
    args = parser.parse_args()

    generate_qa_dataset(args.epic, args.feature, args.story, args.model, args.batches)