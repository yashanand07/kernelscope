# Read and parse the tags file
# Test script to verify we can read the tags file and extract function symbols
# Please go through README.md for more details on how to generate the tags file and usage of this file
# Usage - python testtags.py
count = 0
printed = 0

found = {
    "schedule": False,
    "do_IRQ": False,
    "try_to_wake_up": False
}

print("Reading tags file (streaming)...\n")

with open("tags", "r", errors="ignore") as f:
    for line in f:

        if line.startswith("!"):
            continue

        parts = line.strip().split("\t")

        if len(parts) < 4:
            continue

        symbol = parts[0]
        file = parts[1]

        kind = None
        for p in parts[3:]:
            if p in {"f", "function"}:
                kind = "f"
                break

        if kind != "f":
            continue

        line_number = None
        for p in parts:
            if p.startswith("line:"):
                line_number = p.split(":")[1]
                break

        if not line_number:
            continue

        if symbol.isupper():
            continue

        # Track sanity symbols
        if symbol in found:
            found[symbol] = True

        # Only print first 10 (but keep scanning)
        if printed < 10:
            print(symbol, file, line_number)
            printed += 1

        count += 1

print(f"\nTotal functions parsed: {count:,}")

print("\nSanity checks:")
for k, v in found.items():
    print(f"{'✓' if v else '✗'} {k}")