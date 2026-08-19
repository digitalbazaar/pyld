# :material-file-download-outline: Document Loaders

Document loaders retrieve remote JSON-LD documents and contexts. PyLD ships
class-based loaders for common cases and supports custom subclasses of
`DocumentLoader`.

<div class="grid cards" markdown>

-   [:material-cloud-download:{ .lg .middle } `RequestsDocumentLoader`](requests.md)

    ---

    Synchronous remote document loading with `requests`.

-   [:material-database:{ .lg .middle } `SqliteCacheRequestsDocumentLoader`](sqlite-cache-requests.md)

    ---

    Persistent [:simple-sqlite: SQLite](https://www.sqlite.org/) caching for
    remote JSON-LD documents.

-   [:material-sync:{ .lg .middle } `AioHttpDocumentLoader`](aiohttp.md)

    ---

    Asynchronous fetching with `aiohttp` while JSON-LD processing stays
    synchronous.

-   [:material-snowflake:{ .lg .middle } `FrozenDocumentLoader`](frozen.md)

    ---

    Serve only documents from an allowlist for air-gapped or reproducible runs.

-   [:material-file-outline:{ .lg .middle } `FileDocumentLoader`](file.md)

    ---

    Read local JSON-LD documents from `file:` URLs.

-   [:material-call-split:{ .lg .middle } `SchemeDirectedDocumentLoader`](scheme-directed.md)

    ---

    Delegate to another Document Loader based on the scheme of the URL, for instance, `file:` vs `https://`.

-   [:material-code-braces:{ .lg .middle } __Custom Document Loaders__](custom.md)

    ---

    Subclass `DocumentLoader` for application-specific loading logic.

</div>

## Default Document Loader

The default document loader is selected at import time, in this order:

1. [`RequestsDocumentLoader`](requests.md) if `requests` is available
2. [`AioHttpDocumentLoader`](aiohttp.md) if `aiohttp` is available

If neither is installed, document loading raises.
