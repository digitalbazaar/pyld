"""
Regression test: @base must not be used to expand property keys.

Property names are expanded vocabulary-relative: @vocab, term definitions,
compact IRIs with a defined prefix, etc. The active context's @base is for
document-relative IRI resolution where the algorithms pass that flag (e.g.
certain @id and @type values), not for turning arbitrary keys into absolute
IRIs. Here the context sets only @base; `name` has no term definition and no
@vocab, so it cannot become an absolute property IRI and must be dropped.

See: https://www.w3.org/TR/json-ld11-api/#iri-expansion
"""

import pyld.jsonld as jsonld


def test_base_does_not_expand_property_terms():
    """Property keys must not be resolved against @base without vocabulary-relative mapping."""
    doc = {
        '@context': {'@base': 'https://schema.org/'},
        '@id': 'https://w3.org/yaml-ld/',
        '@type': 'WebContent',
        'name': 'YAML-LD',
    }
    result = jsonld.expand(doc)
    # `name` has no vocabulary-relative mapping (@vocab or term definition);
    # @base must not supply one. The key is dropped.
    assert result == [
        {
            '@id': 'https://w3.org/yaml-ld/',
            '@type': ['https://schema.org/WebContent'],
        }
    ]
