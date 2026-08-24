import json

from pyld import jsonld

doc = {
    "@type": "http://schema.org/Person",
    "http://schema.org/name": "Manu Sporny",
    "http://schema.org/url": {"@id": "http://manu.sporny.org/"},
    "http://schema.org/image": {
        "@id": "http://manu.sporny.org/images/manu.png"
    },
}

identifier_map = jsonld.normalize(
    doc,
    {"algorithm": "RDFC10", "outputMap": True},
)

print(json.dumps(identifier_map, indent=2))
