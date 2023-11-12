---
$id: on-key-dropped-argument
title: Pass on_key_dropped as a named argument to expand()
date: 2023-11-12
author: anatoly-scherbakov
issue: 50
adr:is-blocked-by: on-key-dropped-handler
---

# Pass `on_key_dropped` as a named argument to `expand()`

## Context

We need to pass the value of `on_key_dropped` handler to `jsonld.expand()` somehow.

### :x: Use `options` dictionary

That dictionary contradicts Python conventions.

### :heavy_check_mark: Add a named argument

That's what a Python developer would expect, in most cases.

## Decision

Add as a named argument.

## Consequences

Improve developer experience, even though it is a bit inconsistent.
