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

This library aims to pass the `test suite`_ and conform with the following:

- `JSON-LD 1.0`_,
  W3C Recommendation,
  2014-01-16, and any `errata`_
- `JSON-LD 1.0 Processing Algorithms and API`_,
  W3C Recommendation,
  2014-01-16, and any `errata`_
- `JSON-LD 1.1`_,
  Draft Community Group Report,
  2018-02-15 or `newer <JSON-LD latest_>`_
- `JSON-LD 1.1 Processing Algorithms and API`_,
  Draft Community Group Report,
  2018-02-15 or `newer <JSON-LD Processing Algorithms and API latest_>`_

Requirements
------------

- Python_ (2.7 or later)
- Requests_ (optional)
- aiohttp_ (optional, Python 3.5 or later)

Installation
------------

PyLD can be installed with pip_:

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
    # see: http://json-ld.org/spec/latest/json-ld/#compacted-document-form
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
    # see: http://json-ld.org/spec/latest/json-ld/#expanded-document-form
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
    # see: http://json-ld.org/spec/latest/json-ld/#flattened-document-form
    flattened = jsonld.flatten(doc)
    # all deep-level trees flattened to the top-level

    # frame a document
    # see: http://json-ld.org/spec/latest/json-ld-framing/#introduction
    framed = jsonld.frame(doc, frame)
    # document transformed into a particular tree structure per the given frame

    # normalize a document using the RDF Dataset Normalization Algorithm
    # (URDNA2015), see: http://json-ld.github.io/normalization/spec/
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

http://github.com/digitalbazaar/pyld

Tests
-----

This library includes a sample testing utility which may be used to verify
that changes to the processor maintain the correct output.

To run the sample tests you will need to get the test suite files by cloning
the ``json-ld.org`` and ``normalization`` repositories hosted on GitHub:

- https://github.com/json-ld/json-ld.org
- https://github.com/json-ld/normalization

Then run the test application using the directories containing the tests:

.. code-block:: bash

    python tests/runtests.py -d {PATH_TO_JSON_LD_ORG/test-suite}
    python tests/runtests.py -d {PATH_TO_NORMALIZATION/tests}

The test runner supports different document loaders by setting
``-l requests`` or ``-l aiohttp``. The default document loader is set
to Requests_.

.. _Digital Bazaar: http://digitalbazaar.com/
.. _JSON-LD: http://json-ld.org/
.. _JSON-LD 1.0: http://www.w3.org/TR/2014/REC-json-ld-20140116/
.. _JSON-LD 1.0 Processing Algorithms and API: http://www.w3.org/TR/2014/REC-json-ld-api-20140116/
.. _JSON-LD 1.1: https://json-ld.org/spec/ED/json-ld/20180215/
.. _JSON-LD 1.1 Processing Algorithms and API: https://json-ld.org/spec/ED/json-ld-api/20180215/
.. _JSON-LD latest: https://json-ld.org/spec/latest/json-ld/
.. _JSON-LD Processing Algorithms and API latest: https://json-ld.org/spec/latest/json-ld-api/
.. _Microdata: http://www.w3.org/TR/microdata/
.. _Microformats: http://microformats.org/
.. _Python: http://www.python.org/
.. _Requests: http://docs.python-requests.org/
.. _aiohttp: https://aiohttp.readthedocs.io/
.. _RDFa: http://www.w3.org/TR/rdfa-core/
.. _RFC7159: http://tools.ietf.org/html/rfc7159
.. _errata: http://www.w3.org/2014/json-ld-errata
.. _pip: http://www.pip-installer.org/
.. _test suite: https://github.com/json-ld/json-ld.org/tree/master/test-suite
