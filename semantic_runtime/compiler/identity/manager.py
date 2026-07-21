from semantic_runtime.compiler.identity.hashing import HashProvider
from semantic_runtime.compiler.identity.vocabulary import VocabularyManager
from semantic_runtime.compiler.identity.formatter import IdentityFormatter

class IdentityManager:
    """
    The central entry façade for the KernelScope Identity Layer.
    Coordinates token interning, canonical derivation, and lazy formatting.
    """
    def __init__(self, vocabulary_db: str = "ks_cache/dictionary.ks"):
        self.vocab = VocabularyManager(vocabulary_db)
        self.formatter = IdentityFormatter()

    def derive_node_id(self, domain: str, file_path: str, scope: str, symbol: str, kind: str) -> int:
        """Generates a stable, deterministic 64-bit integer identity for a node."""
        signature = f"{domain}:{file_path}:{scope}:{symbol}:{kind}"
        return HashProvider.compute_uint64_hash(signature)

    def intern_file(self, path: str) -> int:
        return self.vocab.intern_file(path)

    def intern_symbol(self, name: str) -> int:
        return self.vocab.intern_symbol(name)

    def intern_primitive(self, string: str) -> int:
        return self.vocab.intern_primitive(string)

    def format_debug_ir(self, domain: str, file_path: str, scope: str, kind: str, symbol: str) -> str:
        return self.formatter.to_debug_str(domain, file_path, scope, kind, symbol)