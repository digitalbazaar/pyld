import json
from pathlib import Path

from pyld import FileDocumentLoader, jsonld

person = Path(__file__).resolve().parent.parent / 'data' / 'person.jsonld'

loader = FileDocumentLoader()
result = jsonld.expand(
    person.as_uri(),
    options={'documentLoader': loader},
)
print(json.dumps(result, indent=2))
