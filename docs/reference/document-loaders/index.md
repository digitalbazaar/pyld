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

    Persistent SQLite HTTP caching for JSON-LD contexts with `requests-cache`.

-   [:material-sync:{ .lg .middle } `AioHttpDocumentLoader`](aiohttp.md)

    ---

    Asynchronous fetching with `aiohttp` while JSON-LD processing stays
    synchronous.

-   [:material-snowflake:{ .lg .middle } `FrozenDocumentLoader`](frozen.md)

    ---

    Serve only documents from an allowlist for air-gapped or reproducible runs.

-   [:material-code-braces:{ .lg .middle } __Custom Document Loaders__](custom.md)

    ---

    Subclass `DocumentLoader` for application-specific loading logic.

</div>

## Default Document Loader

The default document loader is selected at import time. PyLD uses
`RequestsDocumentLoader` if `requests` is available, falls back to
`AioHttpDocumentLoader` if `aiohttp` is available, and otherwise installs a
dummy loader that raises when invoked.
