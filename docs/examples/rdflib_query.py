import json

from rdflib import Namespace, URIRef

from pyld import jsonld

SCHEMA = Namespace("http://schema.org/")
subject = URIRef("http://dbpedia.org/resource/Earth")

doc = {
    "@context": {"name": str(SCHEMA.name)},
    "@id": str(subject),
    "name": "Earth",
}

dataset = jsonld.to_rdf(doc)
names = [str(value) for value in dataset.objects(subject, SCHEMA.name)]

print(json.dumps(names, indent=2))
