import json

from rdflib import Dataset

from pyld import jsonld

nquads = (
    '<http://dbpedia.org/resource/Earth> '
    '<http://schema.org/name> "Earth" .\n'
)
dataset = Dataset().parse(data=nquads, format="nquads")

doc = jsonld.from_rdf(dataset)
compacted = jsonld.compact(doc, {"name": "http://schema.org/name"})

print(json.dumps(compacted, indent=2))
