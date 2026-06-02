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
from runtime_reconstruction.implementation_descent import (
    reconstruct_implementation_path
)
from runtime_reconstruction.runtime_spine import (
    reconstruct_runtime_spine
)

from runtime_reconstruction.dispatch_analysis import (
    reconstruct_dispatch_path
)

from runtime_reconstruction.full_branch_expansion import (
    reconstruct_full_branch_path
)
from profiles.subsystem_profile import (
    SubsystemSemanticProfile
)
from profiles.scheduler_profile import (
    SCHEDULER_PROFILE
)
from semantic_runtime.traversal_modes import (
    TraversalMode
)
from semantic_runtime.ontology import (
    SemanticEdgeType
)
from semantic_runtime.runtime_graph import (
    RuntimeExecutionGraph,
    ExecutionNode,
    ExecutionEdge
)
from enum import Enum
from hashlib import sha1
from typing import Dict, List, Optional, Set, Any
from visualization.runtime_graph_printer import (
    RuntimeGraphPrinter
)
from visualization.mermaid_exporter import (
    MermaidGraphExporter
)

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
import pickle

MAX_DEPTH = 8
MAX_RUNTIME_NODES = 8
DEBUG = False
LINUX_ROOT = os.environ.get(
    "LINUX_ROOT",
    "."
)
ACTIVE_PROFILE = None
ACTIVE_SEMANTIC_BUNDLE = None
CURRENT_IR_VERSION = 1






CACHE_DIR = "semantic_cache"

SEMANTIC_IR_FILE = os.path.join(
    CACHE_DIR,
    "semantic_ir.json"
)
SEMANTIC_IR_BUNDLE_FILE = os.path.join(
    CACHE_DIR,
    "semantic_ir_bundle.pkl"
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

    edge_type: SemanticEdgeType

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

        self.semantic_edge_index = {}

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
        edge_type: SemanticEdgeType
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
        edge_type: SemanticEdgeType,
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
        # Edge Lookup Index
        # ----------------------------------------------------

        self.semantic_edge_index[
            edge.edge_id
        ] = edge

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

                self.semantic_edge_index[
                    edge.edge_id
                ] = edge

    def number_of_edges(self):
        count = 0
        for edges in self.semantic_edges_by_src.values():
            count += len(edges)
        return count

    def dispatch_edges(self):
        count = 0
        for edges in self.semantic_edges_by_src.values():
            for edge in edges:
                if edge.edge_type == SemanticEdgeType.FUNCTION_POINTER_DISPATCH:
                    count += 1
        dispatch_edge_count = count
        if DEBUG:
            print(
                f"Dispatch edges reconstructed: "
                f"{dispatch_edge_count}"
            )

        return count

    def synthetic_edges(self):
        count = 0
        for edges in self.semantic_edges_by_src.values():
            for edge in edges:
                if edge.edge_type == SemanticEdgeType.SYNTHETIC_CONTINUATION :
                    count += 1
        if DEBUG:
            print(
                f"Synthetic edges reconstructed: "
                f"{count}"
            )
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

   
# ============================================================
# SECTION 2 - Runtime Execution Layer - Ends
# ============================================================

@dataclass
class SemanticIRBundle:

    semantic_graph: SemanticGraph

    symbol_code_index: Dict[str, str]

    ops_index: Dict[str, Set[str]]

    metadata: Dict[str, Any]

    @staticmethod
    def save_semantic_ir_bundle(
        bundle,
    ):
        os.makedirs(CACHE_DIR, exist_ok=True)

        with open(SEMANTIC_IR_BUNDLE_FILE, "wb") as f:
            pickle.dump(bundle, f)

    @staticmethod
    def load_semantic_ir_bundle():
        os.makedirs(CACHE_DIR, exist_ok=True)
        try:
            with open(SEMANTIC_IR_BUNDLE_FILE, "rb") as f:
                bundle = pickle.load(f)
                return bundle
        except Exception as e:
            print(f"Error loading semantic IR bundle: {e}")
            return None

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
    r"\.(\w+)\s*=\s*([A-Za-z0-9_]+)\s*,",
    re.MULTILINE
)

