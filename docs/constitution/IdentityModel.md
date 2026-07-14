# KernelScope 2.1
# Identity Model

## Purpose

The Identity Model defines how every semantic entity is uniquely identified
within KernelScope.

Identity is independent of persistence, presentation, storage technology,
or user interface.

A semantic identity represents engineering knowledge.

Storage merely preserves it.

Presentation merely renders it.

---

## Core Principle

Identity is immutable.

Representation is replaceable.

The compiler reasons using identities.

Humans interact with representations.

---

## Design Laws

### Law 1

Every semantic entity has exactly one canonical identity.

---

### Law 2

Canonical identities are deterministic.

The same semantic concept compiled from the same source structure must
always produce the same identity.

---

### Law 3

Canonical identities never contain presentation information.

Examples:

- formatted strings
- colors
- display names
- UI labels

do not participate in identity.

---

### Law 4

Presentation identifiers are derived.

Human-readable identifiers are generated only when required by a debugger,
CLI, API, or UI.

---

### Law 5

Relationships reference canonical identities only.

No relationship stores presentation strings.

---

## Identity Hierarchy

Compilation Unit
    ↓
Function
    ↓
Semantic Node
    ↓
Relationship

Every identity belongs to exactly one parent scope.

---

## Canonical Identity

A canonical identity is derived from structural invariants of a semantic
concept.

Example inputs include

- Ontology Domain
- Source Scope
- Symbol
- Entity Kind
- Structural Coordinates

The specific hashing algorithm is an implementation detail.

---

## Identity Lifecycle

Source Code
    ↓
Ontology Extraction
    ↓
Semantic Node Creation
    ↓
Canonical Identity
    ↓
Relationship Construction
    ↓
Persistence
    ↓
Working Set
    ↓
Presentation

---

## Typed Identity Spaces

KernelScope maintains independent identity spaces.

- NodeID
- FileID
- SymbolID
- PrimitiveID
- CollectionID
- RelationshipKind
- TypeID

Typed identities improve correctness, debugging, and storage efficiency.

---

## Final Principle

Identity models engineering knowledge.

Storage and presentation are consumers of identity.