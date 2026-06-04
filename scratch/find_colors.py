import os

templates_dir = r"C:\Users\HP\.gemini\antigravity\scratch\resume-analyzer\templates"
colors = ["blue", "indigo", "purple", "cyan"]

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith(".html"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for idx, line in enumerate(lines):
                for color in colors:
                    if color in line.lower():
                        print(f"{file}:{idx+1}: {line.strip()}")
