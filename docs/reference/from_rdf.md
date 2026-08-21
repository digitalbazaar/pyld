# :material-import: `jsonld.from_rdf()`

::: pyld.jsonld.from_rdf
    options:
      show_docstring_description: false

## Options

::: pyld.options.FromRdfOptions
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3

`jsonld.from_rdf()` accepts a
[:material-library: RDFLib](https://rdflib.readthedocs.io/) `rdflib.Dataset`,
an N-Quads string, or the RDF.js-like dataset `dict` returned by PyLD versions
lower than 4. Prefer `rdflib.Dataset` for new in-memory RDF code.

```python
doc = jsonld.from_rdf(dataset)
doc = jsonld.from_rdf(nquads, {"format": "application/n-quads"})
```

## Example

{{ example('from_rdf.py', 'json') }}
