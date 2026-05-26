"""
Linux Kernel Flow Explorer
-------------------------------------------------
Semantic execution analysis for the Linux kernel.

Reconstructs kernel execution paths using:
- semantic retrieval
- subsystem-aware reranking
- scheduler dispatch reconstruction
- execution-path analysis
- local LLM reasoning

Uses:
- Ctags for symbol resolution
- ChromaDB for semantic retrieval
- Mermaid for execution visualization
- Ollama for grounded local reasoning
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from hashlib import sha1
from typing import Dict, List, Optional

import requests
import json
import re
import os
import subprocess
from datetime import datetime
from sentence_transformers import SentenceTransformer
import chromadb
import time
import platform

LINUX_ROOT = os.environ.get(
    "LINUX_ROOT",
    "."
)
ACTIVE_PROFILE = None
ACTIVE_SEMANTIC_GRAPH = None
CURRENT_IR_VERSION = 1


# ============================================================
# ENUMS
# ============================================================

class EdgeType(Enum):
    DIRECT_CALL = "DIRECT_CALL"
    FUNCTION_POINTER_DISPATCH = "FUNCTION_POINTER_DISPATCH"
    SYNTHETIC_BRIDGE = "SYNTHETIC_BRIDGE"
    ASYNC_WAKEUP = "ASYNC_WAKEUP"
    INTERRUPT_ENTRY = "INTERRUPT_ENTRY"
    INTERRUPT_EXIT = "INTERRUPT_EXIT"


CACHE_DIR = "semantic_cache"

SEMANTIC_IR_FILE = os.path.join(
    CACHE_DIR,
    "semantic_ir.json"
)



# ============================================================
# # SECTION 1 - Semantic IR Core Definitions - Starts
# ============================================================

"""
Contains:

