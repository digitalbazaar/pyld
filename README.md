PyLD
====

Introduction
------------

A Python implementation of a [JSON-LD][] processor.

Requirements
------------

 * [Python][] (2.5 or later)

Usage
-----

This library includes a sample testing utility which may be used to verify
that changes to the processor maintain the correct output.

To run the sample tests you will need to get the test suite files from the
[json-ld.org repository][json-ld.org] hosted on GitHub.

https://github.com/json-ld/json-ld.org

Then run the runtests.py application and point it at the directory
containing the tests.

    python tests/runtests.py -d {PATH_TO_JSON_LD_ORG/test-suite/tests}

[Python]: http://www.python.org/
[JSON-LD]: http://json-ld.org/
[json-ld.org]: https://github.com/json-ld/json-ld.org
