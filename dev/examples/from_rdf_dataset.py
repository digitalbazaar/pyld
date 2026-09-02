import json

from rdflib import Dataset

from pyld import jsonld

nquads = (
    '<http://dbpedia.org/resource/Earth> '
    '<http://schema.org/name> "Earth" .\n'
)
dataset = Dataset().parse(data=nquads, format="nquads")

doc = jsonld.from_rdf(dataset)

print(json.dumps(doc, indent=2))
