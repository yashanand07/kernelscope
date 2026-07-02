import contextlib
import time
from typing import List
from abc import ABC, abstractmethod
from semantic_runtime.compiler.indices import CompilerIndices
from semantic_runtime.semantic_model import FunctionSemanticContext
from semantic_runtime.extractors.iterators import IteratorExtractor
from semantic_runtime.extractors.local_symbols import LocalSymbolExtractor
from semantic_runtime.ontology.metadata import ExtractionReport

class SemanticCompiler:
    """
    Phase 1: Compiles individual functions into semantic contexts.
    """
    def __init__(self, indices: CompilerIndices):
        # The global knowledge base provided by Phase 0
        self.indices = indices

        # The sequential pipeline of semantic passes
        self.pipeline: List[SemanticExtractor] = [
            LocalSymbolExtractor(),      # Pass 1: Discover variables and types
            IteratorExtractor(),         # Pass 2: Discover control-flow loops
            # CallExtractor(),             # Pass 3: Extract standard calls
            # MacroAliasExtractor(),       # Pass 4: Resolve macros
            # DispatchExtractor(),         # Pass 5: Resolve vtables
            # LockExtractor(),           # (Future Epic)
            # StateMutationExtractor(),  # (Future Epic)
        ]

    def compile_function(self, symbol_id: str, file_path: str, code: str) -> 'FunctionSemanticContext':
        context = FunctionSemanticContext(symbol_id=symbol_id, file_path=file_path)

        for extractor in self.pipeline:
            # Automatic profiling wrapping the extractor execution
            start_time = time.perf_counter()

            report = extractor.extract(code, context, self.indices)

            end_time = time.perf_counter()
            report.duration_ms = (end_time - start_time) * 1000.0

            # Here we could log the report:
            # print(f"✓ {report.extractor_name} | {report.discovered} found | {report.duration_ms:.2f} ms")
            # Keep a reference to the report on the context object
            if not hasattr(context, '_reports_cached'):
                context._reports_cached = []
            context._reports_cached.append(report)

        return context

class SemanticExtractor(ABC):
    @abstractmethod
    def extract(
        self,
        source: str,
        context: 'FunctionSemanticContext',
        indices: 'CompilerIndices'
    ) -> ExtractionReport:
        """
        Analyzes function code, enriches the context, and returns telemetry.
        """
        pass
# FunctionSemanticContext doesn't know anything about Linux.

# LocalSymbol doesn't know anything about Linux.

# IterationMetadata doesn't know anything about Linux.

# Even CollectionDescriptor only knows about collection families.

# The Linux-specific knowledge now lives in:

# Iterator extractors
# Provider extractors
# Macro extractors
# Profiles
#                         Source Code
#                          │
#          ┌───────────────┴────────────────┐
#          │                                │
#          ▼                                ▼
#   SymbolIdentity                 FunctionSemanticContext
#          │                                │
#          │                                ├── LocalSymbol
#          │                                ├── IterationMetadata
#          │                                ├── LockMetadata
#          │                                ├── StateMutationMetadata
#          │                                ├── ConfigBranchMetadata
#          │                                └── ...
#          │
#          ▼
#   SemanticGraph
#          │
#          ▼
#  Runtime Reconstruction
#          │
#          ▼
#  RuntimeExecutionGraph
#          │
#          ▼
#  Prompt Builder / UI / Mermaid