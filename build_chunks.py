import json
import re
from pathlib import Path

LINUX_ROOT = "."
debug = False

def extract_struct_initializer(
    file_path,
    symbol
):

    with open(file_path, "r", errors="ignore") as f:
        lines = f.readlines()

    started = False
    brace = 0
    chunk = []

    for idx, line in enumerate(lines):

        normalized = line.strip()

        #
        # Match actual initializer definition
        #
        if not started:

            if debug:
                if "DEFINE_SCHED_CLASS(fair)" in normalized:
                    print("MACRO LINE in file at line num", idx + 1, file_path, ":", normalized)
            #
            # direct definition
            #
            direct_match = (
                symbol in normalized
                and re.search(r"\s=\s", normalized)
                and "{" in normalized
            )
           
            macro_name = None
           
            if symbol.endswith("_sched_class"):
                macro_name = symbol.replace(
                    "_sched_class",
                    ""
                )
            #
            # macro-generated scheduler class
            #
            macro_match = (
                macro_name
                and f"DEFINE_SCHED_CLASS({macro_name})" in normalized
                and re.search(r"\s=\s", normalized)
                and "{" in normalized
            )

            if not (direct_match or macro_match):
                continue

            started = True
            if debug:
                if direct_match:
                    print(
                        f"[DIRECT MATCH] line={idx + 1} "
                        f"symbol={symbol} "
                        f"text={normalized}"
                    )

            if debug:
                if macro_match:
                    print(
                        f"[MACRO MATCH] line={idx + 1} "
                        f"symbol={symbol} "
                        f"text={normalized}"
                    )

            if debug:
                if "DEFINE_SCHED_CLASS(fair)" in normalized:
                    print(
                        "FOUND INITIALIZER at line num", idx + 1, file_path, ":",
                        normalized
                    )

        if started:
            brace += line.count("{")
            brace -= line.count("}")
            chunk.append(line)

        if started and brace == 0:
            if debug:
                print(
                    f"[EXTRACTED CHARSbreak] "
                    f"symbol={symbol} "
                    f"size={len(''.join(chunk))}"
                    f" (lines {idx + 1 - len(chunk) + 1} to {idx + 1})"
                )
            break

    result = "".join(chunk)

    if debug:
        print(
            f"[EXTRACTED CHARS] "
            f"symbol={symbol} "
            f"size={len(result)}"
            f" (lines {idx + 1 - len(chunk) + 1} to {idx + 1})"
        )

    return result


def extract_function(file_path, start_line):

    #print(f"Extracting function from {file_path}:{start_line}")
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
            kind = parts[3].strip()
            metadata = {}

            if "fair_sched_class" in symbol:
                if debug:
                    print(
                        "FOUND TAG:",
                        symbol,
                        kind,
                        file,
                        line.strip()
                    )

            for item in parts[4:]:
                if ":" not in item:
                    continue

                key, value = item.split(":", 1)
                metadata[key] = value

            line_number = metadata.get("line")
            if not line_number:
                continue

            if kind not in {"f", "v"}:
                continue

            file_path = Path(LINUX_ROOT) / file

            if not file_path.exists():
                continue

            if kind == "f":
                code = extract_function(file_path, line_number)
            elif (
                kind == "v"
                and symbol.endswith("_sched_class")
            ):
                code = extract_struct_initializer(
                    file_path,
                    symbol
                )
            else:
                continue

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