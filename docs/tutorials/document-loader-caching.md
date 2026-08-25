# :material-cached: Caching remote contexts

Remote JSON-LD contexts are normal documents loaded through a `DocumentLoader`.
Caching therefore belongs in two places:

1. PyLD's `ContextResolver` caches resolved contexts during processing.
2. The `DocumentLoader` can cache HTTP responses before PyLD sees them.

Use `RequestsDocumentLoader` when you want no HTTP cache. Use
`RequestsDocumentLoader` with a `requests_cache.CachedSession` for in-memory
HTTP caching. Use `SqliteCacheRequestsDocumentLoader` when the cache should
survive process restarts. 

For HTTP caching, install the necessary modules first by running:

```bash
pip install "PyLD[requests-cache]"
```

## Choose a Cache Mode

| Mode | Loader | Reused after process restart? |
| --- | --- | --- |
| No HTTP cache | `RequestsDocumentLoader()` | No |
| In-memory HTTP cache | `RequestsDocumentLoader(session=CachedSession(backend="memory"))` | No |
| Persistent HTTP cache | `SqliteCacheRequestsDocumentLoader()` | Yes |

`SqliteCacheRequestsDocumentLoader` uses
[:simple-sqlite: SQLite](https://www.sqlite.org/) through
[:simple-pypi: `requests-cache`](https://pypi.org/project/requests-cache/).
When `sqlite_file_path` is omitted, it stores the cache in the platform user
cache directory.

## Usage

This example configures all three modes and passes the persistent loader through
`documentLoader`. The document uses an inline `@context` so the example is safe
to run without network access; use the same `options` shape when the `@context`
is a remote URL.

{{ example('document_loaders/caching_modes.py', output_syntax='json') }}

For application code, pass the selected loader in the operation `options`:

{{ example('persistent_document_loader_cache.py', output_syntax='json') }}

HTTP cache headers such as `Cache-Control`, `Expires`, and validators are
handled by the cached session. PyLD still applies its normal JSON-LD processing
rules after the remote document is loaded.

??? note "Related reference"
    See [`RequestsDocumentLoader`](../reference/document-loaders/requests.md),
    [`SqliteCacheRequestsDocumentLoader`](../reference/document-loaders/sqlite-cache-requests.md),
    and [`ContextResolver`](../reference/context-resolver.md).