SymbolIdentity
SemanticEdge
SemanticGraph
"""

# --------------------------------------------------------
# Symbol Identity Layer
# --------------------------------------------------------

@dataclass(slots=True)
class SymbolIdentity:
    symbol_id: str

    name: str
    file_path: str

    line: int

    kind: str

    signature: Optional[str]

    subsystem: str


# --------------------------------------------------------
# Semantic Edge Layer
# --------------------------------------------------------

@dataclass(slots=True)
class SemanticEdge:
    edge_id: str

    src_symbol_id: str
    dst_symbol_id: str

    edge_type: EdgeType

    confidence: float

    subsystem: str

    resolution_source: str

    is_deterministic: bool = True

# --------------------------------------------------------
# Central Semantic Graph
# --------------------------------------------------------

class SemanticGraph:

    def __init__(self):

        # ----------------------------------------------------
        # Symbol Registries
        # ----------------------------------------------------

        self.symbol_table: Dict[str, SymbolIdentity] = {}

        self.fq_name_to_id: Dict[str, str] = {}

        self.name_to_symbol_id = {}

        # ----------------------------------------------------
        # Edge Registries
        # ----------------------------------------------------

        self.semantic_edges_by_src: Dict[
            str,
            List[SemanticEdge]
        ] = {}

        self.semantic_edges_by_dst: Dict[
            str,
            List[SemanticEdge]
        ] = {}

    # --------------------------------------------------------
    # Identity Generation (using hashing for stable IDs)
    # --------------------------------------------------------

    @staticmethod
    def generate_symbol_id(
        file_path: str,
        symbol: str,
        signature: Optional[str],
        kind: str
    ) -> str:

        identity_seed = (
            f"{file_path}:{symbol}:{signature}:{kind}"
        )

        return sha1(identity_seed.encode()).hexdigest()

    @staticmethod
    def generate_edge_id(
        src_symbol_id: str,
        dst_symbol_id: str,
        edge_type: EdgeType
    ) -> str:

        edge_seed = (
            f"{src_symbol_id}:"
            f"{dst_symbol_id}:"
            f"{edge_type.value}"
        )

        return sha1(edge_seed.encode()).hexdigest()

    # --------------------------------------------------------
    # Symbol Registration
    # --------------------------------------------------------

    def register_symbol(
        self,
        name: str,
        file_path: str,
        line: int,
        kind: str,
        signature: Optional[str] = None
    ) -> str:

        subsystem = derive_subsystem(file_path)

        symbol_id = self.generate_symbol_id(
            file_path=file_path,
            symbol=name,
            signature=signature,
            kind=kind
        )

        if symbol_id in self.symbol_table:
            return symbol_id

        symbol = SymbolIdentity(
            symbol_id=symbol_id,
            name=name,
            file_path=file_path,
            line=line,
            kind=kind,
            signature=signature,
            subsystem=subsystem
        )

        self.symbol_table[symbol_id] = symbol

        fq_name = f"{file_path}:{name}"

        self.fq_name_to_id[fq_name] = symbol_id

        self.name_to_symbol_id[name] = symbol_id

        return symbol_id

    # --------------------------------------------------------
    # Symbol Lookup and Resolution
    # --------------------------------------------------------

    def lookup_symbol(
        self,
        symbol_id: str
    ) -> Optional[SymbolIdentity]:

        return self.symbol_table.get(symbol_id)

    def resolve_fq_name(
        self,
        file_path: str,
        symbol_name: str
    ) -> Optional[str]:

        fq_name = f"{file_path}:{symbol_name}"

        return self.fq_name_to_id.get(fq_name)

    # --------------------------------------------------------
    # Edge Registration
    # --------------------------------------------------------

    def register_semantic_edge(
        self,
        src_symbol_id: str,
        dst_symbol_id: str,
        edge_type: EdgeType,
        confidence: float,
        resolution_source: str,
        is_deterministic: bool = True
    ) -> str:

        src_symbol = self.lookup_symbol(src_symbol_id)

        if not src_symbol:
            raise ValueError(
                f"Unknown source symbol: {src_symbol_id}"
            )

        edge_id = self.generate_edge_id(
            src_symbol_id,
            dst_symbol_id,
            edge_type
        )

        edge = SemanticEdge(
            edge_id=edge_id,

            src_symbol_id=src_symbol_id,
            dst_symbol_id=dst_symbol_id,

            edge_type=edge_type,

            confidence=confidence,

            subsystem=src_symbol.subsystem,

            resolution_source=resolution_source,

            is_deterministic=is_deterministic
        )

        # To solve the problem of duplicate edges being created due to
        # multiple regex matches or overlapping heuristics,
        # we first check if an identical edge already exists before
        # registering a new one. This ensures that the graph remains
        # clean and prevents bloat from redundant edges.
        existing = self.semantic_edges_by_src.get(
            src_symbol_id,
            []
        )

        for e in existing:
            if e.edge_id == edge_id:
                return edge_id
        # ----------------------------------------------------
        # Forward Index
        # ----------------------------------------------------

        self.semantic_edges_by_src.setdefault(
            src_symbol_id,
            []
        ).append(edge)

        # ----------------------------------------------------
        # Reverse Index
        # ----------------------------------------------------

        self.semantic_edges_by_dst.setdefault(
            dst_symbol_id,
            []
        ).append(edge)

        # ----------------------------------------------------
        # Deterministic Traversal Ordering
        # ----------------------------------------------------

        self.semantic_edges_by_src[src_symbol_id].sort(
            key=lambda e: (
                e.confidence,
                e.is_deterministic
            ),
            reverse=True
        )

        return edge_id

    # --------------------------------------------------------
    # Graph Traversal - Outgoing and Incoming Edges
    # --------------------------------------------------------

    def get_outgoing_edges(
        self,
        symbol_id: str
    ) -> List[SemanticEdge]:

        return self.semantic_edges_by_src.get(
            symbol_id,
            []
        )

    def get_incoming_edges(
        self,
        symbol_id: str
    ) -> List[SemanticEdge]:

        return self.semantic_edges_by_dst.get(
            symbol_id,
            []
        )

    def save_semantic_ir(self, path: str, profile: SubsystemSemanticProfile):

        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(path, "w") as f:

            json.dump(
                self.export_json(),
                f,
                indent=2
            )
        # We will take this out later - for now we want to save
        # metadata together with the IR for easier validation during development
        # yashtbd - separate metadata saving later
        with open(METADATA_FILE, "w") as f:
            json.dump(generate_semantic_ir_metadata(self, profile), f, indent=2)

    @classmethod
    def load_semantic_ir(cls, path: str) -> SemanticGraph:

        with open(path) as f:
            data = json.load(f)

        graph = cls()

        # Rebuild symbols
        for symbol_id, sym_data in data["symbols"].items():
            graph.symbol_table[symbol_id] = (
                SymbolIdentity(**sym_data)
            )

        # Rebuild Forward Edges
        for src_id, edges in data[
            "semantic_edges_by_src"
        ].items():

            graph.semantic_edges_by_src[src_id] = []

            for edge_data in edges:

                edge_data["edge_type"] = (
                    EdgeType(edge_data["edge_type"])
                )

                edge = SemanticEdge(**edge_data)

                graph.semantic_edges_by_src[
                    src_id
                ].append(edge)

        # Rebuild Lookup Indexes
        graph.fq_name_to_id = data["fq_name_to_id"]

        graph.name_to_symbol_id = data["name_to_symbol_id"]

        graph.rebuild_indexes()

        return graph

    def rebuild_indexes(self):


        self.semantic_edges_by_dst = {}

        for src_id, edges in (
            self.semantic_edges_by_src.items()
        ):

            for edge in edges:

                self.semantic_edges_by_dst.setdefault(
                    edge.dst_symbol_id,
                    []
                ).append(edge)

    def number_of_edges(self):
        count = 0
        for edges in self.semantic_edges_by_src.values():
            count += len(edges)
        return count

    def dispatch_edges(self):
        count = 0
        for edges in self.semantic_edges_by_src.values():
            for edge in edges:
                if edge.edge_type == EdgeType.FUNCTION_POINTER_DISPATCH:
                    count += 1
        return count

    def synthetic_edges(self):
        count = 0
        for edges in self.semantic_edges_by_src.values():
            for edge in edges:
                if edge.edge_type == EdgeType.SYNTHETIC_BRIDGE:
                    count += 1
        return count

    def semantic_ir_stats(self):

        return {
            "symbols": len(self.symbol_table),

            "edges": self.number_of_edges(),

            "dispatch_edges":
                self.dispatch_edges(),

            "synthetic_edges":
                self.synthetic_edges()
        }
    # --------------------------------------------------------
    # Serialization for Debugging and Visualization
    # --------------------------------------------------------

    def export_json(self) -> dict:

        return {
            "symbols": {
                k: asdict(v)
                for k, v in self.symbol_table.items()
            },

            "semantic_edges_by_src": {
                k: [
                    {
                        **asdict(e),
                        "edge_type": e.edge_type.value
                    }
                    for e in v
                ]

                for k, v in self.semantic_edges_by_src.items()
            },

            "fq_name_to_id": self.fq_name_to_id,

            "name_to_symbol_id": self.name_to_symbol_id,
        }

    # --------------------------------------------------------
    # Helper for symbol resolution by name
    # --------------------------------------------------------

    def resolve_symbol_by_name(
        self,
        symbol_name: str
    ):

        return self.name_to_symbol_id.get(
            symbol_name
        )

# ============================================================
# SECTION 1 - SEMANTIC IR CORE DEFINITIONS - Ends
# ============================================================

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

@dataclass(slots=True)
class ExecutionNode:
    node_id: str

    symbol_id: str

    cpu: Optional[int]

    context: str

    timestamp: Optional[int]

    depth: int

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

# --------------------------------------------------------
# Runtime Execution Engine - reconstructs execution paths using the semantic graph and heuristics
# --------------------------------------------------------

class RuntimeExecutionEngine:

    def __init__(
        self,
        semantic_graph: SemanticGraph
    ):

        self.semantic_graph = semantic_graph

    #--------------------------------------------------------
    # Deterministic Node ID generation based on symbol, CPU,
    # depth and context
    #--------------------------------------------------------
    @staticmethod
    def generate_execution_node_id(
        symbol_id: str,
        cpu: Optional[int],
        depth: int,
        context: str
    ) -> str:

        seed = (
            f"{symbol_id}:{cpu}:{depth}:{context}"
        )

        return sha1(seed.encode()).hexdigest()

    #--------------------------------------------------------
    # Reconstructs a plausible execution path starting from a
    # given symbol, using the semantic graph and heuristics.
    #--------------------------------------------------------
    def reconstruct_execution_path(
        self,
        start_symbol_id: str,
        cpu: int,
        max_depth: int = 16
    ) -> RuntimeExecutionGraph:

        runtime_graph = RuntimeExecutionGraph()

        # To prevent cycles and redundant paths, we maintain a set of visited symbols.
        visited_symbols = set()

        current_symbol_id = start_symbol_id

        previous_node_id = None

        for depth in range(max_depth):

            # To avoid infinite loops in cases where the semantic
            # graph has cycles or redundant edges
            if current_symbol_id in visited_symbols:
                break

            visited_symbols.add(current_symbol_id)

            node_id = self.generate_execution_node_id(
                symbol_id=current_symbol_id,
                cpu=cpu,
                depth=depth,
                context="process_context"
            )

            node = ExecutionNode(
                node_id=node_id,

                symbol_id=current_symbol_id,

                cpu=cpu,

                context="process_context",

                timestamp=None,

                depth=depth
            )

            runtime_graph.nodes[node_id] = node

            # ------------------------------------------------
            # Link Previous Runtime Node
            # ------------------------------------------------

            if previous_node_id is not None:

                runtime_graph.edges.append(
                    ExecutionEdge(
                        src_node_id=previous_node_id,

                        dst_node_id=node_id,

                        semantic_edge_id=None,

                        execution_context="scheduler_path"
                    )
                )

            # ------------------------------------------------
            # Pull Semantic Transitions
            # ------------------------------------------------

            outgoing_edges = (
                self.semantic_graph.get_outgoing_edges(
                    current_symbol_id
                )
            )

            if not outgoing_edges:
                break

            # Select the most confident outgoing transition from the semantic graph.
            # Edges are sorted by confidence and determinism in register_semantic_edge().
            selected_edge = outgoing_edges[0]

            previous_node_id = node_id

            current_symbol_id = (
                selected_edge.dst_symbol_id
            )

        return runtime_graph

# ============================================================
# SECTION 2 - Runtime Execution Layer - Ends
# ============================================================

# ============================================================
# SUBSYSTEM DETECTION
# ============================================================

SUBSYSTEM_MAP = {
    "kernel/sched": "scheduler",
    "kernel/irq": "interrupts",
    "kernel/softirq": "softirq",
    "fs": "vfs",
    "mm": "memory_management",
    "block": "block_layer",
    "net": "networking",
    "drivers": "drivers",
}

# =================================================================
# Convert filesystem paths into canonical semantic subsystem names.
# =================================================================

def derive_subsystem(file_path: str) -> str:

    normalized = file_path.strip("/")

    for prefix, subsystem in SUBSYSTEM_MAP.items():
        if normalized.startswith(prefix):
            return subsystem

    return "kernel_core"



# =================================================================
# 1. NETWORKING & OLLAMA CONFIGURATION
# =================================================================
def get_ollama_config():
    """Detects WSL or Linux environments and sets the Ollama API endpoint."""
    # Check if we are running inside Windows Subsystem for Linux
    is_wsl = "microsoft-standard" in os.uname().release.lower()
    
    if is_wsl:
        try:
            # Get the Windows host IP address from the WSL gateway
            cmd = "ip route show default | awk '{print $3}'"
            host_ip = subprocess.check_output(cmd, shell=True).decode().strip()
            url = f"http://{host_ip}:11434"
        except Exception:
            url = "http://127.0.0.1:11434"
    else:
        url = "http://127.0.0.1:11434"

    # Perform a health check to see if the LLM server is reachable
    try:
        #requests.get(url, timeout=1)
        requests.get(f"{url}/api/tags", timeout=1)
        return url, True
    except requests.exceptions.RequestException:
        return url, False

OLLAMA_HOST, IS_ACTIVE = get_ollama_config()
OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"

print(f"[OLLAMA] Using endpoint: {OLLAMA_URL}")

# =================================================================
# 2. CORE REGEX PATTERNS
# =================================================================

# Matches standard function calls: func_name(
call_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')

# Token extraction (query + symbol match)
token_pattern = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')

# -----------------------------------------------------------------------------
# Regex patterns used to extract call and dispatch relationships from kernel code.
# -----------------------------------------------------------------------------
fp_pattern = re.compile(
    r'([a-zA-Z_]\w*(?:\s*->\s*[a-zA-Z_]\w*)*)\s*->\s*([a-zA-Z_]\w*)\s*\(',
    re.MULTILINE | re.DOTALL
)
ops_assign_pattern = re.compile(
    r'\.(\w+)\s*=\s*(\w+)'
)

# Cache metadata file path.
METADATA_FILE = os.path.join(CACHE_DIR, "metadata.json")

# -----------------------------
# Linux Kernel commit tracking - MetaData Helpers
# -----------------------------

# def get_kernel_commit():
#     try:
#         return subprocess.check_output(
#             ["git", "rev-parse", "HEAD"],
#             cwd=LINUX_ROOT
#         ).decode().strip()
#     except:
#         return "unknown"

def get_kernel_commit():

    try:

        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],

            cwd=LINUX_ROOT
        ).decode().strip()

        return commit

    except Exception:

        return "unknown"

def build_metadata():
    return {
        "kernel_commit": get_kernel_commit(),
        "generated_at": datetime.now().isoformat(),
        "cache_version": 1,
    }


def generate_semantic_ir_metadata(
        semantic_graph,
        profile
    ):
    return {

    "semantic_ir_version": 1,

    "generated_at": datetime.now().isoformat(),

    "kernel": {

        "commit": get_kernel_commit()
    },

    "host_environment": {
        "host_architecture": platform.machine(),

        "host_kernel_version": platform.release(),

        "build": platform.version()
    },
    # Later we can find the target architecture by parsing the Makefile or using uname -m in the target environment
    # or using autoconf. For now we will just use the host architecture as a proxy for the target architecture during development.
    "semantic_ir_stats": {

        "symbol_count":
            len(semantic_graph.symbol_table),

        "semantic_edge_count":
            semantic_graph.number_of_edges(),

        "dispatch_edge_count":
            semantic_graph.dispatch_edges(),

        "synthetic_bridge_count":
            semantic_graph.synthetic_edges()
    },

    "subsystem_profiles": [
        profile.subsystem_name
    ],
}

def semantic_ir_cache_valid(profile):
    """Return True if the cached semantic IR is present and still valid."""

    required_files = [
        SEMANTIC_IR_FILE,
        METADATA_FILE,
    ]

    if not all(os.path.exists(f) for f in required_files):
        print("Semantic IR cache files missing.", SEMANTIC_IR_FILE, METADATA_FILE)
        return False

    try:
        with open(METADATA_FILE) as f:
            metadata = json.load(f)

        current_commit = get_kernel_commit()

        cached_profiles = metadata.get(
            "subsystem_profiles",
            []
        )
        print(f"Cache metadata loaded. Kernel commit: {metadata['kernel']['commit']}, Current commit: {current_commit}, Cached profiles: {cached_profiles}")
        return (
            metadata["kernel"]["commit"]
            == current_commit

            and

            metadata["semantic_ir_version"]
            == CURRENT_IR_VERSION

            and

            profile.subsystem_name in cached_profiles
        )

    except Exception as e:
        print(f"[semantic cache validation failed] {e}")
        return False

# =================================================================
# SECTION 3 - Semantic Graph Compilation - 2 Pass Approach - Starts
# =================================================================
# Moving onto 2 pass compilation Registration to build the
# semantic graph with edges in compile_semantic_ir

def register_all_symbols(semantic_graph, symbol_index):
    with open("chunks.jsonl") as f:

        for line in f:

            data = json.loads(line)

            symbol = data["symbol"]

            semantic_graph.register_symbol(
                name=symbol,

                file_path=data["file"],

                line=0,

                kind="function"
            )

            entry = symbol_index.setdefault(
                symbol.lower(),
                {
                    "symbol": symbol,
                    "file": data["file"],
                    "code": ""
                }
            )

            entry["code"] += "\n" + data["code"]

# -----------------------------
# Semantic IR Graph compilation
# -----------------------------

def compile_semantic_ir(profile):

    semantic_graph = SemanticGraph()

    call_graph = {}
    fp_call_graph = {}
    symbol_index = {}
    ops_index = {}
    symbol_freq = {}

    # call the 1st pass to register all symbols and build the symbol index with code snippets
    register_all_symbols(
        semantic_graph,
        symbol_index
    )

    with open("chunks.jsonl") as f:
        for line in f:
            data = json.loads(line)

            symbol = data["symbol"]
            # For the moment we keep line=0 (development mode)
            # Eventually use ctags line number
            #yashtbd
            current_src_symbol_id = (
                semantic_graph.resolve_symbol_by_name(
                    symbol
                )
            )
            code = data["code"]

            # Frequency Tracking (for heuristics)
            symbol_freq[symbol] = symbol_freq.get(symbol, 0) + 1

            # Direct Calls extraction (for execution path tracing)
            calls = [
                c for c in call_pattern.findall(code)
                if c != symbol and c not in IGNORE_CALLS
            ]

            # Using set to avoid duplicate callees which can bloat the call graph
            # and cause infinite loops in traversal
            # yashtbd - call graph is not fixed
            #yashcache
            call_graph.setdefault(symbol, set()).update(calls)
            for callee in calls:

                # if callee.lower() in symbol_index:
                #     callee_file = symbol_index[callee.lower()]["file"]
                # else:
                #     callee_file = "unknown"

                dst_symbol_id = semantic_graph.resolve_symbol_by_name(callee)

                if not dst_symbol_id:
                    continue

                if callee in profile.low_signal_calls:
                    confidence = 0.1
                else:
                    confidence = 1.0
                if callee in profile.execution_spine_boost:
                    confidence += profile.execution_spine_boost[callee]
                transition_key = (symbol, callee)
                if transition_key in profile.high_value_transitions:
                    confidence += profile.high_value_transitions[
                        transition_key
                    ]
                semantic_graph.register_semantic_edge(
                    src_symbol_id=current_src_symbol_id,
                    dst_symbol_id=dst_symbol_id,
                    edge_type=EdgeType.DIRECT_CALL,
                    confidence=confidence,
                    resolution_source="regex_call_parse"
                )


    # -----------------------------
    # FIX: Load full function ONCE
    # -----------------------------
    if "__pick_next_task" in symbol_index:
        full = load_full_function("__pick_next_task")
        if full:
            symbol_index["__pick_next_task"]["code"] = full

    for key, entry in symbol_index.items():

        symbol = entry["symbol"].strip()

        full_code = entry["code"]

        if profile.requires_dispatch_analysis(symbol):
            #loaded = load_full_function(symbol)
            if symbol.endswith("_sched_class"):
                loaded = load_full_definition(symbol)
            else:
                loaded = load_full_function(symbol)

            if loaded:
                full_code = loaded
                #if symbol == "__pick_next_task":
                #    print(full_code[:3000])
                matches = ops_assign_pattern.findall(full_code)

                for field, impl in matches:
                    if field in VALID_OPS:
                        ops_index.setdefault(field, set()).add(impl)

        matches = [
            (obj.strip(), fn.strip())
            for obj, fn in fp_pattern.findall(full_code)
            if fn not in IGNORE_CALLS
        ]

        #yashcache
        # The fp_call_graph needs to be modified to bring in semanticedge
        #yashtbd
        if matches:
            fp_call_graph[symbol.strip()] = list(set(matches))
            # create semantic edges for function pointer dispatches

            for obj, method in matches:

                if method not in ops_index:
                    continue

                implementations = ops_index[method]

                for impl in implementations:

                    if impl.lower() in symbol_index:
                        impl_file = symbol_index[impl.lower()]["file"]
                    else:
                        impl_file = "unknown"
                    dst_symbol_id = semantic_graph.resolve_symbol_by_name(impl)

                    if not dst_symbol_id:
                        continue
                    # dst_symbol_id = semantic_graph.register_symbol(
                    #     name=impl,
                    #     file_path=impl_file,
                    #     line=0,
                    #     kind="function"
                    # )
                    if impl in profile.low_signal_calls:
                        confidence = 0.1
                    else:
                        confidence = 1.0
                    current_src_symbol_id = (
                        semantic_graph.resolve_symbol_by_name(
                            symbol
                        )
                    )
                    semantic_graph.register_semantic_edge(
                        src_symbol_id=current_src_symbol_id,

                        dst_symbol_id=dst_symbol_id,

                        edge_type=EdgeType.FUNCTION_POINTER_DISPATCH,

                        confidence=confidence,

                        resolution_source="ops_dispatch_parse",

                        is_deterministic=False
                    )
    # --------------------------------------------------------
    # Inject Synthetic Scheduler Continuations
    # --------------------------------------------------------

    for src_name, dst_name in profile.synthetic_bridges.items():

        src_id = None
        dst_id = None

        # Resolve source symbol
        for sym_id, sym in semantic_graph.symbol_table.items():
            if sym.name == src_name:
                src_id = sym_id
                break

        # Resolve destination symbol
        for sym_id, sym in semantic_graph.symbol_table.items():
            if sym.name == dst_name:
                dst_id = sym_id
                break

        if not src_id or not dst_id:
            continue


        confidence = 100.0
        semantic_graph.register_semantic_edge(
            src_symbol_id=src_id,

            dst_symbol_id=dst_id,

            edge_type=EdgeType.SYNTHETIC_BRIDGE,

            confidence=confidence,

            resolution_source="synthetic_scheduler_bridge",

            is_deterministic=True
        )


    return (
        # call_graph,
        # fp_call_graph,
        # symbol_index,
        # ops_index,
        semantic_graph
    )

def load_full_definition(symbol):

    files = ctags_index.get(symbol, [])

    if not files:
        return None

    for f_path in files:

        full_path = os.path.join(
            LINUX_ROOT,
            f_path
        )

        try:
            with open(full_path, "r") as file:

                content = file.read()

                match = re.search(
                    rf"\b{re.escape(symbol)}\b",
                    content
                )

                if not match:
                    continue

                start = content.find(
                    "{",
                    match.end()
                )

                if start == -1:
                    continue

                brace_count = 0

                for i in range(start, len(content)):

                    if content[i] == "{":
                        brace_count += 1

                    elif content[i] == "}":
                        brace_count -= 1

                        if brace_count == 0:
                            return content[
                                match.start():i+1
                            ]

        except Exception:
            continue

    return None

# -----------------------------
# Function body loader using Ctags metadata
# -----------------------------

def load_full_function(symbol):
    """Uses Ctags metadata to jump to the correct file and extract a function body."""
    files = ctags_index.get(symbol, [])
    if not files: return None

    for f_path in files:
        full_path = os.path.join(
            LINUX_ROOT,
            f_path
        )
        try:
            with open(full_path, "r") as file:
                content = file.read()
                # Handles: symbol(...) and symbol __sched (...)
                match = re.search(
                    rf"\b{re.escape(symbol)}\b\s*\(",
                    content,
                    re.MULTILINE
                )

                if not match:
                    continue
                
                idx = content.rfind("\n", 0, match.start())
                start = content.find("{", match.end())
                if start == -1: continue

                brace_count = 0
                for i in range(start, len(content)):
                    if content[i] == "{": brace_count += 1
                    elif content[i] == "}":
                        brace_count -= 1
                        if brace_count == 0: return content[idx:i+1]
        except Exception: continue
    return None

# =================================================================
# SECTION 3 - Semantic Graph Compilation - 2 Pass Approach - Ends
# =================================================================

# =================================================================
# SECTION 4 - Subsystem Profiles of the Linux kernel - Starts
# =================================================================

# --------------------------------------------------------
# SUBSYSTEM PROFILES - scheduler, irq, mm, driver etc
# --------------------------------------------------------

@dataclass
class SubsystemSemanticProfile:

    subsystem_name: str

    entrypoints: list[str]

    low_signal_calls: set[str]

    execution_spine_boost: dict[str, float]

    high_value_transitions: dict[
        tuple[str, str],
        float
    ]

    synthetic_bridges: dict[str, str]

    def requires_dispatch_analysis(
        self,
        symbol: str
    ) -> bool:

        return (
            "sched" in symbol
            or
            "pick_next_task" in symbol
            or
            "enqueue_task" in symbol
            or
            "dequeue_task" in symbol
            or
            symbol.endswith("_sched_class")
        )

def determine_subsystem_profile(query: str):
    if "sched" in query.lower():
        return SCHEDULER_PROFILE

SCHEDULER_PROFILE = SubsystemSemanticProfile(
    subsystem_name="kernel/sched",

    entrypoints=["schedule", "try_to_wake_up", "wake_up_process"],

    low_signal_calls = {
        "lockdep_assert",
        "task_is_running",
        "schedstat_inc",
        "trace_sched_switch",
        "rcu_note_context_switch",
        "might_sleep",
        "preempt_disable",
        "preempt_enable",
        "WARN_ON",
    },

    execution_spine_boost = {
        "schedule": 10.0,
        "__schedule": 10.0,
        "pick_next_task": 10.0,
        "__pick_next_task": 10.0,
        "pick_next_task_fair": 10.0,
        "context_switch": 10.0,
        "__switch_to": 10.0,
        "finish_task_switch": 10.0,
        "__schedule_loop": 10.0,
    },

    high_value_transitions = {
        ("schedule", "__schedule"): 20.0,

        ("__schedule", "pick_next_task"): 20.0,

        ("pick_next_task", "__pick_next_task"): 20.0,

        ("__pick_next_task", "pick_next_task_fair"): 20.0,

        ("pick_next_task_fair", "context_switch"): 20.0,

        ("context_switch", "__switch_to"): 20.0,

        ("__switch_to", "finish_task_switch"): 20.0,
        ("schedule", "__schedule_loop"): 20.0,
        ("__schedule_loop", "__schedule"): 20.0,
    },

    # These are manually curated edges that we know exist but are not easily
    # detectable through regex parsing due to indirect calls, function pointer
    # dispatches, or complex control flow. They help bridge gaps in the semantic
    # graph and enable more complete execution path reconstruction.
    synthetic_bridges = {
        "pick_next_task_fair": "context_switch",
        "pick_next_task_rt": "context_switch",
        "pick_next_task_idle": "context_switch",

        "context_switch": "__switch_to",

        "__switch_to": "finish_task_switch",
    }
)
"""
class SubsystemSemanticProfile:

    subsystem_name: str

    entrypoints: list[str]

    low_signal_calls: set[str]

    execution_spine_boost:
        dict[str, float]

    high_value_transitions:
        dict[tuple[str, str], float]

    synthetic_bridges:
        dict[str, str]

    dispatch_patterns:
        list[str]

    semantic_layers:
        dict[str, list[str]]

    # These three can also be evolved in the SymbolIdentity layer to
    # track subsystem-specific metadata and associations
    root_directories: list[str]
    associated_structs: set[str]
    total_symbols: int
