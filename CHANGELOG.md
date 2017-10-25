# pyld ChangeLog

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
