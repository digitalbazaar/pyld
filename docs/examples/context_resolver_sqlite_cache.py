import json
from pathlib import Path

from cachetools import LRUCache

from pyld import ContextResolver, SqliteCacheRequestsDocumentLoader, jsonld

loader = SqliteCacheRequestsDocumentLoader(
    sqlite_file_path=Path("/tmp/pyld_example_context_cache.sqlite"),
)
resolver = ContextResolver(LRUCache(maxsize=1000), loader)

doc = {
    "@context": "https://schema.org/",
    "name": "Example Person",
}
options = {"documentLoader": loader, "contextResolver": resolver}

expanded = jsonld.expand(doc, options=options)

print(json.dumps(expanded, indent=2))
