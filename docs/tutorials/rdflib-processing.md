# :material-library: RDFLib and `jsonld`

Use this pattern when JSON-LD is your interchange format, but RDF tooling is the
best place to query, update, serialize, or store the graph.

Install PyLD:

```bash
pip install PyLD
```

PyLD 4 installs and uses [:material-library: RDFLib](https://rdflib.readthedocs.io/)
for RDF datasets. The processing order is:

1. Start with JSON-LD that has a usable `@context`.
2. Convert it with `jsonld.to_rdf()`.
3. Process the returned `rdflib.Dataset` with RDFLib.
4. Convert it back with `jsonld.from_rdf()` if the next layer expects JSON-LD.
5. Compact the result with `jsonld.compact()` if developers or APIs should see
   terms such as `name` instead of full IRIs.

{{ example('rdflib_processing.py', 'json') }}

For simple lookups, use RDFLib's graph methods on the dataset returned by
`jsonld.to_rdf()`:

{{ example('rdflib_query.py', 'json') }}

For RDF that starts outside PyLD, parse it with RDFLib first, then pass the
`rdflib.Dataset` to `jsonld.from_rdf()`:

{{ example('rdflib_parse.py', 'json') }}

Use `format` only when you need a serialized RDF string instead of an in-memory
`rdflib.Dataset`:

```python
nquads = jsonld.to_rdf(doc, {"format": "application/n-quads"})
```

Use `jsonld.from_rdf(dataset)` directly when you already have an
`rdflib.Dataset` from another RDFLib parser, store, or query result.
