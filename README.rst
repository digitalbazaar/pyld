PyLD
====

.. image:: https://travis-ci.org/digitalbazaar/pyld.png?branch=master
   :target: https://travis-ci.org/digitalbazaar/pyld
   :alt: Build Status

Introduction
------------

This library is an implementation of the JSON-LD_ specification in Python_.

JSON, as specified in RFC7159_, is a simple language for representing
objects on the Web. Linked Data is a way of describing content across
different documents or Web sites. Web resources are described using
IRIs, and typically are dereferencable entities that may be used to find
more information, creating a "Web of Knowledge". JSON-LD_ is intended
to be a simple publishing method for expressing not only Linked Data in
JSON, but for adding semantics to existing JSON.

JSON-LD is designed as a light-weight syntax that can be used to express
Linked Data. It is primarily intended to be a way to express Linked Data
in JavaScript and other Web-based programming environments. It is also
useful when building interoperable Web Services and when storing Linked
Data in JSON-based document storage engines. It is practical and
designed to be as simple as possible, utilizing the large number of JSON
parsers and existing code that is in use today. It is designed to be
able to express key-value pairs, RDF data, RDFa_ data,
Microformats_ data, and Microdata_. That is, it supports every
major Web-based structured data model in use today.

The syntax does not require many applications to change their JSON, but
easily add meaning by adding context in a way that is either in-band or
out-of-band. The syntax is designed to not disturb already deployed
systems running on JSON, but provide a smooth migration path from JSON
to JSON with added semantics. Finally, the format is intended to be fast
to parse, fast to generate, stream-based and document-based processing
compatible, and require a very small memory footprint in order to operate.

Conformance
-----------

This library aims to conform with the following:

- `JSON-LD 1.1 <JSON-LD WG 1.1_>`_,
  W3C Candidate Recommendation,
  2019-12-12 or `newer <JSON-LD WG latest_>`_
- `JSON-LD 1.1 Processing Algorithms and API <JSON-LD WG 1.1 API_>`_,
  W3C Candidate Recommendation,
  2019-12-12 or `newer <JSON-LD WG API latest_>`_
- `JSON-LD 1.1 Framing <JSON-LD WG 1.1 Framing_>`_,
  W3C Candidate Recommendation,
  2019-12-12 or `newer <JSON-LD WG Framing latest_>`_
- Working Group `test suite <WG test suite_>`_

The `test runner`_ is often updated to note or skip newer tests that are not
yet supported.

Requirements
------------

- Python_ (3.6 or later)
- Requests_ (optional)
- aiohttp_ (optional, Python 3.5 or later)

Installation
------------

PyLD can be installed with a pip_ `package <https://pypi.org/project/PyLD/>`_

.. code-block:: bash

    pip install PyLD

Defining a dependency on pyld will not pull in Requests_ or aiohttp_.  If you
need one of these for a `Document Loader`_ then either depend on the desired
external library directly or define the requirement as ``PyLD[requests]`` or
``PyLD[aiohttp]``.

Quick Examples
--------------

.. code-block:: Python

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

Document Loader
---------------

The default document loader for PyLD uses Requests_. In a production
environment you may want to setup a custom loader that, at a minimum, sets a
timeout value. You can also force requests to use https, set client certs,
disable verification, or set other Requests_ parameters.

.. code-block:: Python

    jsonld.set_document_loader(jsonld.requests_document_loader(timeout=...))

An asynchronous document loader using aiohttp_ is also available. Please note
that this document loader limits asynchronicity to fetching documents only.
The processing loops remain synchronous.

.. code-block:: Python

    jsonld.set_document_loader(jsonld.aiohttp_document_loader(timeout=...))

When no document loader is specified, the default loader is set to Requests_.
If Requests_ is not available, the loader is set to aiohttp_. The fallback
document loader is a dummy document loader that raises an exception on every
invocation.

Commercial Support
------------------

Commercial support for this library is available upon request from
`Digital Bazaar`_: support@digitalbazaar.com.

Source
------

The source code for the Python implementation of the JSON-LD API
is available at:

https://github.com/digitalbazaar/pyld

Tests
-----

This library includes a sample testing utility which may be used to verify
that changes to the processor maintain the correct output.

To run the sample tests you will need to get the test suite files by cloning
the ``json-ld-api``, ``json-ld-framing``, and ``normalization`` repositories
hosted on GitHub:

- https://github.com/w3c/json-ld-api
- https://github.com/w3c/json-ld-framing
- https://github.com/json-ld/normalization

If the suites repositories are available as sibling directories of the PyLD
source directory, then all the tests can be run with the following:

.. code-block:: bash

    python tests/runtests.py

If you want to test individual manifest ``.jsonld`` files or directories
containing a ``manifest.jsonld``, then you can supply these files or
directories as arguments:

.. code-block:: bash

    python tests/runtests.py TEST_PATH [TEST_PATH...]

The test runner supports different document loaders by setting ``-l requests``
or ``-l aiohttp``. The default document loader is set to Requests_.

An EARL report can be generated using the ``-e`` or ``--earl`` option.


.. _Digital Bazaar: https://digitalbazaar.com/

.. _JSON-LD WG 1.1 API: https://www.w3.org/TR/json-ld11-api/
.. _JSON-LD WG 1.1 Framing: https://www.w3.org/TR/json-ld11-framing/
.. _JSON-LD WG 1.1: https://www.w3.org/TR/json-ld11/

.. _JSON-LD WG API latest: https://w3c.github.io/json-ld-api/
.. _JSON-LD WG Framing latest: https://w3c.github.io/json-ld-framing/
.. _JSON-LD WG latest: https://w3c.github.io/json-ld-syntax/

.. _JSON-LD Benchmarks: https://json-ld.org/benchmarks/
.. _JSON-LD WG: https://www.w3.org/2018/json-ld-wg/
.. _JSON-LD: https://json-ld.org/
.. _Microdata: http://www.w3.org/TR/microdata/
.. _Microformats: http://microformats.org/
.. _Python: https://www.python.org/
.. _Requests: http://docs.python-requests.org/
.. _aiohttp: https://aiohttp.readthedocs.io/
.. _RDFa: http://www.w3.org/TR/rdfa-core/
.. _RFC7159: http://tools.ietf.org/html/rfc7159
.. _WG test suite: https://github.com/w3c/json-ld-api/tree/master/tests
.. _errata: http://www.w3.org/2014/json-ld-errata
.. _pip: http://www.pip-installer.org/
.. _test runner: https://github.com/digitalbazaar/pyld/blob/master/tests/runtests.py
.. _test suite: https://github.com/json-ld/json-ld.org/tree/master/test-suite
