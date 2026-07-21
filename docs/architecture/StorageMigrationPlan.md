# KernelScope 2.1
# Storage Migration Plan

## Purpose

This document defines the migration strategy for evolving KernelScope's
persistent knowledge store from a string-oriented representation to a
canonical identity-based storage model.

The objective is **not** to change the knowledge produced by the compiler.

The objective is to change **how that knowledge is represented,
persisted, and retrieved.**

Storage optimizations must never alter engineering meaning.

---

# Guiding Principles

## Principle 1

Representation is replaceable.

Knowledge is not.

---

## Principle 2

Every migration must preserve deterministic compiler output.

---

## Principle 3

Each migration phase must be independently verifiable.

---

## Principle 4

Storage optimization follows measurement.

No optimization is accepted without profiler evidence.

---

## Current Architecture (KernelScope 2.0)

```
Source Code
      │
      ▼
Semantic Extraction
      │
      ▼
Semantic Metadata
      │
      ▼
Relationship Builder
      │
      ▼
SQLite Persistence

semantic_nodes.ks
relationships.ks
collections.ks
```

Characteristics

- Human-readable identifiers
- Repeated strings
- Embedded file paths
- Embedded domains
- Embedded symbol names

Advantages

- Easy debugging

Limitations

- High storage duplication
- Increased memory pressure
- String comparison overhead
- Cache inefficiency

---

# Target Architecture (KernelScope 2.1)

```
Source Code
      │
      ▼
Semantic Extraction
      │
      ▼
Canonical Identity Layer
      │
      ▼
Vocabulary Resolution
      │
      ▼
Normalized Persistence

dictionary.ks

semantic_nodes.ks

relationships.ks

collections.ks
```

Characteristics

- Deterministic identities
- Typed vocabularies
- Fixed-width relationships
- Lazy presentation formatting

---

# Migration Strategy

KernelScope will migrate incrementally.

Each phase must leave the compiler in a fully working state.

No "big bang" migration is permitted.

---

# Phase 1

## Canonical Identity

Goal

Separate identity from presentation.

Current

```
assign:kernel/sched/core.c:6842:local:rq
```

Target

```
NodeID
```

Deliverables

- IdentityManager
- Canonical NodeID
- Presentation Formatter

Validation

- Existing engineering queries remain identical.
- Graph topology unchanged.
- Relationship counts unchanged.

---

# Phase 2

## Typed Vocabulary Normalization

Goal

Replace repeated strings with canonical vocabularies.

Vocabulary Spaces

- File Registry
- Symbol Registry
- Primitive Registry
- Collection Registry

Deliverables

dictionary.ks

Validation

- Vocabulary lookup reproduces existing presentation strings.
- File count unchanged.
- Symbol count unchanged.

---

# Phase 3

## Semantic Metadata Normalization

Goal

Store only ontology-specific information.

Current

```
Metadata

file

symbol

domain

...
```

Target

```
Metadata

assignment_kind

operator

expression

...
```

Everything structural moves to canonical identities or vocabularies.

Validation

Semantic reconstruction produces identical engineering facts.

---

# Phase 4

## Relationship Normalization

Goal

Represent graph connectivity entirely through canonical identities.

Current

source_string

target_string

relationship_name

Target

source_node_id

target_node_id

relationship_kind

Validation

- Edge count unchanged.
- Graph topology unchanged.
- Traversal results identical.

---

# Phase 5

## Working Set Materialization

Goal

Implement Law 5.

> KernelScope optimizes for the engineer's current problem, not the entire
> software system.

Persistent graph remains passive.

Only localized engineering contexts become active.

Validation

- Peak memory reduced.
- Query latency maintained or improved.
- Working set correctness verified.

---

# Phase 6

## Query Optimization

Goal

Optimize retrieval only after normalization completes.

Candidate optimizations

- Secondary indices
- Relationship ordering
- Adjacency locality
- Batch loading
- Prepared statements

Validation

Benchmark

- Localized Working Set
- Relationship Expansion
- Impact Analysis
- Dispatch Reconstruction

---

# Migration Rules

Every migration must satisfy the following invariants.

Identity

✓ Stable

Knowledge

✓ Unchanged

Relationships

✓ Unchanged

Engineering Queries

✓ Identical

Compiler Output

✓ Deterministic

Only representation may change.

---

# Validation Checklist

After every migration

□ Semantic node count unchanged

□ Relationship count unchanged

□ Collection count unchanged

□ Compiler output unchanged

□ Engineering queries unchanged

□ Existing validation suite passes

□ Performance benchmark recorded

---

# Success Criteria

KernelScope 2.1 is considered complete when

- Canonical identities replace presentation identifiers
- String duplication is eliminated
- Persistent storage is normalized
- Working sets are localized
- Engineering behaviour is identical
- Storage footprint is significantly reduced
- Query latency is maintained or improved

---

# Final Principle

KernelScope migrates representations.

Never engineering meaning.

# Non-Goals

The following are explicitly outside the scope of this migration.

- New ontologies
- New engineering workflows
- New relationships
- New UI features
- LLM improvements
- Web interface

This migration exists solely to strengthen the storage substrate beneath
the existing compiler.