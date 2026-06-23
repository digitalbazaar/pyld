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

=== "jsonld.compact()"

    Compacts a JSON-LD document with a context, replacing full IRIs with shorter
    terms where possible. [Read more :octicons-arrow-right-24:](reference/compact.md)

    {{ example('compact.py', 'json', indent=4) }}

=== "jsonld.expand()"

    Expands a compacted JSON-LD document into full IRI-based form and removes the
    context. [Read more :octicons-arrow-right-24:](reference/expand.md)

    {{ example('expand.py', 'json', indent=4) }}

=== "jsonld.flatten()"

    Flattens nested JSON-LD into a top-level node map so each node can be processed
    independently. [Read more :octicons-arrow-right-24:](reference/flatten.md)

    {{ example('flatten.py', 'json', indent=4) }}

=== "jsonld.frame()"

    Frames expanded JSON-LD into a predictable tree shape that matches a supplied
    frame. [Read more :octicons-arrow-right-24:](reference/frame.md)

    {{ example('frame.py', 'json', indent=4) }}

=== "jsonld.to_rdf()"

    Converts a JSON-LD document into RDF statements in a requested serialization
    format. [Read more :octicons-arrow-right-24:](reference/to_rdf.md)

    {{ example('to_rdf.py', indent=4) }}

=== "jsonld.from_rdf()"

    Converts RDF statements into JSON-LD so the data can be processed with the
    JSON-LD API. [Read more :octicons-arrow-right-24:](reference/from_rdf.md)

    {{ example('from_rdf.py', 'json', indent=4) }}

=== "jsonld.normalize()"

    Normalizes JSON-LD into canonical RDF statements for stable comparison,
    hashing, or signing. [Read more :octicons-arrow-right-24:](reference/normalize.md)

    {{ example('normalize.py', indent=4) }}

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
