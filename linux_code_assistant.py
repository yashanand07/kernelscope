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
import pickle
import subprocess
from datetime import datetime
from sentence_transformers import SentenceTransformer
import chromadb
import time



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

LOW_SIGNAL_CALLS = {
    "lockdep_assert",
    "task_is_running",
    "schedstat_inc",
    "trace_sched_switch",
    "rcu_note_context_switch",
    "might_sleep",
    "preempt_disable",
    "preempt_enable",
    "WARN_ON",
}

EXECUTION_SPINE_BOOST = {
    "schedule": 10.0,
    "__schedule": 10.0,
    "pick_next_task": 10.0,
    "__pick_next_task": 10.0,
    "pick_next_task_fair": 10.0,
    "context_switch": 10.0,
    "__switch_to": 10.0,
    "finish_task_switch": 10.0,
    "__schedule_loop": 10.0,
}

HIGH_VALUE_EXECUTION_SYMBOLS = {
    "schedule",
    "__schedule",
    "pick_next_task",
    "__pick_next_task",
    "pick_next_task_fair",
    "context_switch",
    "__switch_to",
    "finish_task_switch",
}

HIGH_VALUE_TRANSITIONS = {
    ("schedule", "__schedule"): 20.0,

    ("__schedule", "pick_next_task"): 20.0,

    ("pick_next_task", "__pick_next_task"): 20.0,

    ("__pick_next_task", "pick_next_task_fair"): 20.0,

    ("pick_next_task_fair", "context_switch"): 20.0,

    ("context_switch", "__switch_to"): 20.0,

    ("__switch_to", "finish_task_switch"): 20.0,
    ("schedule", "__schedule_loop"): 20.0,
    ("__schedule_loop", "__schedule"): 20.0,
}

MACRO_LIKE_SYMBOLS = {
    "DEFINE_WAIT_OVERRIDE_MAP",
    "WARN_ON_ONCE",
    "might_sleep",
}

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
                k: [asdict(e) for e in v]
                for k, v in self.semantic_edges_by_src.items()
            }
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

        current_symbol_id = start_symbol_id

        previous_node_id = None

        for depth in range(max_depth):

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
            ########## DEBUG CODE - PRINT CURRENT SYMBOL AND OUTGOING EDGES
            print("\nOutgoing edges from:")

            symbol = self.semantic_graph.lookup_symbol(
                current_symbol_id
            )

            print(symbol.name)

            for edge in outgoing_edges:

                dst = self.semantic_graph.lookup_symbol(
                    edge.dst_symbol_id
                )

                print(
                    f"  -> {dst.name} "
                    f"[{edge.edge_type}] "
                    f"confidence={edge.confidence}"
                )
            ########### DEBUG END
            # ------------------------------------------------
            # Highest Ranked Semantic Transition
            # ------------------------------------------------

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

# -----------------------------
# FUNCTION POINTER DETECTION (STAGE 1)
# -----------------------------
# Detect patterns like:
#   ops->enqueue_task(...)
#   file->f_op->read(...)
#
# Current state: DETECT ONLY (not yet resolved)

# Updated pattern to handle chains like p->sched_class->enqueue_task
# Updated regex to handle newlines and complex spacing in kernel code
fp_pattern = re.compile(
    r'([a-zA-Z_]\w*(?:\s*->\s*[a-zA-Z_]\w*)*)\s*->\s*([a-zA-Z_]\w*)\s*\(',
    re.MULTILINE | re.DOTALL
)
# -----------------------------
# OPS STRUCT PARSING (STAGE 1)
# -----------------------------
# Detect patterns like:
#   .enqueue_task = enqueue_task_fair
ops_assign_pattern = re.compile(
    r'\.(\w+)\s*=\s*(\w+)'
)
# -----------------------------
# CORE INDEXES
# -----------------------------
call_graph = {}        # direct calls: fn → [callee]
symbol_index = {}      # symbol → chunk(s)
symbol_freq = {}       # frequency heuristic

# -----------------------------
# FUNCTION POINTER INDEXES (TO ADD)
# -----------------------------

