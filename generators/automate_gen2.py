import json
import subprocess
import os

# Path to your requirements and your generator script
REQUIREMENTS_FILE = "req2.json"
GENERATOR_SCRIPT = "dataset2.py"
MODEL = "llama3.1:8b"

def run_automation():
    if not os.path.exists(REQUIREMENTS_FILE):
        print(f"❌ Error: {REQUIREMENTS_FILE} not found.")
        return

    with open(REQUIREMENTS_FILE, "r") as f:
        data = json.load(f)
    
    total_stories = 0

    for entry in data:
        epic = entry["epic"]
        feature = entry["feature"]
        
        for story in entry["stories"]:
            print(f"\n{'='*60}")
            print(f"🚀 PROCESSING: {story}")
            print(f"{'='*60}")
            
            command = [
                "python3", GENERATOR_SCRIPT,
                "--epic", epic,
                "--feature", feature,
                "--story", story,
                "--model", MODEL,
                "--batches", "1"
            ]
            
            try:
                # Subprocess will run and wait; if it exit with 1 (fail), it raises error
                subprocess.run(command, check=True)
                print(f"✅ Finished Story: {story}. Moving to next...")
                total_stories = total_stories + 1
            except subprocess.CalledProcessError:
                print(f"🛑 Error: Generator failed to produce valid data for {story}. Stopping.")
                return # Stop the entire loop if validation fails after all retries

    print(f"\n🏁 ALL {total_stories} STORIES and {total_stories * 4} ACCEPTANCE CRITERIAS PROCESSED SUCCESSFULLY.")

if __name__ == "__main__":
    run_automation()