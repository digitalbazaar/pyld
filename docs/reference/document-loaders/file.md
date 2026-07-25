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

{{ example('document_loaders/file_basic.py', output_syntax='json') }}

## Content Types

The content type is chosen based on the file extension as follows:

{{ file_content_types_table() }}

Unsupported extensions raise `JsonLdError` with code `loading document failed`.

## Root Confinement

Pass `root` to refuse paths that resolve outside a directory. Resolved paths
and symlink targets are checked, so `..` traversal and symlink escapes are
rejected:

{{ example('document_loaders/file_root.py', output_syntax='json') }}
