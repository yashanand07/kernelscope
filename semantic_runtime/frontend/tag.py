from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass(slots=True)
class Tag:
    """Raw structural token extracted directly from a universal ctags stream."""
    symbol: str
    file: str
    line: int
    kind: str
    pattern: str = ""
    signature: str = ""
    typeref: str = ""
    extensions: Dict[str, str] = field(default_factory=dict)

@dataclass(slots=True)
class NormalizedTag:
    """A verified canonical tag emitted from the normalization pipeline layer."""
    symbol: str
    file: str
    line: int
    kind: str
    original_tag: Tag