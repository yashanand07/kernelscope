import re
import time
from semantic_runtime.extractors.base import BaseExtractor
from semantic_runtime.ontology.metadata import StorageClass, ExtractionReport
from semantic_runtime.semantic_model import LocalSymbol

class LocalSymbolExtractor(BaseExtractor):
    def extract(self, source: str, context, indices, kit=None) -> ExtractionReport:
        start_time = time.perf_counter()
        warnings = []
        discovered = 0

        # Wipes out all single and multiline comment artifacts via the active kit configuration
        clean_source = kit.clean_source_code(source)

        if not kit:
            return ExtractionReport(self.__class__.__name__, 0, 0.0, ["No adaptation kit provided"])

        try:
            prof = kit.symbol_profile()
            discovered += self._extract_parameters(clean_source, context, prof)
            discovered += self._extract_locals(clean_source, context, prof)
        except Exception as e:
            warnings.append(f"Exception during symbol extraction: {str(e)}")

        duration = (time.perf_counter() - start_time) * 1000.0
        return ExtractionReport(self.__class__.__name__, discovered, duration, warnings)

    def _extract_parameters(self, source: str, context, prof) -> int:
        count = 0
        sig_match = re.search(r'\(([^)]*)\)\s*\{?', source)
        if not sig_match or not sig_match.group(1).strip() or sig_match.group(1).strip() == "void":
            return count

        params_str = sig_match.group(1)
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
            raw_type = re.sub(r'\b' + re.escape(name) + r'\b', '', param).strip()
            type_info = prof.type_parser(raw_type, "")

            context.add_local_symbol(LocalSymbol(
                name=name, type_info=type_info,
                storage=StorageClass.PARAMETER,
                declaration_line=line_num, scope_depth=0
            ))
            count += 1
        return count

    def _extract_locals(self, source: str, context, prof) -> int:
        count = 0
        in_body = False

        for line_idx, line in enumerate(source.split('\n')):
            line_num = line_idx + 1
            stripped = line.strip()

            if not in_body:
                if '{' in stripped:
                    in_body = True
                continue

            if not stripped.endswith(';'):
                continue

            match = prof.decl_pattern.match(stripped)
            if not match:
                continue

            raw_type = match.group(1).strip()
            declarators_str = match.group(2).strip()

            if raw_type.split()[-1] in prof.reserved_words:
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
                type_info = prof.type_parser(raw_type, decl_base)

                context.add_local_symbol(LocalSymbol(
                    name=name, type_info=type_info,
                    storage=StorageClass.LOCAL,
                    declaration_line=line_num, scope_depth=1
                ))
                count += 1
        return count