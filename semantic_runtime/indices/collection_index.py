import re
import time
from semantic_runtime.semantic_model import CollectionDescriptor
from semantic_runtime.ontology.metadata import (
    CollectionPattern,
    CollectionFamily,
    ExtractionReport
)

class CollectionIndexBuilder:
    """
    Phase 0 Builder: Sweeps source code to discover globally declared collections.
    """
    # Use string literal type hint to avoid compile-time import cycles
    def __init__(self, collection_index: "CollectionIndex", symbol_db: dict):
        self.collection_index = collection_index
        self.symbol_db = symbol_db

    PATTERNS = [
        CollectionPattern(
            regex=re.compile(r'\bLIST_HEAD\s*\(\s*([A-Za-z0-9_]+)\s*\)'),
            family=CollectionFamily.LINKED_LIST,
            type_name="struct list_head",
            macro_name="LIST_HEAD"
        ),
        CollectionPattern(
            regex=re.compile(r'\bDECLARE_HASHTABLE\s*\(\s*([A-Za-z0-9_]+)\s*,'),
            family=CollectionFamily.HASH_TABLE,
            type_name="DECLARE_HASHTABLE", # Kernel typedef equivalent
            macro_name="DECLARE_HASHTABLE"
        ),
        CollectionPattern(
            regex=re.compile(r'\bDEFINE_XARRAY(?:_FLAGS|_ALLOC)?\s*\(\s*([A-Za-z0-9_]+)\s*\)'),
            family=CollectionFamily.XARRAY,
            type_name="struct xarray",
            macro_name="DEFINE_XARRAY"
        ),
        CollectionPattern(
            regex=re.compile(r'\bDEFINE_IDR\s*\(\s*([A-Za-z0-9_]+)\s*\)'),
            family=CollectionFamily.IDR,
            type_name="struct idr",
            macro_name="DEFINE_IDR"
        ),
        CollectionPattern(
            regex=re.compile(r'\bDECLARE_BITMAP\s*\(\s*([A-Za-z0-9_]+)\s*,'),
            family=CollectionFamily.BITMAP,
            type_name="unsigned long[]",
            macro_name="DECLARE_BITMAP"
        )
    ]

    def extract(self, file_path: str, source: str) -> ExtractionReport:
        start_time = time.perf_counter()
        discovered = 0
        warnings = []

        try:
            for pattern in self.PATTERNS:
                for match in pattern.regex.finditer(source):
                    collection_name = match.group(1)

                    # Optional: Bind to global SymbolIdentity if it exists
                    symbol_ref = None
                    if collection_name in self.symbol_db:
                        # Assuming symbol_db maps to a list of identities
                        symbol_ref = self.symbol_db[collection_name][0]

                    descriptor = CollectionDescriptor(
                        symbol_id=symbol_ref,
                        name=collection_name,
                        type_name=pattern.type_name,
                        collection_family=pattern.family,
                        declaration_file=file_path,
                        declaration_macro=pattern.macro_name,
                        element_type=None # Defer complex element inference
                    )

                    self.collection_index.add(descriptor)
                    discovered += 1

        except Exception as e:
            warnings.append(f"Failed to parse collections in {file_path}: {str(e)}")

        duration = (time.perf_counter() - start_time) * 1000.0

        return ExtractionReport(
            extractor_name="CollectionIndexBuilder",
            discovered=discovered,
            warnings=warnings,
            duration_ms=duration
        )