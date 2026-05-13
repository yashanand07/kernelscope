"""
Linux Kernel Flow Explorer (RAG + Static Analysis)
-------------------------------------------------
An AI-powered tool to navigate and explain Linux kernel execution paths.
Uses Ctags for symbol location, Regex for function pointer resolution,
ChromaDB for RAG, and Ollama for local LLM reasoning.
"""

import requests
import json
import re
import os
import subprocess
from datetime import datetime
from sentence_transformers import SentenceTransformer
import chromadb

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
        requests.get(url, timeout=1)
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
instance_ops = {}      # struct_instance → {method: impl}
struct_instances = {}  # struct_type → instances

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
# 3. KERNEL HEURISTICS & TEMPLATES
# =================================================================

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
# Load chunks + build call graph
# CHUNK PARSING (CRITICAL SECTION)
# -----------------------------

with open("chunks.jsonl") as f:
    for line in f:
        data = json.loads(line)

        symbol = data["symbol"]
        code = data["code"]




        #if "sched_class" in code:
        #    print("FOUND sched_class usage in:", symbol)

        # Build symbol index & allow duplicate symbol names
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
        call_graph.setdefault(symbol, set()).update(calls)

        # -----------------------------
        # FUNCTION POINTER EXTRACTION (TO ADD HERE)
        # -----------------------------
        # Goal:
        #   Extract:
        #       obj->method(...)
        #   Store:
        #       fp_call_graph[symbol] → [(obj, method)]

        # Example:
        #   p->sched_class->enqueue_task(...)
        #   file->f_op->read(...)
        #if symbol not in fp_call_graph:


        # -----------------------------
        # OPS STRUCT PARSING (TO ADD HERE)
        # -----------------------------
        # Goal:
        #   Extract:
        #       .enqueue_task = enqueue_task_fair
        #
        # Build:
        #   ops_index:
        #       enqueue_task → [enqueue_task_fair, enqueue_task_rt]
        #
        # Later:
        #   instance_ops:
        #       fair_sched_class → {enqueue_task: enqueue_task_fair}


        matches = ops_assign_pattern.findall(entry["code"]) # Change later to 346 line

        VALID_OPS = {
            "pick_next_task",
            "pick_task",
            "enqueue_task",
            "dequeue_task",
            "check_preempt_curr",
            "yield_task",
            "wakeup_preempt",
        }

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

    INDIRECT_CALL_HINTS = (
        "->",
        ".pick_next_task",
        ".enqueue_task",
        ".dequeue_task",
        ".check_preempt_curr",
        ".select_task_rq",
        ".task_tick",
    )

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

    if matches:
        fp_call_graph[symbol.strip()] = list(set(matches))

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