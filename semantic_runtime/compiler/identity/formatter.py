class IdentityFormatter:
    """
    Lazy Presentation Formatter. Reconstructs human-readable IR
    representations strictly on-demand for debuggers and UI components.
    """
    @staticmethod
    def to_debug_str(domain: str, file_path: str, scope: str, kind: str, symbol: str) -> str:
        return f"{domain}:{file_path}:{scope}:{kind}:{symbol}"

    @staticmethod
    def to_hex_str(node_id: int) -> str:
        """
        Converts a signed or unsigned integer NodeID into a clean,
        uniform, standard 16-character hexadecimal presentation string.
        """
        # Apply 64-bit bitmask to safely convert signed integers to raw unsigned hex format
        unsigned_raw_bits = node_id & 0xFFFFFFFFFFFFFFFF
        return f"0x{unsigned_raw_bits:016X}"