import json

from cachetools import LRUCache

from pyld import ContextResolver, DocumentLoader, jsonld

CONTEXT_URL = "context://my-app/vocab"

DOCUMENT_CACHE = {
    CONTEXT_URL: {
        "contentType": "application/ld+json",
        "contextUrl": None,
        "documentUrl": CONTEXT_URL,
        "document": {
            "@context": {
                "name": "https://schema.org/name",
                "homepage": {"@id": "https://schema.org/url", "@type": "@id"},
            }
        },
    }
}


class CachedContextLoader(DocumentLoader):
    def __init__(self, documents):
        self.documents = documents
        self.load_count = 0

    def __call__(self, url, options):
        self.load_count += 1
        return self.documents[url]


loader = CachedContextLoader(DOCUMENT_CACHE)
resolved_context_cache = LRUCache(maxsize=1000)
resolver = ContextResolver(
    resolved_context_cache,
    loader,
    max_context_urls=20,
)

doc = {
    "@context": CONTEXT_URL,
    "name": "Example Person",
    "homepage": "https://example.com/",
}
options = {"documentLoader": loader, "contextResolver": resolver}

expanded = jsonld.expand(doc, options=options)
jsonld.expand(doc, options=options)

print(json.dumps({"contextLoads": loader.load_count, "expanded": expanded}, indent=2))
