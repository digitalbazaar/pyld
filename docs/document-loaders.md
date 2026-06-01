# Document Loaders

Document loaders retrieve remote JSON-LD documents and contexts. PyLD accepts
any callable with the loader signature, and also ships class-based loaders for
common cases.

## Built-In Loader Classes

- [RequestsDocumentLoader](document-loaders/requests.md) uses `requests` for
  synchronous remote document loading.
- [AioHttpDocumentLoader](document-loaders/aiohttp.md) uses `aiohttp` for
  asynchronous fetching while keeping JSON-LD processing synchronous.
- [FrozenDocumentLoader](document-loaders/frozen.md) serves only documents from
  an allowlist.

The default document loader is selected at import time. PyLD uses
`RequestsDocumentLoader` if `requests` is available, falls back to
`AioHttpDocumentLoader` if `aiohttp` is available, and otherwise installs a
dummy loader that raises when invoked.

## Custom Loaders

A custom loader returns a remote document mapping with `contextUrl`,
`documentUrl`, and `document` keys:

```python
from pyld import jsonld

document_cache = {
    "https://example.com/context": {
        "contextUrl": None,
        "documentUrl": "https://example.com/context",
        "document": {"@context": {"name": "https://schema.org/name"}},
    }
}


def load_document(url, options=None):
    return document_cache[url]


jsonld.set_document_loader(load_document)
```

For advanced context caching, pass a `ContextResolver` in operation options:

```python
from cachetools import LRUCache
from pyld import ContextResolver, jsonld

resolver = ContextResolver(LRUCache(maxsize=1000), load_document)

expanded = jsonld.expand(
    doc,
    options={"contextResolver": resolver},
)
```
