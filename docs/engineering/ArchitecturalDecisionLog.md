# KernelScope Engineering Decision Log

This document records the major architectural decisions made during the evolution of KernelScope.

Unlike the Constitution, which defines what the project **is**, this document explains **how it became that way**.

Each entry captures the engineering problem, the alternatives considered, the decision reached, and the reasoning behind it.

Software evolves through code. Architecture evolves through decisions. This document preserves those decisions.

---

# Decision 001

## Title

KernelScope is an Engineering Understanding Platform, not an AI Assistant.

## Date

July 2026

## Problem

Large language models can explain small code snippets well but struggle to build reliable mental models of multi-million line codebases.

Simply placing an LLM in front of a repository does not solve software understanding.

## Alternatives

- Pure RAG
- Repository search
- Code chatbot

## Decision

KernelScope will compile deterministic engineering knowledge first.

LLMs become optional downstream consumers.

## Reasoning

Facts should never depend on probabilistic reasoning.

Engineering understanding must exist without AI.

---

# Decision 002

## Title

Engineering Questions drive the architecture.

## Problem

Compiler features were being discussed independently of the problems engineers were trying to solve.

## Decision

Every feature must answer an engineering question.

EngineeringQuestions.md became the starting point for all future design.

## Consequence

The compiler now grows from engineering workflows rather than language constructs.

---

# Decision 003

## Title

Ontologies represent semantic concepts, not programming language constructs.

## Problem

It is tempting to build extractors around syntax.

Syntax does not necessarily correspond to engineering meaning.

## Decision

Each ontology teaches exactly one semantic concept.

Examples:

- Assignment
- Synchronization
- RCU
- Dispatch
- Iteration

instead of

- if
- while
- struct
- typedef

## Consequence

The compiler becomes language-aware without becoming syntax-driven.

---

# Decision 004

## Title

Separate extraction from reasoning.

## Problem

Early discussions mixed extraction logic with relationship inference.

## Decision

Extractors produce isolated facts.

RelationshipBuilder creates knowledge.

## Result

Compiler phases become independent.

Extractors remain reusable.

---

# Decision 005

## Title

Relationships exist only if they unlock engineering workflows.

## Problem

There are infinitely many graph relationships.

Most provide little engineering value.

## Decision

Every relationship must answer at least one engineering question.

Examples

WRITES

PROTECTS

MATCHES

CALLS

TARGETS

DATA_FLOW

must all justify their existence through EngineeringQuestions.md.

---

# Decision 006

## Title

The compiler is framework agnostic.

## Problem

Linux-specific assumptions were leaking into the compiler.

## Decision

Framework knowledge belongs inside Adaptation Kits.

The compiler operates purely on semantic concepts.

## Result

KernelScope can eventually target:

- Linux
- Zephyr
- FreeRTOS
- AUTOSAR
- U-Boot
- LLVM
- proprietary firmware

without compiler changes.

---

# Decision 007

## Title

Identity is deterministic.

## Problem

Sequential IDs prevent reproducibility.

## Decision

Identity becomes an intrinsic property of knowledge.

Persistence merely stores it.

## Consequence

Identity survives recompilation, distribution, and storage changes.

---

# Decision 008

## Title

Persistence is an implementation detail.

## Problem

Database layout was beginning to influence compiler design.

## Decision

Identity, knowledge, and relationships remain independent of storage.

SQLite is merely one persistence backend.

---

# Decision 009

## Title

Documentation becomes part of the architecture.

## Problem

Project knowledge became fragmented across multiple markdown files.

## Decision

Introduce the KernelScope Constitution.

Split documentation into:

- Constitution
- Architecture
- Engineering
- Validation
- Roadmap
- History
- Developer

## Consequence

Documentation gains a single source of truth.

---

# Decision 010

## Title

Optimize for the engineer's current problem.

## Problem

Materializing the entire graph for every interaction is unnecessary.

## Decision

Only construct localized working sets.

Everything else remains passive until requested.

## Result

Low memory usage.

Sub-millisecond engineering queries.

---

# Decision 011

## Title

Storage optimization follows correctness.

## Problem

Premature optimization risked complicating the compiler.

## Decision

Build the complete semantic model first.

Optimize only after measuring.

## Result

Profiling revealed:

- repeated path strings
- repeated semantic IDs
- repeated domains

leading naturally to:

- canonical identities
- typed vocabularies
- string interning

---

# Decision 012

## Title

The product is not the compiler.

## Problem

Discussions frequently focused on implementation.

## Decision

The compiler is infrastructure.

The product is helping engineers answer questions.

Everything else serves that objective.

---

# Decision 013

## Title

Community Edition prioritizes understanding.

## Problem

Debugging, impact analysis and automated testing have significant commercial value.

## Decision

Community focuses on understanding.

Advanced debugging and engineering intelligence remain extensible.

---

# Decision 014

## Title

The engineering workflow defines future development.

## Decision

KernelScope evolves according to engineering workflows:

Understand

↓

Debug

↓

Impact Analysis

↓

Review

↓

Testing

↓

Mitigation

↓

Approval

Every new capability should strengthen one or more of these workflows.

---

# Decision 015

## Title

The Constitution precedes implementation.

## Problem

As the project grew, implementation discussions increasingly depended on unwritten architectural assumptions.

## Decision

Formalize the project's architectural principles before expanding the compiler.

The Constitution becomes the project's permanent reference.

Implementation follows the Constitution—not the other way around.