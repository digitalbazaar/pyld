import json

from pyld import jsonld

doc = {
    "@id": "http://example.com/people/manu",
    "@type": "http://schema.org/Person",
    "http://schema.org/name": "Manu Sporny",
    "http://schema.org/url": {"@id": "http://manu.sporny.org/"},
    "http://schema.org/image": {
        "@id": "http://manu.sporny.org/images/manu.png"
    },
}

frame = {
    "@context": {
        "name": "http://schema.org/name",
        "homepage": {"@id": "http://schema.org/url", "@type": "@id"},
        "image": {"@id": "http://schema.org/image", "@type": "@id"},
    },
    "@type": "http://schema.org/Person",
}

framed = jsonld.frame(doc, frame)

print(json.dumps(framed, indent=2))