fp_call_graph = {}     # fn → [(obj, method)]
ops_index = {}         # method → [implementations]
#instance_ops = {}      # struct_instance → {method: impl}
#struct_instances = {}  # struct_type → instances

# -----------------------------
# CACHING LOGIC for faster iteration
# -----------------------------

CACHE_DIR = "semantic_cache"

CALL_GRAPH_FILE = os.path.join(CACHE_DIR, "call_graph.json")
FP_GRAPH_FILE = os.path.join(CACHE_DIR, "fp_call_graph.json")
SYMBOL_INDEX_FILE = os.path.join(CACHE_DIR, "symbol_index.pkl")
METADATA_FILE = os.path.join(CACHE_DIR, "metadata.json")
OPS_INDEX_FILE = os.path.join(CACHE_DIR, "ops_index.json")

# -----------------------------
# Linux Kernel commit tracking - MetaData Helpers
# -----------------------------

def get_kernel_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=LINUX_ROOT
        ).decode().strip()
    except:
        return "unknown"

def build_metadata():
    return {
        "kernel_commit": get_kernel_commit(),
        "generated_at": datetime.now().isoformat(),
        "cache_version": 1,
    }

# -----------------------------
# Semantic cache saving - to avoid repeated expensive parsing
# -----------------------------

# -----------------------------
# Semantic cache saving
# Avoid repeated expensive kernel parsing
# -----------------------------

def save_semantic_cache(
    call_graph,
    fp_call_graph,
    symbol_index,
    ops_index
):
    start = time.time()
    os.makedirs(CACHE_DIR, exist_ok=True)

    # -----------------------------
    # JSON-safe conversions
    # -----------------------------

    serializable_call_graph = {
        k: list(v)
        for k, v in call_graph.items()
    }

    serializable_fp_graph = {
        k: v
        for k, v in fp_call_graph.items()
    }

    serializable_ops_index = {
        k: list(v)
        for k, v in ops_index.items()
    }

    # -----------------------------
    # Save semantic graphs
    # -----------------------------

    with open(CALL_GRAPH_FILE, "w") as f:
        json.dump(serializable_call_graph, f, indent=2)

    with open(FP_GRAPH_FILE, "w") as f:
        json.dump(serializable_fp_graph, f, indent=2)

    with open(OPS_INDEX_FILE, "w") as f:
        json.dump(serializable_ops_index, f, indent=2)

    # -----------------------------
    # Save symbol index
    # -----------------------------

    with open(SYMBOL_INDEX_FILE, "wb") as f:
        pickle.dump(symbol_index, f)

    # -----------------------------
    # Save metadata
    # -----------------------------

    with open(METADATA_FILE, "w") as f:
        json.dump(build_metadata(), f, indent=2)

    print(f"✅ Semantic cache saved in {time.time() - start:.2f} seconds")

# -----------------------------
# Semantic cache loading
# -----------------------------

def load_semantic_cache():

    # -----------------------------
    # Load semantic graph artifacts
    # -----------------------------

    with open(CALL_GRAPH_FILE) as f:
        call_graph = json.load(f)

    with open(FP_GRAPH_FILE) as f:
        fp_call_graph = json.load(f)

    with open(OPS_INDEX_FILE) as f:
        ops_index = json.load(f)

    # -----------------------------
    # Load symbol database
    # -----------------------------

    with open(SYMBOL_INDEX_FILE, "rb") as f:
        symbol_index = pickle.load(f)

    # -----------------------------
    # Restore set-based structures
    # -----------------------------

    call_graph = {
        k: set(v)
        for k, v in call_graph.items()
    }

    ops_index = {
        k: set(v)
        for k, v in ops_index.items()
    }

    return (
        call_graph,
        fp_call_graph,
        symbol_index,
        ops_index,
    )

# -----------------------------
# MetaData validation - check if cache is still valid for current kernel commit
# -----------------------------

def cache_valid():

    required_files = [
        CALL_GRAPH_FILE,
        FP_GRAPH_FILE,
        SYMBOL_INDEX_FILE,
        OPS_INDEX_FILE,
        METADATA_FILE,
    ]

    if not all(os.path.exists(f) for f in required_files):
        return False

    try:
        with open(METADATA_FILE) as f:
            metadata = json.load(f)

        current_commit = get_kernel_commit()

        return metadata.get("kernel_commit") == current_commit

    except:
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

