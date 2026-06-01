# RequestsDocumentLoader

`RequestsDocumentLoader` retrieves JSON-LD documents with `requests`.

The default remote document loader uses `requests` when it is available.
Production applications should usually set at least a timeout:

```python
from pyld import jsonld

jsonld.set_document_loader(jsonld.requests_document_loader(timeout=10))
```

The concrete loader class is exported from `pyld`:

```python
from pyld import RequestsDocumentLoader, jsonld

jsonld.set_document_loader(RequestsDocumentLoader(timeout=10))
```

Use `secure=True` to require HTTPS URLs:

```python
jsonld.set_document_loader(
    jsonld.requests_document_loader(secure=True, timeout=10)
)
```

Extra keyword arguments are forwarded to `requests.get()`:

```python
from pyld import RequestsDocumentLoader, jsonld

loader = RequestsDocumentLoader(
    timeout=10,
    verify=True,
    cert=("client.crt", "client.key"),
)

jsonld.set_document_loader(loader)
```

Install the optional dependency with:

```bash
pip install "PyLD[requests]"
```
