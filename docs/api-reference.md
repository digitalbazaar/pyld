# API Reference

This page lists the public APIs that are intended for direct user code. PyLD
also contains internal processor classes and helper functions that are not
documented here.

## Module `pyld.jsonld`

### `compact(input_, ctx, options=None)`

Compact a JSON-LD document using the provided context.

### `expand(input_, options=None, on_property_dropped=noop)`

Expand a JSON-LD document, removing context aliases and producing expanded
JSON-LD form. `on_property_dropped` can be used to observe or reject properties
that do not expand to absolute IRIs.

### `flatten(input_, ctx=None, options=None)`

Flatten a JSON-LD document. If `ctx` is supplied, compact the flattened output
with that context.

### `frame(input_, frame, options=None)`

Frame a JSON-LD document according to the supplied frame.

### `link(input_, ctx, options=None)`

Experimentally link a JSON-LD document's nodes in memory. This is equivalent to
framing with `@embed: @link`.

### `normalize(input_, options=None)`

Normalize a JSON-LD document. Common options include `algorithm` and `format`.
Use `{"algorithm": "URDNA2015", "format": "application/n-quads"}` to produce
canonical N-Quads.

### `from_rdf(input_, options=None)`

Convert RDF input to JSON-LD.

### `to_rdf(input_, options=None)`

Convert JSON-LD input to RDF dataset form.

### `set_document_loader(load_document_)`

Set the global document loader callable.

### `get_document_loader()`

Return the current global document loader callable.

### `load_document(url, options, base=None, profile=None, request_profile=None)`

Load a remote document using the configured or supplied document loader.

### `requests_document_loader(**kwargs)`

Create a `requests`-based document loader. Pass `secure=True` to require HTTPS.
Other keyword arguments are forwarded to `requests.get()`.

### `aiohttp_document_loader(**kwargs)`

Create an `aiohttp`-based document loader. Pass `secure=True` to require HTTPS.
Other keyword arguments are forwarded to `aiohttp` request calls.

### `register_rdf_parser(content_type, parser)`

Register an RDF parser for a content type.

### `unregister_rdf_parser(content_type)`

Remove a registered RDF parser for a content type.

### `parse_link_header(header)`

Parse an HTTP `Link` header.

### `JsonLdProcessor`

Processor class behind the module-level convenience functions. Most callers use
the module-level functions directly.

### `JsonLdError`

Exception type raised for JSON-LD processing and loading errors.

### `ContextResolver`

Context resolver that can be supplied in operation options for custom context
loading and caching behavior.

### `freeze(value)`

Return an immutable mapping for dictionary values. This is used by PyLD's
context caches.

## Top-Level Exports

### `jsonld`

The main JSON-LD processing module.

### `DocumentLoader`

Abstract base class for class-based document loaders. PyLD still accepts any
callable with the loader signature.

### `RemoteDocument`

Typed mapping shape returned by document loaders.

### `RequestsDocumentLoader`

Class-based remote document loader implemented with `requests`.

### `AioHttpDocumentLoader`

Class-based remote document loader implemented with `aiohttp`.

### `FrozenDocumentLoader`

Allowlist-only document loader for deployments that must not fetch arbitrary
remote contexts.

### `BUNDLED_CONTEXTS`

Mapping of selected common JSON-LD context URLs to bundled local context files.

### `ContextResolver`

Context resolver that can be supplied in operation options for custom context
loading and caching behavior.
