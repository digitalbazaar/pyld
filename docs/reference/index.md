---
hide: [toc]
---

# :octicons-book-24: Reference

<div class="grid cards" markdown>

-   [:material-arrow-collapse:{ .lg .middle } `jsonld.compact()`](compact.md)

    ---

    Compacts a JSON-LD document with a context, replacing full IRIs with shorter
    terms where possible.

-   [:material-arrow-expand:{ .lg .middle } `jsonld.expand()`](expand.md)

    ---

    Expands a compacted JSON-LD document into full IRI-based form and removes the
    context.

-   [:material-layers-outline:{ .lg .middle } `jsonld.flatten()`](flatten.md)

    ---

    Flattens nested JSON-LD into a top-level node map so each node can be processed
    independently.

-   [:material-view-dashboard-outline:{ .lg .middle } `jsonld.frame()`](frame.md)

    ---

    Frames expanded JSON-LD into a predictable tree shape that matches a supplied
    frame.

-   [:material-export:{ .lg .middle } `jsonld.to_rdf()`](to_rdf.md)

    ---

    Converts a JSON-LD document into RDF statements in a requested serialization
    format.

-   [:material-import:{ .lg .middle } `jsonld.from_rdf()`](from_rdf.md)

    ---

    Converts RDF statements into JSON-LD so the data can be processed with the
    JSON-LD API.

-   [:material-fingerprint:{ .lg .middle } `jsonld.normalize()`](normalize.md)

    ---

    Normalizes JSON-LD into canonical RDF statements for stable comparison,
    hashing, or signing.

</div>

## Also

<div class="grid cards" markdown>

-   [:material-file-download-outline:{ .lg .middle } __Document Loaders__](document-loaders/index.md)

    ---

    Load remote JSON-LD documents and contexts with the built-in loader classes.

-   :material-hard-hat:{ .lg .middle } __In construction__

    ---

    We are working on more reference documentation. It is coming soon.

</div>
