import os
from semantic_runtime.frontend.tag import Tag

class TagParser:
    """Highly robust universal Ctags text format stream engine."""
    @staticmethod
    def parse_file(file_path: str) -> list[Tag]:
        tags = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_content in f:
                    if line_content.startswith('!_TAG_') or not line_content.strip():
                        continue
                    
                    if ';"\t' not in line_content:
                        continue
                        
                    base_info, ext_info = line_content.split(';"\t', 1)
                    base_parts = base_info.split('\t')
                    if len(base_parts) < 3:
                        continue
                        
                    symbol = base_parts[0]
                    tag_file = base_parts[1]
                    pattern = base_parts[2]
                    
                    kind = ""
                    tag_line = 0
                    extensions = {}
                    
                    ext_parts = ext_info.strip().split('\t')
                    
                    # Capture unkeyed structural kind fields if available
                    if len(ext_parts) > 0 and ':' not in ext_parts[0]:
                        kind = ext_parts[0]
                        
                    # Exhaustive key-value extension tracking
                    for part in ext_parts:
                        if ":" in part:
                            k, v = part.split(":", 1)
                            extensions[k] = v
                            if k == "line":
                                tag_line = int(v)
                            elif k == "kind":
                                kind = v
                                
                    if tag_line == 0 and "line" in extensions:
                        tag_line = int(extensions["line"])
                        
                    if tag_line > 0:
                        tags.append(Tag(
                            symbol=symbol,
                            file=tag_file,
                            line=tag_line,
                            kind=kind,
                            pattern=pattern,
                            signature=extensions.get("signature", ""),
                            typeref=extensions.get("typeref", ""),
                            extensions=extensions
                        ))
            return tags
        except FileNotFoundError:
            return []