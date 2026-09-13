import pytest

import pyld.jsonld as jsonld
from pyld.identifier_issuer import IdentifierIssuer


def test_normalize_max_canonicalization_permutations_raises():
    """
    Normalization raises when the RDFC10 permutation budget is exhausted.
    """
    input = (
        '_:a <http://example.org/p> _:b .\n'
        '_:a <http://example.org/p> _:c .\n'
    )

    with pytest.raises(jsonld.JsonLdError) as exc:
        jsonld.normalize(
            input,
            options={
                'algorithm': 'RDFC10',
                'inputFormat': 'application/n-quads',
                'format': 'application/n-quads',
                'maxPermutations': 0,
            },
        )

    assert exc.value.code == 'maximum canonicalization work exceeded'

def test_normalize_does_not_pass_identifier_issuer_to_to_rdf():
    class RaisingIdentifierIssuer(IdentifierIssuer):
        def get_id(self, old=None):
            raise AssertionError('identifierIssuer leaked into normalize')

    input = {'http://example.org/p': {'@id': '_:old'}}

    result = jsonld.normalize(
        input,
        options={
            'format': 'application/n-quads',
            'identifierIssuer': RaisingIdentifierIssuer('_:custom'),
        },
    )

    assert result == '_:c14n1 <http://example.org/p> _:c14n0 .\n'