# Cache metadata file path.
#METADATA_FILE = os.path.join(CACHE_DIR, "metadata.json")

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
    """
    Return True if the semantic IR bundle
    exists and is compatible with the
    current kernel + subsystem profile.
    """

    bundle_path = SEMANTIC_IR_BUNDLE_FILE;
    # os.path.join(
    #     CACHE_DIR,
    #     "semantic_ir_bundle.pkl"
    # )

    if not os.path.exists(bundle_path):
        print("Semantic IR cache bundle missing.", bundle_path)
        return False

    try:
        bundle = SemanticIRBundle.load_semantic_ir_bundle()

        if bundle is None:
            print("Failed to load semantic IR bundle.")
            return False

        metadata = bundle.metadata

        current_commit = get_kernel_commit()

        cached_profiles = metadata.get(
            "subsystem_profiles",
            []
        )
        if DEBUG:
            print(
                "Cache metadata loaded. "
                f"Kernel commit: "
                f"{metadata['kernel']['commit']}, "
                f"Current commit: "
                f"{current_commit}, "
            f"Cached profiles: "
            f"{cached_profiles}"
        )

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

def build_dispatch_index(
    symbol_index,
    profile
):

    ops_index = {}

    for key, entry in symbol_index.items():

        symbol = entry["symbol"].strip()

        loaded = entry["code"]

        if not profile.requires_dispatch_analysis(symbol):
            continue

        provider_pattern = (
            profile.resolve_provider_pattern(symbol)
        )

        if provider_pattern is None:
            continue

        matches = ops_assign_pattern.findall(loaded)

        for field, impl in matches:

            if field in VALID_OPS: #yashtbd To be changed to VALID_DISPATCH_OPERATIONS
                ops_index.setdefault(field, set()).add(impl)

    return ops_index


def resolve_dispatch_edges(
    semantic_graph,
    symbol_index,
    ops_index,
    profile
):

    for key, entry in symbol_index.items():

        symbol = entry["symbol"].strip()

        if profile.subsystem_name not in entry["file"]:
            continue

        loaded = load_full_function(symbol)

        if loaded:
            full_code = loaded
        else:
            full_code = entry["code"]

        matches = [
            (obj.strip(), fn.strip())
            for obj, fn in fp_pattern.findall(full_code)
            if fn not in IGNORE_CALLS
        ]

        if matches:
            for obj, method in matches:

                if method not in ops_index:
                    if DEBUG:
                        print(
                            f"Dispatch method={method}, "
                            f"in ops_index={method in ops_index}"
                        )
                    continue

                implementations = ops_index[method]
                if DEBUG:
                    print(
                        f"Resolved implementations for "
                        f"{method}: {implementations}"
                    )

                for impl in implementations:

                    if impl.lower() in symbol_index:
                        impl_file = symbol_index[impl.lower()]["file"]
                    else:
                        impl_file = "unknown"
                    dst_symbol_id = semantic_graph.resolve_symbol_by_name(impl)

                    if not dst_symbol_id:
                        continue
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

                        edge_type=SemanticEdgeType.FUNCTION_POINTER_DISPATCH,

                        confidence=confidence,

                        resolution_source="ops_dispatch_parse",

                        is_deterministic=False
                    )

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
    symbol_code_index = {}

    # call the 1st pass to register all symbols and build the symbol index with code snippets
    # Phase 1 - Symbol Registration and Indexing - We first register
    # all symbols to build the semantic graph's symbol table.
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
            symbol_code_index[symbol] = code

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
                    edge_type=SemanticEdgeType.DIRECT_CALL,
                    confidence=confidence,
                    resolution_source="regex_call_parse"
                )

    # ============================================================
    # Phase 3: Build Dispatch Implementation Index
    # ============================================================

    ops_index = build_dispatch_index(
        symbol_index,
        profile
    )

    print(
        f"Dispatch implementation fields discovered: "
        f"{len(ops_index)}"
    )

    # ============================================================
    # Phase 4: Resolve Function Pointer Dispatches
    # ============================================================

    resolve_dispatch_edges(
        semantic_graph,
        symbol_index,
        ops_index,
        profile
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

            edge_type=SemanticEdgeType.SYNTHETIC_CONTINUATION ,

            confidence=confidence,

            resolution_source="synthetic_scheduler_bridge",

            is_deterministic=True
        )


    bundle = SemanticIRBundle(
        semantic_graph=semantic_graph,
        symbol_code_index=symbol_code_index,
        ops_index=ops_index,
        metadata=generate_semantic_ir_metadata(
            semantic_graph,
            profile
        )
    )

    return bundle


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
            if DEBUG:
                print(f"Error loading definition for {symbol} from {full_path}")
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





def determine_subsystem_profile(query: str):
    if "sched" in query.lower():
        return SCHEDULER_PROFILE



