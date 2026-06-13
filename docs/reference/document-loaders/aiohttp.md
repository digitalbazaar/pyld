# :material-sync: `AioHttpDocumentLoader`

`AioHttpDocumentLoader` retrieves JSON-LD documents with `aiohttp`.

{{ example('document_loaders/aiohttp_class.py', output_syntax='json') }}

This loader uses asynchronous fetching internally, but JSON-LD processing itself
remains synchronous.

Use `secure=True` to require HTTPS URLs:

{{ example('document_loaders/aiohttp_secure.py', output_syntax='json') }}

Extra keyword arguments are forwarded to `aiohttp` request calls:

{{ example('document_loaders/aiohttp_extra_kwargs.py', output_syntax='json') }}

Install the optional dependency with:

```bash
pip install "PyLD[aiohttp]"
```
