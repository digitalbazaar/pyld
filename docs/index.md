# PyLD

PyLD is a Python implementation of the [JSON-LD][] processor API.

JSON-LD is a lightweight syntax for expressing Linked Data in JSON. It lets
applications add meaning to existing JSON documents with in-band or out-of-band
contexts, while keeping the document shape practical for web APIs, JavaScript,
and JSON document stores.

## Conformance

PyLD aims to conform with:

- [JSON-LD 1.1][json-ld-11]
- [JSON-LD 1.1 Processing Algorithms and API][json-ld-11-api]
- [JSON-LD 1.1 Framing][json-ld-11-framing]
- The JSON-LD Working Group [test suite][wg-test-suite]

The test runner is updated over time to note or skip newer tests that are not
yet supported.

## Requirements

- Python 3.10 or later
- `requests` for the default synchronous document loader, when installed with
  the `requests` extra
- `aiohttp` for the asynchronous document loader, when installed with the
  `aiohttp` extra

## Project Links

- [Source code](https://github.com/digitalbazaar/pyld)
- [Package on PyPI](https://pypi.org/project/PyLD/)
- [JSON-LD](https://json-ld.org/)

[JSON-LD]: https://json-ld.org/
[json-ld-11]: https://www.w3.org/TR/json-ld11/
[json-ld-11-api]: https://www.w3.org/TR/json-ld11-api/
[json-ld-11-framing]: https://www.w3.org/TR/json-ld11-framing/
[wg-test-suite]: https://github.com/w3c/json-ld-api/tree/master/tests
