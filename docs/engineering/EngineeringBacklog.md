# KernelScope Technical Debt & Future Work Ledger

This document records architectural ideas, postponed work, known limitations and future enhancements.

Items should not be removed when completed. Instead, mark them as completed and reference the implementing commit.

---

# High Priority

## Semantic Iterator Reconstruction

Status: Planned

Examples:

* list_for_each_entry
* list_for_each_entry_safe
* hlist_for_each_entry
* xa_for_each
* idr_for_each
* for_each_cpu
* for_each_online_cpu

Planned Semantic Edge:

ITERATES_OVER

Purpose:

Allow KernelScope to reconstruct semantic loop behaviour rather than treating iterator macros as missing functions.

---

## CONFIG-Aware Execution

Status: Planned

Goals:

* Parse CONFIG_* conditionals.
* Represent compile-time execution branches.
* Support configuration-aware execution reconstruction.

Future queries:

* Explain scheduler with CONFIG_PREEMPT enabled.
* Explain receive path with CONFIG_XDP enabled.

---

## Synchronization Semantics

Status: Planned

Future Semantic Edges:

* LOCK_ACQUIRE
* LOCK_RELEASE
* RCU_ENTER
* RCU_EXIT
* ATOMIC_ACCESS

---

## State Mutation Analysis

Status: Planned

Detect assignments that modify subsystem state.

Examples:

adapter->flags

queue_state

device_state

Purpose:

Allow runtime explanations to include state transitions.

---

## Execution Context Reconstruction

Status: Planned

Execution domains include:

* Process Context
* Interrupt
* SoftIRQ
* NAPI
* Workqueue
* Timer
* Thread

---

# Medium Priority

## Provider Pattern Expansion

Extend dispatch recovery to additional Linux subsystems.

Examples:

* VFS
* Netdevice
* Filesystems
* USB
* DRM
* Block Layer

---

## Semantic Ranking Improvements

Improve execution-spine selection.

Potential heuristics:

* Bias setup paths over cleanup paths.
* Prefer dominant runtime behaviour.
* Penalize error handling branches during normal execution reconstruction.

---

## Mermaid Improvements

Future enhancements:

* Edge colouring
* Collapsible subsystem clusters
* Execution context styling
* Legend generation

---

## Telemetry Improvements

Continue reducing non-execution noise.

Review:

* atomic_read
* cpu_to_be32
* be32_to_cpu
* offsetof
* writel_relaxed
* ioread32
* iowrite32

---

# Architectural Refactoring

Planned modularization:

kernelscope-core

kernelscope-dispatch

kernelscope-macro

kernelscope-semantic-ir

kernelscope-iterator

kernelscope-config

kernelscope-sync

kernelscope-visualization

kernelscope-llm

---

# Research Ideas

* Inter-procedural state tracking
* Lifetime analysis
* Ownership propagation
* Lock dependency reconstruction
* Memory allocation lifetime reconstruction
* Wait queue semantics
* IRQ timeline reconstruction
* Scheduler timeline visualization
* Driver probe sequencing
* Execution diff between kernel versions

---

# Commercial Features (Future)

Potential enterprise capabilities:

* Repository-wide semantic indexing
* Incremental indexing
* Multi-version comparison
* BSP comparison
* Security analysis
* Architecture dashboards
* CI integration
* Knowledge graph API
* Team collaboration
* Commercial semantic plugins

---

# Completed

Maintain completed items here with commit references to preserve project history.

* Persistent Semantic IR
* Function Pointer Dispatch Reconstruction
* Scheduler Dispatch Recovery
* Locality-Based Ambiguity Resolution
* Scoped Macro Alias Resolution
* Semantic Macro Alias Edges
* Mermaid Runtime Visualization
* Non-Execution Symbol Filtering
