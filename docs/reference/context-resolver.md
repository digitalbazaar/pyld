# :material-cached: `ContextResolver`

`ContextResolver` resolves remote `@context` documents and caches the resolved
contexts used by JSON-LD operations.

::: pyld.ContextResolver
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3

Pass a custom `ContextResolver` with the `contextResolver` option when you need
to provide your own resolved-context cache or adjust the remote-context recursion
limit. The resolver still uses a `DocumentLoader` to fetch remote context
documents, so pass the same loader with `documentLoader`.

{{ example('context_resolver.py', output_syntax='json') }}

The `shared_cache` object must behave like a mutable mapping. PyLD uses
`cachetools.LRUCache` by default, but applications can provide another mapping
when they need a different eviction policy.

Use `max_context_urls` to change how many remote contexts may be fetched while
resolving nested or imported contexts.
