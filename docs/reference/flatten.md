# :material-layers-outline: `jsonld.flatten()`

::: pyld.jsonld.flatten
    options:
      show_docstring_description: false

## Options

::: pyld.options.FlattenOptions
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3

Pass an `IdentifierIssuer` instance as the `identifierIssuer` option to control
blank node identifiers generated during flattening.

## Example

{{ example('flatten.py', 'json') }}
