---
title: Parse YAML-LD with `ruamel.yaml`
status: decided
date: 2026-11-01
author: Anatoly Scherbakov
tags: [decision]
hide: [toc]
prerequisite:
  title: Implement YAML-LD support in PyLD
  url: /project/decisions/choose-where-to-host-yaml-ld-support/
---

# Parse YAML-LD with `ruamel.yaml`

{{ adr_metadata(date, status, prerequisite) }}

## :material-text-box-outline: Context

PyLD needs a YAML parser that can supply its JSON-compatible internal
representation while preserving YAML scalar semantics. The candidates expose
different data models, so parser-only throughput does not measure the same
completed work.

The implementation must satisfy the pinned YAML-LD requirements in
[:fontawesome-brands-github: `index.html`](https://github.com/w3c/yaml-ld/blob/ec5d431c3aa7da5d89865df34ad150db8c8418e7/index.html)
at `ec5d431` and pass validation on PyLD's supported runtimes.

## :material-arrow-decision-outline: Decision

Use [:simple-python: `ruamel.yaml`](https://yaml.dev/doc/ruamel.yaml/basicuse/)
for its Python-object construction, which reduces the conversion logic that PyLD
must maintain. This choice does not assume a performance advantage over RapidYAML
([:fontawesome-brands-github: `biojppm/rapidyaml-python`](https://github.com/biojppm/rapidyaml-python)).

<table data-adr-comparison markdown="1">
  <tr markdown="span">
    <th>Criterion</th>
    <th class="chosen">[:simple-python: `ruamel.yaml`](https://yaml.dev/doc/ruamel.yaml/)</th>
    <th class="not-selected">RapidYAML Python binding<br>[:fontawesome-brands-github: `biojppm/rapidyaml-python`](https://github.com/biojppm/rapidyaml-python)</th>
  </tr>
  <tr markdown="span">
    <th>Python representation</th>
    <td class="chosen">[Constructs Python objects](https://yaml.dev/doc/ruamel.yaml/basicuse/)</td>
    <td class="not-selected">Indexed tree and scalar string views ([:fontawesome-brands-github: `README.md`](https://github.com/biojppm/rapidyaml-python/blob/master/README.md))</td>
  </tr>
  <tr markdown="span">
    <th>Parser implementation</th>
    <td class="chosen">[Pure Python mode is available; optional C behavior differs](https://yaml.dev/doc/ruamel.yaml/basicuse/)</td>
    <td class="not-selected">Exposes the low-level C++ API ([:fontawesome-brands-github: `README.md`](https://github.com/biojppm/rapidyaml-python/blob/master/README.md))</td>
  </tr>
  <tr markdown="span">
    <th>Decision</th>
    <td class="chosen">:white_check_mark: Chosen</td>
    <td class="not-selected">:material-minus-circle-outline: Not selected</td>
  </tr>
</table>

### Scalar conversion

RapidYAML's Python binding returns untyped scalar text, so PyLD would need to
construct Python dictionaries and lists and resolve scalar types using their
text, style, and tags, as described in
[:fontawesome-brands-github: `README.md`](https://github.com/biojppm/rapidyaml-python/blob/master/README.md).
For example, plain `42` must become a Python `int`, while quoted `"42"` must remain
a `str`. `ruamel.yaml` provides [resolution and construction machinery](https://yaml.dev/doc/ruamel.yaml/basicuse/),
which still needs YAML-LD Core-schema configuration and validation.

### Performance evidence

RapidYAML's published Python comparison omits its Python type conversion;
the authors acknowledge this limitation in
[:fontawesome-brands-github: `README.md`](https://github.com/biojppm/rapidyaml-python/blob/master/README.md#performance).
A future performance comparison must include construction and validation of the
same Python data structure before drawing a PyLD performance conclusion.

## :material-arrow-right-bold-outline: Consequences

`ruamel.yaml` becomes PyLD's optional parser dependency. PyLD remains responsible
for YAML-LD Core-schema configuration and validation.

#### Verification Steps

- [ ] Verify the `ruamel.yaml` configuration against the pinned YAML-LD conformance cases.
- [ ] Verify installation and behavior on the full supported runtime matrix,
  including PyPy.
- [ ] Measure parsing, Python conversion, and YAML-LD validation together on
  representative inputs.
- [ ] Record the tested dependency range.
