import json
import tempfile
from pathlib import Path
from uuid import uuid4

from requests_cache import CachedSession

from pyld import (
    RequestsDocumentLoader,
    SqliteCacheRequestsDocumentLoader,
    jsonld,
)

doc = {
    "@context": {"name": "https://schema.org/name"},
    "name": "Earth",
}

no_cache_loader = RequestsDocumentLoader()

memory_cache_loader = RequestsDocumentLoader(
    session=CachedSession(backend="memory", cache_control=True),
)

persistent_cache_loader = SqliteCacheRequestsDocumentLoader(
    sqlite_file_path=Path(tempfile.gettempdir()) / f"pyld-{uuid4()}.sqlite",
)

result = jsonld.expand(doc, options={"documentLoader": persistent_cache_loader})

print(json.dumps(result, indent=2))
