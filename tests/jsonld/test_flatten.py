import pyld.jsonld as jsonld
from pyld.identifier_issuer import IdentifierIssuer


def test_flatten_uses_identifier_issuer_option():
    input = {'http://example.org/p': {'@id': '_:old'}}

    result = jsonld.flatten(
        input,
        options={'identifierIssuer': IdentifierIssuer('_:custom')},
    )

    assert result == [
        {
            '@id': '_:custom0',
            'http://example.org/p': [{'@id': '_:custom1'}],
        }
    ]
