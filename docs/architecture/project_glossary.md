# KernelScope Project Glossary

Version: 0.1

This document defines the terminology used throughout KernelScope. These definitions serve as the canonical vocabulary for documentation, implementation, validation, prompts, and future contributor onboarding.

---

# A

## Ambiguity Resolution

The process of selecting the correct symbol when multiple symbols share the same name. KernelScope currently uses directory locality, file ownership, and contextual scoring while deliberately refusing ambiguous matches.

---

# C

## Canonical Symbol

The unique semantic identity of a function or object after ambiguity resolution.

Example:

```
open()
```

becomes

```
drivers/net/ethernet/intel/igb/igb_main.c::igb_open()
```

---

## Confidence Score

A numerical estimate describing how strongly KernelScope believes an execution transition belongs to the dominant runtime path.

Confidence influences traversal prioritization but never overrides deterministic correctness.

---

# D

## Deterministic Analysis

Static program analysis that produces reproducible, evidence-based results without relying on probabilistic reasoning.

KernelScope always performs deterministic analysis before invoking an LLM.

---

## DIRECT_CALL
Definition

A conventional function invocation explicitly present in the source code.

Characteristics
Explicit C function call.
No indirection.
Deterministically recoverable through static analysis.
Highest confidence edge type.
Example
igb_open(adapter);

produces

### DIRECT_CALL

__igb_open
    ↓
igb_setup_all_tx_resources

```Mermaid
schedule --DIRECT_CALL--> __schedule
```

Confidence

Very High

---

## Dispatch Reconstruction

Recovery of runtime execution hidden behind indirect function calls.

Examples include:

* sched_class
* tcp_prot
* file_operations
* net_device_ops

Dispatch reconstruction converts function pointer invocation into concrete implementation edges.

---

## Dominant Runtime Path

The execution sequence most representative of normal subsystem behavior.

This differs from a complete call graph by intentionally deprioritizing cleanup, logging and uncommon error paths.

---

# E

## Execution Context

The environment in which execution occurs.

Future examples include:

* Process Context
* Interrupt Context
* SoftIRQ
* NAPI
* Workqueue
* Timer
* Thread

---

## Execution Narrative

A human-readable explanation of subsystem runtime behavior reconstructed from the Semantic IR.

Execution narratives are generated from semantic facts rather than source code alone.

---

## Execution Spine

The highest-value execution path reconstructed through a subsystem.

Execution spine reconstruction attempts to preserve the semantic flow of runtime execution while suppressing auxiliary branches.

---

## ExecutionEdge

A runtime edge stored within RuntimeExecutionGraph.

ExecutionEdge references a SemanticEdge through semantic_edge_id.

---

# F

## FUNCTION_POINTER_DISPATCH

### Definition

Represents runtime dispatch through a function pointer whose concrete implementation has been reconstructed by KernelScope.
Execution that occurs indirectly through function pointers rather than explicit function calls.

### Motivation

Many Linux subsystems use operation tables rather than explicit function calls.

### Examples include

sched_class
file_operations
tcp_prot
net_device_ops
platform_driver

A normal call graph stops here.

KernelScope reconstructs the concrete implementation.

### Example

Source

p->sched_class->pick_next_task(...)

KernelScope reconstructs

pick_next_task_fair()

Resulting semantic edge **FUNCTION_POINTER_DISPATCH**

pick_next_task
    ↓
pick_next_task_fair

```Mermaid
pick_next_task
    ==FUNCTION_POINTER_DISPATCH==>
pick_next_task_fair
```

Represented using:

```
SemanticEdgeType.FUNCTION_POINTER_DISPATCH
```

### Confidence

High


---

# G

## Graph Poisoning

Introduction of incorrect semantic relationships into the graph through poor ambiguity resolution or incorrect reconstruction.

KernelScope deliberately rejects uncertain relationships to avoid graph poisoning.

---

# H

## High Value Transition

A transition known to represent meaningful runtime progress.

Used to bias execution-spine reconstruction.

Example:

```
schedule()

↓

__schedule()

↓

pick_next_task()
```

---

# L

## Local LLM

A locally executed Large Language Model used exclusively for explanation and reasoning.

The Local LLM never determines execution flow.

---

## Locality Rank

A numerical measure describing filesystem proximity between two symbols.

KernelScope uses locality as a semantic signal during ambiguity resolution and macro alias resolution.

---

# M

## MACRO_ALIAS

### Definition

Represents execution that is hidden behind a subsystem-local macro. A subsystem-local macro representing an executable function.

Unlike textual macro expansion, KernelScope resolves executable aliases into semantic runtime transitions.

### Motivation

Linux drivers frequently invoke

rd32(...)
wr32(...)

These are not globally meaningful.

Each subsystem defines its own implementation.

### KernelScope reconstructs

rd32()
↓
igb_rd32()
↓
readl()

