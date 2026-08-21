---
hide: [toc]
---
# :material-shape-outline: `TypeDirectedDocumentLoader`

::: pyld.TypeDirectedDocumentLoader
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3
      members: false

`TypeDirectedDocumentLoader` dispatches a value to the loader registered for its Python type. Applications can register any types that represent distinct document locations or loading policies.

This example registers `Path` for local documents and `str` for URL values. A local document is loaded through `FileDocumentLoader`; its remote `@context` is a URL string, so the `str` registration delegates to a nested `SchemeDirectedDocumentLoader`.

=== "Example"

    {{ example('document_loaders/type_directed.py', output_syntax='json', indent=4) }}

=== "person_remote_context.jsonld"

    {{ example_data('data/person_remote_context.jsonld', indent=4) }}
