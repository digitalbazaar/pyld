---
hide: [toc]
---

# :material-cached: `pyld cache`

!!! warning "Requires `pip install PyLD[cli]`"

Clear the HTTP cache for remote JSON-LD contexts fetched by the CLI.

The cache file lives in a `cli/` subdirectory of the platform user cache
directory documented for
[`SqliteCacheRequestsDocumentLoader`](../reference/document-loaders/sqlite-cache-requests.md).

Override the location with `--cache-file` or the `PYLD_CACHE_FILE` environment
variable (`--cache-file` wins when both are set):

{{ terminal('pyld --cache-file /tmp/pyld-cache.sqlite cache clear') }}

::: mkdocs-typer2
    :module: pyld.cli
    :name: pyld
    :command: cache
    :termynal: true
    :width: 88
    :subcommands: 1

## Clear the cache

{{ terminal('pyld cache clear') }}