# =================================================================
# SECTION 4 - Subsystem Profiles of the Linux kernel - Ends
# =================================================================

def run_semantic_workflow(
    semantic_graph,
    profile,
    traversal_mode
):

    runtime_engine = RuntimeExecutionEngine(
        semantic_graph
    )

    # Resolve subsystem entrypoint
    entrypoint = profile.entrypoints[0]

    start_symbol_id = (
        semantic_graph.resolve_symbol_by_name(
            entrypoint
        )
    )

    if not start_symbol_id:
        raise RuntimeError(
            f"Unable to resolve entrypoint: "
            f"{entrypoint}"
        )

    # Runtime Spine Traversal
    if (
        traversal_mode ==
        TraversalMode.RUNTIME_SPINE
    ):
        runtime_graph = (
            reconstruct_runtime_spine(
                runtime_engine=runtime_engine,
                profile=profile,
                start_symbol_id=start_symbol_id,
                cpu=0,
                max_depth=MAX_DEPTH
            )
        )

    # Implementation Descent
    elif (
        traversal_mode ==
        TraversalMode.IMPLEMENTATION_DESCENT
    ):
        runtime_graph = (
            reconstruct_implementation_path(
                runtime_engine=runtime_engine,
                profile=profile,
                start_symbol_id=start_symbol_id,
                cpu=0,
                max_depth=MAX_DEPTH
            )
        )

    #
    # Dispatch Analysis
    #
    elif (
        traversal_mode ==
        TraversalMode.DISPATCH_ANALYSIS
    ):
        runtime_graph = (
            reconstruct_dispatch_path(
                runtime_engine=runtime_engine,
                profile=profile,
                start_symbol_id=start_symbol_id,
                cpu=0,
                max_depth=MAX_DEPTH
            )
        )

    # Full Branch Expansion
    elif (
        traversal_mode ==
        TraversalMode.FULL_BRANCH_EXPANSION
    ):
        runtime_graph = (
            reconstruct_full_branch_path(
                runtime_engine=runtime_engine,
                profile=profile,
                start_symbol_id=start_symbol_id,
                cpu=0,
                max_depth=MAX_DEPTH
            )
        )

    else:
        raise RuntimeError(
            f"Unsupported traversal mode: "
            f"{traversal_mode}"
        )

    RuntimeGraphPrinter.print_graph(
        runtime_graph,
        semantic_graph
    )

    return runtime_graph


# =================================================================
# 3. KERNEL HEURISTICS & TEMPLATES
# =================================================================

