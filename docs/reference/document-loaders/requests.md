# :material-cloud-download: `RequestsDocumentLoader`

`RequestsDocumentLoader` retrieves JSON-LD documents with `requests`.

The default remote document loader uses `requests` when it is available.
Production applications should usually set at least a timeout:

{{ example('document_loaders/requests_timeout.py', output_syntax='json') }}

Use `secure=True` to require HTTPS URLs:

{{ example('document_loaders/requests_secure.py', output_syntax='json') }}

Extra keyword arguments are forwarded to `requests.get()`:

{{ example('document_loaders/requests_extra_kwargs.py', output_syntax='json') }}

Install the optional dependency with:

```bash
pip install "PyLD[requests]"
```
