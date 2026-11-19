---
title: Implement YAML-LD support in PyLD
status: decided
date: 2026-11-01
author: Anatoly Scherbakov
tags: [decision]
hide: [toc]
prerequisite:
  title: Use `pyld.jsonld.expand()` for YAML-LD expansion
  url: /project/decisions/use-pyld-jsonld-expand-for-yaml-ld/
---

# Implement YAML-LD support in PyLD

{{ adr_metadata(date, status, prerequisite) }}

## :material-text-box-outline: Context

[:fontawesome-brands-github: `iolanta-tech/python-yaml-ld`](https://github.com/iolanta-tech/python-yaml-ld)
wraps PyLD operations to add YAML input. We want YAML-LD support in the existing
PyLD API and CLI, with one owner for its parsing policy and processing integration.

## :material-arrow-decision-outline: Decision

Implement YAML-LD parsing policy and loading integration in
[:fontawesome-brands-github: `digitalbazaar/pyld`](https://github.com/digitalbazaar/pyld).
Make the parser dependency optional through `PyLD[yaml-ld]`; users of the CLI
install `PyLD[cli,yaml-ld]`.

The assessment favors one ownership and release boundary unless independent
parser reuse justifies a separate implementation package.

<table data-adr-comparison markdown="1">
  <tr markdown="span">
    <th>Alternative</th>
    <th>Decision</th>
    <th>ADR assessment</th>
  </tr>
  <tr markdown="span">
    <th class="chosen">PyLD-owned integration<br>[:fontawesome-brands-github: `digitalbazaar/pyld`](https://github.com/digitalbazaar/pyld)</th>
    <td class="chosen">:white_check_mark: Chosen</td>
    <td class="chosen">[One owner for parsing policy, loaders, API, and CLI](#ownership).</td>
  </tr>
  <tr markdown="span">
    <th class="not-selected">[Separate parser adapter](#alternative-considered)</th>
    <td class="not-selected">:material-minus-circle-outline: Not selected</td>
    <td class="not-selected">[Adds interface and release coordination without an identified independent consumer](#alternative-considered).</td>
  </tr>
</table>

### Ownership

PyLD owns YAML-LD parsing-policy fixes together with loader, API, and CLI fixes.
They ship in PyLD releases. This avoids maintaining a versioned parser-adapter
interface and a second implementation package's compatibility matrix.

### Alternative considered

A separate parser-only adapter could release its parsing-policy fixes independently
and serve consumers outside PyLD. It would require PyLD to test its supported
adapter version range and coordinate interface changes. No independent consumer
has been identified for this proposal, so that additional boundary is not selected.

Parser selection is recorded separately in
[Parse YAML-LD with `ruamel.yaml`]({{ documentation_url('/project/decisions/parse-yaml-ld-with/') }}).

## :material-arrow-right-bold-outline: Consequences

- Keep `pyld.jsonld.*` and `pyld` as the public processing interfaces. Preserve
  existing URL and parsed-document inputs, JSON stdin defaults, and raw RDF boundaries.
- Implement the pinned YAML-LD rules in
  [:fontawesome-brands-github: `index.html`](https://github.com/w3c/yaml-ld/blob/ec5d431c3aa7da5d89865df34ad150db8c8418e7/index.html#L1299-L1360)
  at `ec5d431`:
  accept zero or one YAML document per input; `extractAllScripts` selects HTML scripts only.
- Convert the existing `yaml-ld` distribution into a dependency-only installation
  proxy, using a [dependency with an extra](https://packaging.python.org/en/latest/specifications/dependency-specifiers/#extras).
  Its minimum required PyLD version will be the first release providing the
  `yaml-ld` extra; dependency resolution may select a newer compatible release.
  Thus `pip install yaml-ld` remains an installation route after migration.
  The proxy delegates parsing and processing to PyLD.
- Migrate the old package's imports and CLI to `pyld.jsonld.*` and `pyld`.
  The installation proxy preserves the install route, not the old API or CLI.

#### Implementation Steps

- [ ] Implement optional parser/loading integration and conformance coverage in PyLD.
- [ ] Release PyLD with the `yaml-ld` extra.
- [ ] Convert and publish the `yaml-ld` installation proxy and its migration guide.
- [ ] Update installation and usage documentation; validate package installs,
  processing tests, and rendered examples.
