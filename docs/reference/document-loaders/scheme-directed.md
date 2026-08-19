---
hide: [toc]
---
# :material-call-split: `SchemeDirectedDocumentLoader`

::: pyld.SchemeDirectedDocumentLoader
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3
      members: false

Compose per-scheme loaders so a local document can resolve a remote `@context`:

=== "Example"

    {{ example('document_loaders/scheme_directed.py', output_syntax='json', indent=4) }}

=== "person_remote_context.jsonld"

    {{ example_data('data/person_remote_context.jsonld', indent=4) }}
