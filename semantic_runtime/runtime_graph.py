# ============================================================
# SECTION 2 - RUNTIME EXECUTION LAYER - Starts
# ============================================================
"""
Contains:

RuntimeExecutionEngine
ExecutionNode
ExecutionEdge
"""
# --------------------------------------------------------
# Execution Graph Layer
# --------------------------------------------------------
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass(slots=True)
class ExecutionNode:
    node_id: str

    symbol_id: str

    cpu: Optional[int]

    context: str

    timestamp: Optional[int]

    depth: int

    semantic_annotations: List[Any] = field(
    default_factory=list
    )
# --------------------------------------------------------
# Execution Edge Layer
# --------------------------------------------------------

@dataclass(slots=True)
class ExecutionEdge:
    src_node_id: str
    dst_node_id: str

    semantic_edge_id: Optional[str]

    execution_context: str

# --------------------------------------------------------
# Runtime Execution Graph
# --------------------------------------------------------
@dataclass(slots=True)
class RuntimeExecutionGraph:
    nodes: Dict[str, ExecutionNode] = field(default_factory=dict)

    edges: List[ExecutionEdge] = field(default_factory=list)