def compile_semantic_ir():

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
            # current_src_symbol_id = semantic_graph.register_symbol(
            #     name=symbol,
            #     file_path=data["file"],
            #     line=0,
            #     kind="function"
            # )
            code = data["code"]

            #if "sched_class" in code:
            #    print("FOUND sched_class usage in:", symbol)

            # Build symbol index & allow duplicate symbol names
            #yashtbd
            #pass2
            # entry = symbol_index.setdefault(symbol.lower(), {
            #     "symbol": symbol,
            #     "file": data["file"],
            #     "code": ""
            # })

            # entry["code"] += "\n" + code
            # For debugging: print the first 200 chars of the code 
            # for __pick_next_task to verify it's being loaded correctly
            #if symbol == "__pick_next_task":
                #print("CODE SNIPPET:\n", code[:500])
                #print("FP MATCHES FULL:", fp_pattern.findall(entry["code"])[:5])

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

                # dst_symbol_id = semantic_graph.register_symbol(
                #     name=callee,
                #     file_path=callee_file,
                #     line=0,     # Change later to actual line if found in symbol_index
                #     kind="function"
                # )

                if callee in LOW_SIGNAL_CALLS:
                    confidence = 0.1
                else:
                    confidence = 1.0
                if callee in EXECUTION_SPINE_BOOST:
                    confidence += EXECUTION_SPINE_BOOST[callee]
                transition_key = (symbol, callee)
                if transition_key in HIGH_VALUE_TRANSITIONS:
                    confidence += HIGH_VALUE_TRANSITIONS[
                        transition_key
                    ]
                semantic_graph.register_semantic_edge(
                    src_symbol_id=current_src_symbol_id,
                    dst_symbol_id=dst_symbol_id,
                    edge_type=EdgeType.DIRECT_CALL,
                    confidence=confidence,
                    resolution_source="regex_call_parse"
                )

            #matches = ops_assign_pattern.findall(entry["code"]) # Change later to 346 line
            # full_code = symbol_index[symbol.lower()]["code"]
            # matches = ops_assign_pattern.findall(full_code)

            # for field, impl in matches:
            #     if field in VALID_OPS:
            #         ops_index.setdefault(field, set()).add(impl)

    # -----------------------------
    # FIX: Load full function ONCE
    # -----------------------------
    if "__pick_next_task" in symbol_index:
        full = load_full_function("__pick_next_task")
        if full:
            symbol_index["__pick_next_task"]["code"] = full

        #print("FP MATCHES FULL:",
        #    fp_pattern.findall(symbol_index["__pick_next_task"]["code"])[:5])
    #print("Call graph loaded:", len(call_graph))
    #print(call_graph.get("pick_next_task"))
    #print(call_graph.get("__pick_next_task"))
    #print("Building Full FP Call Graph...")
    SYNTHETIC_SCHED_BRIDGES = {
        "pick_next_task_fair": "context_switch",
        "pick_next_task_rt": "context_switch",
        "pick_next_task_idle": "context_switch",

        "context_switch": "__switch_to",

        "__switch_to": "finish_task_switch",
    }
    for key, entry in symbol_index.items():

        symbol = entry["symbol"].strip()

        full_code = entry["code"]



        # Only FP-heavy functions require full reconstruction.
        if any(hint in full_code for hint in INDIRECT_CALL_HINTS):
            loaded = load_full_function(symbol)
            if loaded:
                full_code = loaded

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
                    if callee in LOW_SIGNAL_CALLS:
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

    for src_name, dst_name in SYNTHETIC_SCHED_BRIDGES.items():

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
        call_graph,
        fp_call_graph,
        symbol_index,
        ops_index,
        semantic_graph,
    )

# -----------------------------
# Function body loader using Ctags metadata
# -----------------------------

