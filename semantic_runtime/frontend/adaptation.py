
from abc import ABC, abstractmethod
from typing import List, Set, Dict
from semantic_runtime.frontend.normalizer import TagNormalizerRule
from semantic_runtime.frontend.profiles import (
    SynchronizationProfile,
    IteratorProfile,
    RcuProfile,
    AssignmentProfile,
    DispatchProfile
)
#yashtbd

class AdaptationKit(ABC):
    """
    The universal ecosystem contract for KernelScope 2.0.

    Acts as an isolation gate. All framework-specific syntax variations,
    macro patterns, operational conventions, and symbol categories must be
    quarantined inside implementations of this class.

    The Compiler Core consumes only this agnostic protocol interface.
    """

    @abstractmethod
    def synchronization_profile(self) -> SynchronizationProfile:
        """Returns the complete concurrency/lock ontology maps."""
        pass

    @abstractmethod
    def iterator_profile(self) -> IteratorProfile:
        """Returns the expected syntax rewrites for iteration/control loops."""
        pass

    @abstractmethod
    def rcu_profile(self) -> RcuProfile:
        """Returns the read-copy-update boundary token criteria."""
        pass

    @abstractmethod
    def assignment_profile(self) -> AssignmentProfile:
        """Returns target structural mutation qualifiers."""
        pass