import json

from pyld import AioHttpDocumentLoader, jsonld

doc = {
    "@context": {"name": "http://schema.org/name"},
    "name": "Earth",
}

loader = AioHttpDocumentLoader(secure=True, timeout=10)
result = jsonld.expand(doc, options={"documentLoader": loader})
print(json.dumps(result, indent=2))
