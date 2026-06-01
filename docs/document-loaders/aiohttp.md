# AioHttpDocumentLoader

`AioHttpDocumentLoader` retrieves JSON-LD documents with `aiohttp`.

```python
from pyld import jsonld

jsonld.set_document_loader(jsonld.aiohttp_document_loader(timeout=10))
```

This loader uses asynchronous fetching internally, but JSON-LD processing itself
remains synchronous.

The concrete loader class is exported from `pyld`:

```python
from pyld import AioHttpDocumentLoader, jsonld

jsonld.set_document_loader(AioHttpDocumentLoader(timeout=10))
```

Use `secure=True` to require HTTPS URLs:

```python
jsonld.set_document_loader(
    jsonld.aiohttp_document_loader(secure=True, timeout=10)
)
```

Extra keyword arguments are forwarded to `aiohttp` request calls:

```python
from pyld import AioHttpDocumentLoader, jsonld

loader = AioHttpDocumentLoader(timeout=10)

jsonld.set_document_loader(loader)
```

Install the optional dependency with:

```bash
pip install "PyLD[aiohttp]"
```
