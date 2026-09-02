import json

from pyld import jsonld

doc = {
    "@context": {
        "name": "http://schema.org/name",
        "homepage": {"@id": "http://schema.org/url", "@type": "@id"},
        "image": {"@id": "http://schema.org/image", "@type": "@id"},
    },
    "image": "http://manu.sporny.org/images/manu.png",
    "homepage": "http://manu.sporny.org/",
    "name": "Manu Sporny",
}

expanded = jsonld.expand(doc)

print(json.dumps(expanded, indent=2))
