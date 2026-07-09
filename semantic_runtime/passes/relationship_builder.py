import enum
from dataclasses import dataclass
from semantic_runtime.ontology.metadata import SemanticDomain

class RelationshipType(enum.Enum):
    DESCRIBES = "describes"
    WRITES    = "writes"
    CONTAINS  = "contains"

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

    def run(self, context) -> int:
        links_created = 0
        
        # Pass 1: Global Symbol Table Write Linking (Process EVERY assignment node)
        for obj in context.semantic_constructs:
            if obj.domain == SemanticDomain.ASSIGNMENT:
                # Type safe reference check
                if getattr(obj, 'resolved_symbol', None) and obj.resolved_symbol in context.local_symbols:
                    # Strip "func:" prefix cleanly if present to preserve exact symbol table string anchor
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

        # Pass 2: Line Coordinate Aggregation for Overlap (Only look for line collisions)
        line_map = {}
        for obj in context.semantic_constructs:
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
                        
        return links_created