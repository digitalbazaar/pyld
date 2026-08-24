# :material-export: `jsonld.to_rdf()`

::: pyld.jsonld.to_rdf
    options:
      show_docstring_description: false

## Options

::: pyld.options.ToRdfOptions
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3

When `format` is not set, `jsonld.to_rdf()` returns a
[:material-library: RDFLib](https://rdflib.readthedocs.io/) `rdflib.Dataset`.
Set `legacyMode` to `True` to return the RDF.js-like dataset `dict` used by
PyLD versions lower than 4.

`legacyMode` only affects the unformatted return value. If `format` is set,
`jsonld.to_rdf()` returns the requested serialization.

## Examples

### Serializing JSON-LD to N-Quads

{{ example('to_rdf.py') }}

### Transforming JSON-LD into an `rdflib.Dataset`

{{ example('to_rdf_dataset.py') }}

### Transforming JSON-LD into an legacy RDF.js-like dict

{{ example('to_rdf_legacy.py', 'json') }}
