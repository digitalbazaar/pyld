import json

from pyld import jsonld

doc = {
    "http://schema.org/name": "Manu Sporny",
    "http://schema.org/url": {"@id": "http://manu.sporny.org/"},
    "http://schema.org/image": {
        "@id": "http://manu.sporny.org/images/manu.png"
    },
}

context = {
    "name": "http://schema.org/name",
    "homepage": {"@id": "http://schema.org/url", "@type": "@id"},
    "image": {"@id": "http://schema.org/image", "@type": "@id"},
}

compacted = jsonld.compact(doc, context)

print(json.dumps(compacted, indent=2))
