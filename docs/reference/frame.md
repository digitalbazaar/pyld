# :material-view-dashboard-outline: `jsonld.frame()`

::: pyld.jsonld.frame
    options:
      show_docstring_description: false

## Options

::: pyld.options.FrameOptions
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3

Pass an `IdentifierIssuer` instance as the `identifierIssuer` option to control
blank node identifiers generated during framing.

## Example

{{ example('frame.py', 'json') }}
