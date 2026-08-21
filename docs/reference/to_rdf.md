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

Pass an `IdentifierIssuer` instance as the `identifierIssuer` option to control
blank node identifiers generated during RDF conversion.

## Example

{{ example('to_rdf.py') }}
