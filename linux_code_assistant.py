import requests
from sentence_transformers import SentenceTransformer
import chromadb
import json
import re
import os
from datetime import datetime

ENTRY_POINT_MAP = {
    "context_switch": "schedule",
    "__schedule": "schedule",
    "try_to_wake_up": "wake_up_process",
    "ttwu_queue": "wake_up_process",
    "switch_to": "schedule",
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
    "switch_to",
    "finish_task_switch"
]

KERNEL_EXECUTION_TEMPLATES = {

    "scheduler": [
        "schedule",
        "__schedule",
        "pick_next_task",
        "context_switch",
        "switch_to",
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
# -----------------------------
# Regex patterns
# -----------------------------

call_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
token_pattern = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')

# -----------------------------
# Global indexes
# -----------------------------

call_graph = {}
symbol_index = {}
symbol_freq = {}

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

# -----------------------------
# Load chunks + build call graph
# -----------------------------

with open("chunks.jsonl") as f:
    for line in f:
        data = json.loads(line)

        symbol = data["symbol"]
        code = data["code"]

        # allow duplicate symbol names
        symbol_index.setdefault(symbol.lower(), []).append(data)

        # frequency count
        symbol_freq[symbol] = symbol_freq.get(symbol, 0) + 1

        calls = [
            c for c in call_pattern.findall(code)
            if c != symbol and c not in IGNORE_CALLS
        ]

        # Using set to avoid duplicate callees which can bloat the call graph
        # and cause infinite loops in traversal
        call_graph.setdefault(symbol, set()).update(calls)

print("Call graph loaded:", len(call_graph))
print("\nKernel Flow Explorer ready.")
print("Ask questions about Linux kernel execution paths.\n")


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
print("Using ChromaDB at:", DB_PATH)
collection = client.get_collection("linux_kernel")

# -----------------------------
# Subsystem detection
# -----------------------------
def detect_domains(query):

    q = query.lower()

    domains = []

    if "interrupt" in q or "irq" in q:
        domains.append("interrupt")

    if "timer" in q:
        domains.append("timer")

    if "softirq" in q:
        domains.append("softirq")

    if "wake" in q or "sleep" in q:
        domains.append("wakeup")

    if "context switch" in q:
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
            matches.extend(symbol_index[key])

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

    print("\nTop Vector retrieval candidates:\n")
    for s in scored[:5]:
        print(s[2]["symbol"], s[2]["file"], "score:", s[0])

    docs = [s[1] for s in scored][:3]
    metas = [s[2] for s in scored][:3]

    # -------------------------
    # Interrupt entry injection
    # -------------------------
    domains = detect_domains(query)

    if "interrupt" in domains:

        anchors = ["generic_handle_irq", "handle_irq_event", "handle_irq_event_percpu"]

        injected_docs = []
        injected_meta = []

        for anchor in anchors:

            if anchor not in symbol_index:
                continue

            best = None

            for entry in symbol_index[anchor]:

                path = entry["file"]

                # Prefer generic IRQ subsystem implementation
                if path.startswith("kernel/irq"):
                    best = entry
                    break

                # fallback candidate
                if best is None:
                    best = entry

            if best:
                injected_docs.append(best["code"])
                injected_meta.append({
                    "symbol": best["symbol"],
                    "file": best["file"]
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

    print(f"\nTop function: {metas[0]['symbol']} ({metas[0]['file']})")
    print("\nRetrieved functions:\n")

    for m in metas:
        subsystem = "/".join(m["file"].split("/")[:2])
        print(f"{m['symbol']}   ({m['file']})   [{subsystem}]")

    return docs, metas


# -----------------------------
# Execution path tracing
# -----------------------------
def trace_execution_path(symbol, query):

    # Experimental heuristic tracer:
    # Build execution path using subsystem templates
    # based on domains detected from the query.
    domains = detect_domains(query)

    path = []

    for d in domains:
        if d in KERNEL_EXECUTION_TEMPLATES:
            path.extend(KERNEL_EXECUTION_TEMPLATES[d])

    # remove duplicates while preserving order
    seen = set()
    final = []

    for p in path:
        if p not in seen:
            final.append(p)
            seen.add(p)

    if symbol not in final:
        final.insert(0, symbol)

    return final
    # Future Improvement - TODO
    # Replce template tracer with real call-graph traversal
    # Prototype logic kept below for reference
        # fallback to call graph traversal with query-based heuristics

    # query_tokens = {
    #     t for t in token_pattern.findall(query.lower())
    #     if t not in STOPWORDS
    # }

    # path = [symbol]
    # current = symbol

    # for _ in range(depth):

    #     callees = list(call_graph.get(current, []))

    #     if not callees:
    #         break

    #     # Prefer explicit schedular flow if detected in callees
    #     found = False
    #     for target in SCHED_PATH:
    #         if target in callees:
    #             path.append(target)
    #             current = target
    #             found = True
    #             break

    #     if found:
    #         continue

    #     ranked = sorted(
    #         callees,
    #         key=lambda c: (
    #             (c in ctags_index) * 2 +
    #             sum(t in c.lower() for t in query_tokens) * 3
    #         ),
    #         reverse=True
    #     )

    #     next_fn = None

    #     for c in ranked:
    #         if c in ctags_index:
    #             next_fn = c
    #             break

    #     if not next_fn:
    #         break

    #     path.append(next_fn)
    #     current = next_fn

    # return path


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
            "http://localhost:11434/api/generate",
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

    for callee in list(call_graph.get(symbol, []))[:4]:

        if callee.lower() in symbol_index:

            entry = symbol_index[callee.lower()][0]

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
    top_symbol = metas[0]["symbol"]

    if top_symbol == "context_switch":
        top_symbol = "schedule"

    if top_symbol in ENTRY_POINT_MAP:
        top_symbol = ENTRY_POINT_MAP[top_symbol]

    domains = detect_domains(query)
    domain = domains[0]

    append_callees(top_symbol, docs, metas)
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