instead of treating

rd32()

as a missing function.

### Example

Source

rd32(E1000_STATUS);

### Semantic graph MACRO_ALIAS

rd32
    ↓
igb_rd32
Mermaid
rd32
    -.MACRO_ALIAS.->
igb_rd32

### Confidence

High (after scoped alias resolution)
Macros become semantic edges rather than remaining textual substitutions.

---

## Macro Expansion

Replacement of a macro invocation with its concrete implementation.

KernelScope performs semantic macro expansion rather than preprocessor expansion.

---

# P

## Provider Pattern

A declarative description of an indirect dispatch mechanism.

Examples include:

* sched_class
* file_operations
* tcp_prot
* net_device_ops

Provider patterns allow dispatch recovery without subsystem-specific traversal logic.

---

# R

## Runtime Execution Graph

A graph representing reconstructed runtime execution.

Unlike SemanticGraph, RuntimeExecutionGraph stores only the execution path selected during traversal.

---

## Runtime Reconstruction

The process of rebuilding runtime execution behavior from static source code.

Runtime reconstruction is KernelScope's primary objective.

---

# S

## Semantic Edge

A relationship between two symbols representing runtime semantics rather than merely syntactic structure.

Examples include:

* DIRECT_CALL
* FUNCTION_POINTER_DISPATCH
* MACRO_ALIAS
* SYNTHETIC_CONTINUATION

---

## Semantic Edge Type

The classification assigned to a semantic relationship.

Future semantic edge types include locking, iteration, state mutation and synchronization.

---

## Semantic Graph

KernelScope's canonical graph representation containing symbols and semantic relationships.

All runtime reconstruction begins from the Semantic Graph.

---

## Semantic Intermediate Representation (Semantic IR)

The persistent intermediate representation connecting parsing, graph construction, runtime reconstruction and LLM reasoning.

Semantic IR is the architectural core of KernelScope.

---

## Semantic Reconstruction

The process of enriching syntactic source code with runtime meaning.

Examples include:

* Dispatch recovery
* Macro resolution
* Execution-spine reconstruction

---

## Symbol Identity

The unique identity of a kernel symbol.

A SymbolIdentity contains:

* Name
* File
* Line
* Kind
* Symbol ID

---

## SYNTHETIC_CONTINUATION

### Definition

Represents a semantic continuation inferred by KernelScope when explicit source-level calls do not fully describe runtime progression. A semantic edge representing inferred runtime progression where explicit source-level control flow is insufficient.

This is not an invented execution path.

It is a bridge introduced to preserve the dominant runtime narrative.

### Motivation

Large kernel functions often invoke dozens of helper routines.

Runtime understanding requires identifying which transition continues the primary execution story.

Synthetic continuations connect these dominant transitions.

### Example

Suppose

__netif_receive_skb_core()

├── statistics()

├── tracing()

├── logging()

└── deliver_skb()

KernelScope identifies

deliver_skb()

as the dominant continuation.

The graph records

**SYNTHETIC_CONTINUATION**

__netif_receive_skb_core
        ↓
deliver_skb

```Mermaid
__netif_receive_skb_core
    -.SYNTHETIC_CONTINUATION.->
deliver_skb
```

### Represented using:

```
SemanticEdgeType.SYNTHETIC_CONTINUATION
```

### Confidence

Derived from execution-spine heuristics.

---

# T

## Telemetry

Instrumentation generated during graph construction to evaluate reconstruction quality.

Examples include:

* Missing symbols
* Ambiguous symbols
* Dispatch statistics
* Macro alias statistics

Telemetry guides future semantic improvements.

---

## Traversal Engine

The subsystem responsible for converting SemanticGraph into RuntimeExecutionGraph.

Traversal applies semantic ranking, confidence scoring and execution-spine heuristics.

---

# V

## Validation Profile

A predefined subsystem used to verify reconstruction quality.

Examples:

* Scheduler
* MM
* IRQ
* Network RX
* Block I/O

Validation profiles are documented under docs/validation.

---

# Future Terms

The following concepts are planned but not yet fully implemented:

| Edge              | Purpose                      |
| ----------------- | ---------------------------- |
| ITERATES_OVER     | Semantic loop reconstruction |
| LOCK_ACQUIRE      | Synchronization analysis     |
| LOCK_RELEASE      | Synchronization analysis     |
| RCU_ENTER         | RCU lifetime analysis        |
| RCU_EXIT          | RCU lifetime analysis        |
| CONFIG_BRANCH     | Compile-time execution       |
| STATE_MUTATION    | State transition tracking    |
| WORKQUEUE_QUEUE   | Deferred execution           |
| WORKQUEUE_EXECUTE | Workqueue processing         |
| IRQ_ENTRY         | Interrupt context transition |
| IRQ_EXIT          | Interrupt return             |

