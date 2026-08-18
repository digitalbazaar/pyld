---
title: Treat YAML-LD support as …
status: undecided
date: 2026-07-19
author: Anatoly Scherbakov
tags: [decision]
hide: [toc]
---

# Treat YAML-LD support as …

{{ adr_metadata(date, status) }}

## :material-text-box-outline: Context

At the moment of writing this document, the [JSON-LD Working Group](https://www.w3.org/groups/wg/json-ld/) is preparing a new specification, [YAML-LD](https://www.w3.org/TR/yaml-ld-10/), for the status of [Recommendation](https://www.w3.org/standards/types/#x2-5-recommendation). It [leverages the readability and conciseness of YAML, but relies on the JSON-LD data model and API](https://www.w3.org/TR/yaml-ld-10/). Here is an example:

{{ source_file('project/decisions/examples/intro.yamlld') }}

The specification is already stable in the normative sense, and the Working Group is inviting implementations for the new standard.

Should we provide such an implementation for Python within [:fontawesome-brands-github: `digitalbazaar/pyld`](https://github.com/digitalbazaar/pyld)?

## :material-arrow-decision-outline: Decision

<table markdown="1">
  <tr markdown="span">
    <th></th>
    <th class="adr-col-undecided">PyLD implements YAML-LD</th>
    <th class="adr-col-undecided">`python-yaml-ld` implements YAML-LD</th>
    <th class="adr-col-rejected">PyLD is a façade on top of `python-yaml-ld`</th>
  </tr>
  <tr markdown="span">
    <th>Install</th>
    <td class="adr-col-undecided">`pip install 'PyLD[yaml-ld]'`</td>
    <td class="adr-col-undecided">`pip install yaml-ld`</td>
    <td class="adr-col-rejected">`pip install 'PyLD[yaml-ld]'`</td>
  </tr>
  <tr markdown="span">
    <th>Dependencies</th>
    <td class="adr-col-undecided">YAML parser, for instance: `ruamel.yaml` or `pyyaml`</td>
    <td class="adr-col-undecided">[PyLD](https://github.com/iolanta-tech/python-yaml-ld/blob/master/pyproject.toml)</td>
    <td class="adr-col-rejected">`PyLD` → `yaml-ld` → `PyLD`</td>
  </tr>
  <tr markdown="span">
    <th>Test suite</th>
    <td class="adr-col-undecided">PyLD (`specifications/yaml-ld`)</td>
    <td class="adr-col-undecided">`yaml-ld`</td>
    <td class="adr-col-rejected">`yaml-ld`</td>
  </tr>
  <tr markdown="span">
    <th>YAML parsing</th>
    <td class="adr-col-undecided">`PyLD`</td>
    <td class="adr-col-undecided">`yaml-ld`</td>
    <td class="adr-col-rejected">`yaml-ld`</td>
  </tr>
  <tr markdown="span">
    <th>How to expand()</th>
    <td class="adr-col-undecided">`pyld.jsonld.expand()`</td>
    <td class="adr-col-undecided">`yaml_ld.expand()`</td>
    <td class="adr-col-rejected">`pyld.jsonld.expand()`</td>
  </tr>
  <tr markdown="span">
    <th>Decision</th>
    <td class="adr-col-undecided">:question:</td>
    <td class="adr-col-undecided">:question:</td>
    <td class="adr-col-rejected">:x: Circular dependency (`PyLD` → `yaml-ld` → `PyLD`)</td>
  </tr>
</table>

## :material-arrow-right-bold-outline: Consequences

- Docs, optional extras, and ownership of YAML-LD conformance must match the chosen packaging home.
- Dependency surface (YAML parser and any optional extras) will either grow in PyLD or stay in a separate package.
- Release cadence for YAML-LD support fixes will either couple to PyLD releases or remain with a separate package.

#### Implementation Steps

- [ ] Record the Decision row outcome in this ADR (flip status to decided)
- [ ] Align suite location, YAML parsing ownership, `expand()` entry point, and install surface with the chosen column
- [ ] Update project index / user docs if needed