def load_full_function(symbol):
    """Uses Ctags metadata to jump to the correct file and extract a function body."""
    files = ctags_index.get(symbol, [])
    if not files: return None

    for f_path in files:
        try:
            with open(f_path, "r") as file:
                content = file.read()
                # Handles: symbol(...) and symbol __sched (...)
                match = re.search(rf"\b{symbol}\b\s*\(", content)
                if not match:
                    match = re.search(rf"\b{symbol}\b\s+__\w+\s*\(", content)
                
                if not match: continue
                
                idx = content.rfind("\n", 0, match.start())
                start = content.find("{", idx)
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
# =================================================================
# SECTION 4 - Subsystem Profiles of the Linux kernel - Ends
# =================================================================


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

# Add code here to parse ops struct assignments and populate ops_index

if cache_valid():

    print("✅ Loading semantic cache...")
    start = time.time()

    (
        call_graph,
        fp_call_graph,
        symbol_index,
        ops_index,
    ) = load_semantic_cache()
    print(f"✅ Semantic cache loaded in {time.time() - start:.2f} seconds")
else:

    print("⚙️ Building semantic graphs...")
    start = time.time()
    # (
    #     call_graph,
    #     fp_call_graph,
    #     symbol_index,
    #     ops_index,
    # ) = build_semantic_graphs()

    (
        call_graph,
        fp_call_graph,
        symbol_index,
        ops_index,
        semantic_graph
    ) = compile_semantic_ir()

    print(
        len(semantic_graph.symbol_table)
    )

    edge_count = sum(
        len(v)
        for v in semantic_graph.semantic_edges_by_src.values()
    )

    print(f"⚙️ Semantic graphs built in {time.time() - start:.2f} seconds")
    save_semantic_cache(
        call_graph,
        fp_call_graph,
        symbol_index,
        ops_index
    )
#print("FP Analysis complete.")
print("\nKernel Flow Explorer ready.")
# print("FP GRAPH __pick_next_task:",
#       fp_call_graph.get("__pick_next_task"))
# if "__schedule" in symbol_index:
#     code = symbol_index["__schedule"]["code"]
#     print("FINAL LENGTH:", len(code))
#     print("HAS pick_next_task:", "pick_next_task(" in code)
#print("Ask questions about Linux kernel execution paths.\n")


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


