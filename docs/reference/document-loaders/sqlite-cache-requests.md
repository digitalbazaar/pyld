---
hide: [toc]
---

# :material-database: `SqliteCacheRequestsDocumentLoader`

!!! info "Prerequisite"
    This functionality requires an extra dependency, [:simple-pypi: `requests-cache`](https://pypi.org/project/requests-cache). Install `PyLD` with:

    ```shell
    pip install 'PyLD[requests-cache]'
    ```

::: pyld.SqliteCacheRequestsDocumentLoader
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3

When `sqlite_file_path` is omitted, the cache defaults to the platform user
cache directory:

| OS | Default path |
|----|--------------|
| :simple-linux: Linux | `~/.cache/pyld/http_cache.sqlite` |
| :simple-apple: macOS | `~/Library/Caches/pyld/http_cache.sqlite` |
| :material-microsoft-windows-classic: Windows | `%LOCALAPPDATA%\pyld\http_cache.sqlite` |

`SqliteCacheRequestsDocumentLoader` retrieves remote JSON-LD documents and keeps
them in a persistent [:simple-sqlite: SQLite](https://www.sqlite.org/) cache. It
is useful for applications that repeatedly load the same remote contexts across
process runs.

HTTP cache headers (`Cache-Control`, `Expires`, validators) are honored, so
publishers can control how cached context documents are reused.

[JSON-LD Best Practices](https://w3c.github.io/json-ld-bp/) recommends:

> **Best Practice 14:** Cache JSON-LD Contexts
>
> Services providing a JSON-LD Context *SHOULD* set HTTP cache-control headers to
> allow liberal caching of such contexts, and clients *SHOULD* attempt to use a
> locally cached version of these documents.
>
> - [§ 8.1 Cache JSON-LD Contexts](https://w3c.github.io/json-ld-bp/#cache-json-ld-contexts)

{{ example('document_loaders/sqlite_cache_basic.py', output_syntax='json') }}

??? note "Decisions"
    This page is influenced by the decision to
    [use `requests-cache` for persistent HTTP caching in synchronous Python code](/pyld/project/decisions/use-requests-cache-for-sync-http-caching-in-document-loaders/).
