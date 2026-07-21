from typing import Optional
from semantic_runtime.frontend.normalizer import TagNormalizerRule
from semantic_runtime.frontend.tag import Tag, NormalizedTag

class ACPINormalizer(TagNormalizerRule):
    """Category 2: Normalizes trailing metadata wrappers (ACPI Exports)."""
    def normalize(self, tag: Tag) -> Optional[NormalizedTag]:
        if tag.symbol in ("ACPI_EXPORT_SYMBOL", "ACPI_EXPORT_SYMBOL_INIT"):
            canonical_name = tag.signature.strip("()")
            if canonical_name:
                return NormalizedTag(
                    symbol=canonical_name,
                    file=tag.file,
                    line=tag.line,
                    kind="function",
                    original_tag=tag
                )
        return None

class BPFNormalizer(TagNormalizerRule):
    """
    Category 3: Interprets eBPF DSL constructs.
    Extracts true names from function-generating macros and handles section attributes.
    """
    def normalize(self, tag: Tag) -> Optional[NormalizedTag]:
        # Handle Category 3: Function-Generating Macros (BPF_KSYSCALL, BPF_PROG)
        if tag.symbol.startswith("BPF_KSYSCALL") or tag.symbol.startswith("BPF_PROG"):
            canonical_name = tag.signature.strip("()")
            if canonical_name:
                return NormalizedTag(
                    symbol=canonical_name,
                    file=tag.file,
                    line=tag.line,
                    kind="function",
                    original_tag=tag
                )

        # Handle Category 3: Section Annotation Attributes (SEC)
        # We catch these here to prevent them from becoming corrupted function chunks.
        if tag.symbol == "SEC":
            # For now, we drop section attributes from generating code chunks,
            # reserving them for the AttributeExtractor stage in the future.
            return None

        return None

class ModuleNormalizer(TagNormalizerRule):
    """Category 2: Normalizes trailing subsystem lifecycle hooks (module_init, etc.)."""
    def normalize(self, tag: Tag) -> Optional[NormalizedTag]:
        if tag.symbol in ("module_init", "module_exit", "device_initcall"):
            canonical_name = tag.signature.strip("()")
            if canonical_name:
                return NormalizedTag(
                    symbol=canonical_name,
                    file=tag.file,
                    line=tag.line,
                    kind="function",
                    original_tag=tag
                )
        return None