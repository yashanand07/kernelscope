# Installation Guide

This guide walks through setting up KernelScope from scratch.

The project builds a Semantic IR from Linux kernel source code and reconstructs runtime execution paths using subsystem-specific semantic profiles

---

## � Tested Environment

- Ubuntu 22.04  
- Python 3.10 / 3.12  
- CPU-only  

> **WSL2 (Windows)** is in the works with the current changes

---

## � 1. Install System Dependencies

```bash
sudo apt update
sudo apt install universal-ctags python3-pip
```
Verify:

```bash
ctags --version
```
```text
Expected output should contain:
Universal Ctags
```
---

## � 2. Install Python Dependencies

```bash
pip insta;; pyyaml requests
```

---

## � 3. Install Local LLM (Ollama)

Install Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull the model:

```bash
ollama pull qwen2.5-coder:7b
```
Verify
```bash
ollama list
```

---

## � 4. Clone Linux Kernel

```bash
git clone --depth 1 https://github.com/torvalds/linux.git
cd linux
```

---

## � 5. Generate Tags (ctags)

```bash
ctags \
   --languages=C \
   --kinds-C=+p+x+v \
   --fields=+iaS \
   --extras=+q \
   -R .
ls -l  tags
```

This creates a large `tags` file used for symbol lookup which needs to be copied into the linux_kernel_flow_explorer folder.

---

## � 6. Clone Linux Kernel Flow Explorer

Run:

```bash
git clone https://github.com/yashanand07/linux-kernel-flow-explorer.git
cp tags linux-kernel-flow-explorer
cd linux-kernel-flow-explorer
```

---

## � 7. Build chunks.jsonl

The semantic graph compiler currently reads symbols from: chunks.jsonl

Generate it using:
```bash
python build_chunks.py
```

This creates:

```
ls -l chunks.jsonl
```

Sanity check:

```bash
wc -l chunks.jsonl
```

Expected:

```
~600K+ lines
```

---

## � 8. Configure the Project
```text
Edit:

config/config.yaml

Example:

project:
    linux_root: "/home/user/linux"

cache:
    enabled: true
    semantic_bundle_path: "./semantic_cache/semantic_ir_bundle.pkl"

llm:
    enabled: true
    provider: "ollama"

ollama:
    endpoint: "http://127.0.0.1:11434"
    model: "qwen2.5-coder:7b"

exports:
    mermaid_dir: "./exports/mermaid"
    graph_dir: "./exports/graphs"
    report_dir: "./exports/reports"

runtime:
    debug_traversal: false
    max_depth_default: 16

profiles:
    auto_detect: true

Update:

project:
    linux_root:

to point to your Linux kernel source tree.
```
---

## � 9. Run the Assistant

```bash
python linux_code_assistant.py
```

#### First Run
```text
On first execution the tool:

    1. Registers symbols from chunks.jsonl
    2. Builds the semantic graph
    3. Reconstructs dispatch relationships
    4. Reconstructs synthetic continuations
    5. Saves the semantic graph bundle

Example output:

Building semantic graphs...
Saving semantic graphs...

A cache file is created:

semantic_cache/semantic_ir_bundle.pkl
```
---

## � 10. Example Queries

```text
Traversal modes:

1 - Runtime Spine Analysis
2 - Implementation Descent
3 - Dispatch Analysis
4 - Full Branch Exploration

Examples:

1-Explain the Linux scheduler

2-Explain page fault handling

2-Explain VFS read

2-Explain IRQ handling

2-Explain block I/O submission

2-Explain workqueue submission
```
---
## � Output

Each query may produce:

    - Runtime Execution Graph
    - Mermaid graph
    - LLM-generated explanation (if enabled)

Mermaid files are written under:

*exports/mermaid/*

---

## � Output

Each query produces:

- execution path (console)
- Mermaid graph (`callgraphs/` folder)
- LLM-generated explanation

---

## � Notes & Gotchas

### Disk Usage
- `tags` file → large  
- `chunks.jsonl` → hundreds of MB  
- ChromaDB index → large  

### Performance
- Embedding step is CPU-heavy  
- Queries after setup are fast  

### WSL Users
- Use `/home`, not `/mnt/c`  
- Avoid Windows filesystem for indexing  

### First Run Cost
- Tagging + chunking + embedding takes time  
- After that → instant queries  

---

## ❗ Troubleshooting

### Missing symbols (`schedule`, `do_IRQ`)
- Recreate ctags and verify the size of tags file.
- Make sure the tags file is in the linux_kernel_flow_explorer folder

### Linux symbols not found
```text
Verify in config/config.yaml:

project.linux_root

points to the correct Linux source tree.

Ensure the Linux source tree contains a valid tags file.
```
### Ollama connection issues
```text
Verify:

ollama serve

and ensure the configured endpoint matches:

llm:
  ollama:
    endpoint:
```
---

## ✅ Done

You now have:

- Linux kernel source indexed locally
- Semantic graph generation
- Runtime execution path reconstruction
- Mermaid graph generation
- Optional local LLM explanations

All running locally.