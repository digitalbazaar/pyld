PyLD
====

.. image:: https://travis-ci.org/bollwyvl/pyld.png?branch=travis
   :target: https://travis-ci.org/bollwyvl/pyld

Introduction
------------

This library is an implementation of the JSON-LD_ specification in Python_.

JSON, as specified in RFC4627_, is a simple language for representing
objects on the Web. Linked Data is a way of describing content across
different documents or Web sites. Web resources are described using IRIs,
and typically are dereferencable entities that may be used to find more
information, creating a "Web of Knowledge". JSON-LD is intended to be a
simple publishing method for expressing not only Linked Data in JSON, but
for adding semantics to existing JSON.

JSON-LD is designed as a light-weight syntax that can be used to express
Linked Data. It is primarily intended to be a way to express Linked Data in
Javascript and other Web-based programming environments. It is also useful
when building interoperable Web Services and when storing Linked Data in
JSON-based document storage engines. It is practical and designed to be as
simple as possible, utilizing the large number of JSON parsers and existing
code that is in use today. It is designed to be able to express key-value
pairs, RDF data, RDFa_ data, Microformats_ data, and Microdata_. That is, it
supports every major Web-based structured data model in use today.

The syntax does not require many applications to change their JSON, but
easily add meaning by adding context in a way that is either in-band or
out-of-band. The syntax is designed to not disturb already deployed systems
running on JSON, but provide a smooth migration path from JSON to JSON with
added semantics. Finally, the format is intended to be fast to parse, fast
to generate, stream-based and document-based processing compatible, and
require a very small memory footprint in order to operate.

Commercial Support
------------------

Commercial support for this library is available upon request from
`Digital Bazaar`_: support@digitalbazaar.com.

Requirements
------------

- Python_ (2.5 or later)

Source
------

The source code for the Python implementation of the JSON-LD API is
available at:

http://github.com/digitalbazaar/pyld

This library includes a sample testing utility which may be used to verify
that changes to the processor maintain the correct output.

To run the sample tests you will need to get the test suite files by cloning
the ``json-ld.org`` hosted on GitHub:

https://github.com/json-ld/json-ld.org

Then run the jsonld-tests.php application and point it at the directory
containing the tests.

::

    python tests/runtests.py -d {PATH_TO_JSON_LD_ORG/test-suite/tests}

.. _JSON-LD: http://json-ld.org/
.. _Python: http://www.python.org/
.. _Digital Bazaar: http://digitalbazaar.com/
.. _RDFa: http://www.w3.org/TR/rdfa-core/
.. _Microformats: http://microformats.org/
.. _Microdata: http://www.w3.org/TR/microdata/
.. _RFC4627: http://www.ietf.org/rfc/rfc4627.txt
