import os
import json

log_path = r"C:\Users\HP\.gemini\antigravity\brain\10269afb-8e39-4d8f-9d27-1e2030317f6b\.system_generated\logs\transcript.jsonl"

if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                content = str(data)
                if "def setup_nlp" in content:
                    print("MATCH FOUND:")
                    print(content[:2000]) # Print first 2000 chars of matching step
                    print("\n" + "="*80 + "\n")
            except Exception as e:
                pass
else:
    print("Log path not found")
