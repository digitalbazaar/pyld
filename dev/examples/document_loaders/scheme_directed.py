import json
from pathlib import Path

from pyld import (
    SchemeDirectedDocumentLoader,
    FileDocumentLoader,
    FrozenDocumentLoader,
    jsonld,
)

person = (
    Path(__file__).resolve().parent.parent / 'data' / 'person_remote_context.jsonld'
)

http = FrozenDocumentLoader(
    documents={
        'https://example.com/context': {
            '@context': {'name': 'http://schema.org/name'},
        },
    }
)
loader = SchemeDirectedDocumentLoader(
    file=FileDocumentLoader(),
    http=http,
    https=http,
)
result = jsonld.expand(
    person.as_uri(),
    options={'documentLoader': loader},
)
print(json.dumps(result, indent=2))
