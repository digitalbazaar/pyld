import json
from pathlib import Path

from pyld import SqliteCacheRequestsDocumentLoader, jsonld

doc = {
    "@context": {"name": "http://schema.org/name"},
    "name": "Earth",
}

loader = SqliteCacheRequestsDocumentLoader(
    sqlite_file_path=Path("/tmp/pyld_example_http_cache.sqlite"),
)
result = jsonld.expand(doc, options={"documentLoader": loader})
print(json.dumps(result, indent=2))
