# KernelScope 2.1
# Knowledge Model

## Purpose

KernelScope does not compile source code.

KernelScope compiles engineering knowledge.

The Knowledge Model defines the semantic concepts that may exist inside the
compiler.

---

## Design Laws

### Law 1

Every ontology teaches exactly one semantic concept.

---

### Law 2

Ontologies are independent.

---

### Law 3

Every ontology answers one or more engineering questions.

---

### Law 4

Framework-specific syntax belongs inside Adaptation Kits.

---

## Knowledge Hierarchy

Engineering Question
        ↓
Ontology
        ↓
Semantic Metadata
        ↓
Canonical Identity
        ↓
Relationships
        ↓
Engineering Understanding

---

## Knowledge Domains

Examples include

- Function Invocation
- Assignment
- Synchronization
- RCU
- Dispatch
- State Mutation
- Lifetime
- Ownership
- Interrupts
- Workqueues

Additional domains may be introduced without modifying the compiler core.

---

## Metadata

Each ontology emits structured metadata.

Metadata contains facts.

Metadata never performs reasoning.

---

## Compiler Philosophy

Extraction creates facts.

Relationships create knowledge.

Engineering workflows create understanding.

---

## Final Principle

KernelScope grows by teaching new concepts rather than adding new syntax
rules.