from pyld import jsonld

doc = {
    "@context": {
        "name": "http://schema.org/name",
    },
    "@id": "http://dbpedia.org/resource/Earth",
    "name": "Earth",
}

print(jsonld.to_rdf(doc, {"format": "application/n-quads"}))
