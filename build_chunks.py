import json
from pathlib import Path

LINUX_ROOT = "."

def extract_function(file_path, start_line):

    with open(file_path, "r", errors="ignore") as f:
        lines = f.readlines()

    start = int(start_line) - 1

    brace = 0
    chunk = []
    started = False

    for line in lines[start:]:

        if "{" in line:
            started = True

        if started:
            brace += line.count("{")
            brace -= line.count("}")

        chunk.append(line)

        if started and brace == 0:
            break

    return "".join(chunk)


written = 0

with open("chunks.jsonl", "w") as out:

    with open("tags", "r", errors="ignore") as f:

        for line in f:

            if line.startswith("!"):
                continue

            parts = line.split("\t")

            if len(parts) < 5:
                continue

            symbol = parts[0]
            file = parts[1]
            kind = parts[3]

            if kind != "f":
                continue

            line_number = parts[4].split(":")[1]

            file_path = Path(LINUX_ROOT) / file

            if not file_path.exists():
                continue

            code = extract_function(file_path, line_number)

            if not code.strip():
                continue

            record = {
                "symbol": symbol,
                "file": file,
                "code": code
            }

            out.write(json.dumps(record) + "\n")

            written += 1

            if written % 1000 == 0:
                print("written:", written)

print("done:", written)