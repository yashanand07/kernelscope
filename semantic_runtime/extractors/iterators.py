from re import match
from typing import Optional
from semantic_runtime.semantic_model import (
    FunctionSemanticContext,
    LocalSymbol, CollectionDescriptor
)
from semantic_runtime.compiler.indices import CompilerIndices
from semantic_runtime.ontology.metadata import ExtractionReport, IterationMetadata, TraversalProperties, SourceLocation
from semantic_runtime.parser import c_patterns
#from semantic_runtime.compiler.semantic_ir import SemanticExtractor

class IteratorExtractor():
    """
    Phase 1 Pass: Discovers control-flow loops (iterators) inside a function.
    Delegates to Phase 0 (CompilerIndices) to resolve global collection semantics,
    and to the local context to resolve cursor types.
    """

    def extract(
        self,
        source: str,
        context: FunctionSemanticContext,
        indices: CompilerIndices
    ) -> ExtractionReport:

        discovered = 0
        warnings = []

        # We will define ITERATOR_PATTERN in c_patterns.py
        # It matches: `macro_name(args_string)`
        for match in c_patterns.ITERATOR_PATTERN.finditer(source):
            try:
                macro_name = match.group(1).strip()
                args_string = match.group(2).strip()

                # 1. Parse raw arguments using the C-pattern heuristics
                cursor_expr, coll_expr, member = c_patterns.parse_iterator_args(macro_name, args_string)

                # 2. Phase 1: Resolve the collection semantics
                collection_desc = self._resolve_collection(coll_expr, indices)

                # 3. Phase 2: Resolve the cursor semantics
                cursor_symbol = self._resolve_cursor(cursor_expr, context)

                # 4. Phase 3: Build the final semantic metadata
                metadata = self._synthesize_iteration(
                    context=context,
                    macro=macro_name,
                    coll_expr=coll_expr,
                    cursor_expr=cursor_expr,
                    member=member,
                    collection_desc=collection_desc,
                    cursor_symbol=cursor_symbol,
                    match_offset=match.start(),
                    source=source
                )

                context.semantic_constructs.append(metadata)
                discovered += 1

            except Exception as e:
                warnings.append(f"Failed to parse iterator {macro_name}: {str(e)}")

        return ExtractionReport(
            extractor_name="IteratorExtractor",
            discovered=discovered,
            warnings=warnings
        )

    def _resolve_collection(
        self,
        collection_expression: str,
        indices: CompilerIndices
    ) -> Optional[CollectionDescriptor]:
        """
        Queries Phase 0 indices to see if this is a known global collection.
        The index handles normalization (e.g., stripping '&').
        """
        if not collection_expression:
            return None

        return indices.collections.lookup(collection_expression)

    def _resolve_cursor(
        self,
        cursor_expression: str,
        context: FunctionSemanticContext
    ) -> Optional[LocalSymbol]:
        """
        Queries the previously populated FunctionSemanticContext to find
        the local variable acting as the cursor.
        """
        if not cursor_expression:
            return None

        # Clean the cursor name (e.g., if it has pointer math or casting,
        # though kernel cursors are usually clean identifiers)
        cursor_name = cursor_expression.strip().lstrip('*')
        return context.lookup_local(cursor_name)

    def _synthesize_iteration(
        self,
        context: FunctionSemanticContext,
        macro: str,
        coll_expr: str,
        cursor_expr: str,
        member: Optional[str],
        collection_desc: Optional[CollectionDescriptor],
        cursor_symbol: Optional[LocalSymbol],
        match_offset: int,
        source: str
    ) -> IterationMetadata:
        """
        Synthesizes the resolved components into the final semantic snapshot.
        """
        # Fallback values if the descriptor wasn't found
        coll_name = coll_expr.lstrip('&')
        coll_family = "unknown"
        coll_type = None
        coll_symbol_id = None

        # Enrich with Phase 0 data if available
        declared_by = "Unknown"
        if collection_desc:
            coll_name = collection_desc.name
            coll_family = collection_desc.collection_family
            coll_type = collection_desc.type_name
            coll_symbol_id = collection_desc.symbol_id if collection_desc.symbol_id else None
            declared_by = collection_desc.declaration_macro or "Unknown" # Map Phase 0 definition

        # Determine element type from the cursor (Phase 1 data)
        element_type = None
        if cursor_symbol:
            element_type = cursor_symbol.type_info.type_name

        # Calculate absolute line numbers using the unified context coordinates
        relative_line = source.count('\n', 0, match_offset)
        absolute_line = context.start_line + relative_line
        
        loc = SourceLocation(file=context.file_path, line=absolute_line)
        action_id = f"{context.symbol_id}#iterator:{macro}:L{absolute_line}"

        return IterationMetadata(
            semantic_id=action_id,
            location=loc,                       # <-- Replaces source_line=line_num
            source_text=match.group(0).strip(),  # Optional but great for tracing raw macros
            macro=macro,
            collection_name=coll_name,
            collection_expression=coll_expr,
            collection_symbol_id=coll_symbol_id,
            collection_family=coll_family,
            collection_type=coll_type,
            declared_by=declared_by,
            element_type=element_type,
            cursor_variable=cursor_expr,
            member_field=member,
            properties=self._decode_traversal_properties(macro)
        )

    def _decode_traversal_properties(self, macro: str) -> TraversalProperties:
        """Derives standard traversal modifiers purely from the macro name."""
        return TraversalProperties(
            deletion_safe="_safe" in macro,
            reverse="_reverse" in macro,
            rcu_protected="_rcu" in macro,
            continue_iteration="_continue" in macro or "_from" in macro
        )