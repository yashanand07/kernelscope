# Engineering Questions Catalog

## Purpose

KernelScope exists to help engineers understand large software systems.

Every semantic extractor, relationship builder, visualization, and AI
integration must ultimately exist to answer one or more engineering
questions.

If a proposed feature cannot be mapped to an engineering question,
it does not belong in the compiler.

---

# Level 1 — Software Understanding

These are the questions engineers naturally ask when approaching an
unfamiliar codebase.

## Function Understanding

- What does this function do?
- Why does it exist?
- Who calls it?
- What does it call?
- Which subsystem owns it?
- Is it an API or an implementation?

Required Ontology

✓ Call
✓ Dispatch
✓ Collections

---

## Execution

- How does execution reach here?
- Where can execution continue?
- Which execution paths exist?
- Which paths are architecture dependent?
- Which paths are asynchronous?

Required Ontology

✓ Call
✓ Dispatch
✓ Workqueues
✓ IRQ
✓ Timers
✓ Context Switches

---

## Concurrency

- What protects this state?
- Which lock guards this object?
- Where is the lock acquired?
- Where is it released?
- Can this execute concurrently?
- Is RCU involved?

Required Ontology

✓ Locks
✓ Unlocks
✓ RCU
✓ Wait Queues

---

## State

- What writes this variable?
- What reads this variable?
- Which structure fields change?
- Which topology changes occur?
- Which state transitions occur?

Required Ontology

✓ Assignment
✓ State Mutation

---

## Lifetime

- Who allocates this object?
- Who frees it?
- Who owns it?
- Is reference counting involved?
- Where does ownership transfer?

Required Ontology

✓ Lifetime
✓ Refcount
✓ Allocation

---

## Architecture

- Which subsystem owns this?
- Which modules depend on it?
- Which interfaces expose it?
- Which providers implement it?

Required Ontology

✓ Collections
✓ Dispatch
✓ Relationships

---

## Impact Analysis

- What could break if I modify this?
- Which execution paths are affected?
- Which synchronization changes?
- Which ownership chains change?

Required Ontology

✓ Entire Semantic Graph

---

# Level 2 — AI Assisted Questions

These questions are answered by an LLM only after KernelScope has
constructed deterministic semantic context.

Examples

- Explain this function.
- Explain this execution path.
- Explain why this lock exists.
- Explain the lifetime of this object.
- Summarize this subsystem.

KernelScope supplies context.

The LLM supplies language.

---

# Design Principle

Every future ontology must answer one or more engineering questions.

The compiler is not built around programming language constructs.

It is built around engineering reasoning.