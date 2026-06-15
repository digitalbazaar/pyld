---
hide: [toc]
---

# :material-graph-outline: PyLD

[![Main CI](https://github.com/digitalbazaar/pyld/actions/workflows/main.yaml/badge.svg)](https://github.com/digitalbazaar/pyld/actions/workflows/main.yaml)
[![PyPI](https://img.shields.io/pypi/v/PyLD.svg)](https://pypi.org/project/PyLD/)
[![Downloads](https://img.shields.io/pypi/dw/PyLD.svg)](https://pypi.org/project/PyLD/)

PyLD is a Python implementation of the [JSON-LD](https://json-ld.org/) processor API.

JSON-LD is a lightweight syntax for expressing Linked Data in JSON. It lets
applications add meaning to existing JSON documents with in-band or out-of-band
contexts, while keeping the document shape practical for web APIs, JavaScript,
and JSON document stores.

## :material-lightning-bolt: Quick Examples

### `jsonld.compact()`

Compacts a JSON-LD document with a context, replacing full IRIs with shorter
terms where possible.

{{ example('compact.py', 'json') }}

### `jsonld.expand()`

Expands a compacted JSON-LD document into full IRI-based form and removes the
context.

{{ example('expand.py', 'json') }}

### `jsonld.flatten()`

Flattens nested JSON-LD into a top-level node map so each node can be processed
independently.

{{ example('flatten.py', 'json') }}

### `jsonld.frame()`

Frames expanded JSON-LD into a predictable tree shape that matches a supplied
frame.

{{ example('frame.py', 'json') }}

### `jsonld.to_rdf()`

Converts a JSON-LD document into RDF statements in a requested serialization
format.

{{ example('to_rdf.py') }}

### `jsonld.from_rdf()`

Converts RDF statements into JSON-LD so the data can be processed with the
JSON-LD API.

{{ example('from_rdf.py', 'json') }}

### `jsonld.normalize()`

Normalizes JSON-LD into canonical RDF statements for stable comparison,
hashing, or signing.

{{ example('normalize.py') }}

## :fontawesome-solid-people-line: Maintainers

<div class="grid cards maintainers" markdown>

-   __Miel Vander Sande__

    ---

    [![Miel Vander Sande](https://github.com/mielvds.png?s=128)](https://github.com/mielvds)

    :fontawesome-brands-github:{ .middle } [`@mielvds`](https://github.com/mielvds)  
    :fontawesome-brands-linkedin:{ .middle } [LinkedIn](https://www.linkedin.com/in/miel-vander-sande-41070236)  
    :material-web:{ .middle } [meemoo.be](https://www.meemoo.be/)

-   __Anatoly Scherbakov__

    ---

    [![Anatoly Scherbakov](https://github.com/anatoly-scherbakov.png?s=128)](https://github.com/anatoly-scherbakov)

    :fontawesome-brands-github:{ .middle } [`@anatoly-scherbakov`](https://github.com/anatoly-scherbakov)  
    :fontawesome-brands-linkedin:{ .middle } [LinkedIn](https://www.linkedin.com/in/anatoly-scherbakov)  
    :material-web:{ .middle } [yeti.sh](https://yeti.sh)

-   __Digital Bazaar__

    ---

    [![Digital Bazaar](https://github.com/digitalbazaar.png?s=128)](https://github.com/digitalbazaar)

    :fontawesome-brands-github:{ .middle } [`@digitalbazaar`](https://github.com/digitalbazaar)  
    :fontawesome-brands-linkedin:{ .middle } [Digital Bazaar, Inc.](https://www.linkedin.com/company/digital-bazaar-inc-)  
    :material-web:{ .middle } [digitalbazaar.com](https://www.digitalbazaar.com/)  
    :heart: Original authors of `PyLD`

</div>