VALID_OPS = {
    "pick_next_task",
    "pick_task",
    "enqueue_task",
    "dequeue_task",
    "check_preempt_curr",
    "yield_task",
    "wakeup_preempt",
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

#---------------------------------------
# Prompt builder - Constructs a detailed prompt for
# the LLM based on the runtime graph, semantic graph,
# query, and relevant code snippets.
#---------------------------------------
def build_runtime_prompt(
    runtime_graph,
    semantic_graph,
    query,
    profile,
    symbol_code_index
):

    MAX_CODE_CHARS = 6000

    runtime_lines = []
    semantic_lines = []
    code_blocks = []

    #
    # Runtime execution flow
    #
    for edge in runtime_graph.edges:

        src_node = runtime_graph.nodes[
            edge.src_node_id
        ]

        dst_node = runtime_graph.nodes[
            edge.dst_node_id
        ]

        src_symbol = semantic_graph.lookup_symbol(
            src_node.symbol_id
        )

        dst_symbol = semantic_graph.lookup_symbol(
            dst_node.symbol_id
        )

        context = edge.execution_context.upper()

        runtime_lines.append(
            f"[{context}] "
            f"{src_symbol.name} "
            f" -> "
            f"{dst_symbol.name}"
        )

    #
    # Semantic dispatch edges
    #
    for edge in (
        semantic_graph
        .semantic_edge_index
        .values()
    ):

        if (
            edge.edge_type !=
            SemanticEdgeType.FUNCTION_POINTER_DISPATCH
        ):
            continue

        src_symbol = semantic_graph.lookup_symbol(
            edge.src_symbol_id
        )

        dst_symbol = semantic_graph.lookup_symbol(
            edge.dst_symbol_id
        )

        semantic_lines.append(
            f"[DISPATCH] "
            f"{src_symbol.name} "
            f"-> "
            f"{dst_symbol.name}"
        )

    #
    # Collect code for runtime symbols
    #
    seen = set()

    runtime_nodes = list(
        runtime_graph.nodes.values()
    )[:MAX_RUNTIME_NODES]

    for node in runtime_nodes:

        symbol = semantic_graph.lookup_symbol(
            node.symbol_id
        )

        if symbol.name in seen:
            continue

        seen.add(symbol.name)

        code = symbol_code_index.get(
            symbol.name
        )

        if not code:
            continue

        code_blocks.append(
            f"FILE: {symbol.file_path}\n"
            f"SYMBOL: {symbol.name}\n\n"
            f"{code[:600]}"
        )

    code_context = "\n\n".join(
        code_blocks
    )[:MAX_CODE_CHARS]

    runtime_text = "\n".join(runtime_lines)

    semantic_text = "\n".join(semantic_lines)

    prompt = f"""
You are a senior Linux kernel engineer.

QUESTION:
{query}

SUBSYSTEM:
{profile.subsystem_name}

RUNTIME EXECUTION FLOW:
{runtime_text}

SEMANTIC DISPATCH FLOW:
{semantic_text}

RELEVANT KERNEL CODE:
{code_context}

Instructions:

1. Explain the actual runtime execution path.
2. Explain scheduler/runtime state transitions.
3. Explain indirect dispatch behavior.
4. Distinguish direct calls from polymorphic dispatch.
5. Explain subsystem interactions.
6. Explain why the runtime path evolves this way.
7. Use the semantic dispatch flow when describing scheduler class behavior.
8. Avoid generic Operating System explanations
9. Use only the provided runtime graph and kernel code.
10. Do not assume any scheduler behavior or transitions that are not explicitly present in the runtime graph.
11. Focus on Linux kernel specifics and execution behavior.
12. The runtime execution graph is the primary source of truth.
13. Do not infer additional scheduler transitions not explicitly present in the runtime graph.
14. If a transition is not present in the runtime graph, do not describe it as part of the execution flow.
15. Do not substitute Linux kernel textbook knowledge for the provided runtime graph.
16. Follow the runtime graph edges exactly in order.
"""

    return prompt

#---------------------------------------
# LLM call - Sends the constructed prompt
# to the LLM and returns the response.
#---------------------------------------
def ask_llm(
    prompt,
    model="qwen2.5-coder:7b",
    temperature=0.1,
    num_predict=1200,
    debug=False
):

    if DEBUG:
        print(
            "PROMPT SIZE:",
            len(prompt)
        )
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        }
    }

    if DEBUG:

        print("\n========== LLM PROMPT ==========\n")

        print(prompt[:12000])

        print("\n========== END PROMPT ==========\n")

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=300
        )

        response.raise_for_status()

        data = response.json()

        answer = data.get(
            "response",
            ""
        ).strip()

        if DEBUG:

            print("\n========== LLM RESPONSE ==========\n")

            print(answer)

            print("\n=================================\n")

        return answer

    except requests.exceptions.Timeout:

        return (
            "LLM timed out. "
            "Try reducing runtime graph size."
        )

    except requests.exceptions.ConnectionError:

        return (
            "Could not connect to Ollama."
        )

    except Exception as e:

        return f"LLM error: {str(e)}"


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
# def test_real_scheduler_runtime(
#     semantic_graph: SemanticGraph
# ):

#     # --------------------------------------------------------
#     # Resolve Entry Point
#     # --------------------------------------------------------

#     schedule_id = semantic_graph.resolve_fq_name(
#         "kernel/sched/core.c",
#         "schedule"
#     )

#     if not schedule_id:
#         print("Could not resolve schedule()")
#         return

#     # --------------------------------------------------------
#     # Runtime Reconstruction
#     # --------------------------------------------------------

#     runtime_engine = RuntimeExecutionEngine(
#         semantic_graph
#     )

#     runtime_graph = (
#         runtime_engine.reconstruct_execution_path(
#             start_symbol_id=schedule_id,
#             cpu=0,
#             max_depth=MAX_DEPTH
#         )
#     )

    # --------------------------------------------------------
    # Print Runtime Graph
    # --------------------------------------------------------

    RuntimeGraphPrinter.print_graph(
        runtime_graph,
        semantic_graph
    )


