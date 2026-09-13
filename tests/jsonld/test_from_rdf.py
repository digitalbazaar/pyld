import pytest

import pyld.jsonld as jsonld


def test_compound_literal_direction_without_language():
    """
    Compound literals with rdf:direction should become JSON-LD value
    objects when rdfDirection is compound-literal.
    """
    input = """
    <http://example.com/a> <http://example.org/label> _:cl1 .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#value> "no language" .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#direction> "rtl" .
    """

    expected = [
        {
            '@id': 'http://example.com/a',
            'http://example.org/label': [
                {'@value': 'no language', '@direction': 'rtl'}
            ],
        }
    ]

    result = jsonld.from_rdf(input, {'rdfDirection': 'compound-literal'})

    assert result == expected

def test_compound_literal_direction_with_language():
    """
    Compound literals with rdf:language should preserve the language
    when rdfDirection is compound-literal.
    """
    input = """
    <http://example.com/a> <http://example.org/label> _:cl1 .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#value> "en-US" .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#language> "en-us" .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#direction> "rtl" .
    """

    expected = [
        {
            '@id': 'http://example.com/a',
            'http://example.org/label': [
                {
                    '@value': 'en-US',
                    '@language': 'en-us',
                    '@direction': 'rtl',
                }
            ],
        }
    ]

    result = jsonld.from_rdf(input, {'rdfDirection': 'compound-literal'})

    assert result == expected

def test_shared_compound_literal_blank_node_remains_node():
    """
    Compound literal blank nodes must only be decoded once when referenced.
    """
    input = """
    <http://example.com/a> <http://example.org/label> _:cl1 .
    <http://example.com/b> <http://example.org/label> _:cl1 .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#value> "shared" .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#direction> "rtl" .
    """

    expected = [
        {
            '@id': '_:cl1',
            'http://www.w3.org/1999/02/22-rdf-syntax-ns#direction': [
                {'@value': 'rtl'}
            ],
            'http://www.w3.org/1999/02/22-rdf-syntax-ns#value': [
                {'@value': 'shared'}
            ],
        },
        {
            '@id': 'http://example.com/a',
            'http://example.org/label': [{'@id': '_:cl1'}],
        },
        {
            '@id': 'http://example.com/b',
            'http://example.org/label': [{'@id': '_:cl1'}],
        },
    ]

    result = jsonld.from_rdf(input, {'rdfDirection': 'compound-literal'})

    assert result == expected

def test_compound_literal_invalid_direction_fails():
    """
    Invalid rdf:direction values in compound literals must fail.
    """
    input = """
    <http://example.com/a> <http://example.org/label> _:cl1 .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#value> "bad" .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#direction> "up" .
    """

    with pytest.raises(jsonld.JsonLdError) as exc:
        jsonld.from_rdf(input, {'rdfDirection': 'compound-literal'})

    assert exc.value.code == 'invalid base direction'

def test_compound_literal_invalid_value_fails():
    """
    Invalid rdf:value entries in compound literals must fail.
    """
    input = """
    <http://example.com/a> <http://example.org/label> _:cl1 .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#value> "one" .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#value> "two" .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#direction> "rtl" .
    """

    with pytest.raises(jsonld.JsonLdError) as exc:
        jsonld.from_rdf(input, {'rdfDirection': 'compound-literal'})

    assert exc.value.code == 'invalid value object'

def test_compound_literal_invalid_language_fails():
    """
    Invalid rdf:language values in compound literals must fail.
    """
    input = """
    <http://example.com/a> <http://example.org/label> _:cl1 .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#value> "bad lang" .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#language> "bad_lang" .
    _:cl1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#direction> "rtl" .
    """

    with pytest.raises(jsonld.JsonLdError) as exc:
        jsonld.from_rdf(input, {'rdfDirection': 'compound-literal'})

    assert exc.value.code == 'invalid language-tagged string'