"""
# ============================================================
# IR TEST HARNESS
# ============================================================

def print_runtime_graph(
    runtime_graph: RuntimeExecutionGraph,
    semantic_graph: SemanticGraph
):

    print("\n========== Runtime Execution Graph ==========\n")

    for node_id, node in runtime_graph.nodes.items():

        symbol = semantic_graph.lookup_symbol(
            node.symbol_id
        )

        print(
            f"[CPU {node.cpu}] "
            f"Depth={node.depth} "
            f"{symbol.name} "
            f"({symbol.file_path})"
        )

    print("\n========== Runtime Edges ==========\n")

    for edge in runtime_graph.edges:

        src = runtime_graph.nodes[edge.src_node_id]
        dst = runtime_graph.nodes[edge.dst_node_id]

        src_sym = semantic_graph.lookup_symbol(src.symbol_id)
        dst_sym = semantic_graph.lookup_symbol(dst.symbol_id)

        print(
            f"{src_sym.name}"
            f" --> "
            f"{dst_sym.name}"
        )

# =================================================================
# SECTION 4 - Subsystem Profiles of the Linux kernel - Ends
# =================================================================

def run_scheduler_semantic_workflow(semantic_graph, profile):
    print("[workflow] scheduler")

    runtime_engine = RuntimeExecutionEngine(
        semantic_graph
    )

    start_symbol_id = (
        semantic_graph.resolve_symbol_by_name(
            "schedule"
        )
    )

    runtime_graph = (
        runtime_engine.reconstruct_execution_path(
            start_symbol_id=start_symbol_id,

            cpu=0,

            max_depth=16
        )
    )

    print_runtime_graph(
        runtime_graph,
        semantic_graph
    )


# =================================================================
# 3. KERNEL HEURISTICS & TEMPLATES
# =================================================================

INDIRECT_CALL_HINTS = (
    "->",
    ".pick_next_task",
    ".enqueue_task",
    ".dequeue_task",
    ".check_preempt_curr",
    ".select_task_rq",
    ".task_tick",
)

VALID_OPS = {
    "pick_next_task",
    "pick_task",
    "enqueue_task",
    "dequeue_task",
    "check_preempt_curr",
    "yield_task",
    "wakeup_preempt",
}

ENTRY_POINT_MAP = {
    "context_switch": "schedule",
    "__schedule": "schedule",
    "try_to_wake_up": "wake_up_process",
    "ttwu_queue": "wake_up_process",
    "__switch_to": "schedule",
    # interrupt aliases
    "arch_show_interrupts": "do_IRQ",
    "spurious_interrupt": "do_IRQ",
    "handle_badint": "do_IRQ",
}

SCHED_PATH = [
    "schedule",
    "__schedule",
    "pick_next_task",
    "context_switch",
    "__switch_to",
    "finish_task_switch"
]

KERNEL_EXECUTION_TEMPLATES = {

    "scheduler": [
        "schedule",
        "__schedule",
        "pick_next_task",
        "context_switch",
        "__switch_to",
        "finish_task_switch"
    ],

    "wakeup": [
        "try_to_wake_up",
        "ttwu_queue",
        "ttwu_do_activate",
        "activate_task",
        "enqueue_task",
        "check_preempt_curr"
    ],

    "futex": [
        "futex_wake",
        "try_to_wake_up",
        "ttwu_queue",
        "ttwu_do_activate",
        "activate_task"
    ],

    "interrupt": [
        "generic_handle_irq",
        "handle_irq_desc",
        "handle_irq_event",
        "handle_irq_event_percpu",
        #"irq_handler"
    ],

    "softirq": [
        "__do_softirq",
        "run_timer_softirq",
        "hrtimer_interrupt"
    ],

    "timer": [
        "hrtimer_interrupt",
        "__hrtimer_run_queues",
        "run_timer_softirq"
    ],

    "workqueue": [
        "process_one_work",
        "worker_thread",
        "schedule"
    ],

    "syscall": [
        "do_syscall_64",
        "syscall_enter_from_user_mode",
        "invoke_syscall",
        "syscall_exit_to_user_mode"
    ],

    "memory": [
        "handle_mm_fault",
        "__handle_mm_fault",
        "do_fault",
        "handle_pte_fault"
    ],

    "interrupt_entry": [
        "idtentry",
        "do_IRQ",
        "common_interrupt",
        "irq_enter",
        "generic_handle_irq"
    ]
}

# -----------------------------
# Load Ctags index
# -----------------------------
ctags_index = {}

with open("tags") as f:

    for line in f:

        if line.startswith("!"):
            continue

        parts = line.split("\t")

        if len(parts) < 2:
            continue

        sym = parts[0]
        file = parts[1]

        ctags_index.setdefault(sym, []).append(file)

    print("CTAGS symbols loaded:", len(ctags_index))
    #print("HAS __switch_to:", "__switch_to" in ctags_index)

IGNORE_CALLS = {
    "if","for","while","switch","return","sizeof",

    "__acquires","__releases","__must_check",
    "__always_inline","__maybe_unused","__sched",

    # common kernel macros that look like calls
    "likely","unlikely",
    "WARN_ON","BUG_ON",
    "container_of",
    "READ_ONCE","WRITE_ONCE",
    "TEST",
    "SYSCALL_DEFINE",
    "SYSCALL_DEFINE0",
    "SYSCALL_DEFINE1",
    "SYSCALL_DEFINE2",
    "SYSCALL_DEFINE3",
    "SYSCALL_DEFINE4",
    "SYSCALL_DEFINE5",
    "SYSCALL_DEFINE6",
    "module_init",
    "module_exit",
    "DEFINE_INTERRUPT_HANDLER",
    "DECLARE_INTERRUPT_HANDLER",
    "DEFINE_IDTENTRY",
    "DECLARE_IDTENTRY",
    "DEFINE_IDTENTRY_RAW",
}

STOPWORDS = {
    "how", "does", "the", "linux", "what", "where", "why",
    "a", "an", "is"
}

#ops_index = {}




# -----------------------------
# Embedding model
# -----------------------------

embed_model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5",
    device="cpu"
)

# -----------------------------
# Vector DB
# -----------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chroma_db")

client = chromadb.PersistentClient(path=DB_PATH)
#print("Using ChromaDB at:", DB_PATH)
collection = client.get_collection("linux_kernel")

# -----------------------------
# Subsystem detection
# -----------------------------
def detect_domains(query):

    q = query.lower()

    domains = []

    if "vector" in q or "idt" in q:
        domains.append("interrupt_entry")

    if "interrupt" in q or "irq" in q:
        domains.append("interrupt")

    if "timer" in q:
        domains.append("timer")

    if "softirq" in q:
        domains.append("softirq")

    if "wake" in q or "sleep" in q:
        domains.append("wakeup")

    if any(x in q for x in ["schedule", "scheduler", "context switch"]):
        domains.append("scheduler")

    if not domains:
        domains.append("kernel")

    return domains

# -----------------------------
# Symbol extraction
# -----------------------------

def extract_symbols(query):

    tokens = token_pattern.findall(query.lower())

    matches = []

    for t in tokens:
        key = t

        if key not in STOPWORDS and key in symbol_index:
            matches.extend([symbol_index[key]])

    return matches


# -----------------------------
# Retrieval
# -----------------------------

def retrieve_code(query):

    vec = embed_model.encode(query, normalize_embeddings=True)

    results = collection.query(
        query_embeddings=[vec],
        n_results=40
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]

    # -------------------------
    # Symbol injection
    # -------------------------

    symbol_hits = extract_symbols(query)
    existing = {m["symbol"] for m in metas}

    for hit in symbol_hits[:3]:

        if hit["symbol"] not in existing:

            docs.insert(0, hit["code"])
            metas.insert(0, {
                "symbol": hit["symbol"],
                "file": hit["file"]
            })

    # -------------------------
    # Query tokens
    # -------------------------

    tokens = token_pattern.findall(query.lower())
    query_tokens = {
        t for t in tokens if t not in STOPWORDS
    }

    # -------------------------
    # Reranking
    # -------------------------

    scored = []

    for d, m in zip(docs, metas):

        if len(m["symbol"]) <= 2:
            continue

        sym = m["symbol"].lower()
        file = m["file"].lower()

        # Ignore macro-style symbols
        if sym.isupper():
            continue

        # Ignore diagnostic IRQ functions
        if sym in {"arch_show_interrupts", "spurious_interrupt", "handle_badint"}:
            continue

        # remove testing noise completely
        if "selftest" in file or "testing" in file:
            continue

        if not ("kernel/" in file or "arch/" in file):
            continue

        if "relocs.c" in file:
            continue

        if "traps.c" in file:
            continue

        score = 0

        if sym in query_tokens:
            score += 15

        # Prefer generic IRQ entry points
        if sym == "do_irq":
            score += 120

        elif sym in {"handle_irq_event", "handle_irq_event_percpu"}:
            score += 100

        # Structural importance boost
        # Commented out because it was causing irrelevant popular functions 
        # to dominate results, but can be re-enabled if needed for recall
        # Symbols like TEST, SYSCALL_DEFINE, module_init, etc. appear thousands 
        # of times in the kernel tree. Their symbol_freq becomes very large 
        # and overwhelms all the other signals.
        score += sum(1 for t in query_tokens if t in sym) * 5
        score += sum(1 for t in query_tokens if t in file) * 2

        # scheduler bias
        if "kernel/sched" in file:
            score += 40

        if "kernel/irq" in file:
            score += 40

        if file.startswith("tools/"):
            score -= 30

        #if "selftest" in file or "testing" in file:
        #    score -= 6

        if file.startswith("kernel/"):
            score += 10

        if file.startswith("drivers/gpu"):
            score -= 20

        if file.startswith("arch/") and "kernel" not in file:
            score -= 10

        # Penalize architecture-specific interrupt helpers
        if file.startswith("arch/") and "irq.c" in file:
            score -= 30
        scored.append((score, d, m))
            
    scored.sort(key=lambda x: x[0], reverse=True)

    # print("\nTop Vector retrieval candidates:\n")
    # for s in scored[:5]:
    #     print(s[2]["symbol"], s[2]["file"], "score:", s[0])

    docs = [s[1] for s in scored][:3]
    metas = [s[2] for s in scored][:3]

    # -------------------------
    # Interrupt entry injection
    # -------------------------
    domains = detect_domains(query)

    if "interrupt" in domains and "vector" not in query.lower():

        anchors = ["generic_handle_irq", "handle_irq_event", "handle_irq_event_percpu"]

        injected_docs = []
        injected_meta = []

        for anchor in anchors:

            if anchor.lower() not in symbol_index:
                continue

            best = None

            entry = symbol_index.get(anchor.lower())

            if entry:
                injected_docs.append(entry["code"])
                injected_meta.append({
                    "symbol": entry["symbol"],
                    "file": entry["file"]
                })

        existing = {m["symbol"] for m in metas}

        for d, m in zip(injected_docs, injected_meta):
            if m["symbol"] not in existing:
                docs.insert(0, d)
                metas.insert(0, m)

        docs = docs[:3]
        metas = metas[:3]

    if not metas:
        print("No functions retrieved")
        return [], []

    #   print(f"\nTop function: {metas[0]['symbol']} ({metas[0]['file']})")
    print("\nRetrieved functions:\n")

    for m in metas:
        subsystem = "/".join(m["file"].split("/")[:2])
        print(f"{m['symbol']}   ({m['file']})   [{subsystem}]")

    return docs, metas



# -----------------------------
# Prompt builder
# -----------------------------

def build_prompt(query, docs, subsystem, chain):

    MAX_CHARS = 12000
    #context = "\n\n".join(docs)[:MAX_CHARS]
    trimmed = [d[:1200] if len(d) > 1200 else d for d in docs]
    context = "\n\n".join(trimmed)
    chain_text = " → ".join(chain[:6])

    prompt = f"""
