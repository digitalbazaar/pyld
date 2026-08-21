import json
from pathlib import Path

from pyld import (
    FileDocumentLoader,
    FrozenDocumentLoader,
    SchemeDirectedDocumentLoader,
    TypeDirectedDocumentLoader,
    jsonld,
)

person = (
    Path(__file__).resolve().parent.parent / 'data' / 'person_remote_context.jsonld'
)

file_loader = FileDocumentLoader()
http_loader = FrozenDocumentLoader(
    documents={
        'https://example.com/context': {
            '@context': {'name': 'http://schema.org/name'},
        },
    }
)
loader = TypeDirectedDocumentLoader(
    {
        Path: file_loader,
        str: SchemeDirectedDocumentLoader(
            file=file_loader,
            http=http_loader,
            https=http_loader,
        ),
    }
)
remote = jsonld.load_document(person, options={'documentLoader': loader})
result = jsonld.expand(
    remote['document'],
    options={
        'documentLoader': loader,
        'base': remote['documentUrl'],
    },
)
print(json.dumps(result, indent=2))
