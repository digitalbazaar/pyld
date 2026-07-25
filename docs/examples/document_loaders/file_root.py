import json
from pathlib import Path

from pyld import FileDocumentLoader, jsonld

data_dir = Path(__file__).resolve().parent.parent / 'data'
person = data_dir / 'person.jsonld'

loader = FileDocumentLoader(root=data_dir)
result = jsonld.expand(
    person.as_uri(),
    options={'documentLoader': loader},
)
print(json.dumps(result, indent=2))
