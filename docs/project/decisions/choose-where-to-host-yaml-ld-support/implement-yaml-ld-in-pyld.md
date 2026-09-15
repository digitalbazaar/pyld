# :material-package-variant: Implement YAML-LD in PyLD

!!! info "Conditional roadmap"

    This is the implementation universe in which [:fontawesome-brands-github: `digitalbazaar/pyld`](https://github.com/digitalbazaar/pyld) owns YAML-LD support. It applies only if the parent decision selects this alternative.

## :material-target: Delivered contract

`PyLD[yaml-ld]` adds YAML-LD document loading to the existing PyLD API; `PyLD[cli,yaml-ld]` adds that capability to the CLI. The implementation supports the YAML-LD JSON profile only: YAML 1.2 Core-schema values that produce JSON values. It does not implement the YAML-LD extended profile: `processingMode='yaml-ld-extended'`, or a profile token exactly `http://www.w3.org/ns/json-ld#extended`, fails with `jsonld.LoadDocumentError`, code `profile-error`. Ignore unknown profile tokens; do not reject an arbitrary `profile` parameter. YAML tags outside the Core schema are discarded when constructing the JSON representation, as required by the JSON profile. A missing `ruamel.yaml` import fails only when a YAML document is actually parsed, with an actionable `yaml-ld` extra message.

Raw YAML `str` and `bytes` are not new public inputs to `expand`, `compact`, `flatten`, `frame`, `to_rdf`, or `normalize`: a string remains a document URL and a mapping/list remains an already-parsed JSON-compatible document. YAML enters those APIs through a document URL and its document loader. `from_rdf` remains raw RDF input only.

Do not add `pyld.yaml_ld.expand()` or sibling transformation functions. A
`pyld.yaml_ld` namespace may expose parsing helpers such as `loads()` and
`loads_all()`, while `pyld.jsonld.*` remains the sole transformation API.

## :material-source-branch: Implementation baseline

Build this work on [:fontawesome-brands-github: `306-complete-pyld-cli`](https://github.com/digitalbazaar/pyld/tree/306-complete-pyld-cli), which adds [`lib/pyld/cli/input.py`](https://github.com/digitalbazaar/pyld/blob/306-complete-pyld-cli/lib/pyld/cli/input.py) and the command test contract. Either rebase after that branch merges, or create this as a stacked PR with `306-complete-pyld-cli` as its base. Do not reimplement the CLI in this change.

## :material-clipboard-check-outline: Architectural decisions

### One media parser at the PyLD loading boundary

Add `lib/pyld/documentloader/media.py`, with a single idempotent entry point used by [`jsonld.load_document`](https://github.com/digitalbazaar/pyld/blob/master/lib/pyld/jsonld.py): `parse_remote_document(remote_doc, options, profile) -> RemoteDocument`.

1. Normalize `contentType` by lowercasing the media type and removing parameters for dispatch, while retaining the parameter map to inspect `profile`. Recognize `application/ld+yaml`, `application/yaml`, `application/x-yaml`, and `*+yaml`; recognize JSON as `application/ld+json`, `application/json`, and `*+json`; retain the existing HTML types.
2. If `remote_doc['document']` is a mapping or list, return it unchanged. This makes the boundary idempotent and keeps custom loaders which already return parsed JSON compatible.
3. Built-in loaders always supply raw bytes. A custom loader may supply text, which the boundary first encodes as UTF-8 and then decodes using the same optional-BOM path; an unencodable string or malformed byte sequence is `invalid-encoding`. Any other value is a `loading document failed` error. Dispatch YAML and JSON to the media parser; dispatch HTML to the PyLD HTML folding algorithm below. The parser replaces `remote_doc['document']` with only ordinary Python `dict`, `list`, `str`, `int`, `float`, `bool`, or `None` values.
4. Call this helper exactly once, immediately after `options['documentLoader'](url, options)` in `load_document`, before the null-document check and before processing API code observes the result. It owns parsing, HTML traversal, base handling, profile selection, and fragment selection. Built-in and custom loader output therefore follows the same path.

Change [`FileDocumentLoader`](https://github.com/digitalbazaar/pyld/blob/master/lib/pyld/documentloader/file.py), [`RequestsDocumentLoader`](https://github.com/digitalbazaar/pyld/blob/master/lib/pyld/documentloader/requests.py), and [`AioHttpDocumentLoader`](https://github.com/digitalbazaar/pyld/blob/master/lib/pyld/documentloader/aiohttp.py) to return raw bytes in `document`, plus `contentType`, `contextUrl`, and final `documentUrl`. In particular, replace Requests’ `response.json()` and aiohttp’s `response.json(content_type=None)` with raw-body reads. `SqliteCacheRequestsDocumentLoader` continues to inherit the Requests behavior. Do not change the documented `RemoteDocument` fields or require third-party loaders to change: their parsed mapping/list output is the idempotent case.

### YAML parsing and errors

Use `ruamel.yaml >=0.19`, configured for YAML 1.2 and the Core schema. Decode once, safely compose/load every document in a stream, and recursively convert it to JSON values: keys must be strings; aliases are copied; undefined aliases and cyclic aliases fail; `.inf` and `.nan` are rejected because they are not JSON numbers. A top-level scalar fails and an empty stream fails. With `extractAllScripts=False`, a YAML stream returns its first document; with `extractAllScripts=True`, it returns an array of all stream documents, including an array of one document. This rule applies equally to direct YAML and YAML script bodies.

Production errors use the current YAML-LD vocabulary: decode errors are `invalid-encoding`; non-string mapping keys are `mapping-key-error`; and the extended profile is `profile-error`. Syntax errors, scalar roots, empty streams, undefined/cyclic aliases, non-JSON floats, and unsupported document shapes are `loading document failed`. JSON is parsed only by the JSON dispatch branch and YAML only by YAML dispatch: do not describe or implement a “valid JSON but invalid YAML” fallback.

### HTTP, files, links, and negotiation

Extend `CONTENT_TYPES` with `.yamlld` → `application/ld+yaml` and `.yaml` → `application/yaml`. The exact default `Accept` header, unless the caller supplied `options['headers']`, is:

```text
application/ld+yaml, application/ld+json;q=0.9, application/yaml;q=0.8, application/x-yaml;q=0.8, application/json;q=0.7, text/html;q=0.5, application/xhtml+xml;q=0.5
```

This intentional YAML-first ordering implements the YAML-LD alternative’s preference; test the literal value in both HTTP loaders. When `requestProfile` is set, prepend the RFC-quoted `application/ld+json;profile="<requestProfile>", `, preserving the remaining order.

Normalize a response `Content-Type` before link decisions. Continue to reject multiple JSON-LD context links. A `rel=alternate` is followed only if its normalized `type` is a supported YAML or JSON media type and the response is neither a supported YAML nor JSON media type; resolve it against the original request URL and recurse through the same loader with the same options. A context link is retained only when the response is neither `application/ld+json` nor `application/ld+yaml`; do not synthesize a context link from a YAML document. Preserve final URLs, redirect behavior, secure-mode enforcement, supplied headers, cache keys, and cache hit/miss behavior.

### HTML folding, owned by PyLD

`parse_remote_document` calls a refactored `load_html` that takes the raw HTML text, `documentUrl`, `profile`, and `options`; no transport loader parses HTML or script bodies.

1. Parse HTML and resolve the first `<base href>` against `options['base']` or `documentUrl`; store the resolved base in `options['base']` and replace the remote document URL as current `load_document` does.
2. If `documentUrl` has a fragment, select exactly the script whose `id` equals that fragment. It must have a supported JSON or YAML media type; otherwise raise `loading document failed`. Ignore `extractAllScripts` in this case and return only that script’s parsed document(s).
3. Otherwise select `<script>` elements in document order whose normalized `type` is supported JSON or YAML. When a JSON `profile` argument is supplied, first select only `application/ld+json` scripts with the same profile parameter; if none match, select all supported scripts. Ignore unknown profile tokens. A YAML script carrying `http://www.w3.org/ns/json-ld#extended`, or an options processing mode of `yaml-ld-extended`, is `profile-error`; other YAML profile tokens are ignored.
4. For each selected script, read its text without manually dedenting it, use its normalized type to invoke the same JSON/YAML parser, and retain each resulting mapping/list. A YAML stream contributes its documents in stream order.
5. With `extractAllScripts=True`, flatten script and YAML-stream documents in source order to one list. Otherwise return the first parsed document. No selected script is `loading document failed`; a parse failure in a selected script is `invalid script element`, wrapping the canonical YAML/JSON cause.

Test indentation, whitespace, JSON/YAML interleaving, profiles, fragment selection, a single and a multi-document YAML stream, and HTML base replacement.

## :material-file-code-outline: Ordered implementation

### 1. Package and expose the capability

- [ ] Add `yaml-ld: ['ruamel.yaml>=0.19']` to `extras_require` in [`setup.py`](https://github.com/digitalbazaar/pyld/blob/306-complete-pyld-cli/setup.py). Add the CLI extra already defined by the baseline so `PyLD[cli,yaml-ld]` installs both groups; do not claim that extras conditionally create console scripts.
- [ ] Add the parser module to the `pyld.documentloader` package and export only any intentionally public media constants/helpers from its package `__init__`; keep parsing functions internal otherwise.
- [ ] Add `ruamel.yaml` to test dependencies and CI installation. Test installation/import without the extra, with `yaml-ld`, and with `cli,yaml-ld`.

### 2. Change loader transport and central parsing

- [ ] Implement the parser, then refactor `load_document`, built-in loaders, and SQLite-cache tests according to the single-boundary contract above.
- [ ] Add unit tests for a custom `DocumentLoader` returning raw YAML text/bytes and a pre-parsed mapping. The former is parsed centrally and the latter stays unchanged.
- [ ] Preserve `FileDocumentLoader` root confinement and Path/file-URL behavior. Preserve Requests/AioHTTP URL validation, sessions, TLS/secure mode, redirects, caller headers, alternate-link recursion, context-link errors, and cached raw response behavior.

### 3. Preserve API contracts

- [ ] Route URL input to `expand`, `compact`, `flatten`, `frame`, `to_rdf`, and URL-input `normalize` through `load_document`; retain dict/list behavior and all existing option defaults, including `processingMode` and omitted tri-state CLI-derived values.
- [ ] Leave `from_rdf` and `inputFormat` behavior unchanged. Add API parity fixtures that compare a YAML URL with an equivalent JSON-LD URL for expand, compact, flatten, frame, `to_rdf`, and URL-based normalize.

### 4. Make stdin format explicit in the CLI

- [ ] Add `--stdin-format {json,yaml}` to the primary input commands `get`, `expand`, `compact`, `flatten`, `frame`, and `to-rdf`. It defaults to `json`, preserving the baseline CLI behavior. Reject it when `INPUT` is not `-`; reject values other than the two enum values through Typer validation. `--stdin-format yaml` calls the YAML parser directly and requires the extra; there is no content sniffing or JSON-to-YAML fallback.
- [ ] Keep primary paths and HTTP(S) URLs as `document_url()` values. They must flow through `load_document` so final URL, base IRI, Content-Type, cache, secure mode, redirects, and custom CLI loader policy survive.
- [ ] Implement `JSONOnlyOperand`: for `-`, it yields `json.load(sys.stdin)`; otherwise it yields the canonical source URL from `document_url()`. Pass that URL, not an eagerly parsed dict, as `CONTEXT`, `FRAME`, `--context`, or `--expand-context` to the processing operation.
- [ ] Add `RestrictDesignatedUrlsToJson(delegate, designated_urls)` as the operation’s document-loader view. It delegates every URL through the configured file/remote/cache/security/header policy. Only when the requested URL is one of those explicit secondary source URLs does it normalize the returned `RemoteDocument` content type and reject YAML, HTML, and unsupported types; it returns the complete, unchanged `RemoteDocument` so `load_document` preserves `documentUrl`, `contextUrl`, and base metadata. Primary documents and nested contexts remain unrestricted. Contexts, frames, and expand contexts deliberately have no YAML format option.
- [ ] Before installing that view, canonicalize a non-stdin primary `INPUT` with `document_url()` and reject the invocation with `typer.BadParameter('INPUT must not name the same URL as a JSON-only operand.')` when it equals a designated secondary URL. Without this check the view cannot distinguish a primary fetch from an explicitly JSON-only secondary fetch of the same URL. Test this error for local paths and HTTP URLs.
- [ ] Retain `ensure_single_stdin()` across all primary and secondary operands. Retain raw RDF boundaries: `from-rdf` accepts only local N-Quads or `-` via `read_nquads`; `to-rdf` emits exactly `print_nquads()` → `sys.stdout.write()`, with no Rich formatting, added newline, escaping, or YAML serialization.
- [ ] Keep JSON-LD 1.1-only. The top-level handler converts parser and loader failures to concise errors unless `--traceback` is passed.

### 5. Complete the YAML-LD conformance runner

Retain and pin the repository’s existing `specifications/yaml-ld` submodule revision [`af4c9c8eb77454645a0b16e69ec16b28a322ff06`](https://github.com/w3c/yaml-ld/commit/af4c9c8eb77454645a0b16e69ec16b28a322ff06) (`Add Introduction bridge paragraph`), and record that hash in the implementation PR description. Its `tests/manifest.jsonld` entry `#cr-utf8-2-negative` uses the legacy expected value `invalid encoding`, while its specification enum uses `invalid-encoding`. Production and direct unit tests use `invalid-encoding`; in `tests/runtests.py`, normalize **only that YAML-LD manifest expectation** `invalid encoding` to `invalid-encoding` before comparing `JsonLdError.code`. Do not alter expected error strings for other suites. Modify [`tests/runtests.py`](https://github.com/digitalbazaar/pyld/blob/master/tests/runtests.py) as follows:

- [ ] In `read_test_property`, load `.yamlld` and `.yaml` expected, context, frame, and option files through the new media parser rather than `read_file`; retain `read_json` for JSON. Make `create_test_options` similarly parse YAML `expandContext` and preserve `extractAllScripts` supplied by a manifest.
- [ ] In `load_locally`, recognize `.yamlld` and `.yaml`, retain fragments in `documentUrl`, return raw body plus normalized metadata, and let `jsonld.load_document` perform parsing. Apply manifest `contentType`, `httpLink`, `httpStatus`, and `redirectTo` before parsing; use the same normalized YAML/JSON alternate and context-link rules as production.
- [ ] Delete YAML-primary-document `idRegex` skips: `compact-local-json-ld-context`, `cir-*`, `cr-*`, `aa-*`, `html-and-yaml-streams`, `html-dedent-*`, `*-documents-from-stream`, `local-json-ld-context`, `core-*`, `flatten`, `frame-t0001`, and the YAML-primary-document `to-rdf` skips. Retain, with an explicit `YAML context operands are outside this universe` comment, `compact-local-yaml-ld-context` and `local-yaml-ld-context`; do not claim zero skips for the whole suite. `#mixed-script-types` is not present at the pinned revision.
- [ ] Run the pinned suite’s selected JSON-profile/YAML-primary-document set with `pytest tests/test_manifests.py --tests=./specifications/yaml-ld/tests --loader=requests` and again with `--loader=aiohttp`, excluding only the two retained YAML-context fixture identifiers above, on every current workflow matrix member (CPython 3.10–3.14 and PyPy 3.10/3.11). Update [`.github/workflows/main.yaml`](https://github.com/digitalbazaar/pyld/blob/master/.github/workflows/main.yaml) so the YAML dependency is installed before those commands.

## :material-test-tube: Acceptance checklist

- [ ] Parser tests cover UTF-8/BOM and exact `invalid-encoding`, Core values, non-Core tags, extended-profile rejection and ignored unknown profile tokens, string-key enforcement, scalar/empty roots, syntax/decode errors, aliases/undefined aliases/cycles, `.inf`/`.nan`, and YAML streams under both `extractAllScripts` values.
- [ ] Loader tests cover each supported MIME type with parameters and `+yaml`, both extensions, exact Accept headers, YAML/JSON alternate links, context links, redirects, cache behavior, final/base URLs, secure failures, and custom raw/preparsed loaders.
- [ ] HTML tests cover source ordering, mixed scripts, base, fragments, profiles, whitespace/indentation, and streams with both values of `extractAllScripts`.
- [ ] CLI tests cover every primary command’s JSON stdin default and YAML `--stdin-format yaml`, invalid/misplaced option errors, no sniffing, primary YAML with each JSON URL secondary operand, rejected YAML explicit secondary URLs, same-primary/same-secondary URL rejection, JSON stdin secondary operands, one-stdin rejection, and missing-extra diagnostics.
- [ ] Existing raw N-Quads exact-output, empty-output, remote-`from-rdf` rejection, option-default, and no-traceback tests stay green.
- [ ] Run focused parser/loader/API/CLI tests, the full manifest matrix, `make lint`, and strict `make docs-build`; validate the rendered documentation in Chromium.

??? info "Decisions"
    This conditional roadmap supports [Implement YAML-LD support in …](index.md). It is not an adopted implementation plan until that ADR selects this alternative.
