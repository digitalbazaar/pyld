import json

from pyld import jsonld

doc = {
    "name": "Ada Lovelace",
    "homepage": "https://example.com/ada",
}
source_context = {
    "name": "http://schema.org/name",
    "homepage": {"@id": "http://schema.org/url", "@type": "@id"},
}
output_context = {
    "name": "http://schema.org/name",
    "url": {"@id": "http://schema.org/url", "@type": "@id"},
}

compacted = jsonld.compact(
    doc,
    output_context,
    {"expandContext": source_context},
)

print(json.dumps(compacted, indent=2))
