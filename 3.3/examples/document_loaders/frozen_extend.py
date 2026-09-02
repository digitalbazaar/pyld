import json

from pyld import BUNDLED_CONTEXTS, FrozenDocumentLoader, jsonld

loader = FrozenDocumentLoader(
    documents=dict(
        BUNDLED_CONTEXTS,
        **{
            "https://example.com/context": {
                "@context": {"name": "https://schema.org/name"}
            }
        },
    )
)

doc = {
    "@context": "https://example.com/context",
    "name": "Earth",
}

result = jsonld.expand(doc, options={"documentLoader": loader})
print(json.dumps(result, indent=2))
