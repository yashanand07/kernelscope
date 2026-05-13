# Installation Guide

This guide walks you through setting up the project locally from scratch.

---

## � Tested Environment

- Ubuntu 22.04  
- Python 3.10 / 3.12  
- CPU-only  

> Also works on **WSL2 (Windows)** using Ubuntu

---

## � 1. System Dependencies

```bash
sudo apt update
sudo apt install universal-ctags python3-pip
```

---

## � 2. Python Dependencies

```bash
pip install chromadb sentence-transformers requests
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

---

## � 4. Clone Linux Kernel

```bash
git clone --depth 1 https://github.com/torvalds/linux.git
cd linux
```

---

## � 5. Generate Tags (ctags)

```bash
ctags -R .
ctags -R --languages=C --kinds-C=f --fields=+n
```

This creates a large `tags` file used for symbol lookup.

---

## ✅ 6. Validate Tags

Run:

```bash
python testtags.py
```

Expected output:

- ~600K+ functions parsed  
- Key symbols present:

```
✓ schedule
✓ do_IRQ
✓ try_to_wake_up
```

If these are missing → regenerate tags.

---

## � 7. Build Code Chunks

```bash
python build_chunks.py
```

This creates:

```
chunks.jsonl
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

## � 8. Create Embeddings

```bash
python embed_chunks.py
```

⚠️ This is the slowest step.

- Can take **30–90 minutes on CPU**
- Outputs:

```
embedded: XXXXX
```

This step builds your **local vector database (ChromaDB)**.

---

## � 9. Test Retrieval Pipeline

```bash
python search_linux.py
```

This verifies:

- embeddings work  
- vector search works  
- retrieval is meaningful  

---

## � 10. Run the Assistant

```bash
git clone <your-repo>
cd <your-repo>

python linux_code_assistant.py
```

---

## � Example Query

```
How does Linux handle an interrupt?
```

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
```bash
ctags -R .
```

### Small or empty `chunks.jsonl`
- Check `build_chunks.py`

### No results from search
- Ensure embeddings completed successfully  

---

## ✅ Done

You now have:

- Linux kernel indexed locally  
- Vector search (ChromaDB)  
- Execution path reconstruction  
- Local LLM explanations  

All running **offline, with zero cost**.