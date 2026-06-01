# FrozenDocumentLoader

`FrozenDocumentLoader` serves only URLs in an allowlist and refuses all other
document loads. It is intended for air-gapped runs, reproducible builds, and
deployments that must avoid remote context fetching.

With no arguments, the loader serves the curated `BUNDLED_CONTEXTS` mapping:

```python
from pyld import FrozenDocumentLoader, jsonld

jsonld.set_document_loader(FrozenDocumentLoader())
```

Extend the bundled mapping with additional vetted contexts:

```python
from pathlib import Path

from pyld import BUNDLED_CONTEXTS, FrozenDocumentLoader, jsonld

loader = FrozenDocumentLoader(
    documents=dict(
        BUNDLED_CONTEXTS,
        **{"https://example.com/context": Path("contexts/example.jsonld")},
    )
)

jsonld.expand(doc, options={"documentLoader": loader})
```

The `documents` mapping may contain parsed JSON-LD dictionaries or
`pathlib.Path` instances pointing to JSON files. Path entries are read lazily
and cached after the first request.

Any URL outside the allowlist raises `JsonLdError` with code
`loading document failed`.
