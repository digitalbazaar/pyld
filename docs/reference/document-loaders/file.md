---
hide: [toc]
---
# :material-file-outline: `FileDocumentLoader`

::: pyld.FileDocumentLoader
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3
      members: false

`FileDocumentLoader` accepts `file:` URLs, scheme-less absolute paths, and
`pathlib.Path` instances. Its optional `root` constructor argument confines
the files it may read to a chosen directory.

{{ example('document_loaders/file_basic.py', output_syntax='json') }}

## Content Types

The content type is chosen based on the file extension as follows:

{{ file_content_types_table() }}

Unsupported extensions raise `JsonLdError` with code `loading document failed`.

## Root Confinement

All requested paths, including symlink targets, must resolve beneath `root`,
so `..` traversal and symlink escapes are rejected:

{{ example('document_loaders/file_root.py', output_syntax='json') }}
