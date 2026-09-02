import json

from pyld import FrozenDocumentLoader, jsonld

doc = {
    "@context": {"name": "http://schema.org/name"},
    "name": "Earth",
}

loader = FrozenDocumentLoader()
result = jsonld.expand(doc, options={"documentLoader": loader})
print(json.dumps(result, indent=2))
