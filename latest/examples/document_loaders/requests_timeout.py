import json

from pyld import RequestsDocumentLoader, jsonld

doc = {
    "@context": {"name": "http://schema.org/name"},
    "name": "Earth",
}

loader = RequestsDocumentLoader(timeout=10)
result = jsonld.expand(doc, options={"documentLoader": loader})
print(json.dumps(result, indent=2))
