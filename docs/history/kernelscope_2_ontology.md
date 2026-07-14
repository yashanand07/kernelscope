# KernelScope 2.0 Semantic Ontology

**Status:** Architecture Baseline

**Author:** KernelScope Project

---

# 1. Introduction

KernelScope began as a semantic execution reconstruction engine capable of rebuilding Linux kernel execution paths from static source code. The initial architecture focused on **inter-function semantics**:

- Symbol discovery
- Direct-call reconstruction
- Function pointer dispatch recovery
- Macro alias resolution
- Runtime execution graph synthesis

This architecture proved capable of reconstructing execution paths without compiler instrumentation or a running kernel.

As the project matured, a limitation became apparent.

KernelScope understood **how functions related to one another**, but treated the inside of each function largely as opaque C code.

KernelScope 2.0 introduces **Intra-Function Semantics**.

Instead of treating a function as merely a collection of call sites, the compiler now extracts the semantic constructs that describe runtime behaviour inside that function.

---

# 2. Design Goals

KernelScope 2.0 is designed around the following principles.

## Deterministic First

Semantic information should be extracted directly from source whenever possible.

Heuristics should only be used when deterministic extraction is impossible.

---

## Preserve Locality

Semantic reasoning should happen while parsing a function.

Avoid expensive global lookups after compilation whenever possible.

---

## Self-Describing Functions

Every function should contain sufficient semantic information for explanation without requiring additional graph traversal.

Prompt generation should never need to perform semantic inference.

---

## Modular Semantic Extraction

Every new semantic capability should be implemented as an independent extractor.

The compiler core should remain unchanged as new features are introduced.

---

## Language Independence

The ontology is not Linux specific.

Linux is the first frontend.

Future frontends may include:

- Android Framework
- AOSP HAL
- GPU Drivers
- Chromium
- LLVM
- PostgreSQL
- Embedded firmware

---

# 3. Architecture Overview

```
                    Source Code
                         │
         ┌───────────────┴────────────────┐
         │                                │
         ▼                                ▼
 Inter-Function                    Intra-Function
    Semantics                        Semantics
         │                                │
         ▼                                ▼
 SemanticGraph               FunctionSemanticContext
         │                                │
         └──────────────┬─────────────────┘
                        ▼
            Runtime Reconstruction
                        ▼
             RuntimeExecutionGraph
                        ▼
         Prompt Builder / UI / Mermaid
```

The Semantic Graph models relationships **between** functions.

The FunctionSemanticContext models semantic behaviour **inside** a function.

Together they form the complete semantic representation of a program.

---

# 4. Semantic Philosophy

KernelScope does not attempt to understand C syntax.

KernelScope reconstructs runtime semantics.

Examples:

| Source Construct | Runtime Semantic              |
| ---------------- | ----------------------------- |
| Function Call    | Runtime Invocation            |
| Function Pointer | Dynamic Dispatch              |
| Macro Alias      | Runtime Alias                 |
| Iterator Macro   | Collection Traversal          |
| spin_lock()      | Synchronization               |
| CONFIG_*         | Conditional Runtime Behaviour |

This distinction allows KernelScope to reason about execution instead of syntax.

---

# 5. Semantic Layers

```
Layer 1
--------
Source Code

Layer 2
--------
SymbolIdentity

Layer 3
--------
SemanticGraph

Layer 4
--------
FunctionSemanticContext

Layer 5
--------
RuntimeExecutionGraph
```

Each layer enriches the previous one without duplicating responsibilities.

---

# 6. Core Ontology

## SymbolIdentity

Represents globally declared program entities.

Examples:

- Functions
- Global Variables
- Structures
- Typedefs
- Enums

SymbolIdentity is the canonical source of truth for globally visible symbols.

---

## LocalSymbol

Represents symbols declared inside a function.

Examples:

```c
struct igb_ring *rx_ring;
const char *name;
int cpu;
```

Attributes:

- Name
- Type
- Storage class
- Pointer information
- Scope depth

---

## CollectionDescriptor

Compiler-side cache describing globally known collections.

Purpose:

- Accelerate iterator resolution
- Avoid repeated SymbolIdentity lookups
- Preserve collection semantics

Examples:

```
clkdm_list

↓

CollectionDescriptor

Type:
struct list_head

Family:
linked_list

Element:
struct clockdomain
```

CollectionDescriptor is never directly exposed to the Prompt Builder.

---

## SemanticMetadata

Base class for every semantic construct extracted from a function.

Future semantic constructs inherit from this class.

Examples:

- IterationMetadata
- LockMetadata
- StateMutationMetadata
- ConfigBranchMetadata
- WaitQueueMetadata
- InterruptMetadata

---

## IterationMetadata

Represents semantic collection traversal.

