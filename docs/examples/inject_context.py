import json

from pyld import jsonld

doc = {
    "name": "Ada Lovelace",
    "homepage": "https://example.com/ada",
}
context = {
    "name": "http://schema.org/name",
    "homepage": {"@id": "http://schema.org/url", "@type": "@id"},
}

expanded = jsonld.expand(doc, {"expandContext": context})

print(json.dumps(expanded, indent=2))
