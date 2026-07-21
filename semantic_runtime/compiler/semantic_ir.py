from config.config import app_config
from semantic_runtime.passes.relationship_builder import RelationshipBuilder
from semantic_runtime.extractors.assignment import AssignmentExtractor
import traceback
import sys
import contextlib
import time
from typing import List
from abc import ABC, abstractmethod
from semantic_runtime.extractors.call_extractor import CallExtractor
from semantic_runtime.compiler.indices import CompilerIndices
from semantic_runtime.semantic_model import FunctionSemanticContext
from semantic_runtime.extractors.iterators import IteratorExtractor
from semantic_runtime.extractors.local_symbols import LocalSymbolExtractor
from semantic_runtime.ontology.metadata import ExtractionReport
from semantic_runtime.extractors.synchronization import SynchronizationExtractor
from semantic_runtime.frontend.adaptation import AdaptationKit
from semantic_runtime.extractors.rcu_extractor import RCUExtractor
from semantic_runtime.passes.relationship_builder import RelationshipBuilder

class SemanticCompiler:
    """
    Phase 1: Compiles individual functions into semantic contexts.
    """
    def __init__(self, indices: CompilerIndices, kit: AdaptationKit):
        # The global knowledge base provided by Phase 0
        self.indices = indices
        self.kit = kit

        # The sequential pipeline of semantic passes
        self.pipeline: List[SemanticExtractor] = [
            LocalSymbolExtractor(),      # Pass 1: Discover variables and types
            IteratorExtractor(),         # Pass 2: Discover control-flow loops
            CallExtractor(),             # Pass 3: Extract standard calls
            SynchronizationExtractor(),  # Pass 4: Resolve synchronization primitives
            AssignmentExtractor(),       # Pass 5: Discover assignment semantics
            RCUExtractor()               # Pass 6: Canonical capitalization match secured
            # MacroAliasExtractor(),     # Pass 5: Resolve macros
            # DispatchExtractor(),       # Pass 6: Resolve vtables
            # LockExtractor(),           # (Future Epic)
        ]

        # Phase 1.5: Post-extraction context synthesis and graph linking passes
        self.post_pipeline = [
            RelationshipBuilder()
            # Future expansion hooks:
            # StateInferencePass(),
            # LifetimeInferencePass(),
            # CriticalRegionSynthesizer()
        ]

    def compile_function(
        self,
        symbol_id: str,
        file_path: str,
        code: str,
        start_line: int = 1,
        end_line: int = 1
    ) -> 'FunctionSemanticContext':
        """Compiles raw function string into a structured semantic frame with absolute coordinate bounds."""

        # Instantiate the context with the global source tree offsets
        context = FunctionSemanticContext(
            symbol_id=symbol_id,
            file_path=file_path,
            code=code,
            start_line=start_line,
            end_line=end_line
        )

        # 1. Stateless Fact Extraction Phase (Phase 1 Extractor Passes)
        for extractor in self.pipeline:
            try:
                events = extractor.extract(code, context, self.indices, self.kit)
            except Exception as e:
                if app_config.runtime.fail_fast:
                    print(f"\n[FATAL PIPELINE CRASH]")
                    print(f"Extractor : {extractor.__class__.__name__}")
                    print(f"Function  : {context.symbol_id}")
                    print(f"Error     : {str(e)}")
                    print("-" * 60)
                    traceback.print_exc(file=sys.stdout)
                    print("-" * 60)
                    sys.exit(1)
                else:
                    context.warnings.append(
                        f"Extractor {extractor.__class__.__name__} failed on {context.symbol_id}: {str(e)}"
                    )

        # 2. Structural Graph Handshake Phase (Phase 1.5 Context Synthesis & Relationship Building)
        for pass_ in self.post_pipeline:
            try:
                # Clean, decoupled execution pass passing the framework profile kit
                pass_.run(context, self.kit)
            except Exception as e:
                if app_config.runtime.fail_fast:
                    print(f"\n[FATAL POST-PIPELINE CRASH]")
                    print(f"Pass      : {pass_.__class__.__name__}")
                    print(f"Function  : {context.symbol_id}")
                    print(f"Error     : {str(e)}")
                    sys.exit(1)
                else:
                    context.warnings.append(
                        f"Post-Pipeline Pass {pass_.__class__.__name__} failed on {context.symbol_id}: {str(e)}"
                    )

        return context

class SemanticExtractor(ABC):
    @abstractmethod
    def extract(
        self,
        source: str,
        context: 'FunctionSemanticContext',
        indices: 'CompilerIndices',
        kit: 'AdaptationKit'
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
#          │                                ├── AssignmentMetadata
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