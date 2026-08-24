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

## Examples

### Parsing N-Quads as JSON-LD

{{ example('from_rdf.py', 'json') }}

### Transforming an `rdflib.Dataset` into JSON-LD

{{ example('from_rdf_dataset.py', 'json') }}
