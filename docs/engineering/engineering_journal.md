# KernelScope Engineering Journal

> "Every feature exists because an earlier assumption proved insufficient."

---

# Project Origin

KernelScope began with a simple but frustrating observation.

The Linux kernel contains decades of engineering knowledge spread across millions of lines of C code, yet understanding how a subsystem actually executes remains one of the hardest problems for engineers. Existing tools provide symbol lookup, call graphs, tracing, debugging, and source navigation, but they rarely answer the question:

**"What is the runtime story of this subsystem?"**

KernelScope was created to bridge this gap by reconstructing runtime execution behaviour directly from static source code.

The long-term vision is not another code browser, call graph generator, or LLM wrapper.

KernelScope aims to become a **Semantic Execution Reconstruction Platform**.

---

# Guiding Philosophy

The project is built around several core principles.

## Deterministic before Probabilistic

Static analysis establishes facts.

Large Language Models explain those facts.

The LLM should never invent execution behaviour.

---

## Runtime over Syntax

KernelScope is interested in how software behaves rather than how source code is written.

A call graph is only an intermediate representation.

Execution reconstruction is the goal.

---

## Every Edge Must Carry Meaning

Edges represent semantic relationships rather than merely syntactic ones.

Examples include:

* DIRECT_CALL
* FUNCTION_POINTER_DISPATCH
* MACRO_ALIAS
* SYNTHETIC_CONTINUATION

Future semantic relationships will include locking, iteration, workqueues, interrupts, state mutation, CONFIG branches and synchronization.

---

## Never Guess

Ambiguity should be rejected rather than guessed.

Returning no answer is preferable to producing an incorrect execution path.

---

# Evolution of KernelScope

## Phase 1 – Static Call Graph

The earliest prototype consisted of:

* ctags
* regex call extraction
* symbol graph
* LLM explanations

The approach worked for small examples but quickly failed on real kernel subsystems because indirect execution could not be reconstructed.

---

## Phase 2 – Semantic IR

A dedicated Semantic Intermediate Representation (Semantic IR) replaced the simple symbol graph.

Each symbol became an identity with semantic relationships rather than merely a string.

This became the architectural foundation for every future capability.

---

## Phase 3 – Scheduler Reconstruction

The Linux scheduler exposed the first major weakness.

Static analysis observes:

schedule()
→ pick_next_task()

Runtime executes:

pick_next_task_fair()

or

pick_next_task_rt()

depending on the active scheduling class.

KernelScope introduced semantic function-pointer reconstruction to bridge this gap.

---

## Phase 4 – Function Pointer Dispatch

Provider structures such as scheduler classes, protocol operations and operation tables became first-class semantic entities.

KernelScope learned to reconstruct dispatch through provider tables rather than relying solely on explicit function calls.

---

## Phase 5 – Execution Spine

Large kernel functions often invoke dozens of helper routines.

Treating every call equally produced noisy execution graphs.

Execution-spine reconstruction introduced:

* execution_spine_boost
* high_value_transitions
* synthetic continuation edges

allowing KernelScope to prioritize dominant execution behaviour.

---

## Phase 6 – Ambiguity Resolution

Generic function names such as:

* probe()
* remove()
* open()
* close()

appear throughout the Linux kernel.

KernelScope introduced locality-based ambiguity resolution using directory proximity and contextual scoring while deliberately refusing ambiguous matches.

---

## Phase 7 – Macro Alias Resolution

Driver development revealed another blind spot.

Many execution transitions are hidden behind subsystem-specific macros.

Example:

rd32()

actually represents

igb_rd32()

which eventually performs

readl()

KernelScope introduced a scoped Macro Alias layer capable of resolving subsystem-local aliases without polluting unrelated drivers.

Macro expansion became a semantic relationship rather than simple textual substitution.

---

## Phase 8 – Noise Reduction

Telemetry revealed that the majority of unresolved symbols were not executable behaviour.

Examples included:

* ARRAY_SIZE
* BIT
* IS_ERR
* FIELD_PREP
* dev_err
* pr_debug

Rather than expanding these, KernelScope classified them as non-execution symbols and excluded them from runtime reconstruction.

---

## Current Architecture

KernelScope currently provides:

* Semantic IR
* Persistent semantic graph cache
* Runtime execution reconstruction
* Function pointer dispatch recovery
* Macro alias resolution
* Locality-based ambiguity resolution
* Scheduler execution reconstruction
* Mermaid runtime visualization
* Local LLM-assisted subsystem explanation

Current scale:

* ~675,000 kernel symbols
* ~1.3 million semantic relationships

---

# Lessons Learned

Several architectural decisions emerged naturally during development.

* Deterministic reconstruction should always precede AI reasoning.
* Semantic richness is more valuable than larger call graphs.
* Linux directory structure carries valuable semantic locality.
* Runtime narratives are more useful than exhaustive call trees.
* Rejecting uncertainty produces more trustworthy explanations.

---

# Long-Term Vision

KernelScope is intended to evolve into a semantic execution platform capable of understanding complex systems software.

Although Linux is the initial target, the underlying architecture is expected to generalize to:

* Linux kernel
* U-Boot
* Zephyr
* RTOS kernels
* Hypervisors
* Firmware stacks
* Large embedded C/C++ codebases

The objective is to reconstruct behaviour rather than merely index source code.
