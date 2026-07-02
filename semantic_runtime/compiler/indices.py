from semantic_runtime.indices.collection_index import CollectionIndexBuilder
from typing import Dict, Optional
from semantic_runtime.semantic_model import CollectionDescriptor


class CompilerIndexBuilder:
    """
    Phase 0: Builds the global compiler indices from the raw chunk stream.
    """
    def __init__(self, symbol_db):
        self.indices = CompilerIndices()

        # Initialize individual index builders
        # Pass the global symbol_db so they can link SymbolIdentities
        self.builders = [
            CollectionIndexBuilder(self.indices.collections, symbol_db),
            #MacroIndexBuilder(self.indices.macros, symbol_db),
            #ProviderIndexBuilder(self.indices.providers, symbol_db)
        ]

    def process_chunk(self, file_path: str, code: str):
        """
        Routes the chunk through all Phase 0 index builders.
        """
        for builder in self.builders:
            builder.extract(file_path, code)
        # self.collection_builder.extract(file_path, code)
        # self.macro_builder.extract(file_path, code)
        # self.provider_builder.extract(file_path, code)



class CollectionIndex:
    """Rich compiler index for collections. Owns normalization."""

    def __init__(self):
        self._collections: Dict[str, CollectionDescriptor] = {}

    def add(self, descriptor: CollectionDescriptor) -> None:
        self._collections[descriptor.name] = descriptor

    def _normalize(self, expression: str) -> str:
        """Centralized normalization rules for C collection expressions."""
        # Strip address-of operators and whitespace
        return expression.lstrip('&').strip()

    def lookup(self, expression: str) -> Optional[CollectionDescriptor]:
        """Consumers pass raw expressions; the index handles resolution."""
        normalized = self._normalize(expression)
        return self._collections.get(normalized)

    def contains(self, name: str) -> bool:
        return self._normalize(name) in self._collections

    def all(self) -> Dict[str, CollectionDescriptor]:
        return self._collections.values()

    def __len__(self) -> int:
        return len(self._collections)

    def __iter__(self):
        return iter(self._collections.values())

    def __getitem__(self, key):
        return self._collections[key]

class CompilerIndices:
    """The unified registry of all Phase 0 compiler indices."""
    def __init__(self):
        self.collections = CollectionIndex()
        # self.macros = MacroIndex()
        # self.providers = ProviderIndex()