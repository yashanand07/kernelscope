# KernelScope 2.1
# Relationship Model

## Purpose

Relationships transform isolated semantic facts into engineering knowledge.

Without relationships the compiler stores observations.

With relationships it supports reasoning.

---

## Design Laws

### Law 1

Relationships are deterministic.

---

### Law 2

Relationships never modify metadata.

---

### Law 3

Relationships connect canonical identities only.

---

### Law 4

Every relationship must unlock one or more engineering workflows.

---

## Relationship Pipeline

Semantic Metadata
        ↓
Relationship Builder
        ↓
Knowledge Graph
        ↓
Engineering Session

---

## Relationship Categories

Execution

- CALLS
- TARGETS

Concurrency

- PROTECTS
- MATCHES

State

- WRITES
- READS
- DATA_FLOW

Ownership

- ALLOCATES
- FREES
- OWNS

Architecture

- BELONGS_TO
- IMPLEMENTS
- DEPENDS_ON

---

## Relationship Responsibilities

Relationships never infer facts.

They connect existing facts.

---

## Engineering Principle

Every new relationship should unlock at least one engineering workflow.

---

## Final Principle

Metadata explains what exists.

Relationships explain how everything is connected.