You are a senior Linux kernel engineer.

The question relates to the Linux kernel **{subsystem} domain**.

QUESTION:
{query}

KERNEL CODE:
{context}

DETECTED CALL FLOW:
{chain_text}

Instructions:

1. Identify the relevant functions and their roles.
2. Explain how the call chain works.
3. Describe kernel state changes (task state, runqueue, CPU idle, etc).
4. Explain how the {subsystem} subsystem interacts with the scheduler or kernel.
5. Summarize the behavior clearly.

Use only the provided code. Avoid generic OS explanations.
Focus on the actual Linux kernel execution path.
Do not speculate beyond the code provided.
"""

    return prompt


# -----------------------------
# LLM call
# -----------------------------

def ask_llm(prompt, model="qwen2.5-coder:7b"):

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=300
        )

        response.raise_for_status()
        return response.json()["response"]

    except requests.exceptions.Timeout:
        return "LLM timed out. Try reducing retrieved code size."

# -----------------------------
# Entry point mapping
# -----------------------------
def get_entry_point(symbol, domains):

    if "interrupt_entry" in domains:
        return "idtentry"

    if "interrupt" in domains:
        return "generic_handle_irq"

    if "scheduler" in domains:
        return "schedule"

    return symbol

# -----------------------------
# Mermaid call graph export
# -----------------------------
# LEGACY - Will convert toMermaidGraphExporter which is the semantic graph exporter - yashtbd
def export_execution_path(path, domains, query):

    base_dir = "callgraphs"
    domain_name = "_".join(domains)

    folder = os.path.join(base_dir, domain_name)
    os.makedirs(folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{domain_name}_{timestamp}.mmd"
    filepath = os.path.join(folder, filename)

    with open(filepath, "w") as f:

        f.write("graph TD\n")
        f.write(f"%% Query: {query}\n")

        for i in range(len(path) - 1):

            a = path[i].replace("-", "_")
            b = path[i+1].replace("-", "_")
            f.write(f"  {a} --> {b}\n")

    print(f"Execution path written to {filepath}")


# -----------------------------
# Append callees to context
# -----------------------------
def append_callees(symbol, docs, metas):

    existing = {m["symbol"] for m in metas}

    for callee in list(call_graph.get(symbol, []))[:8]: # originally 4

        if callee.lower() in symbol_index:

            entry = symbol_index[callee.lower()]
            # Duplication check to prevent bloating context with multiple similar callees
            #docs.insert(0, entry["code"])

            if entry["symbol"] in existing:
                continue

            docs.append(entry["code"])
            metas.append({
                "symbol": entry["symbol"],
                "file": entry["file"]
            })
#############################


# --------------------------------------------------------
# Test function to validate runtime reconstruction of the
# scheduler execution path using the semantic graph.
# --------------------------------------------------------
# DEBUG/DEVELOPMENT FUNCTION - yashtbd
def test_real_scheduler_runtime(
    semantic_graph: SemanticGraph
):

    # --------------------------------------------------------
    # Resolve Entry Point
    # --------------------------------------------------------

    schedule_id = semantic_graph.resolve_fq_name(
        "kernel/sched/core.c",
        "schedule"
    )

    if not schedule_id:
        print("Could not resolve schedule()")
        return

    # --------------------------------------------------------
    # Runtime Reconstruction
    # --------------------------------------------------------

    runtime_engine = RuntimeExecutionEngine(
        semantic_graph
    )

    runtime_graph = (
        runtime_engine.reconstruct_execution_path(
            start_symbol_id=schedule_id,
            cpu=0,
            max_depth=16
        )
    )

    # --------------------------------------------------------
    # Print Runtime Graph
    # --------------------------------------------------------

    print_runtime_graph(
        runtime_graph,
        semantic_graph
    )

# --------------------------------------------------------
# This test function constructs a minimal semantic graph for the scheduler subsystem
# and validates that the RuntimeExecutionEngine can reconstruct the expected execution path.
# --------------------------------------------------------
# DEBUG/DEVELOPMENT FUNCTION - yashtbd
def test_scheduler_semantic_ir():

    graph = SemanticGraph()

    # --------------------------------------------------------
    # Register Scheduler Symbols
    # --------------------------------------------------------

    schedule_id = graph.register_symbol(
        name="schedule",
        file_path="kernel/sched/core.c",
        line=5000,
        kind="function"
    )

    __schedule_id = graph.register_symbol(
        name="__schedule",
        file_path="kernel/sched/core.c",
        line=5100,
        kind="function"
    )

    pick_next_task_id = graph.register_symbol(
        name="pick_next_task",
        file_path="kernel/sched/core.c",
        line=5200,
        kind="function"
    )

    __pick_next_task_id = graph.register_symbol(
        name="__pick_next_task",
        file_path="kernel/sched/core.c",
        line=5300,
        kind="function"
    )

    pick_next_task_fair_id = graph.register_symbol(
        name="pick_next_task_fair",
        file_path="kernel/sched/fair.c",
        line=8100,
        kind="function"
    )

    context_switch_id = graph.register_symbol(
        name="context_switch",
        file_path="kernel/sched/core.c",
        line=9000,
        kind="function"
    )

    __switch_to_id = graph.register_symbol(
        name="__switch_to",
        file_path="arch/x86/kernel/process.c",
        line=700,
        kind="function"
    )

    finish_task_switch_id = graph.register_symbol(
        name="finish_task_switch",
        file_path="kernel/sched/core.c",
        line=9200,
        kind="function"
    )

    # --------------------------------------------------------
    # Register Semantic Edges
    # --------------------------------------------------------

    graph.register_semantic_edge(
        schedule_id,
        __schedule_id,
        EdgeType.DIRECT_CALL,
        1.0,
        "direct_call"
    )

    graph.register_semantic_edge(
        __schedule_id,
        pick_next_task_id,
        EdgeType.DIRECT_CALL,
        1.0,
        "direct_call"
    )

    graph.register_semantic_edge(
        pick_next_task_id,
        __pick_next_task_id,
        EdgeType.DIRECT_CALL,
        1.0,
        "direct_call"
    )

    graph.register_semantic_edge(
        __pick_next_task_id,
        pick_next_task_fair_id,
        EdgeType.FUNCTION_POINTER_DISPATCH,
        0.95,
        "sched_class_dispatch"
    )

    graph.register_semantic_edge(
        pick_next_task_fair_id,
        context_switch_id,
        EdgeType.SYNTHETIC_BRIDGE,
        1.0,
        "scheduler_semantic_bridge"
    )

    graph.register_semantic_edge(
        context_switch_id,
        __switch_to_id,
        EdgeType.SYNTHETIC_BRIDGE,
        1.0,
        "context_switch_continuation"
    )

    graph.register_semantic_edge(
        __switch_to_id,
        finish_task_switch_id,
        EdgeType.SYNTHETIC_BRIDGE,
        1.0,
        "switch_to_continuation"
    )

    # --------------------------------------------------------
    # Runtime Reconstruction
    # --------------------------------------------------------

    runtime_engine = RuntimeExecutionEngine(graph)

    runtime_graph = (
        runtime_engine.reconstruct_execution_path(
            start_symbol_id=schedule_id,
            cpu=0,
            max_depth=16
        )
    )

    print_runtime_graph(
        runtime_graph,
        graph
    )

def run_subsystem_workflow(semantic_graph, profile):

    if profile == SCHEDULER_PROFILE:
        return run_scheduler_semantic_workflow(
            semantic_graph,
            profile
        )

#def build_runtime_prompt(runtime_graph, semantic_graph, query):

def main():
    global ACTIVE_PROFILE, ACTIVE_SEMANTIC_GRAPH
    if not IS_ACTIVE:
        print(f"\n[!] CANNOT CONNECT TO OLLAMA AT {OLLAMA_HOST}")
        print("-" * 50)
        print("Quick Fixes:")
        print("1. If on Windows/WSL: Run 'scripts/start_ollama.bat'")
        print("2. If on Ubuntu: Run 'ollama serve'")
        print("3. Ensure OLLAMA_HOST is set to 0.0.0.0 on the host machine.")
        print("-" * 50)
        exit(1)

    print(f"✅ Connected to Ollama at {OLLAMA_HOST}")

    while True:
        query = input("\nAsk about Linux kernel (or 'exit/stop/quit'): ").strip()

        if not query:
            print("Please enter a question about the Linux Kernel.")
            return

        if query.lower() in {"exit", "quit", "stop"}:
            return

        profile = determine_subsystem_profile(
            query
        )

        print(f"\n[Profile Detected]: {profile.subsystem_name}\n")
        if (
            ACTIVE_SEMANTIC_GRAPH is not None
            and
            ACTIVE_PROFILE == profile.subsystem_name
        ):
            semantic_graph = ACTIVE_SEMANTIC_GRAPH
            print("✅ Reusing active semantic graph from session")
            
        elif semantic_ir_cache_valid(profile):

            print("✅ Loading semantic cache...")
            start = time.time()
            semantic_graph = (
                SemanticGraph.load_semantic_ir(
                    SEMANTIC_IR_FILE
                )
            )
            ACTIVE_PROFILE = profile.subsystem_name
            ACTIVE_SEMANTIC_GRAPH = semantic_graph
            print(f"✅ Semantic cache loaded in {time.time() - start:.2f} seconds")

        else:
            print("⚙️ Building semantic graphs...")
            start = time.time()
            semantic_graph = compile_semantic_ir(
                profile
            )
            print(f"⚙️ Semantic graphs built in {time.time() - start:.2f} seconds")

            ACTIVE_PROFILE = profile.subsystem_name
            ACTIVE_SEMANTIC_GRAPH = semantic_graph

            print("⚙️ Saving semantic graphs...")
            semantic_graph.save_semantic_ir(
                SEMANTIC_IR_FILE,
                profile
            )
            print("⚙️ Saving semantic graphs completed...")


        print("Semantic graph stats:")
        if semantic_graph:
            print(semantic_graph.semantic_ir_stats())
        print("\nKernel Flow Explorer ready.")

        run_scheduler_semantic_workflow(semantic_graph, profile)

        # MermaidGraphExporter.export_runtime_graph()

        # build_runtime_prompt(runtime_graph, semantic_graph, query)

        # answer = ask_llm(prompt)

        # print("\n*********************** Answer from the LLM ************************\n")
        # print(answer)

#############################
# -----------------------------
# Main loop
# -----------------------------
if __name__ == "__main__":
    main()