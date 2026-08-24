import json
from pathlib import Path

from pyld import jsonld

path = Path(__file__).resolve().parent / "data" / "person.jsonld"
doc = json.loads(path.read_text())

expanded = jsonld.expand(doc)

print(json.dumps(expanded, indent=2))
