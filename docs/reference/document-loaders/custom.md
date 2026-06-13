# :material-code-braces: Custom Document Loaders

Subclass `DocumentLoader` and implement `__call__` to return a remote document
mapping with `contentType`, `contextUrl`, `documentUrl`, and `document` keys.
Custom schemes such as `context://` cannot be fetched over HTTP, so a custom
loader is required to resolve them.

{{ example('document_loaders/custom_document_loader.py', output_syntax='json') }}