# -------------------------------
# Execution path tracing - Tracer
# -------------------------------
def trace_execution_path(symbol, query, depth=8):

    domains = detect_domains(query)

    query_tokens = {
        t for t in token_pattern.findall(query.lower())
        if t not in STOPWORDS
    }

    # Template guidance
    template = []
    for d in domains:
        template.extend(KERNEL_EXECUTION_TEMPLATES.get(d, []))
    template_set = set(template)

    path = [symbol]
    visited = {symbol}
    current = symbol

    # Strict scheduler backbone only
    FAST_PATH = {
        "schedule": "__schedule",
        "__schedule": "pick_next_task",
        "pick_next_task": "__pick_next_task",
    }

    for _ in range(depth):

        current = current.strip()
        #print(f"[TRACE] current = {current}")

        # -----------------------------
        # FAST PATH (STRICTLY LIMITED)
        # -----------------------------
        if current in {"schedule", "__schedule", "pick_next_task"}:
            next_fn = FAST_PATH[current]
            if next_fn in symbol_index and next_fn not in visited:
                path.append(next_fn)
                visited.add(next_fn)
                #print(f"[FAST-PATH] {current} -> {next_fn}")
                current = next_fn
                continue

        # -----------------------------
        # Base callees
        # -----------------------------
        callees = list(call_graph.get(current, []))

        # -----------------------------
        # FP RESOLUTION
        # -----------------------------
        fp_derived = set()

        fps_in_current = fp_call_graph.get(current, [])
        if fps_in_current:
            #print(f"[FP FOUND in {current}]: {fps_in_current}")

            NON_DISPATCH_FIELDS = {
                "on_cpu", "state", "se", "nvcsw", "nivcsw",
                "prio", "policy", "flags", "sched_class", "rq"
            }
            for obj, method in fps_in_current:

                # Filter non-dispatch fields
                if method in NON_DISPATCH_FIELDS:
                    continue
                if method in ops_index:
                    impls = sorted(ops_index[method])[:3]

                    #print(f"[FP RESOLVED] {obj}->{method} => {impls}")

                    for impl in impls:
                        if impl not in callees:
                            callees.append(impl)

                    fp_derived.update(impls)

                # fallback if no ops info
                elif method in ctags_index and method.startswith(
                    ("pick_", "enqueue_", "dequeue_", "task_", "irq_", "ndo_", "file_")
                ):
                    callees.append(method)

        #else:
        #    print(f"[NO FP in {current}]")

        # -----------------------------
        # SEMANTIC FLOW FIX (CRITICAL)
        # -----------------------------
        if current == "pick_next_task_fair":
            if "context_switch" in ctags_index:
                callees.append("context_switch")

        # -----------------------------
        # CONTEXT SWITCH CONTINUATION
        # -----------------------------
        #yashtbd
        # Should disappear for semantic Graphs
        if current == "context_switch":
            callees.insert(0, "__switch_to")

        # -----------------------------
        # SWITCH_TO CONTINUATION
        # -----------------------------
        if current == "__switch_to":
            if "finish_task_switch" in ctags_index:
                callees.append("finish_task_switch")

        # Deduplicate AFTER all expansions
        callees = list(dict.fromkeys(callees))

        if not callees:
            break

        # -----------------------------
        # SCORING
        # -----------------------------
        scored = []

        ARCH_SYNTHETIC = {
            "__switch_to",
            "finish_task_switch"
        }
        for c in callees:

            if (c not in ctags_index
                and c not in fp_derived
                and c not in call_graph
                and c not in ARCH_SYNTHETIC):
                continue

            score = 0
            c_lower = c.lower()

            # FP dominance
            if c in fp_derived:
                score += 300

            # Scheduler backbone guidance
            if current == "__schedule" and c == "pick_next_task":
                score += 200

            if current == "pick_next_task" and c == "__pick_next_task":
                score += 200

            # Query relevance
            score += sum(t in c_lower for t in query_tokens) * 5

            # Template guidance
            if c in template_set:
                score += 10

            # Demo-friendly bias
            if "scheduler" in domains and "fair" in c_lower:
                score += 20

            # RETURN FLOW (ONLY AFTER FAIR SELECTION)
            if current == "pick_next_task_fair" and c == "context_switch":
                score += 400

            #yashtbd
            # Should disappear for semantic Graphs
            if current == "context_switch":
                if c == "__switch_to":
                    score += 1000   # force correct transition
                elif c == "finish_task_switch":
                    score -= 500    # prevent premature jump

            if current == "__switch_to" and c == "finish_task_switch":
                score += 300

            scored.append((score, c))

        if not scored:
            break

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        next_fn = scored[0][1]

        if next_fn in visited:
            break

        path.append(next_fn)
        visited.add(next_fn)
        #print(f"[TRACE-NEXT] {path[-2]} -> {next_fn}")
        current = next_fn

    return path[:12]

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

# --------------------------------------------------------
# Test function to validate runtime reconstruction of the
# scheduler execution path using the semantic graph.
# --------------------------------------------------------
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
#############################
# -----------------------------
# Main loop
# -----------------------------
#endpoint, is_active = get_ollama_config()

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
# Now proceed with your Analysis Engine logic...

# Isolated IR Validation
#test_scheduler_semantic_ir()
(
    call_graph,
    fp_call_graph,
    symbol_index,
    ops_index,
    semantic_graph,
) = compile_semantic_ir()

# Working for the scheduler subsystem but needs more tuning and validation for others,
# especially interrupt handling which has more complex patterns and less direct calls.
test_real_scheduler_runtime(
    semantic_graph
)

