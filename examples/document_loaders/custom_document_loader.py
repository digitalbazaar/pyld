import json

from pyld import DocumentLoader, jsonld

DOCUMENT_CACHE = {
    "context://my-app/vocab": {
        "contentType": "application/ld+json",
        "contextUrl": None,
        "documentUrl": "context://my-app/vocab",
        "document": {"@context": {"name": "https://schema.org/name"}},
    }
}


class ExampleDocumentLoader(DocumentLoader):
    def __call__(self, url, options):
        return DOCUMENT_CACHE[url]


doc = {
    "@context": "context://my-app/vocab",
    "name": "Earth",
}

loader = ExampleDocumentLoader()
result = jsonld.expand(doc, options={"documentLoader": loader})
print(json.dumps(result, indent=2))
