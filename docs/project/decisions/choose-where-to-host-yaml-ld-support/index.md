---
title: Implement YAML-LD support in …
status: undecided
date: 2026-09-01
author: Anatoly Scherbakov
tags: [decision]
hide: [toc]
prerequisite:
  title: Use `pyld.jsonld.expand()` for YAML-LD expansion
  url: /pyld/project/decisions/use-pyld-jsonld-expand-for-yaml-ld/
---

# Implement YAML-LD support in …

{{ adr_metadata(date, status, prerequisite) }}

## :material-text-box-outline: Context

This ADR compares the possible Python packaging homes for a YAML-LD implementation.

### Requirements

- [x] PyLD's `pyld` command is the sole callable YAML-LD CLI; do not introduce or retain a separate `yaml-ld` command.
- [x] Require no backwards compatibility with the existing `python-yaml-ld` API, CLI, or package behavior. The selected universe may redesign or remove those surfaces to satisfy the PyLD-owned interface constraint.

## :material-arrow-decision-outline: Decision

<table data-adr-comparison markdown="1">
  <tr markdown="span">
    <th>Alternative</th>
    <th>[PyLD implements YAML-LD](implement-yaml-ld-in-pyld.md)<br>[:fontawesome-brands-github: `digitalbazaar/pyld`](https://github.com/digitalbazaar/pyld)</th>
    <th>[PyLD uses a parser-only YAML-LD adapter](provide-yaml-ld-through-a-pyld-facade.md)<br>[:fontawesome-brands-github: `digitalbazaar/pyld`](https://github.com/digitalbazaar/pyld) + [:fontawesome-brands-github: `iolanta-tech/yaml-ld-adapter`](https://github.com/iolanta-tech/yaml-ld-adapter)</th>
  </tr>
  <tr markdown="span">
    <th>Install</th>
    <td>Proposed `pyld[yaml-ld]` extra</td>
    <td>Proposed `pyld[yaml-ld]` extra</td>
  </tr>
  <tr markdown="span">
    <th>Dependencies</th>
    <td>Proposed direct `ruamel.yaml ⩾0.19` dependency</td>
    <td>Proposed `yaml-ld-adapter` dependency</td>
  </tr>
  <tr markdown="span">
    <th>Test suite</th>
    <td>PyLD CI [:fontawesome-brands-github: `main.yaml`](https://github.com/digitalbazaar/pyld/blob/6f29288adf241a72a49897787430c69752bf95d7/.github/workflows/main.yaml#L72) runs `specifications/yaml-ld/tests`</td>
    <td>PyLD owns JSON-LD operation/conformance coverage; `yaml-ld-adapter` owns parser fixtures</td>
  </tr>
  <tr markdown="span">
    <th>YAML parsing</th>
    <td>Proposed PyLD-owned parser integration</td>
    <td>Proposed use of its YAML parser adapter</td>
  </tr>
  <tr markdown="span">
    <th>Decision</th>
    <td></td>
    <td></td>
  </tr>
</table>

## :material-arrow-right-bold-outline: Consequences

- Docs, optional extras, and ownership of YAML-LD conformance must match the chosen packaging home.
- Dependency surface (YAML parser and any optional extras) will either grow in PyLD or stay in a separate package.
- Release cadence for YAML-LD support fixes will either couple to PyLD releases or remain with a separate package.

#### Implementation Steps

- [ ] Record the Decision row outcome in this ADR (flip status to decided)
- [ ] Align suite location, YAML parsing ownership, and install surface with the chosen column
- [ ] Update project index / user docs if needed
