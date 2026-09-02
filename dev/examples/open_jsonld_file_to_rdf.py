import json
from pathlib import Path

from pyld import jsonld

path = Path(__file__).resolve().parent / "data" / "person.jsonld"
doc = json.loads(path.read_text())

nquads = jsonld.to_rdf(doc, {"format": "application/n-quads"})

print(nquads)
