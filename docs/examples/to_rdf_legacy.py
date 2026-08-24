import json

from pyld import jsonld

doc = {
    "@context": {
        "name": "http://schema.org/name",
    },
    "@id": "http://dbpedia.org/resource/Earth",
    "name": "Earth",
}

legacy_dataset = jsonld.to_rdf(doc, {"legacyMode": True})

print(json.dumps(legacy_dataset, indent=2))
