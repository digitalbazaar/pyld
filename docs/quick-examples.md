# Quick Examples

```python
from pyld import jsonld
import json

doc = {
    "http://schema.org/name": "Manu Sporny",
    "http://schema.org/url": {"@id": "http://manu.sporny.org/"},
    "http://schema.org/image": {"@id": "http://manu.sporny.org/images/manu.png"},
}

context = {
    "name": "http://schema.org/name",
    "homepage": {"@id": "http://schema.org/url", "@type": "@id"},
    "image": {"@id": "http://schema.org/image", "@type": "@id"},
}

compacted = jsonld.compact(doc, context)
print(json.dumps(compacted, indent=2))
```

The compacted output uses terms from the supplied context:

```json
{
  "@context": {
    "name": "http://schema.org/name",
    "homepage": {
      "@id": "http://schema.org/url",
      "@type": "@id"
    },
    "image": {
      "@id": "http://schema.org/image",
      "@type": "@id"
    }
  },
  "image": "http://manu.sporny.org/images/manu.png",
  "homepage": "http://manu.sporny.org/",
  "name": "Manu Sporny"
}
```

Expand a compacted document:

```python
expanded = jsonld.expand(compacted)
print(json.dumps(expanded, indent=2))
```

Flatten a document:

```python
flattened = jsonld.flatten(doc)
```

Frame a document:

```python
framed = jsonld.frame(doc, frame)
```

Normalize a document using RDF Dataset Canonicalization:

```python
normalized = jsonld.normalize(
    doc,
    {"algorithm": "URDNA2015", "format": "application/n-quads"},
)
```

The normalized value is a canonical N-Quads string that can be used for hashing,
comparison, or signing workflows.
