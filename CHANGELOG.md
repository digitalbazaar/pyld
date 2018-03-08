# pyld ChangeLog

## 1.0.2 - 2018-03-08

### Fixed
- Missing error parameter.

## 1.0.1 - 2018-03-06

### Fixed
- Include document loaders in distribution.

## 1.0.0 - 2018-03-06

### Notes
- **1.0.0**!
- [Semantic Versioning](https://semver.org/) is now past the "initial
  development" 0.x.y stage (after 6+ years!).
- [Conformance](README.rst#conformance):
  - JSON-LD 1.0 + JSON-LD 1.0 errata
  - JSON-LD 1.1 drafts
- Thanks to the JSON-LD and related communities and the many many people over
  the years who contributed ideas, code, bug reports, and support!

### Fixed
- Don't always use arrays for `@graph`. Fixes 1.0 compatibility issue.
- Process @type term contexts before key iteration.

### Changed
- **BREAKING**: A dependency of pyld will not pull in [Requests][] anymore.
  One needs to define a dependency to `pyld[requests]` or create an
  explicit dependency on `requests` seperately. Use `pyld[aiohttp]` for
  [aiohttp][].
- The default document loader is set to `request_document_loader`. If
  [Requests][] is not available, `aiohttp_document_loader` is used. When
  [aiohttp][] is not availabke, a `dummy_document_loader` is used.
- Use the W3C standard MIME type for N-Quads of "application/n-quads". Accept
  "application/nquads" for compatibility.

### Added
- Support for asynchronous document loader library [aiohttp][].
- Added `dummy_document_loader` which allows libraries to depend on
  pyld without depending on [Requests][] or [aiohttp][].
- The test runner contains an additional parameter `-l` to specify the
  default document loader.
- Expansion and Compaction using scoped contexts on property and `@type` terms.
- Expansion and Compaction of nested properties.
- Index graph containers using `@id` and `@index`, with `@set` variations.
- Index node objects using `@id` and `@type`, with `@set` variations.
- Framing default and named graphs in addition to merged graph.
- Value patterns when framing, allowing a subset of values to appear in the
  output.

## 0.8.2 - 2017-10-24

### Fixed
- Use default document loader for older exposed `load_document` API.

## 0.8.1 - 2017-10-24

### Fixed
- Use `__about__.py` to hold versioning and other meta data. Load file in
  `setup.py` and `jsonld.py`. Fixes testing and installation issues.

## 0.8.0 - 2017-10-20

### Fixed
- **BREAKING**: Default http (80) and https (443) ports removed from URLs. This
  matches test suite behavior and other processing libs such as [jsonld.js][].
- **BREAKING**: Fix path normalization to pass test suite RFC 3984 tests. This
  could change output for various relative URL edge cases.
- Allow empty lists to be compacted to any `@list` container term. (Port from
  [jsonld.js][])

### Changed
- **BREAKING**: Remove older document loader code. SSL/SNI support wasn't
  working well with newer Pythons.
- **BREAKING**: Switch to [Requests][] for document loading. Some behavior
  could slightly change. Better supported in Python 2 and Python 3.

### Added
- Support for test suite using http or https.
- Easier to create a custom Requests document loader with the
  `requests_document_loader` call. Adds a `secure` flag to always use HTTPS.
  Can pass in keywords that [Requests][] understands. `verify` to disable SSL
  verification or use custom cert bundles. `cert` to use client certs.
  `timeout` to fail on timeouts (important for production use!). See
  [Requests][] docs for more info.

## Before 0.8.0

- See git history for changes.

[jsonld.js]: https://github.com/digitalbazaar/jsonld.js
[Requests]: http://docs.python-requests.org/
[aiohttp]: https://docs.aiohttp.org/
