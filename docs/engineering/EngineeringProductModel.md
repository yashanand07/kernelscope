# KernelScope
# Engineering Product Model

## Purpose

This document defines the product philosophy of KernelScope.

It explains the engineering problem KernelScope addresses, the principles guiding its design, and the interaction model through which engineers investigate complex software systems.

This document intentionally avoids implementation details.

It defines **what KernelScope is**, not **how it is implemented**.

---

# The Engineering Problem

Modern software systems continue to grow in size, complexity, and lifetime.

Development tools have dramatically improved the speed at which software can be written.

Artificial Intelligence has accelerated software generation even further.

Understanding that software has not improved at the same pace.

As software evolves, engineers spend increasing amounts of time answering questions such as:

- What does this function do?
- How does execution reach here?
- What protects this state?
- What changes if I modify this?
- Which subsystems depend on this?
- What should I validate before committing this change?

The difficulty is rarely writing code.

The difficulty is building sufficient understanding to make confident engineering decisions.

KernelScope exists to reduce the effort required to build that understanding.

---

# Product Vision

KernelScope is an Engineering Investigation Engine.

It does not generate software.

It does not replace engineering judgement.

It does not compete with Artificial Intelligence.

Instead, it provides deterministic engineering context that engineers—and optionally AI models—can use to understand large software systems more effectively.

When used together with AI, KernelScope narrows large codebases into focused engineering evidence, reducing unnecessary context while improving the quality and grounding of AI-generated explanations.

KernelScope accelerates engineering investigations.

Engineers remain responsible for engineering decisions.

---

# Core Philosophy

Engineers rarely attempt to understand an entire software system at once.

Instead, they investigate one aspect of the system at a time.

They navigate to a point of interest.

They choose what they wish to investigate.

They examine the available engineering evidence.

They repeat this process until they have built sufficient understanding.

KernelScope mirrors this natural engineering workflow.

Rather than attempting to answer arbitrary questions, KernelScope assists engineers in performing structured engineering investigations.

---

# Product Interaction Model

KernelScope participates only after the engineer has identified what they wish to investigate.

```text
Engineer
    │
    ▼
Navigate Software
    │
    ▼
Select Anchor
    │
    ▼
Choose Engineering Capability
    │
    ▼
KernelScope Investigation
    │
    ▼
Engineering Context
    │
    ▼
Engineer Continues Investigation
```

KernelScope does not determine the engineer's problem.

It accelerates the investigation once the engineer has decided what they wish to understand.

---

# Anchors

Every investigation begins from an explicitly selected software element.

Examples include:

- Function
- Variable
- Structure Field
- Type
- Function Pointer
- Lock Primitive
- RCU Primitive
- Workqueue
- Timer
- Interrupt Handler
- Graph Node
- Search Result

KernelScope never attempts to infer the engineer's point of interest through unrestricted natural language.

The engineer always establishes the anchor.

---

# Engineering Capabilities

Once an anchor has been established, KernelScope presents the engineering capabilities applicable to that anchor.

Examples include:

- Understand Function
- Trace Execution
- Show Synchronization
- Explore State Changes
- Analyze Lifetime
- Perform Impact Analysis
- Explore Architecture
- Review Changes

Capabilities define what KernelScope can do.

The engineer decides which capability best supports the current investigation.

---

# Engineering Context

Executing a capability produces an Engineering Context.

An Engineering Context is a localized collection of engineering evidence assembled specifically for the current investigation.

Depending on the selected capability, it may include:

- Execution Paths
- State Changes
- Synchronization Information
- Ownership Information
- Architectural Relationships
- Impact Indicators
- Engineering Metrics
- Supporting Evidence

Engineering Context exists only for the current investigation.

It is intentionally focused on the engineer's immediate objective.

---

# Engineering Decisions

KernelScope does not diagnose failures.

KernelScope does not approve code.

KernelScope does not determine engineering risk.

KernelScope assembles engineering evidence.

Engineers interpret that evidence and make engineering decisions.

KernelScope accelerates understanding.

Engineers retain responsibility.

---

# Design Principles

## Principle 1

KernelScope shall optimize for engineering understanding rather than software generation.

---

## Principle 2

KernelScope shall assist engineering investigations, not replace engineering judgement.

---

## Principle 3

Every investigation shall begin from an explicit anchor selected by the engineer.

KernelScope shall not infer investigation targets through unrestricted natural language.

---

## Principle 4

Every Engineering Capability shall answer exactly one class of engineering investigation.

---

## Principle 5

Every investigation shall produce a localized Engineering Context focused only on the current objective.

---

## Principle 6

KernelScope shall remain deterministic.

Artificial Intelligence is an optional consumer of Engineering Context, never the source of engineering knowledge.

---

# Relationship to the Constitution

This document defines the product philosophy.

The remaining engineering documents progressively refine that philosophy.

```text
Engineering Product Model
        │
        ▼
Engineering Questions
        │
        ▼
Engineering Capabilities
        │
        ▼
Engineering Session Model
        │
        ▼
Engineering Workflows
        │
        ▼
UI Interaction Model
```

The engineering documents define how engineers interact with KernelScope.

The constitutional documents define how KernelScope constructs engineering knowledge.

Together they describe the complete KernelScope architecture.

---

# Final Principle

KernelScope is not a source code explorer.

It is not an AI coding assistant.

It is not a conversational interface.

KernelScope is an Engineering Investigation Engine.

Its purpose is to help engineers investigate complex software systems by constructing the smallest useful engineering context required for the current investigation.

The measure of KernelScope is not the amount of information it stores.

The measure of KernelScope is how effectively it reduces the time required for engineers to build accurate mental models and make confident engineering decisions.