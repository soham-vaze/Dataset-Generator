import argparse
import json
import logging
import os
import subprocess
from typing import List

logger = logging.getLogger(__name__)

# Defaults (overridable via CLI args)
DEFAULT_REQUIREMENTS_FILE = "requirements.json"
DEFAULT_GENERATOR_SCRIPT = "dataset.py"
DEFAULT_MODEL = "llama3.1:8b"


def run_automation(
    requirements_file: str = DEFAULT_REQUIREMENTS_FILE,
    generator_script: str = DEFAULT_GENERATOR_SCRIPT,
    model: str = DEFAULT_MODEL,
) -> None:
    if not os.path.exists(requirements_file):
        logger.error("Error: %s not found.", requirements_file)
        return

    with open(requirements_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    total_stories = 0

    for entry in data:
        epic: str = entry["epic"]
        feature: str = entry["feature"]
        
        for story in entry["stories"]:
            logger.info("=" * 60)
            logger.info("PROCESSING: %s", story)
            logger.info("=" * 60)
            
            command: List[str] = [
                "python3", generator_script,
                "--epic", epic,
                "--feature", feature,
                "--story", story,
                "--model", model,
                "--batches", "1"
            ]
            
            try:
                subprocess.run(command, check=True, timeout=600)
                logger.info("Finished Story: %s. Moving to next...", story)
                total_stories = total_stories + 1
            except subprocess.CalledProcessError:
                logger.error("Generator failed to produce valid data for %s. Stopping.", story)
                return
            except subprocess.TimeoutExpired:
                logger.error("Generator timed out for %s. Stopping.", story)
                return

    logger.info("ALL %d STORIES and %d ACCEPTANCE CRITERIAS PROCESSED SUCCESSFULLY.", total_stories, total_stories * 4)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", default=DEFAULT_REQUIREMENTS_FILE, help="Path to requirements JSON file")
    parser.add_argument("--generator", default=DEFAULT_GENERATOR_SCRIPT, help="Path to generator script")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model to use")
    args = parser.parse_args()

    run_automation(args.requirements, args.generator, args.model)