import re
#import os
from pathlib import Path
from typing import List, Tuple, Any

def _remove_c_comments(text: str) -> str:
    """
    Strips C-style comments (/* ... */ and // ...) to prevent 
    rogue braces inside comments from breaking the brace counter.
    """
    pattern = re.compile(r'//.*?$|/\*.*?\*/', re.DOTALL | re.MULTILINE)
    return re.sub(pattern, '', text)

def _extract_brace_block(text: str, start_index: int) -> str:
    """
    STEP 2: Captures the initializer block using balanced brace counting.
    Starts at the opening '{' and stops at the matching '}'.
    """
    brace_depth = 0
    in_block = False
    end_index = start_index

    for i in range(start_index, len(text)):
        if text[i] == '{':
            brace_depth += 1
            in_block = True
        elif text[i] == '}':
            brace_depth -= 1
        
        # When we've entered the block and depth returns to 0, we found the end.
        if in_block and brace_depth == 0:
            end_index = i + 1
            break

    return text[start_index:end_index]


def extract_provider_dispatch_edges(
    kernel_root: str,
    profile: Any
) -> List[Tuple[str, str, str, str]]:
    """
    Extracts semantic function pointer dispatch edges from C source files.
    
    Returns:
        List of tuples: [("provider_kind", "provider_name", "operation", "concrete_function"), ...]
        Example: [("read_iter", "ext4_file_read_iter"), ...]
    """
    extracted_edges = []
    
    # STEP 3: The regex for designated initializers (e.g., .read_iter = ext4_file_read_iter)
    initializer_pattern = re.compile(r"\.(\w+)\s*=\s*([A-Za-z0-9_]+)")

    provider_patterns = [
        pattern
        for pattern in profile.provider_patterns
    ]

    for rel_path in getattr(profile, 'dispatch_provider_files', []):
        file_path = Path(kernel_root) / rel_path
        
        if not file_path.exists():
            continue

        with open(file_path, 'r', errors='ignore') as f:
            raw_content = f.read()

        # Clean comments to make brace parsing bulletproof
        clean_content = _remove_c_comments(raw_content)

        for pattern in provider_patterns:
            struct_kind = pattern.struct_type
            provider_kind = pattern.provider_kind
            # STEP 1: Find the provider block header
            # Matches: const struct file_operations ext4_file_operations = {
            # Matches: struct sched_class fair_sched_class = {
            #header_regex = rf"struct\s+{struct_kind}\s+([A-Za-z0-9_]+)\s*=\s*\{{"
            provider_blocks = []

            if pattern.macro_name:

                for match in re.finditer(
                    rf"{pattern.macro_name}\(([A-Za-z0-9_]+)\)\s*=\s*\{{",
                    clean_content
                ):
                    provider_blocks.append(
                        (
                            f"{match.group(1)}{pattern.suffix}",
                            match
                        )
                    )

            if pattern.struct_type:

                for match in re.finditer(
                    rf"(?:static\s+)?"
                    rf"(?:const\s+)?"
                    rf"struct\s+{struct_kind}\s+"
                    rf"([A-Za-z0-9_]+)"
                    rf"\s*=\s*\{{",
                    clean_content
                ):
                    provider_blocks.append(
                        (
                            match.group(1),
                            match
                        )
                    )
            
            #for header_match in re.finditer(header_regex, clean_content):
            for provider_name, header_match in provider_blocks:
                
                # The match.end() - 1 points exactly to the '{' character
                start_idx = header_match.end() - 1 
                
                # STEP 2: Balanced capture
                block = _extract_brace_block(clean_content, start_idx)

                # STEP 3 & 4: Parse designated initializers and Filter
                for assign_match in initializer_pattern.finditer(block):
                    operation = assign_match.group(1)
                    concrete_func = assign_match.group(2)

                    # STEP 4: Validate against the profile's allowed operations
                    if operation in profile.valid_dispatch_operations:
                        print(
                            f"[PROVIDER] "
                            f"{provider_name}.{operation}"
                            f" -> "
                            f"{concrete_func}"
                        )
                        
                        # STEP 5: Create the raw semantic dispatch edge data
                        #extracted_edges.append((operation, concrete_func))
                        extracted_edges.append(
                            (
                                provider_kind,  # provider kind (e.g., file_operations)
                                provider_name,
                                operation,
                                concrete_func
                            )
                        )
                        
                        # (Optional Debug: print(f"Found: {provider_name}.{operation} -> {concrete_func}"))
                        print(
                            f"[DISPATCH] "
                            f"{provider_name}.{operation}"
                            f" -> "
                            f"{concrete_func}"
                        )

    return extracted_edges