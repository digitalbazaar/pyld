# :material-snowflake: `FrozenDocumentLoader`

::: pyld.FrozenDocumentLoader
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3
      members: false

With no arguments, the loader serves the curated `BUNDLED_CONTEXTS` mapping:

{{ example('document_loaders/frozen_default.py', output_syntax='json') }}

## Bundled Contexts

{{ bundled_contexts_table() }}

Extend the bundled mapping with additional vetted contexts:

{{ example('document_loaders/frozen_extend.py', output_syntax='json') }}

The `documents` mapping may contain parsed JSON-LD dictionaries or
`pathlib.Path` instances pointing to JSON files. Path entries are read lazily
and cached after the first request.

Any URL outside the allowlist raises `JsonLdError` with code
`loading document failed`.
