# :material-database: `SqliteCacheRequestsDocumentLoader`

`SqliteCacheRequestsDocumentLoader` retrieves JSON-LD documents with
`requests-cache`, storing responses in a persistent SQLite file. HTTP cache
headers (`Cache-Control`, `Expires`, validators) are always honored.

Caching is opt-in: pass the loader via `options["documentLoader"]`. It composes
`RequestsDocumentLoader` internally.

Specify an absolute path to the `.sqlite` cache file:

{{ example('document_loaders/sqlite_cache_basic.py', output_syntax='json') }}

When `sqlite_file_path` is omitted, the cache defaults to the platform user
cache directory:

| OS | Default path |
|----|--------------|
| Linux | `~/.cache/pyld/http_cache.sqlite` |
| macOS | `~/Library/Caches/pyld/http_cache.sqlite` |
| Windows | `%LOCALAPPDATA%\pyld\http_cache.sqlite` |

Inspect the resolved path at runtime with `loader.session.cache.db_path`.

For other `CachedSession` options (memory backend, custom TTL, and so on), use
`RequestsDocumentLoader` with a pre-built session:

```python
from requests_cache import CachedSession

from pyld import RequestsDocumentLoader

loader = RequestsDocumentLoader(
    session=CachedSession("cache", backend="memory", cache_control=True),
    timeout=10,
)
```

Install the optional dependency with:

```bash
pip install "PyLD[requests-cache]"
```