def parse_mode(
    query: str
):

    query = query.strip()

    if query.startswith("1-"):
        return (
            TraversalMode.RUNTIME_SPINE,
            query[2:].strip()
        )

    elif query.startswith("2-"):
        return (
            TraversalMode.IMPLEMENTATION_DESCENT,
            query[2:].strip()
        )

    elif query.startswith("3-"):
        return (
            TraversalMode.DISPATCH_ANALYSIS,
            query[2:].strip()
        )

    elif query.startswith("4-"):
        return (
            TraversalMode.FULL_BRANCH_EXPANSION,
            query[2:].strip()
        )

    else:
        return (
            TraversalMode.RUNTIME_SPINE,
            query
        )

def print_query_modes():

    print(
        """
Create your query with one prefix:

1 - Runtime Spine Analysis (Default)
    Follow dominant subsystem execution flow

2 - Implementation Descent
    Dive into low-level implementation details

3 - Dispatch Analysis
    Explore runtime function-pointer dispatch

4 - Full Branch Exploration
    Enumerate all semantic execution paths

Example:
"1-Explain the Linux scheduler"
"""
    )

def main():
    global ACTIVE_PROFILE, ACTIVE_SEMANTIC_BUNDLE
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
        print_query_modes()

        query = input(
            "(or 'exit/stop/quit'): "
        ).strip()
        #yashtbd
        # From the query we find the traversal_mode and then imbark upon creating the
        # runtime graph using the semantic graph and then build a detailed prompt
        # for the LLM to answer the question based on the runtime graph,
        # semantic graph, and relevant code snippets.
        traversal_mode, cleaned_query = parse_mode(query)

        if not cleaned_query:
            print("Please enter a question about the Linux Kernel.")
            return

        if cleaned_query.lower() in {"exit", "quit", "stop"}:
            return

        profile = determine_subsystem_profile(
            cleaned_query
        )

        print(f"\n[Profile Detected]: {profile.subsystem_name}\n")
        if (
            ACTIVE_SEMANTIC_BUNDLE is not None
            and
            ACTIVE_PROFILE == profile.subsystem_name
        ):
            semantic_graph = ACTIVE_SEMANTIC_BUNDLE.semantic_graph
            symbol_code_index = ACTIVE_SEMANTIC_BUNDLE.symbol_code_index
            print("✅ Reusing active semantic graph from session")

        elif semantic_ir_cache_valid(profile):

            print("✅ Loading semantic cache...")
            start = time.time()
            # semantic_graph = (
            #     SemanticGraph.load_semantic_ir(
            #         SEMANTIC_IR_FILE
            #     )
            # )
            bundle = SemanticIRBundle.load_semantic_ir_bundle()

            semantic_graph = bundle.semantic_graph
            symbol_code_index = bundle.symbol_code_index
            ACTIVE_PROFILE = profile.subsystem_name
            ACTIVE_SEMANTIC_BUNDLE = bundle
            print(f"✅ Semantic cache loaded in {time.time() - start:.2f} seconds")

        else:
            print("⚙️ Building semantic graphs...")
            start = time.time()
            semantic_bundle = compile_semantic_ir(profile)

            semantic_graph = semantic_bundle.semantic_graph
            symbol_code_index = semantic_bundle.symbol_code_index

            print(f"⚙️ Semantic graphs built in {time.time() - start:.2f} seconds")

            ACTIVE_PROFILE = profile.subsystem_name
            ACTIVE_SEMANTIC_BUNDLE = semantic_bundle

            print("⚙️ Saving semantic graphs...")
            SemanticIRBundle.save_semantic_ir_bundle(
                semantic_bundle,
            )
            print("⚙️ Saving semantic graphs completed...")


        print("Semantic graph stats:")
        if semantic_graph:
            print(semantic_graph.semantic_ir_stats())
        print("\nKernel Flow Explorer ready.")

        runtime_graph = run_semantic_workflow(
            semantic_graph,
            profile,
            traversal_mode
        )

        print("Exporting Mermaid runtime graph...")
        MermaidGraphExporter.export_runtime_graph(runtime_graph, semantic_graph, profile)
        print("Mermaid export completed. Check the 'exports' directory.")

        runtime_prompt = build_runtime_prompt(
            runtime_graph, semantic_graph, cleaned_query, profile, symbol_code_index)

        answer = ask_llm(
           prompt=runtime_prompt,
           model="qwen2.5-coder:7b", #profile.preferred_model,
           temperature=0.1,
           num_predict=1200,
           debug=False
        )

        print("\n*********************** Answer from the LLM ************************\n")
        print(answer)

    #############################
# -----------------------------
# Main loop
# -----------------------------
if __name__ == "__main__":
    main()