Unlike raw C syntax, IterationMetadata stores runtime meaning.

Example:

```
Macro

list_for_each_entry

↓

Collection

clkdm_list

↓

Element

struct clockdomain

↓

Cursor

temp_clkdm
```

This allows PromptBuilder to describe runtime behaviour without re-parsing source code.

---

## FunctionSemanticContext

Persistent semantic representation of a function.

Unlike an AST, FunctionSemanticContext stores semantic knowledge rather than syntax.

Contents include:

- Local symbols
- Iterator semantics
- Lock semantics
- State mutations
- CONFIG branches
- Future semantic constructs

FunctionSemanticContext becomes the primary semantic input for PromptBuilder.

---

# 7. Compiler Pipeline

Each function passes through a sequence of semantic extractors.

```
Raw Function
      │
      ▼
LocalSymbolExtractor
      │
      ▼
IteratorExtractor
      │
      ▼
CallExtractor
      │
      ▼
DispatchExtractor
      │
      ▼
MacroAliasExtractor
      │
      ▼
LockExtractor
      │
      ▼
StateMutationExtractor
      │
      ▼
ConfigExtractor
      │
      ▼
...
```

Each extractor enriches the same FunctionSemanticContext.

No extractor owns the compiler.

---

# 8. Ownership Rules

| Object                  | Owns                          | Never Owns               |
| ----------------------- | ----------------------------- | ------------------------ |
| SymbolIdentity          | Global program entities       | Function-local semantics |
| LocalSymbol             | Function-local declarations   | Global objects           |
| SemanticGraph           | Relationships between symbols | Local variable state     |
| FunctionSemanticContext | Intra-function semantics      | Cross-function graph     |
| RuntimeExecutionGraph   | Runtime execution             | Compilation state        |
| PromptBuilder           | Presentation                  | Semantic inference       |

These ownership boundaries prevent architectural drift.

---

# 9. Compiler Indices

KernelScope avoids linear searches through canonical data structures.

Instead, specialised compiler indices accelerate compilation.

Examples:

```
SymbolIdentity

↓

symbol_name_index

↓

SemanticEdge
```

KernelScope 2.0 extends this pattern.

```
CollectionDescriptor

↓

collection_index

↓

IterationMetadata
```

Canonical data remains stored once.

Indices accelerate compilation.

Semantic snapshots accelerate explanation.

---

# 10. Why Semantic Snapshots?

PromptBuilder should never perform semantic inference.

Instead, semantic constructs contain self-contained semantic snapshots.

Example:

```
IterationMetadata

Collection:
clkdm_list

Family:
linked_list

Element:
struct clockdomain

Cursor:
temp_clkdm
```

This allows explanations without additional graph traversal.

---

# 11. Future Semantic Extractors

Current:

- Direct Calls
- Dispatch Recovery
- Macro Alias Resolution
- Iterator Reconstruction

Planned:

- Lock Analysis
- State Mutation Analysis
- CONFIG Consumption
- RCU Sections
- Wait Queues
- Workqueues
- Timers
- IRQ Context
- Memory Ownership
- Reference Counting
- Error Propagation

Each feature integrates through a dedicated Semantic Extractor.

---

# 12. Worked Example

```
list_for_each_entry(
        temp_clkdm,
        &clkdm_list,
        node)
```

Produces:

```
IterationMetadata

Collection:
clkdm_list

Family:
linked_list

Element:
struct clockdomain

Cursor:
temp_clkdm

Member:
node
```

PromptBuilder receives this semantic snapshot directly.

No additional lookups are required.

---

# 13. KernelScope 2.0 Principles

## Semantic First

Model runtime meaning rather than C syntax.

---

## Deterministic Before Heuristic

Use deterministic extraction whenever possible.

---

## One Source of Truth

Canonical entities exist exactly once.

Compiler indices provide fast lookup.

Semantic snapshots provide explanation.

---

## Explainability by Construction

Every semantic construct should contain enough information to explain itself.

---

## Composable Semantics

Every new capability integrates through a Semantic Extractor.

---

## Generality over Specificity

The ontology models semantic concepts rather than Linux-specific constructs.

Linux is the first frontend.

The architecture is intended to scale to arbitrary large-scale C/C++ systems.

---

# 14. Conclusion

KernelScope 2.0 separates semantic understanding into two complementary domains.

- **Inter-function semantics**, represented by the Semantic Graph, describe relationships between program entities.
- **Intra-function semantics**, represented by the FunctionSemanticContext, describe the runtime behaviour contained within an individual function.

Together they provide a complete semantic representation of a codebase while remaining deterministic, modular, explainable, and extensible.

Future features are expected to integrate by enriching this ontology rather than introducing parallel semantic models.
