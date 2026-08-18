---
hide: [toc]
---

# :material-hard-hat: Project

Project documentation for PyLD — architecture decisions, development notes, and other material that sits alongside the API reference.

## :material-gavel: Architecture Decision Records

Architecture Decision Records (ADRs) document the technical choices taken during development of PyLD.

<div id="adr-index" markdown>

!!! warning inline "[Treat YAML-LD support as …](decisions/choose-where-to-host-yaml-ld-support/)"
    :material-calendar-clock: 19 July 2026

    Bundle into PyLD, keep a separate package (with suite under `specifications/`),
    expose a thin PyLD facade, or treat YAML-LD as out of scope (no suite either).

!!! success inline "[Use `requests-cache` for persistent HTTP caching in synchronous Python code](decisions/use-requests-cache-for-sync-http-caching-in-document-loaders/)"
    :material-calendar-clock: 29 June 2026

    Choose `requests-cache` for persistent, HTTP-aware synchronous
    document-loader caching.

!!! quote inline "Document the next important project decision"
    When a technical choice changes PyLD's architecture, public API, dependencies,
    or long-term maintenance path, capture the reasoning here as an
    [Architecture Decision Record](https://adr.github.io/).

</div>

## :material-source-branch: Decision Process

ADRs are useful when a technical choice has meaningful consequences for PyLD's
architecture, public API, dependencies, or long-term maintenance. A PR
discussion is enough to establish consensus for an ADR: if the maintainers agree
with the decision and merge the PR, the ADR lands as `decided`.

When consensus has not been reached yet, an ADR can land as `draft` and be
refined in follow-up PRs. If a later decision replaces an earlier one, mark the
earlier ADR as `superseded` and link to the new decision.
