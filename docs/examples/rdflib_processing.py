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
dataset.add((subject, SCHEMA.url, URIRef("https://example.com/earth")))

jsonld_doc = jsonld.from_rdf(dataset)
compacted = jsonld.compact(
    jsonld_doc,
    {
        "name": str(SCHEMA.name),
        "homepage": {"@id": str(SCHEMA.url), "@type": "@id"},
    },
)

print(json.dumps(compacted, indent=2))
