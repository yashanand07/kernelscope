# KernelScope 2.0
# Ontology Roadmap

## Purpose

KernelScope is a semantic compiler whose purpose is to transform software
systems into structured engineering knowledge.

Every ontology introduced into the compiler teaches exactly one engineering
concept.

Together, these ontologies form the language through which KernelScope
understands software.

The compiler does not reason about syntax.

It reasons about engineering concepts.

---

# Design Laws

## Law 1

Every ontology teaches exactly one semantic concept.

---

## Law 2

Ontologies are independent.

No ontology should require implementation knowledge from another.

Relationships are established later by the Relationship Builder.

---

## Law 3

Ontologies answer engineering questions.

No ontology exists simply because a language construct exists.

Every ontology must map directly to one or more entries in
EngineeringQuestions.md.

---

## Law 4

The compiler remains framework agnostic.

Framework-specific syntax belongs exclusively inside Adaptation Kits.


## Law 5

KernelScope should optimize for the engineer's current problem, not the entire software system.

Only the information required to answer the current engineering question should be actively materialized.

Everything else remains passive until requested.

---

# Knowledge Acquisition Pipeline

                 Source Code
                      │
                      ▼
            Adaptation Kit Profiles
                      │
                      ▼
             Ontology Extractors
                      │
                      ▼
              Semantic Metadata
                      │
                      ▼
           Relationship Builder
                      │
                      ▼
          Semantic Knowledge Graph
                      │
                      ▼
     UI / Query Engine / Optional AI

---

# Ontology Evolution

KernelScope grows by teaching the compiler progressively richer concepts.

Each phase increases the compiler's understanding of software.

---

## Phase 0

### Identity Ontology

Purpose

Teach the compiler where things exist.

Concepts

- Functions
- Variables
- Structures
- Files
- Collections
- Source Locations

Current Status

✓ Complete

---

## Phase 1

### Execution Ontology

Purpose

Teach the compiler how execution flows.

Concepts

- Calls
- Iteration
- Dispatch
- Function Context

Metadata

- CallMetadata
- DispatchMetadata
- IterationMetadata

Current Status

✓ Mostly Complete

Future

- Generic Dispatch V2
- Context Switch Modeling

---

## Phase 2

### Synchronization Ontology

Purpose

Teach serialization and concurrent execution.

Engineering Questions

- What protects this state?
- Where is the lock acquired?
- Where is it released?

Concepts

- Lock Acquire
- Lock Release
- Mutex
- RW Lock
- IRQ Save
- Wait Queue

Metadata

- LockAcquireMetadata
- LockReleaseMetadata

Current Status

✓ Active

Future

- Completions
- Wait Queues
- Reader/Writer Locks

---

## Phase 3

### Assignment Ontology

Purpose

Teach state modification.

Engineering Questions

- Who writes this?
- What changed?

Concepts

- Local Assignment
- Structure Assignment

Metadata

- AssignmentMetadata

Current Status

✓ Complete

---

## Phase 4

### State Ontology

Purpose

Teach structural state transitions.

Engineering Questions

- What topology changed?
- Which kernel object changed state?

Concepts

- list_add()
- list_del()
- hash_add()
- hash_del()
- set_bit()
- clear_bit()

Future Metadata

- StateTransitionMetadata
- TopologyMutationMetadata

Current Status

Planned

---

## Phase 5

### Lifetime Ontology

Purpose

Teach ownership and object lifetime.

Engineering Questions

- Who owns this object?
- Where is it allocated?
- Where is it destroyed?

Concepts

- kmalloc
- kfree
- refcount
- atomic lifetime
- get/put

Future Metadata

- AllocationMetadata
- FreeMetadata
- LifetimeMetadata

Current Status

Planned

---

## Phase 6

### RCU Ontology

Purpose

Teach lockless synchronization.

Engineering Questions

- Is this pointer protected?
- Where is it published?
- Where is it dereferenced?

Concepts

- Read Lock
- Read Unlock
- Publish
- Dereference
- Grace Period
- RCU Iteration

Metadata

- RcuReadLockMetadata
- RcuDereferenceMetadata
- RcuPublishMetadata
- RcuGracePeriodMetadata

Current Status

In Progress

---

## Phase 7

### Deferred Execution Ontology

Purpose

Teach asynchronous execution.

Engineering Questions

- What executes later?
- Which context executes this?

Concepts

- Workqueues
- Delayed Work
- Timers
- Tasklets
- SoftIRQ

Current Status

Planned

---

## Phase 8

### Interrupt Ontology

Purpose

Teach hardware execution.

Engineering Questions

- Which interrupt reaches here?
- What executes inside IRQ context?

Concepts

- request_irq
- free_irq
- threaded IRQ
- interrupt entry
- interrupt exit

Current Status

Planned

---

## Phase 9

### Relationship Ontology

Purpose

Transform isolated semantic facts into engineering knowledge.

Relationships

WRITES

READS

PROTECTS

CALLS

IMPLEMENTS

TARGETS

ALLOCATES

FREES

OWNS

PUBLISHES

USES

DEPENDS_ON

Current Status

In Progress

Future

Relationship inference

Relationship ranking

Cross-function reasoning

---

## Phase 10

### Reasoning Ontology

Purpose

Allow engineers to ask questions rather than search code.

Example Questions

- What protects this object?

- Which execution paths reach here?

- Which functions modify this structure?

- Show ownership graph.

- Show architecture graph.

- Show subsystem dependencies.

Current Status

Planned

---

# Adaptation Kits

The compiler never contains framework knowledge.

Each Adaptation Kit contributes

- Profiles
- Extractor Rules
- Naming Conventions
- Macro Definitions
- Dispatch Providers
- Framework Metadata

Examples

Linux

FreeBSD

Zephyr

LLVM

QEMU

PostgreSQL

Chromium

Proprietary Middleware

Embedded RTOS

The compiler remains unchanged.

Only the adaptation changes.

---

# Long-Term Vision

KernelScope evolves by expanding its ontology one engineering concept at
a time.

Every ontology increases the compiler's ability to answer engineering
questions.

Eventually, the compiler becomes capable of constructing a complete,
queryable understanding of a software system independent of the
programming language or framework.

The Semantic Knowledge Graph becomes the single source of truth.

Visualization, query engines, documentation generators, and AI assistants
become consumers of that knowledge rather than producers of it.