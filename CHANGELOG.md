# pyld ChangeLog

### Fixed
- **BREAKING**: Default http (80) and https (443) ports removed from URLs. This
  matches test suite behavior and other processing libs such as [jsonld.js][].
- **BREAKING**: Fix path normalization to pass test suite RFC 3984 tests. This
  could change output for various relative URL edge cases.
- Allow empty lists to be compacted to any @list container term. (Port from
  [jsonld.js][])

### Changed
- **BREAKING**: Remove older document loader code. SSL/SNI support wasn't
  working well with newer Pythons.
- **BREAKING**: Switch to [requests][] for document loading. Some behavior
  could slightly change. Better supported in Python 2 and Python 3.

### Added
- Support for test suite using http or https.
- Easier to create a custom Requests document loader with the
  `requests\_document\_loader` call. Adds a `secure` flag to always use HTTPS.
  Can pass in keywords that [requests][] understands. `verify` to disable SSL
  verification or use custom cert bundles. `cert` to use client certs.
  `timeout` to fail on timeouts (important for production use!). See
  [requests][] docs for more info.

## Before 0.7.4

- See git history for changes.

[jsonld.js]: https://github.com/digitalbazaar/jsonld.js
[requests]: http://docs.python-requests.org/
