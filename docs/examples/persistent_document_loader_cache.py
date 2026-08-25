import json
import tempfile
from pathlib import Path
from uuid import uuid4

from pyld import SqliteCacheRequestsDocumentLoader, jsonld

cache_path = Path(tempfile.gettempdir()) / f"pyld-{uuid4()}.sqlite"
loader = SqliteCacheRequestsDocumentLoader(sqlite_file_path=cache_path)

doc = {
    "@context": {"name": "https://schema.org/name"},
    "name": "Earth",
}

expanded = jsonld.expand(doc, options={"documentLoader": loader})

print(json.dumps(expanded, indent=2))
