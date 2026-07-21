from abc import ABC, abstractmethod
from typing import List
from semantic_runtime.frontend.adaptation import AdaptationKit

class BaseExtractor(ABC):
    """
    Abstract Base Class for all KernelScope Semantic Compiler passes.

    Extractors are pure, deterministic algorithmic engines that implement
    behavioral compilation passes. They are completely decoupled from ecosystem-specific
    syntax constraints, which are dynamically queried from the injected Adaptation Kit.
    """

    @abstractmethod
    def extract(self, source: str, context, indices, kit: AdaptationKit) -> List:
        """
        Executes a deterministic semantic pass over an isolated source code chunk.

        Args:
            source: The raw text string of the function body or struct initializer.
            context: The persistent FunctionSemanticContext (tracks local symbols, bounds, etc.).
            indices: The global CompilerIndices reference (provides type and collection lookup maps).
            kit: The configured AdaptationKit supplying ecosystem-specific semantic profiles.

        Returns:
            A list of instantiated SemanticMetadata nodes (e.g., LockAcquireMetadata, CallMetadata).
            If no matching concepts are discovered, returns an empty list.
        """
        pass