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

# At the first execution, this will perform a network request to https://schema.org,
# but subsequent executions of the same code will not, using a cached response.
result = jsonld.expand(doc, options={"documentLoader": loader})

print(json.dumps(result, indent=2))
