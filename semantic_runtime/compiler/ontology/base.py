from abc import ABC, abstractmethod
from typing import Dict, Any

class SemanticMetadata(ABC):
    """
    Base structural contract implemented by all KernelScope ontology models.
    Forces typed semantic facts away from arbitrary representation schemas.
    """
    @property
    @abstractmethod
    def version(self) -> int:
        """Returns the schema tracking version of this specific ontology metadata."""
        pass

    @abstractmethod
    def to_json_payload(self) -> str:
        """Serializes strictly normalized internal metrics down to a passive string format."""
        pass