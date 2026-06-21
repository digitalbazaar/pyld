import json

from pyld import jsonld

doc = {
    "http://schema.org/name": "Manu Sporny",
    "http://schema.org/url": {"@id": "http://manu.sporny.org/"},
    "http://schema.org/image": {
        "@id": "http://manu.sporny.org/images/manu.png"
    },
}

flattened = jsonld.flatten(doc)

print(json.dumps(flattened, indent=2))
