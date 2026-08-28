---
hide: [toc]
icon: material/console
---

# :material-console: CLI

!!! warning "Requires `pip install PyLD[cli]`"

PyLD ships a `pyld` command-line tool for JSON-LD 1.1 transformations.

JSON-LD inputs accept a local path, URL, or explicit `-` for standard input.
Contexts and frames accept a local path, URL, or `-`. Only one operand in an
invocation may consume standard input. Raw N-Quads input accepts only a local
path or `-`, and N-Quads output is written directly to standard output without
JSON quoting or terminal styling.

<div class="grid cards" markdown>

-   [:material-download:{ .lg .middle } `pyld get`](get.md)

    ---

    Retrieve a JSON-LD document from a path, URL, or explicit stdin input (`-`).

-   [:material-arrow-expand:{ .lg .middle } `pyld expand`](expand.md)

    ---

    Expand a JSON-LD document into full IRI-based form.

-   [:material-arrow-collapse:{ .lg .middle } `pyld compact`](compact.md)

    ---

    Compact a JSON-LD document using a context.

-   [:material-format-list-group:{ .lg .middle } `pyld flatten`](flatten.md)

    ---

    Flatten a JSON-LD document into a single node map.

-   [:material-image-frame:{ .lg .middle } `pyld frame`](frame.md)

    ---

    Frame a JSON-LD document into a selected tree shape.

-   [:material-export:{ .lg .middle } `pyld to-rdf`](to-rdf.md)

    ---

    Convert JSON-LD to raw N-Quads.

-   [:material-import:{ .lg .middle } `pyld from-rdf`](from-rdf.md)

    ---

    Convert raw N-Quads to JSON-LD.

-   [:material-cached:{ .lg .middle } `pyld cache`](cache.md)

    ---

    Manage the CLI HTTP cache for remote JSON-LD contexts.

</div>
