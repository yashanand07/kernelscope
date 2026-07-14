# KernelScope UI Interaction Model

## Philosophy

KernelScope is not a graph viewer.

KernelScope is an Engineering Reasoning Interface.

Graphs are the substrate.

Questions are the product.

---

# Interaction Model

Every semantic node exposes four layers.

Node

↓

Quick Facts

↓

Relationships

↓

Engineering Questions

↓

AI Explanation (Optional)

---

# Quick Facts

Immediate information.

Examples

Lock

- Primitive
- IRQ Safe
- Recursive
- Source Location

Assignment

- Variable
- Assignment Kind
- Structure Field

Dispatch

- Provider
- Implementation
- Dynamic Target

RCU

- Read Side
- Publish
- Dereference
- Grace Period

---

# Relationships

Show first-order relationships.

Examples

WRITES

PROTECTS

CALLS

IMPLEMENTS

TARGETS

PUBLISHES

OWNS

ALLOCATES

FREES

---

# Engineering Questions

Questions depend on node type.

Lock

- What state does this protect?
- Show lock lifetime.
- Show concurrent accesses.
- Show matching unlock.
- Show critical region.

Assignment

- Who reads this?
- Who writes this?
- What state changed?
- Show ownership.
- Show affected execution paths.

Function

- Explain this function.
- Show callers.
- Show callees.
- Show execution graph.
- Show dispatch paths.
- Show architecture graph.

Dispatch

- Show implementations.
- Show providers.
- Show runtime targets.
- Compare architectures.

RCU

- Show protected region.
- Show dereferences.
- Show publication.
- Show grace period.

---

# AI Integration

AI is optional.

Selecting

Explain

packages the current semantic neighborhood.

Current Node

+

Relationships

+

Execution Context

+

Ontology

↓

Prompt Builder

↓

LLM

The LLM never discovers knowledge.

It explains knowledge already compiled by KernelScope.

---

# Adaptation Model

Every Adaptation Kit contributes

Node Types

Relationships

Questions

Visualizations

without modifying the compiler.

Example

Linux

spin_lock()

↓

Show Critical Region

PostgreSQL

LWLockAcquire()

↓

Show Contention Graph

Compiler unchanged.

Only the adaptation changes.

---

# Design Principle

The UI should never require users to know what question to ask next.

KernelScope should guide exploration by presenting meaningful questions
at every semantic node.