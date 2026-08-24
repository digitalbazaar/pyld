# :material-fingerprint: `jsonld.normalize()`

::: pyld.jsonld.normalize
    options:
      show_docstring_description: false

## Options

::: pyld.options.NormalizeOptions
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3

`RDFC10` is the default algorithm in PyLD 4. Use `URDNA2015` or `URGNA2012`
explicitly when an integration requires the older canonicalization output.

## Examples

### Normalizing RDF as canonical N-Quads

{{ example('normalize.py') }}

### Outputting the Identifier Map of the canonicalization process (RDFC1.0)

{{ example('normalize_output_map.py', 'json') }}
