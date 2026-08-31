---
title: Use `pyld.jsonld.expand()` for YAML-LD expansion
status: decided
date: 2026-09-01
author: Anatoly Scherbakov
tags: [decision]
hide: [toc]
---

# Use `pyld.jsonld.expand()` for YAML-LD expansion

{{ adr_metadata(date, status) }}

*[DRY]: Don't Repeat Yourself

## :material-text-box-outline: Context

We are considering YAML-LD support in PyLD based on the
[YAML-LD specification](https://www.w3.org/TR/yaml-ld-10/), which reuses the
JSON-LD data model and processing API. Here is an example:

{{ source_file('project/decisions/examples/intro.yamlld') }}

The JSON-LD API defines
[`JsonLdProcessor.expand(input, options)`](https://www.w3.org/TR/json-ld11-api/#idl-def-jsonldprocessor-expand-input-options)
as an example expansion endpoint.

How should we expand a YAML-LD document programmatically?

## :material-arrow-decision-outline: Decision

<table data-adr-comparison markdown="1">
  <tr markdown="span">
    <th>Expansion function</th>
    <th>Decision</th>
  </tr>
  <tr markdown="span">
    <th class="chosen">[:material-arrow-expand: `pyld.jsonld.expand()`](/pyld/reference/expand/)</th>
    <td class="chosen">:white_check_mark: Chosen</td>
  </tr>
  <tr markdown="span">
    <th class="excl">`pyld.yaml_ld.expand()`</th>
    <td class="excl">:x: Creates a competing expand API, violating [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)</td>
  </tr>
  <tr markdown="span">
    <th class="excl">`yaml_ld.expand()`</th>
    <td class="excl">:x: Creates a competing expand API, violating [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)</td>
  </tr>
</table>
