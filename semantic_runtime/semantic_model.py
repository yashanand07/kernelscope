from re import Pattern
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from abc import abstractmethod, ABC

from semantic_runtime.ontology.metadata import (
    ExtractionReport,
    SemanticMetadata,
    StorageClass,
    TypeDescriptor,
    CollectionFamily
)


# =========================================================
# Semantic Compilation Model
#
# KernelScope 2.0
#
# Inter-function semantics
#      ↓
# SymbolIdentity
# SemanticGraph
#
# Intra-function semantics
#      ↓
# FunctionSemanticContext
#
# =========================================================


# ---------------------------------------------------------
# Local Symbol Model
# ---------------------------------------------------------

@dataclass
class LocalSymbol:
    """
    Symbol declared within a single function.

    Examples

        struct igb_ring *rx_ring;

        const char *name;

        int cpu;
    """

    name: str

    type_info: TypeDescriptor

    storage: StorageClass

    declaration_line: Optional[int]

    scope_depth: int


# ---------------------------------------------------------
# Global Collection Descriptor
#
# Compiler-side cache.
#
# Constructed once during Semantic IR generation.
#
# Never exposed directly to the LLM.
# ---------------------------------------------------------

@dataclass
class CollectionDescriptor:

    symbol_id: str

    name: str

    type_name: str
    # struct list_head

    collection_family: CollectionFamily
    # linked_list
    # hash_table
    # bitmap
    # cpu_mask
    # xarray
    # ...

    element_type: Optional[str] = None
    # struct igb_ring

    declaration_file: Optional[str] = None
    declaration_line: Optional[int] = None
    declaration_macro: Optional[str] = None




# ---------------------------------------------------------
# Function Semantic Context
#
# Persistent semantic representation of a function.
#
# This is NOT an AST.
#
# It represents runtime semantics discovered during
# compilation.
#
# PromptBuilder consumes this directly.
# ---------------------------------------------------------

@dataclass
class FunctionSemanticContext:

    #
    # Owner
    #

    symbol_id: str

    file_path: str

    #
    # Local namespace
    #

    local_symbols: Dict[str, List[LocalSymbol]] = field(
        default_factory=dict
    )

    #
    # Timeline of semantic constructs discovered inside
    # the function.
    # The list must remain ordered by source location, not by extractor execution order.

    semantic_constructs: List[SemanticMetadata] = field(
        default_factory=list
    )

    def add_local_symbol(self, symbol: LocalSymbol) -> None:
        """Appends a new declaration. Shadowed variables are pushed to the end."""
        if symbol.name not in self.local_symbols:
            self.local_symbols[symbol.name] = []
        self.local_symbols[symbol.name].append(symbol)

    def lookup_local(self, name: str) -> Optional[LocalSymbol]:
        """
        Returns the most recently encountered declaration (deepest scope).
        This policy can be upgraded later to handle exact scope boundaries.
        """
        symbols = self.local_symbols.get(name)
        return symbols[-1] if symbols else None

    def lookup_all(self, name: str) -> List[LocalSymbol]:
        """Returns the complete history of declarations for a shadowed variable."""
        return self.local_symbols.get(name, [])

    def finalize(self):

        #
        # Keep semantic constructs ordered
        #

        self.semantic_constructs.sort(
            key=lambda m: (
                m.source_line or 0,
                m.semantic_id
            )
        )
        # Later
        # self.validate()
        # self.sort()
        # self.freeze()