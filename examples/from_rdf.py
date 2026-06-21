import json

from pyld import jsonld

nquads = (
    '<http://dbpedia.org/resource/Earth> '
    '<http://schema.org/name> "Earth" .\n'
)

doc = jsonld.from_rdf(nquads, {"format": "application/n-quads"})

print(json.dumps(doc, indent=2))
