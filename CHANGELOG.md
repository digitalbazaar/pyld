# pyld ChangeLog

## 2.0.4 - 2024-02-16

### Fixed
- Use explicit `None` or `False` for context checks. Fixes an issue while
  framing with an empty context.

## 2.0.3 - 2020-08-06

### Fixed
- Fix deprecation warnings due to invalid escape sequences.

## 2.0.2 - 2020-04-20

### Fixed
- Fix inverse context cache indexing to use the uuid field.

## 2.0.1 - 2020-04-15

### Changed
- Improve EARL output.

## 2.0.0 - 2020-04-15

### Notes
- This release adds JSON-LD 1.1 support. Significant thanks goes to Gregg
  Kellogg!
- **BREAKING**: It is highly recommended to do proper testing when upgrading
  from the previous version. The framing API in particular now follows the 1.1
  spec and some of the defaults changed.

### Changed
- **BREAKING**: Versions of Python before 3.6 are no longer supported.
- Update conformance docs.
- Add all keywords and update options.
- Default `processingMode` to `json-ld-1.1`.
- Implement logic for marking tests as pending, so that it will fail if a
  pending test passes.
- Consolidate `documentLoader` option and defaults into a `load_document` method
  to also handle JSON (eventually HTML) parsing.
- Add support for `rel=alternate` for non-JSON-LD docs.
- Use `lxml.html` to load HTML and parse in `load_html`.
  - For HTML, the API base option can be updated from base element.
- Context processing:
  - Support `@propagate` in context processing and propagate option.
  - Support for `@import`. (Some issues confusing recursion errors for invalid
    contexts).
  - Make `override_protected` and `propagate` optional arguments to
    `_create_term_definition` and `_process_context` instead of using option
    argument.
  - Improve management of previous contexts.
  - Imported contexts must resolve to an object.
  - Do remote context processing from within `_process_contexts`, as logic is
    too complicated for pre-loading. Removes `_find_context_urls` and
    `_retrieve_context_urls`.
  - Added a `ContextResolver` which can use a shared LRU cache for storing
    externally retrieved contexts, and the result of processing them relative
    to a particular active context.
  - Return a `frozendict` from context processing and reduce deepcopies.
  - Store inverse context in an LRU cache rather than trying to modify a frozen context.
  - Don't set `@base` in initial context and don't resolve a relative IRI
    when setting `@base` in a context, so that the document location can
    be kept separate from the context itself.
  - Use static initial contexts composed of just `mappings` and `processingMode`
    to enhance preprocessed context cachability.
- Create Term Definition:
  - Allow `@type` as a term under certain circumstances.
  - Reject and warn on keyword-like terms.
  - Support protected term definitions.
  - Look for keyword patterns and warn/return.
  - Look for terms that are compact IRIs that don't expand to the same thing.
  - Basic support for `@json` and `@none` as values of `@type`.
  - If `@container` includes `@type`, `@type` must be `@id` or `@vocab`.
  - Support `@index` and `@direction`.
  - Corner-case checking for `@prefix`.
  - Validate scoped contexts even if not used.
  - Support relative vocabulary IRIs.
  - Fix check that term has the form of an IRI.
  - Delay adding mapping to end of `_create_term_definition`.
  - If a scoped context is null, wrap it in an array so it doesn't seem to be
    undefined.
- IRI Expansion:
  - Find keyword patterns.
  - Don't treat terms starting with a colon as IRIs.
  - Only return a resulting IRI if it is absolute.
  - Fix `_is_absolute_iri` to use a reasonable regular expression and some
    other `_expand_iri issues`.
  - Fix to detecting relative IRIs.
  - Fix special case where relative path should not have a leading '/'
  - Pass in document location (through 'base' option) and use when resolving
    document-relative IRIs.
- IRI Compaction:
  - Pass in document location (through 'base' option) and use when compacting
    document-relative IRIs.
- Compaction:
  - Compact `@direction`.
  - Compact `@type`: `@none`.
  - Compact `@included`.
  - Honor `@container`: `@set` on `@type`.
  - Lists of Lists.
  - Improve handling of scoped contexts and propagate.
  - Improve map compaction, including indexed properties.
  - Catch Absolute IRI confused with prefix.
- Expansion:
  - Updates to expansion algorithm.
  - `_expand_value` adds `@direction` from term definition.
  - JSON Literals.
  - Support `@direction` when expanding.
  - Support lists of lists.
  - Support property indexes.
  - Improve graph container expansion.
  - Order types when applying scoped contexts.
  - Use `type_scoped_ctx` when expanding values of `@type`.
  - Use propagate and `override_protected` properly when creating expansion
    contexts.
- Flattening:
  - Rewrite `_create_node_map` based on 1.1 algorithm.
  - Flatten `@included`.
  - Flatten lists of lists.
  - Update `merge_node_maps` for `@type`.
- Framing:
  - Change default for `requireAll` from True to False.
  - Change default for 'embed' from '@last' to '@once'.
  - Add defaults for `omitGraph` and `pruneBlankNodeIdentifiers`
    based on processing mode.
  - Change `_remove_preserve` to `_cleanup_preserve` which happens before
    compaction.
  - Add `_cleanup_null` which happens after compaction.
  - Update frame matching to 1.1 spec.
  - Support `@included`.
- ToRdf:
  - Support for I18N direction.
  - Support for Lists of Lists.
  - Partial support for JSON canonicalization of JSON literals.
    - Includes local copy of JCS library, but doesn't load.
  - Lists of Lists.
  - Text Direction 'i18n-datatype'.
- Testing
  - Switched to argparse.
  - **BREAKING**: Removed `-d` and `-m` test runner options in favor of just
    listing as arguments.
  - If no test manifests or directories are specified, default to sibling
    directories for json-ld-api, json-ld-framing, and normalization.

## 1.0.5 - 2019-05-09

### Fixed
- Use `return` instead of `raise StopIteration` to terminate generator.

## 1.0.4 - 2018-12-11

### Fixed
- Accept N-Quads upper case language tag.

## 1.0.3 - 2018-03-09

### Fixed
- Reorder code to avoid undefined symbols.

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
