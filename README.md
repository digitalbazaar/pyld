# PyLD: A Python JSON-LD Processor

[Documentation](https://digitalbazaar.github.io/pyld/) |
[Installation](#installation) | [Usage](#usage) | [Advanced
Topics](#advanced-topics) | [Contributing](./CONTRIBUTING.md) |
[Changelog](./CHANGELOG.md)

## Introduction

This library is an implementation of the JSON-LD specification in
[Python](https://www.python.org/).

JSON, as specified in [RFC7159](http://tools.ietf.org/html/rfc7159), is a simple
language for representing objects on the Web. Linked Data is a way of describing
content across different documents or Web sites. Web resources are described
using IRIs, and typically are dereferencable entities that may be used to find
more information, creating a "Web of Knowledge". [JSON-LD](https://json-ld.org/)
is intended to be a simple publishing method for expressing not only Linked Data
in JSON, but for adding semantics to existing JSON.

JSON-LD is designed as a light-weight syntax that can be used to express Linked
Data. It is primarily intended to be a way to express Linked Data in JavaScript
and other Web-based programming environments. It is also useful when building
interoperable Web Services and when storing Linked Data in JSON-based document
storage engines. It is practical and designed to be as simple as possible,
utilizing the large number of JSON parsers and existing code that is in use
today. It is designed to be able to express key-value pairs, RDF data,
[RDFa](http://www.w3.org/TR/rdfa-core/) data,
[Microformats](http://microformats.org/) data, and
[Microdata](http://www.w3.org/TR/microdata/). That is, it supports every major
Web-based structured data model in use today.

The syntax does not require many applications to change their JSON, but easily
add meaning by adding context in a way that is either in-band or out-of-band.
The syntax is designed to not disturb already deployed systems running on JSON,
but provide a smooth migration path from JSON to JSON with added semantics.
Finally, the format is intended to be fast to parse, fast to generate,
stream-based and document-based processing compatible, and require a very small
memory footprint in order to operate.

## Requirements

* Python (3.10 or later)
* [Requests](http://docs.python-requests.org/) (optional)
* [aiohttp](https://aiohttp.readthedocs.io/) (optional)

## Installation

PyLD can be installed with a [pip](http://www.pip-installer.org/)
[package](https://pypi.org/project/PyLD/):

```bash
pip install PyLD
```

Defining a dependency on pyld will not pull in
[Requests](http://docs.python-requests.org/) or
[aiohttp](https://aiohttp.readthedocs.io/). If you need one of these for a
[Document Loader](#document-loader) then either depend on the desired external library directly
or define the requirement as `PyLD[requests]` or `PyLD[aiohttp]`.

## Usage

Here are some quick examples to get started:

```python
from pyld import jsonld
import json

doc = {
    "http://schema.org/name": "Manu Sporny",
    "http://schema.org/url": {"@id": "http://manu.sporny.org/"},
    "http://schema.org/image": {"@id": "http://manu.sporny.org/images/manu.png"}
}

context = {
    "name": "http://schema.org/name",
    "homepage": {"@id": "http://schema.org/url", "@type": "@id"},
    "image": {"@id": "http://schema.org/image", "@type": "@id"}
}

# compact a document according to a particular context
# see: https://json-ld.org/spec/latest/json-ld/#compacted-document-form
compacted = jsonld.compact(doc, context)

print(json.dumps(compacted, indent=2))
# Output:
# {
#   "@context": {...},
#   "image": "http://manu.sporny.org/images/manu.png",
#   "homepage": "http://manu.sporny.org/",
#   "name": "Manu Sporny"
# }

# compact using URLs
jsonld.compact('http://example.org/doc', 'http://example.org/context')

# expand a document, removing its context
# see: https://json-ld.org/spec/latest/json-ld/#expanded-document-form
expanded = jsonld.expand(compacted)

print(json.dumps(expanded, indent=2))
# Output:
# [{
#   "http://schema.org/image": [{"@id": "http://manu.sporny.org/images/manu.png"}],
#   "http://schema.org/name": [{"@value": "Manu Sporny"}],
#   "http://schema.org/url": [{"@id": "http://manu.sporny.org/"}]
# }]

# expand using URLs
jsonld.expand('http://example.org/doc')

# flatten a document
# see: https://json-ld.org/spec/latest/json-ld/#flattened-document-form
flattened = jsonld.flatten(doc)
# all deep-level trees flattened to the top-level

# frame a document
# see: https://json-ld.org/spec/latest/json-ld-framing/#introduction
framed = jsonld.frame(doc, frame)
# document transformed into a particular tree structure per the given frame

# normalize a document using the RDF Dataset Normalization Algorithm
# (URDNA2015), see: https://www.w3.org/TR/rdf-canon/
normalized = jsonld.normalize(
    doc, {'algorithm': 'URDNA2015', 'format': 'application/n-quads'})
# normalized is a string that is a canonical representation of the document
# that can be used for hashing, comparison, etc.
```

## Features & conformance

This library aims to conform with the following W3C Recommendations:

| Standard | Status | 
| :--- | :--- |
| [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/) | W3C Recommendation | 
| [JSON-LD 1.1 Processing Algorithms and API](https://www.w3.org/TR/json-ld11-api/) | W3C Recommendation | 
| [JSON-LD 1.1 Framing](https://www.w3.org/TR/json-ld11-framing/) | W3C Recommendation | 
| [RDF Dataset Canonicalization](https://www.w3.org/TR/rdf-canon/) | W3C Recommendation | 


The [`test
runner`](https://github.com/digitalbazaar/pyld/blob/master/tests/runtests.py) is
often updated to note or skip newer tests that are not yet supported.

## Advanced Topics

### Document Loader

The default document loader for PyLD uses
[Requests](http://docs.python-requests.org/). In a production environment you
may want to setup a custom loader that, at a minimum, sets a timeout value. You
can also force requests to use https, set client certs, disable verification, or
set other Requests parameters.

```python
jsonld.set_document_loader(jsonld.requests_document_loader(timeout=...))
```

The factory remains the compatibility API, and the concrete class is also
available when class-based construction is preferred:

```python
from pyld import RequestsDocumentLoader

jsonld.set_document_loader(RequestsDocumentLoader(timeout=...))
```

An asynchronous document loader using aiohttp is also available. Please note
that this document loader limits asynchronicity to fetching documents only. The
processing loops remain synchronous.

```python
jsonld.set_document_loader(jsonld.aiohttp_document_loader(timeout=...))
```

The concrete aiohttp loader class is available from `pyld` as well:

```python
from pyld import AioHttpDocumentLoader

jsonld.set_document_loader(AioHttpDocumentLoader(timeout=...))
```

When no document loader is specified, the default loader is set to
[Requests](http://docs.python-requests.org/). If Requests is not available, the
loader is set to aiohttp. The fallback document loader is a dummy document
loader that raises an exception on every invocation.

### Frozen Document Loader

For air-gapped runs, reproducible builds, and security-hardened deployments that
must not perform any remote context fetches at all, PyLD ships
`FrozenDocumentLoader`: a class-based loader that serves only the URLs in its
`documents` allowlist and refuses everything else with
`JsonLdError(code='loading document failed')`.

Instantiating with no arguments serves the curated `BUNDLED_CONTEXTS` set
(ActivityStreams, DID v1, Verifiable Credentials v1 and v2, Linked Data Security
v1/v2, Ed25519-2020, and JWS-2020). To extend the bundle with additional
pre-vetted contexts, pass a merged mapping:

```python
from pyld import jsonld, FrozenDocumentLoader, BUNDLED_CONTEXTS

loader = FrozenDocumentLoader(documents=dict(
    BUNDLED_CONTEXTS,
    **{'https://example.com/my-ctx': Path('contexts/my-ctx.jsonld')},
))
jsonld.expand(doc, options={'documentLoader': loader})
```

This honors the W3C *JSON-LD Best Practices* recommendation that clients SHOULD
attempt to use a locally cached version of contexts (see
[§ Cache JSON-LD Contexts](https://w3c.github.io/json-ld-bp/#cache-json-ld-contexts)).
Refresh the bundled copies with `make download-bundled-contexts`.

### Customizing the ContextLoader

You can customize the way contexts are loaded and cached by passing an instance
of `ContextResolver`. The following example implements a loader with a prefilled
custom document cache and uses a custom LRU cache for resolved contexts:

```python
from pyld.jsonld import compact, expand, set_document_loader, ContextResolver
import json
from cachetools import LRUCache

# Load the Linked Art context from file-system
fh = open('linked-art.json')
js = json.load(fh)
fh.close()

# Add to document cache
docCache = {
    "https://linked.art/ns/v1/linked-art.json": {
        "contextUrl": None,
        "documentUrl": "https://linked.art/ns/v1/linked-art.json",
        "document": js
    }
}

# Custom loader that uses the document cache
def load_document_and_cache(url, options={}):
    if url in docCache:
        return docCache[url]
    doc = {"contextUrl": None, "documentUrl": url, "document": ""}
    resp = requests.get(url)
    doc["document"] = resp.json()
    docCache[url] = doc
    return doc

# Set the custom loader as global document loader
set_document_loader(load_document_and_cache)
# Create custom context resolver with custom LRU cache and custom loader
resolved_context_cache = LRUCache(maxsize=1000)
resolver = ContextResolver(resolved_context_cache, load_document_and_cache)

# Expand JSON-LD document using custom context resolver
input = {"@context":"https://linked.art/ns/v1/linked-art.json", "id": "tag:foo", "type": "Person"}
output = expand(input, options={'contextResolver': resolver})
```

It is also possible to change the maximum number of times that the loader
recursively fetches contexts, by passing the `max_context_urls` parameter:

```python
resolver = ContextResolver(resolved_context_cache, load_document_and_cache, max_context_urls=20)
# Or you can do...
# resolver = ContextResolver(resolved_context_cache, load_document_and_cache)
# resolver.max_context_urls = 20
output = expand(input, options={'contextResolver': resolver})
```

### Handling ignored properties during JSON-LD expansion

If a property in a JSON-LD document does not map to an absolute IRI then it is
ignored. You can customize this behaviour by passing a customizable handler to
`on_property_dropped` parameter of `jsonld.expand()`.

For example, you can introduce a strict mode by raising a ValueError on every
dropped property:

```python
def raise_this(value):
    raise ValueError(value)

jsonld.expand(doc, None, on_property_dropped=raise_this)
```

## Contributing

Want to contribute to PyLD? Great! Please consult [`CONTRIBUTING.md`](./CONTRIBUTING.md) for some guidelines.

### Building the source

The source code for the Python implementation of the JSON-LD API is available
at:

[https://github.com/digitalbazaar/pyld](https://github.com/digitalbazaar/pyld)

You can install the source using `make`:

```
pip install -r requirements.txt requirements-test.txt
make install
```

### Testing

This library includes a sample testing utility which may be used to verify that
changes to the processor maintain the correct output.

To run the sample tests you will need to get the test suite files, which by
default, are stored in the `specifications/` folder. The test suites can be
obtained by either using git submodules or by cloning them manually.

#### Using git submodules

The test suites are included as git submodules to ensure versions are in sync.
When cloning the repository, use the `--recurse-submodules` flag to
automatically clone the submodules. If you have cloned the repository without
the submodules, you can initialize them with the following commands:

```bash
git submodule init
git submodule update
```

#### Cloning manually

You can also avoid using git submodules by manually cloning the `json-ld-api`,
`json-ld-framing`, and `normalization` repositories hosted on GitHub using the
following commands:

```bash
git clone https://github.com/w3c/json-ld-api ./specifications/json-ld-api
git clone https://github.com/w3c/json-ld-framing ./specifications/json-ld-framing
git clone https://github.com/json-ld/normalization ./specifications/normalization
```

Note that you can clone these repositories into any location you wish; however,
if you do not clone them into the default `specifications/` folder, you will
need to provide the paths to the test runner as arguments when running the
tests, as explained below.

#### Running the sample test suites and unit tests using pytest

If the suites repositories are available in the `specifications/` folder of the
PyLD source directory, then all unittests, including the sample test suites, can
be run with `pytest`:

```bash
pytest 
```

If you wish to store the test suites in a different location than the default
`specifications/` folder, or you want to test individual manifest `.jsonld`
files or directories containing a `manifest.jsonld`, then you can supply these
files or directories as arguments:

```bash
# use: pytest --tests=TEST_PATH [--tests=TEST_PATH...]
pytest --tests=./specifications/json-ld-api/tests
```

The test runner supports different document loaders by setting `--loader
requests` or `--loader aiohttp`. The default document loader is set to
[Requests](http://docs.python-requests.org/).

```bash
pytest --loader=requests --tests=./specifications/json-ld-api/tests
```

An EARL report can be generated using the `--earl` option.

```bash
pytest --earl=./earl-report.json
```

#### Running the sample test suites using the original test runner

You can also run the JSON-LD test suites using the original test runner script
provided:

```bash
python tests/runtests.py
```

If you wish to store the test suites in a different location than the default
`specifications/` folder, or you want to test individual manifest `.jsonld`
files or directories containing a `manifest.jsonld`, then you can supply these
files or directories as arguments:

```bash
python tests/runtests.py TEST_PATH [TEST_PATH...]
```

The test runner supports different document loaders by setting `-l requests` or
`-l aiohttp`. The default document loader is set to
[Requests](http://docs.python-requests.org/).

```bash
python tests/runtests.py -l requests ./specifications/json-ld-api/tests
```

An EARL report can be generated using the `-e` or `--earl` option.

```bash
python tests/runtests.py -e ./earl-report.json
```

## License

BSD-3-Clause license 
See [`LICENSE`](./LICENSE) file for details.

## Maintainers

The PyLD library is maintained by [Miel Vander
Sande](https://github.com/mielvds), [Anatoly
Scherbakov](https://github.com/anatoly-scherbakov) and [Digital
Bazaar](https://github.com/digitalbazaar) (Original authors of `PyLD`).