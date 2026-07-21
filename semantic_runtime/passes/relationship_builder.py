import enum
import time
from dataclasses import dataclass
from semantic_runtime.ontology.metadata import SemanticDomain

class RelationshipType(enum.Enum):
    # Existing Invariants
    DESCRIBES = "describes"
    WRITES    = "writes"
    CONTAINS  = "contains"

    # Newly Formalized Constitutional Invariants
    MATCHES   = "matches"
    PROTECTS  = "protects"

@dataclass(slots=True)
class SemanticRelationship:
    """Ontology Edge: A first-class, uniquely addressable directed graph entity."""
    relationship_id: str  # rel:file:line:type:slug
    relationship_type: RelationshipType
    source_semantic_id: str
    target_semantic_id: str

class RelationshipBuilder:
    def __init__(self):
        pass

    def run(self, context, kit=None) -> int:
        links_created = 0
        timeline = context.semantic_constructs

        # ────────────────────────────────────────────────────────────────
        # PASS 1: Global Symbol Table Write Linking (Your Original Pass)
        # ────────────────────────────────────────────────────────────────
        for obj in timeline:
            if obj.domain == SemanticDomain.ASSIGNMENT:
                if getattr(obj, 'resolved_symbol', None) and obj.resolved_symbol in context.local_symbols:
                    clean_sym_id = context.symbol_id.replace("func:", "")
                    symbol_target_uri = f"sym:{context.file_path}:{clean_sym_id}:{obj.resolved_symbol}"
                    edge_id = f"rel:{context.file_path}:{obj.location.line}:writes:{obj.resolved_symbol}"

                    context.relationships.append(SemanticRelationship(
                        relationship_id=edge_id,
                        relationship_type=RelationshipType.WRITES,
                        source_semantic_id=obj.semantic_id,
                        target_semantic_id=symbol_target_uri
                    ))
                    links_created += 1

        # ────────────────────────────────────────────────────────────────
        # PASS 2: Line Coordinate Aggregation for Overlap (Your Original Pass)
        # ────────────────────────────────────────────────────────────────
        line_map = {}
        for obj in timeline:
            line_map.setdefault(obj.location.line, []).append(obj)

        for line, items in line_map.items():
            if len(items) < 2:
                continue

            sync_nodes = [i for i in items if i.domain == SemanticDomain.SYNCHRONIZATION]
            call_nodes = [i for i in items if i.domain == SemanticDomain.CALL]

            for sync in sync_nodes:
                for call in call_nodes:
                    if call.target_function in sync.semantic_id or sync.primitive in call.target_function:
                        edge_id = f"rel:{context.file_path}:{line}:describes:{call.target_function}"

                        context.relationships.append(SemanticRelationship(
                            relationship_id=edge_id,
                            relationship_type=RelationshipType.DESCRIBES,
                            source_semantic_id=sync.semantic_id,
                            target_semantic_id=call.semantic_id
                        ))
                        links_created += 1

        # ────────────────────────────────────────────────────────────────
        # PASS 3: Level 3 Concurrency Boundary Tracking (Decoupled Scope Synthesis)
        # ────────────────────────────────────────────────────────────────
        if kit:
            sync_prof = kit.synchronization_profile() if hasattr(kit, 'synchronization_profile') else None
            rcu_prof = kit.rcu_profile() if hasattr(kit, 'rcu_profile') else None

            # State tracking stack for active open concurrency guard boundaries
            active_guards = []

            for idx, node in enumerate(timeline):
                node_id = node.semantic_id
                is_opening = False
                is_closing = False

                # 1. Framework-Blind Category Role Evaluation
                if node.domain == SemanticDomain.SYNCHRONIZATION and sync_prof:
                    primitive = getattr(node, 'primitive', '')
                    if sync_prof.is_acquire(primitive):
                        is_opening = True
                    elif sync_prof.is_release(primitive):
                        is_closing = True

                elif node.domain == SemanticDomain.RCU and rcu_prof:
                    api = getattr(node, 'api', '')
                    if rcu_prof.is_reader_enter(api):
                        is_opening = True
                    elif rcu_prof.is_reader_exit(api):
                        is_closing = True

                # 2. MATCHES Edge Generation Rules
                if is_opening:
                    active_guards.append(node)
                elif is_closing:
                    if active_guards:
                        matching_guard = active_guards.pop()
                        edge_id = f"rel:{context.file_path}:{node.location.line}:matches:{matching_guard.semantic_id.split(':')[-1]}"

                        context.relationships.append(SemanticRelationship(
                            relationship_id=edge_id,
                            relationship_type=RelationshipType.MATCHES,
                            source_semantic_id=matching_guard.semantic_id,
                            target_semantic_id=node_id
                        ))
                        links_created += 1

                # 3. PROTECTS Scope Boundary Propagation
                elif node.domain in [SemanticDomain.ASSIGNMENT, SemanticDomain.CALL, SemanticDomain.RCU]:
                    for guard in active_guards:
                        edge_id = f"rel:{context.file_path}:{node.location.line}:protects:{guard.semantic_id.split(':')[-1]}"

                        context.relationships.append(SemanticRelationship(
                            relationship_id=edge_id,
                            relationship_type=RelationshipType.PROTECTS,
                            source_semantic_id=guard.semantic_id,
                            target_semantic_id=node_id
                        ))
                        links_created += 1

        return links_created