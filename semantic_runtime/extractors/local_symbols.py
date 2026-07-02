import re
from typing import List, Tuple, TYPE_CHECKING

# 1. Import strictly low-level domain metadata & structures
from semantic_runtime.ontology.metadata import (
    TypeDescriptor,
    StorageClass,
    ExtractionReport,
    TypeKind,
)
from semantic_runtime.semantic_model import LocalSymbol
#   from semantic_runtime.compiler.semantic_ir import SemanticExtractor

# 2. Guard high-level objects causing the loop.
# They are only parsed by type-checkers, completely ignored by Python at runtime.
if TYPE_CHECKING:
    from semantic_runtime.semantic_model import FunctionSemanticContext
    from semantic_runtime.compiler.indices import CompilerIndices

class LocalSymbolExtractor():
    """
    Phase 1 Pass: Sweeps the raw function code to populate the Local Symbol Table.
    Uses precise regex to identify parameters and locals, resolving their TypeDescriptors.
    """

    RESERVED_WORDS = {
        'return', 'goto', 'if', 'else', 'while', 'for',
        'switch', 'case', 'break', 'continue', 'sizeof'
    }

    # Matches: [Modifiers] Type [*]var1, [*]var2 = init;
    DECL_PATTERN = re.compile(
        r'^\s*'
        r'('                                      # Group 1: Type prefix
            r'(?:(?:static|const|struct|union|enum|unsigned|signed|long|short|volatile)\s+)*'
            r'[a-zA-Z_]\w*'                       # Base type name
        r')\s+'
        r'([*a-zA-Z_][^;]*)'                      # Group 2: Declarators list
        r';\s*$'
    )

    # Use string literals for the guarded types in the signature
    def extract(self, source: str, context: 'FunctionSemanticContext', indices: 'CompilerIndices') -> ExtractionReport:
        warnings = []
        discovered = 0

        try:
            discovered += self._extract_parameters(source, context)
            discovered += self._extract_locals(source, context)
        except Exception as e:
            warnings.append(f"Exception during extraction: {str(e)}")

        return ExtractionReport(
            extractor_name="LocalSymbolExtractor",
            discovered=discovered,
            warnings=warnings
        )

    def _parse_type(self, raw_type: str, declarator: str) -> TypeDescriptor:
        """Helper to convert C syntax into a rich TypeDescriptor without breaking names like 'device'."""
        qualifiers = []
        for qual in ['const', 'volatile', 'restrict']:
            if qual in raw_type:
                qualifiers.append(qual)

        pointer_level = raw_type.count('*') + declarator.count('*')
        # FIX: Safe substring cleaning using regex word boundaries to prevent matching 'device' -> 'ice'
        clean_type = raw_type
        clean_type = re.sub(r'\b(const|volatile|restrict)\b', '', clean_type)
        clean_type = clean_type.replace('*', '')

        # Determine Kind and extract pure type name using boundaries
        kind = TypeKind.BUILTIN
        type_name = clean_type.strip()

        if re.search(r'\bstruct\b', clean_type):
            kind = TypeKind.STRUCT
            type_name = re.sub(r'\bstruct\b', '', clean_type).strip()
        elif re.search(r'\benum\b', clean_type):
            kind = TypeKind.ENUM
            type_name = re.sub(r'\benum\b', '', clean_type).strip()
        elif re.search(r'\bunion\b', clean_type):
            kind = TypeKind.UNION
            type_name = re.sub(r'\bunion\b', '', clean_type).strip()
        elif clean_type.strip().endswith('_t') or clean_type.strip() not in {'int', 'char', 'void', 'long', 'short', 'float', 'double', 'unsigned', 'signed'}:
            kind = TypeKind.TYPEDEF

        return TypeDescriptor(
            type_name=type_name,
            kind=kind,
            qualifiers=qualifiers,
            pointer_level=pointer_level
        )

    def _extract_parameters(self, source: str, context: 'FunctionSemanticContext') -> int:
        count = 0
        sig_match = re.search(r'\(([^)]*)\)\s*\{?', source)
        if not sig_match:
            return count

        params_str = sig_match.group(1)
        if not params_str or params_str.strip() == "void":
            return count

        sig_start_idx = sig_match.start(1)

        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue

            param_idx = source.find(param, sig_start_idx)
            line_num = source.count('\n', 0, param_idx) + 1 if param_idx != -1 else 1

            words = re.findall(r'[a-zA-Z_]\w*', param)
            if not words:
                continue

            name = words[-1]
            # Using a regex word-boundary substitution
            raw_type = re.sub(r'\b' + re.escape(name) + r'\b', '', param).strip()
            type_info = self._parse_type(raw_type, "")

            symbol = LocalSymbol(
                name=name,
                type_info=type_info,
                storage=StorageClass.PARAMETER,
                declaration_line=line_num,
                scope_depth=0
            )

            context.add_local_symbol(symbol)
            count += 1

        return count

    def _extract_locals(self, source: str, context: 'FunctionSemanticContext') -> int:
        count = 0
        lines = source.split('\n')
        in_body = False

        for line_idx, line in enumerate(lines):
            line_num = line_idx + 1
            stripped = line.strip()

            if not in_body:
                if '{' in stripped:
                    in_body = True
                continue

            if not stripped.endswith(';'):
                continue

            match = self.DECL_PATTERN.match(stripped)
            if not match:
                continue

            raw_type = match.group(1).strip()
            declarators_str = match.group(2).strip()

            if raw_type.split()[-1] in self.RESERVED_WORDS:
                continue

            for decl in declarators_str.split(','):
                decl = decl.strip()
                if not decl:
                    continue

                decl_base = decl.split('=')[0].strip()
                name_match = re.search(r'[a-zA-Z_]\w*', decl_base)
                if not name_match:
                    continue

                name = name_match.group(0)
                type_info = self._parse_type(raw_type, decl_base)

                symbol = LocalSymbol(
                    name=name,
                    type_info=type_info,
                    storage=StorageClass.LOCAL,
                    declaration_line=line_num,
                    scope_depth=1
                )

                context.add_local_symbol(symbol)
                count += 1

        return count