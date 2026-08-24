from pyld import jsonld

doc = {
    "@context": {
        "name": "http://schema.org/name",
    },
    "@id": "http://dbpedia.org/resource/Earth",
    "name": "Earth",
}

dataset = jsonld.to_rdf(doc)

print(type(dataset).__name__)
print(dataset.serialize(format="nquads"))
