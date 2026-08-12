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

When `format` is not set, `jsonld.to_rdf()` returns an
[`rdflib.Dataset`](https://rdflib.readthedocs.io/). Set `legacyMode` to `True`
to return the RDF.js-like dataset `dict` used by PyLD versions lower than 4.

## Example

{{ example('to_rdf.py') }}
