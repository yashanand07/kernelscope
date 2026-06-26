# Dispatch Reconstruction

Version: 0.1

## Purpose

Recover runtime dispatch hidden behind indirect function pointers.

---

## Motivation

Traditional static analysis stops at function pointers.

KernelScope reconstructs concrete implementations.

---

## Current Providers

- sched_class
- tcp_prot

---

## Components

- ProviderPattern
- Dispatch Edge Builder
- Dispatch Analysis

---

## Semantic Edge

FUNCTION_POINTER_DISPATCH

---

## Validation

See validation/dispatch_validation.md