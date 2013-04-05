# -*- coding: utf-8 -*-
"""
pyld
====
`pyld`_ is a Python `JSON-LD` library.

.. _pyld: http://github.com/digitalbazaar/pyld
.. _JSON-LD: http://json-ld.org/
"""
from distutils.core import setup

long_desc = '''
Introduction
------------

JSON, as specified in RFC4627, is a simple language for representing
objects on the Web. Linked Data is a way of describing content across
different documents or Web sites. Web resources are described using
IRIs, and typically are dereferencable entities that may be used to find
more information, creating a "Web of Knowledge". JSON-LD is intended to
be a simple publishing method for expressing not only Linked Data in
JSON, but for adding semantics to existing JSON.

This library is an implementation of the
`JSON-LD <http://json-ld.org/>`_ specification in
`Python <http://www.python.org/>`_.

JSON-LD is designed as a light-weight syntax that can be used to express
Linked Data. It is primarily intended to be a way to express Linked Data
in Javascript and other Web-based programming environments. It is also
useful when building interoperable Web Services and when storing Linked
Data in JSON-based document storage engines. It is practical and
designed to be as simple as possible, utilizing the large number of JSON
parsers and existing code that is in use today. It is designed to be
able to express key-value pairs, RDF data, RDFa [RDFA-CORE] data,
Microformats [MICROFORMATS] data, and Microdata [MICRODATA]. That is, it
supports every major Web-based structured data model in use today.

The syntax does not require many applications to change their JSON, but
easily add meaning by adding context in a way that is either in-band or
out-of-band. The syntax is designed to not disturb already deployed
systems running on JSON, but provide a smooth migration path from JSON
to JSON with added semantics. Finally, the format is intended to be fast
to parse, fast to generate, stream-based and document-based processing
compatible, and require a very small memory footprint in order to
operate.

Commercial Support
------------------

Commercial support for this library is available upon request from
Digital Bazaar: support@digitalbazaar.com

Requirements
------------

-  `Python <http://www.python.org/>`_ (2.5 or later)

Source
------

The source code for the Python implementation of the JSON-LD API is
available at:

http://github.com/digitalbazaar/pyld

This library includes a sample testing utility which may be used to
verify that changes to the processor maintain the correct output.

To run the sample tests you will need to get the test suite files by
cloning the `json-ld.org
repository <https://github.com/json-ld/json-ld.org>`_ hosted on GitHub.

https://github.com/json-ld/json-ld.org

Then run the jsonld-tests.php application and point it at the directory
containing the tests.

::

    python tests/runtests.py -d {PATH_TO_JSON_LD_ORG/test-suite/tests}
'''

setup(
    name = 'pyld',
    version = '0.0.1',
    description = 'Python implementation of the JSON-LD API',
    long_description=long_desc,
    license = 'BSD 3-Clause license',
    url = 'http://github.com/digitalbazaar/pyld',
    author = 'Digital Bazaar',
    author_email = 'support@digitalbazaar.com',
    platforms = 'OS Independant',
    package_dir = {'': 'lib'},
    packages = ['pyld'],
)
