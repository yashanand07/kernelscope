# Macro Alias Resolution

Version: 0.1

## Purpose

Recover subsystem-local function aliases hidden behind C macros.

---

## Motivation

Driver code frequently invokes macros such as:

rd32()

wr32()

rather than concrete functions.

---

## Architecture

Macro Extraction

↓

MacroAlias

↓

Scoped Lookup

↓

SemanticEdge(MACRO_ALIAS)

---

## Current Capabilities

- Scoped lookup
- Locality ranking
- Noise filtering

---

## Validation

See validation/macro_alias_validation.md