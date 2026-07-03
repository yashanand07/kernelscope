import os
import json
import re
from semantic_runtime.frontend.parser import TagParser
from semantic_runtime.frontend.noise_filter import NoiseFilter
from semantic_runtime.frontend.normalizer import NormalizerPipeline
from semantic_runtime.drivers.linux.tag_normalizers import ACPINormalizer, BPFNormalizer, ModuleNormalizer

KERNEL_ROOT = "../"
VERBOSE = False

def extract_function(file_path: str, tag_line: int) -> tuple[str, int, int]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (FileNotFoundError, UnicodeDecodeError):
        return "", 0, 0
    if tag_line < 1 or tag_line > len(lines):
        return "", 0, 0
    start = tag_line - 1
    brace, started = 0, False
    chunk, end_line = [], start + 1
    for idx, line in enumerate(lines[start:], start=start):
        chunk.append(line)
        if '{' in line:
            brace += line.count('{')
            started = True
        if '}' in line:
            brace -= line.count('}')
        if started and brace == 0:
            end_line = idx + 1
            break
    return "".join(chunk), start + 1, end_line

def extract_struct_initializer(file_path: str, symbol: str) -> tuple[str, int, int]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (FileNotFoundError, UnicodeDecodeError):
        return "", 0, 0
    pattern = re.compile(r'struct\s+.*\b' + re.escape(symbol) + r'\b.*=')
    brace, started = 0, False
    chunk, start_line, end_line = [], 0, 0
    for idx, line in enumerate(lines):
        if not started:
            if pattern.search(line):
                started = True
                start_line = idx + 1
                chunk.append(line)
                brace += line.count('{')
                brace -= line.count('}')
                if brace == 0 and ';' in line:
                    end_line = idx + 1
                    break
        else:
            chunk.append(line)
            brace += line.count('{')
            brace -= line.count('}')
            if brace == 0:
                end_line = idx + 1
                break
    return "".join(chunk), start_line, end_line

def main():
    tags_file = "tags"
    output_file = "chunks.jsonl"
    
    if not os.path.exists(tags_file):
        print(f"Error: {tags_file} missing.")
        return

    print("Parsing ctags file...")
    raw_tags = TagParser.parse_file(tags_file)
    print(f"Loaded {len(raw_tags):,} raw tags.")

    # Step 1: Execute Noise Filtration Layer
    filtered_tags = [tag for tag in raw_tags if not NoiseFilter.is_noise(tag)]
    print(f"NoiseFilter dropped out-of-tree artifacts down to {len(filtered_tags):,} tags.")

    # Step 2: Execute Polymorphic Normalization Pipeline Pass
    print("Executing Phase 0.5: Frontend Semantic Analysis...")
    linux_pipeline = NormalizerPipeline([
        ACPINormalizer(),
        BPFNormalizer(),
        ModuleNormalizer()
    ])
    
    normalized_tags, stats = linux_pipeline.execute(filtered_tags)
    print(f"Normalized down to {len(normalized_tags):,} clean structural targets.")

    # Render Frontend Telemetry Dashboard
    print("\nPhase 0: Frontend Semantic Analysis")
    print("---------------------------------------")
    print(f"Raw Tags                {stats.raw_tags:,}")
    print(f"Functions Tags          {stats.functions:,}")
    print(f"Variables Tags          {stats.variables:,}")
    print("")
    print(f"Wrappers Canonicalized  {stats.wrappers_canonicalized:,}")
    print(f"Duplicates Removed      {stats.duplicates_removed:,}")
    print("---------------------------------------")
    print(f"Canonical Tags          {stats.canonical_symbols:,}\n")

    extracted_count = 0
    with open(output_file, "w", encoding="utf-8") as out:
        for n_tag in normalized_tags:
            # If a normalizer rule returns None (like SEC attributes), it's cleanly skipped
            if not n_tag:
                continue

            disk_path = os.path.join(KERNEL_ROOT, n_tag.file)
            if not os.path.exists(disk_path):
                continue

            code, start_line, end_line = "", 0, 0

            if n_tag.kind in ("function", "f"):
                code, start_line, end_line = extract_function(disk_path, n_tag.line)
            elif n_tag.kind in ("variable", "v") and n_tag.symbol.endswith("_sched_class"):
                code, start_line, end_line = extract_struct_initializer(disk_path, n_tag.symbol)
            
            if code:
                symbol_id = f"func:{n_tag.file}:{n_tag.symbol}" if n_tag.kind in ("function", "f") else f"var:{n_tag.file}:{n_tag.symbol}"
                record = {
                    "schema_version": 2,
                    "symbol": n_tag.symbol,
                    "symbol_type": n_tag.kind,
                    "symbol_id": symbol_id,
                    "ctags_kind": n_tag.original_tag.kind,
                    "file": n_tag.file,
                    "start_line": start_line,
                    "end_line": end_line,
                    "code": code
                }
                out.write(json.dumps(record) + "\n")
                extracted_count += 1
                
                if extracted_count % 5000 == 0:
                    print(f"Extracted {extracted_count:,} chunks...")

    print(f"Extraction complete. {extracted_count:,} chunks successfully generated.")

if __name__ == "__main__":
    main()