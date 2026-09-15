# :material-transit-connection-variant: Provide YAML-LD through a PyLD façade

!!! info "Conditional roadmap"

    This is the implementation universe in which [:fontawesome-brands-github: `digitalbazaar/pyld`](https://github.com/digitalbazaar/pyld) presents YAML-LD through an adapter extracted from [:fontawesome-brands-github: `iolanta-tech/python-yaml-ld`](https://github.com/iolanta-tech/python-yaml-ld). It applies only if the parent decision selects this alternative.

## :material-target: Target experience

Users install `PyLD[cli,yaml-ld]` and use the existing PyLD operations and the single `pyld` command. The optional PyLD extra installs the small `yaml-ld-adapter` distribution, not the `yaml-ld` high-level wrappers. Before the façade is released, remove the original package's high-level transformation wrappers, CLI modules, and conflicting `pyld` entry point; its migration guidance directs users to PyLD's `pyld` command and `pyld.jsonld.*` API.

Build this work on [`306-complete-pyld-cli`](https://github.com/digitalbazaar/pyld/tree/306-complete-pyld-cli): either rebase after that branch merges, or submit this work as a PR stacked on it. That branch supplies the command modules, CLI cache, and class-based loaders on which this roadmap relies.

## :material-clipboard-check-outline: Fixed implementation decisions

### Adapter release contract

- [ ] Create [:fontawesome-brands-github: `iolanta-tech/yaml-ld-adapter`](https://github.com/iolanta-tech/yaml-ld-adapter) as a `src/`-layout package: distribution `yaml-ld-adapter`, import package `yaml_ld_adapter`, source directory `src/yaml_ld_adapter/`, and tests in `tests/`.
- [ ] Publish `yaml-ld-adapter` `1.0.0` before changing PyLD. Its runtime dependency is `ruamel.yaml>=0.19,<1`; its supported runtimes are PyLD's current matrix: CPython 3.10, 3.11, 3.12, 3.13, and 3.14, plus PyPy 3.10 and 3.11. Test the adapter on every member of that matrix before release.
- [ ] Give the adapter exactly this public surface, with `JSONValue` recursively meaning `None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]` and `JSONDocument` meaning `dict[str, JSONValue] | list[JSONValue]`:

    ```python
    class YamlLdAdapterError(Exception):
        code: Literal[
            'invalid-encoding',
            'mapping-key-error',
            'loading-document-failed',
            'profile-error',
        ]

    def parse_yaml_ld_stream(
        data: bytes | str,
        *,
        source_url: str,
        profile: str | None = None,
    ) -> tuple[JSONDocument, ...]: ...
    ```

    The adapter accepts only raw YAML-LD and returns every document in a YAML stream; it performs no I/O, HTTP negotiation, HTML traversal, JSON-LD processing, caching, or CLI work.

- [ ] Implement the YAML-LD Basic profile only. The adapter receives either `None` or the recognized `http://www.w3.org/ns/json-ld#extended` profile URI, and rejects the latter with `YamlLdAdapterError(code='profile-error')`. The PyLD media and HTML layers tokenize a space-separated `profile` parameter into URI tokens, ignore unknown tokens, and pass the recognized Extended URI to the adapter. This makes YAML tags and other Extended-profile features unsupported, rather than silently treating them as Basic YAML-LD. The [YAML-LD specification](https://w3c.github.io/yaml-ld/#application-ld-yaml) defines that profile parameter and identifies the Extended profile separately.
- [ ] Parse UTF-8 or UTF-8 with a BOM using YAML 1.2 Core-schema rules. Preserve date-like scalars as strings; require string mapping keys; deep-copy aliases into a JSON tree; reject undefined aliases, cycles, scalar roots, empty streams, non-finite numbers, syntax failures, and non-UTF-8 input. Map those failures to the four adapter codes above. The current `python-yaml-ld` parser and its [`ruamel.yaml`](https://pypi.org/project/ruamel.yaml/) Core-schema configuration are the porting source; the YAML-LD specification requires YAML 1.2-compatible processing and JSON-compatible mapping keys.

### PyLD media boundary and ownership

- [ ] Add `pyld.documentloader.media.coerce_remote_document(remote_document, *, options, profile)` and make [`jsonld.load_document`](https://github.com/digitalbazaar/pyld/blob/306-complete-pyld-cli/lib/pyld/jsonld.py) call it exactly once after *every* built-in or user-supplied `documentLoader` returns **and after** its existing `base` override has set `remote_document['documentUrl']`. This ordering gives HTML parsing the final document URL. It returns a `RemoteDocument` with a parsed `document`; a dict or list is returned unchanged, making the step idempotent for custom loaders that already parse JSON.
- [ ] Change `FileDocumentLoader`, `RequestsDocumentLoader`, and `AioHttpDocumentLoader` to return raw `bytes` plus `contentType`, `documentUrl`, and `contextUrl`. Do not call `response.json()` in transport loaders. `SqliteCacheRequestsDocumentLoader` continues to cache the raw HTTP response through its Requests delegate; parsing happens after a cache hit or miss through `coerce_remote_document`.
- [ ] In `coerce_remote_document`, parse and normalize a Content-Type case-insensitively before stripping its parameters; retain the original `RemoteDocument['contentType']` value for callers. Use `json.loads` for JSON and `yaml_ld_adapter.parse_yaml_ld_stream` for `application/ld+yaml`, explicit HTTP/custom `application/yaml` or `application/x-yaml`, and registered `+yaml` types. For direct YAML, `extractAllScripts=False` selects the first YAML document and `True` returns a top-level array of every document, including a one-document stream; an empty stream is `loading document failed`. Recognize both `.yamlld` and `.yaml` as the canonical `application/ld+yaml` in `FileDocumentLoader`.
- [ ] Normalize Content-Type and typed Link-header `alternate` parameters before applying the existing JSON-LD Link-header rules, while preserving the raw header values. Recognize a typed alternate with a supported YAML media type as dereferenceable alongside JSON-LD. Test Content-Type parameters, redirects, `secure=True`, cache hits, link contexts, and alternates with both raw built-in responses and a custom `DocumentLoader` returning `str` or `bytes`.
- [ ] Change the default Accept header to this exact YAML-first order:

    ```text
    application/ld+yaml, application/ld+json;q=0.9, application/json;q=0.8, text/html;q=0.5, application/xhtml+xml;q=0.5
    ```

    Do not send an Extended-profile parameter because it is unsupported. Test that Requests and AioHTTP receive that exact header unless an API caller supplies `options['headers']`.

### HTML is PyLD's responsibility

- [ ] Keep HTML traversal in PyLD's `load_html`, which owns HTML `<base>` resolution, `documentUrl`, JSON-LD profile selection, fragment lookup, and the `options['base']` update. For every selected script, normalize its `type` and tokenize its space-separated profile parameter with the same rules as an HTTP Content-Type; parse JSON-LD scripts with `json.loads` and YAML-LD scripts with the adapter. Pass each YAML script's source text unchanged to the adapter: indentation and whitespace are significant YAML input.
- [ ] With a fragment, select the named script only and reject a missing script or an unsupported script type as `loading document failed`. Without a fragment, `extractAllScripts=False` uses the first supported JSON-LD or YAML-LD script in source order. With `extractAllScripts=True`, process every supported script in source order.
- [ ] Fold an all-scripts result deterministically: a JSON-LD array contributes its members; each YAML stream contributes its YAML documents in stream order; a mapping contributes itself. Thus a YAML stream in one HTML script behaves as separate scripts while mixed JSON/YAML scripts preserve document order. Add fixtures for mixed types, both indentation cases, fragments, HTML `<base>`, YAML streams, and `extractAllScripts` true and false.
- [ ] Convert `YamlLdAdapterError` only in the PyLD media boundary: retain `invalid-encoding`, `mapping-key-error`, and `profile-error` as `JsonLdError.code`; map every other adapter parser failure to `loading document failed`. An HTML YAML-script failure is `invalid script element` with the adapter code in the error details. Do not expose adapter exceptions from PyLD.

### CLI format and secondary-operand contract

- [ ] Add `--input-format {json,yaml}` to the primary `INPUT` of `get`, `expand`, `compact`, `flatten`, `frame`, and `to-rdf`. It is required exactly when `INPUT` is `-` and rejected for a path or HTTP(S) URL. `json` calls `json.load`; `yaml` passes stdin bytes to the adapter. There is no format sniffing. `from-rdf` keeps its existing raw N-Quads stdin reader and has no `--input-format`.
- [ ] Keep `CONTEXT`, `FRAME`, `--context`, and `--expand-context` JSON-only. They intentionally receive no YAML-format option. Their `-` form is JSON only and continues to participate in `ensure_single_stdin`.
- [ ] Add `JsonOnlyOperandReader` in `pyld.cli.input`. For local paths and HTTP(S) URLs it calls the configured PyLD file/Requests/AioHTTP transport, cache, URL validation, redirect handling, and secure-mode checks, then parses only JSON. It returns a `RemoteDocument` retaining `contentType`, `contextUrl`, and final `documentUrl`; it rejects YAML and HTML before the general media boundary runs.
- [ ] Add a `JsonOnlyOperandDocumentLoader` view around the configured loader. It serves that pre-read `RemoteDocument` when the processor dereferences the matching secondary URL, then delegates all other URLs to the regular loader. Pass the original canonical URL plus this view into `compact`, `frame`, `expand`, and `flatten`, so remote-context and relative-IRI semantics retain the pre-read document's final URL. For stdin, pass the parsed JSON value directly because it has no dereferenceable document URL.
- [ ] Preserve PR #330's raw RDF boundary: `from-rdf` accepts only a local path or stdin as N-Quads; `to-rdf` accepts JSON or YAML primary input but writes exact N-Quads with `sys.stdout.write()` and never serializes YAML. Keep the concise CLI error handler unless `--traceback` is requested. Its package-install diagnostic must distinguish missing CLI dependencies (`PyLD[cli]`) from a YAML adapter requested by YAML input (`PyLD[cli,yaml-ld]`).

## :material-map: Ordered implementation and verification

### Release the adapter first

- [ ] Extract the Core-schema parser from `python-yaml-ld` into `yaml-ld-adapter`; remove the high-level transformation wrappers, CLI modules, and conflicting `pyld` entry point, and publish a migration guide to PyLD's `pyld` command and `pyld.jsonld.*` API.
- [ ] Add unit tests for every adapter signature and error code, byte/text parity, BOM, streams, aliases and cycles, mapping keys, scalar roots, non-finite floats, and Basic-profile tags. Run them on the declared CPython and PyPy matrix and build/test both sdist and wheel.
- [ ] Release `yaml-ld-adapter==1.0.0`. Only after it is available, add `yaml-ld-adapter>=1.0.0,<2.0.0` to PyLD's `setup.py` `yaml-ld` extra; `cli` remains an independent extra. A JSON-only PyLD install must neither import `yaml_ld_adapter` nor depend on `ruamel.yaml`.

### Add the façade in PyLD

- [ ] Implement the raw-transport change and the single `coerce_remote_document` call site before adding YAML parsing. Add PyLD `documentloader.media` tests for Content-Type and Link-alternate normalization, profile token handling, direct YAML stream selection, and empty streams. Prove existing JSON, custom-loader, HTTP cache, Link-header, redirect, base-IRI, and secure-mode tests are unchanged.
- [ ] Implement direct YAML media parsing, then HTML YAML-script parsing, then the JSON-only CLI reader/view and `--input-format` option. Add command-level tests for every command accepting primary stdin in each format, missing/invalid `--input-format`, JSON-only secondary stdin, multiple `-` rejection, local/remote JSON contexts and frames, raw N-Quads input/output, and no Rich styling in N-Quads output.
- [ ] Add `yaml-ld-adapter` to CI's YAML-LD test environment and update `tests/runtests.py`: initialize the `specifications/yaml-ld` submodule, infer `.yamlld` and `.yaml` as `application/ld+yaml` in `create_document_loader`, honor each manifest `contentType`, preserve Link/redirect metadata, and add YAML alternates. Remove the in-scope YAML-LD `idRegex` skips rather than masking failures.
- [ ] Run the YAML-LD manifest suite through the façade's `expand`, `compact`, `flatten`, `frame`, `to_rdf`, and `normalize` paths on the full matrix and with both Requests and AioHTTP. Adapter tests own parser/media fixtures; PyLD owns JSON-LD operation and manifest conformance. Any remaining non-normative Extended-profile test is skipped only by its manifest `normative: false` marker, with no broad regular-expression skip.

### Ship jointly

- [ ] Build PyLD wheels and install-test `PyLD[yaml-ld]` and `PyLD[cli,yaml-ld]` at both ends of the adapter version range. Gate release on the complete adapter matrix, PyLD matrix, adapter fixtures, PyLD manifests, CLI byte-output tests, strict documentation build, and package-isolation test.
- [ ] Release adapter `1.0.0`, then the PyLD feature release. PyLD owns façade, HTTP, cache, and CLI regressions; adapter maintainers own parser CVEs. For an adapter defect, publish a compatible adapter patch or constrain PyLD's extra bound and release coordinated advisories.

??? info "Decisions"
    This conditional roadmap supports [Implement YAML-LD support in …](index.md). It is not an adopted implementation plan until that ADR selects this alternative.
