from semantic_runtime.frontend.tag import Tag

#yashtbd - Use noise_prefixes from adaptation kit - adaptation/linux/kit.py
class NoiseFilter:
    """Drops tags pointing to documentation, out-of-tree samples, or testing suites."""
    NOISE_PATH_PREFIXES = {
        "tools/",
        "samples/",
        "Documentation/",
    }

    @classmethod
    def is_noise(cls, tag: Tag) -> bool:
        # Filter by file path prefix
        if any(tag.file.startswith(prefix) for prefix in cls.NOISE_PATH_PREFIXES):
            return True
        return False