exit(0)
# code below this is not in the critical path for the IR testing and
# will be used for interactive exploration once the IR-based runtime reconstruction is validated.
while True:
    
    query = input("\nAsk about Linux kernel (or 'exit/stop/quit'): ").strip()

    if not query:
        print("Please enter a question about the Linux Kernel.")
        continue

    if query.lower() in {"exit", "quit", "stop"}:
        break

    docs, metas = retrieve_code(query)

    if not metas:
        continue

    # Logic is based on domain and not subsystem because many functions are shared
    # across subsystems, but domain detection is still useful for prompt construction
    # and execution path heuristics
    # Step 1: get top symbol
    top_symbol = metas[0]["symbol"]

    #Step 2: detect domains
    domains = detect_domains(query)
    domain = domains[0]

    # Step 3: Normalize symbol
    if top_symbol == "context_switch":
        top_symbol = "schedule"

    if top_symbol in ENTRY_POINT_MAP:
        top_symbol = ENTRY_POINT_MAP[top_symbol]

    # Step 4: Override with correct entry points based on detected domain for better execution path tracing
    top_symbol = get_entry_point(top_symbol, domains)

    # Step 5: expand context with callees of the top symbol to provide more execution flow info to the LLM
    append_callees(top_symbol, docs, metas)

    # Step 6: trace execution
    path = trace_execution_path(top_symbol, query)

    print("\nDetected kernel execution path:\n")
    for p in path:
        print(" →", p)

    export_execution_path(path, domains, query)

    chain = path

    prompt = build_prompt(query, docs, domain, chain)

    answer = ask_llm(prompt)

    print("\n*********************** Answer from the LLM ************************\n")
    print(answer)

# -----------------------------
# Semantic graph compilation
# Builds:
#   - call graph
#   - FP dispatch graph
#   - symbol index
#   - ops dispatch index
# Will keep this function for reference but the main code now uses compile_semantic_ir()
# which constructs a unified semantic graph instead of separate structures.
# This can act as the fallback mechanism if there are issues with the new IR-based approach,
# and also serves as a reference for how the semantic graph is constructed from the raw data.
# If runtime construction stalls or fails then we fallback to this 
# simpler approach which is less precise but more robust.
# -----------------------------
"""
def build_semantic_graphs():

    call_graph = {}
    fp_call_graph = {}
    symbol_index = {}
    ops_index = {}
    symbol_freq = {}
    with open("chunks.jsonl") as f:
        for line in f:
            data = json.loads(line)

            symbol = data["symbol"]
            code = data["code"]




            #if "sched_class" in code:
            #    print("FOUND sched_class usage in:", symbol)

            # Build symbol index & allow duplicate symbol names
            #yashcache
            entry = symbol_index.setdefault(symbol.lower(), {
                "symbol": symbol,
                "file": data["file"],
                "code": ""
            })

            entry["code"] += "\n" + code
            # For debugging: print the first 200 chars of the code
            # for __pick_next_task to verify it's being loaded correctly
            #if symbol == "__pick_next_task":
                #print("CODE SNIPPET:\n", code[:500])
                #print("FP MATCHES FULL:", fp_pattern.findall(entry["code"])[:5])

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

            matches = ops_assign_pattern.findall(entry["code"]) # Change later to 346 line

            for field, impl in matches:
                if field in VALID_OPS:
                    ops_index.setdefault(field, set()).add(impl)

    # -----------------------------
    # FIX: Load full function ONCE
    # -----------------------------
    if "__pick_next_task" in symbol_index:
        full = load_full_function("__pick_next_task")
        if full:
            symbol_index["__pick_next_task"]["code"] = full

        #print("FP MATCHES FULL:",
        #    fp_pattern.findall(symbol_index["__pick_next_task"]["code"])[:5])
    #print("Call graph loaded:", len(call_graph))
    #print(call_graph.get("pick_next_task"))
    #print(call_graph.get("__pick_next_task"))
    #print("Building Full FP Call Graph...")

    for key, entry in symbol_index.items():

        symbol = entry["symbol"].strip()

        full_code = entry["code"]



        # Only FP-heavy functions require full reconstruction.
        if any(hint in full_code for hint in INDIRECT_CALL_HINTS):
            loaded = load_full_function(symbol)
            if loaded:
                full_code = loaded

        matches = [
            (obj.strip(), fn.strip())
            for obj, fn in fp_pattern.findall(full_code)
            if fn not in IGNORE_CALLS
        ]

        #yashcache
        if matches:
            fp_call_graph[symbol.strip()] = list(set(matches))
    return (
        call_graph,
        fp_call_graph,
        symbol_index,
        ops_index,
    )
"""