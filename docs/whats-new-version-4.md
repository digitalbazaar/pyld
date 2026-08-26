# :material-new-box: What's new in version 4

PyLD 4 moves the RDF datastructure to [:material-library: RDFLib](https://rdflib.readthedocs.io/)
and adds RDF Dataset Canonicalization 1.0 support. The JSON-LD document APIs
remain the same, but RDF-facing code should review return types, canonicalization
defaults, and N-Quads behavior before upgrading.

## RDFLib datasets are now the native RDF model

`jsonld.to_rdf()` returns an `rdflib.Dataset` by default when `format` is not
set. In PyLD 3.x and earlier, it returned a RDF.js-like nested `dict`.

{{ example('to_rdf_dataset.py') }}

Request N-Quads when you need a serialized string:

{{ example('to_rdf.py') }}

Use `legacyMode` when existing code still expects the PyLD 3.x dataset `dict`:

{{ example('to_rdf_legacy.py', 'json') }}

`jsonld.from_rdf()` accepts an `rdflib.Dataset`, an N-Quads string, or the
legacy dataset `dict`. New code should prefer `rdflib.Dataset` for in-memory RDF
work and `application/n-quads` for process or storage boundaries.

## `RDFC10` is available and is the normalization default

`jsonld.normalize()` now defaults to `RDFC10`, the RDF Dataset Canonicalization
1.0 algorithm. `URDNA2015` and `URGNA2012` remain available by setting
`algorithm` explicitly.

{{ example('normalize.py') }}

For RDFC 1.0 test vectors and integrations that need the canonical blank node
identifier map, pass `outputMap`:

{{ example('normalize_output_map.py', 'json') }}

`RDFC10` also accepts `hashAlgorithm` for test suites and specialized
integrations. Most applications should keep the default SHA-256 behavior.

## N-Quads parsing and serialization delegates to RDFLib

PyLD 4 removes the internal `pyld.nquads` parser and serializer module. Public
JSON-LD APIs still accept and produce N-Quads through `format: "application/n-quads"`, 
but imports from `pyld.nquads` need to be removed.

If you previously used `pyld.nquads` directly, replace it with one of these
paths:

- Use `jsonld.from_rdf(nquads, {"format": "application/n-quads"})` to convert
  N-Quads to JSON-LD.
- Use `jsonld.to_rdf(doc, {"format": "application/n-quads"})` to serialize
  JSON-LD as N-Quads.
- Use `jsonld.parse_nquads(doc, {"legacyMode": True})` to convert nquads 
  to a RDF.js-like nested `dict` from PyLD 3.x and earlier. 
  Omit `legacyMode` to return an `rdflib.Dataset`. 
  This method preserves blank node identifiers from the input document.
- Use `rdflib.Dataset().parse(data=nquads, format="nquads")` or 
  `rdflib.plugins.parsers.nquads.NQuadsParser()` for direct RDFLib parsing. 
  Note that, opposed to `jsonld.parse_nquads`, this does NOT preserve blank node 
  identifiers by default.

## Compatibility helpers

PyLD 4 includes conversion helpers for applications that need to bridge between
the old in-memory RDF.js-like nested `dict` and RDFLib:

{{ example('legacy_helpers.py') }}

Treat these helpers as migration aids. Prefer RDFLib terms and datasets in new
code so RDF processing is compatible with the rest of the Python RDF ecosystem.

## Behavior fixes to expect

The RDFLib migration also fixes several RDF conversion edge cases:

- RDF literal lexical forms are preserved more carefully through RDFLib
  conversion, including canonical double output, large numeric values, and
  compound literals.
- Invalid IRI and language values are skipped during `jsonld.to_rdf()` instead
  of producing invalid triples or crashing.
- Query and fragment reconstruction in `iri_resolver.unresolve()` is corrected.
- More W3C URDNA2015, URDNA2012, RDFC10, and JSON-LD `toRdf` tests run through
  the default test runner.

## Upgrade checklist

- Add `rdflib` to application constraints if dependencies are pinned outside
  PyLD's package metadata.
- Audit `jsonld.to_rdf()` call sites that do not pass `format`. Update them to
  handle `rdflib.Dataset` or temporarily pass `legacyMode`.
- Remove imports of `pyld.nquads`.
- Check normalization call sites that relied on the old default algorithm. Pass
  `{"algorithm": "URDNA2015"}` explicitly if that output must remain stable.
- Compare N-Quads as RDF data or sorted lines in tests unless the test requires
  exact serializer ordering.
