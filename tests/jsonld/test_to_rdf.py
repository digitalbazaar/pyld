from rdflib import Dataset

import pyld.jsonld as jsonld
from pyld.identifier_issuer import IdentifierIssuer

# PR: https://github.com/digitalbazaar/pyld/pull/202

def test_double_and_float_values():
    """
    String values with @type: "xsd:double" should be converted to float value during to_rdf.
    """
    input = {
        "@context": {"xsd": "http://www.w3.org/2001/XMLSchema#"},
        "@graph": [
            {"@id": "ex:1", "ex:p": {"@type": "xsd:double", "@value": "45"}}
        ],
    }

    expected = """<ex:1> <ex:p> "4.5E1"^^<http://www.w3.org/2001/XMLSchema#double>  .

"""
    nquads = jsonld.to_rdf(input, {"format": "application/n-quads"})
    assert nquads == expected

def test_legacy_mode():
    """
    legacyMode should return the PyLD 3.x RDF.js-like dataset dict.
    """
    input = {
        "@context": {"xsd": "http://www.w3.org/2001/XMLSchema#"},
        "@graph": [
            {"@id": "ex:1", "ex:p": {"@type": "xsd:double", "@value": "45"}}
        ],
    }
    expected = {
        "@default": [
            {
                "subject": {"type": "IRI", "value": "ex:1"},
                "predicate": {"type": "IRI", "value": "ex:p"},
                "object": {
                    "type": "literal",
                    "value": "4.5E1",
                    "datatype": "http://www.w3.org/2001/XMLSchema#double",
                },
            }
        ]
    }

    assert isinstance(jsonld.to_rdf(input), Dataset)
    assert jsonld.to_rdf(input, {"legacyMode": True}) == expected

def test_format_takes_precedence_over_legacy_mode():
    """
    N-Quads format output should still be returned when legacyMode is true.
    """
    input = {
        "@context": {"xsd": "http://www.w3.org/2001/XMLSchema#"},
        "@graph": [
            {"@id": "ex:1", "ex:p": {"@type": "xsd:double", "@value": "45"}}
        ],
    }

    expected = """<ex:1> <ex:p> "4.5E1"^^<http://www.w3.org/2001/XMLSchema#double>  .

"""
    nquads = jsonld.to_rdf(
        input,
        {"format": "application/n-quads", "legacyMode": True},
    )
    assert nquads == expected

def test_to_rdf_skips_relative_vocab_property_that_expands_to_invalid_iri():
    """
    to_rdf should omit property IRIs that expand to invalid RDF IRIs.
    """
    input = {
        "@context": [
            {
                "@version": 1.1,
                "@base": "http://example.com/some/deep/directory/and/file/",
                "@vocab": "http://example.com/vocabulary/",
            },
            {"@vocab": "./rel2#"},
        ],
        "@id": "relativePropertyIris",
        "link": "link",
        "#fragment-works": "#fragment-works",
    }

    nquads = jsonld.to_rdf(input, options={'format': 'application/n-quads'})

    assert (
        '<http://example.com/some/deep/directory/and/file/relativePropertyIris> '
        '<http://example.com/vocabulary/./rel2#link> '
        '"link"^^<http://www.w3.org/2001/XMLSchema#string>  .'
    ) in nquads
    assert '##fragment-works' not in nquads

def test_large_integer_to_rdf_double_conversion_processing_mode():
    """
    In json-ld-1.1 processing mode, large integers should be emitted as xsd:double,
    while in json-ld-1.0 processing mode, they should be kept as xsd:integer.
    """
    input = {
        '@id': 'http://example.com/s',
        'http://example.com/p': 1000000000000000000000,
    }

    nquads = jsonld.to_rdf(input, options={'format': 'application/n-quads'})
    expected = """<http://example.com/s> <http://example.com/p> "1.0E21"^^<http://www.w3.org/2001/XMLSchema#double>  .

"""
    assert nquads == expected

    nquads = jsonld.to_rdf(
        input,
        options={
            'format': 'application/n-quads',
            'processingMode': 'json-ld-1.0',
        },
    )
    expected = """<http://example.com/s> <http://example.com/p> "1000000000000000000000"^^<http://www.w3.org/2001/XMLSchema#integer>  .

"""
    assert nquads == expected

def test_to_rdf_uses_identifier_issuer_option():
    input = {'http://example.org/p': [{'@list': ['a', 'b']}]}
    issuer = IdentifierIssuer('_:custom')

    expected = """_:custom0 <http://example.org/p> _:custom1  .
_:custom1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#first> "a"^^<http://www.w3.org/2001/XMLSchema#string>  .
_:custom1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#rest> _:custom2  .
_:custom2 <http://www.w3.org/1999/02/22-rdf-syntax-ns#first> "b"^^<http://www.w3.org/2001/XMLSchema#string>  .
_:custom2 <http://www.w3.org/1999/02/22-rdf-syntax-ns#rest> <http://www.w3.org/1999/02/22-rdf-syntax-ns#nil>  .

"""

    nquads = jsonld.to_rdf(
        input,
        options={'format': 'application/n-quads', 'identifierIssuer': issuer},
    )

    assert sorted(nquads.splitlines()) == sorted(expected.splitlines())

def test_compound_literal_direction_without_language():
    """
    Values with @direction should become compound literals during to_rdf
    when rdfDirection is compound-literal.
    """
    input = {
        'http://example.org/label': {
            '@value': 'no language',
            '@direction': 'rtl',
        }
    }

    expected = """_:b0 <http://example.org/label> _:b1  .
_:b1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#direction> "rtl"^^<http://www.w3.org/2001/XMLSchema#string>  .
_:b1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#value> "no language"^^<http://www.w3.org/2001/XMLSchema#string>  .

"""

    nquads = jsonld.to_rdf(
        input,
        options={
            'format': 'application/n-quads',
            'rdfDirection': 'compound-literal',
        },
    )

    assert sorted(nquads.splitlines()) == sorted(expected.splitlines())

def test_compound_literal_direction_with_language():
    """
    Values with @language should preserve it in compound literals during
    to_rdf when rdfDirection is compound-literal.
    """
    input = {
        'http://example.org/label': {
            '@value': 'en-US',
            '@language': 'en-US',
            '@direction': 'rtl',
        }
    }

    expected = """_:b0 <http://example.org/label> _:b1  .
_:b1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#direction> "rtl"^^<http://www.w3.org/2001/XMLSchema#string>  .
_:b1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#language> "en-us"^^<http://www.w3.org/2001/XMLSchema#string>  .
_:b1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#value> "en-US"^^<http://www.w3.org/2001/XMLSchema#string>  .

"""

    nquads = jsonld.to_rdf(
        input,
        options={
            'format': 'application/n-quads',
            'rdfDirection': 'compound-literal',
        },
    )

    assert sorted(nquads.splitlines()) == sorted(expected.splitlines())

def test_invalid_language_tag_is_skipped():
    """
    Conversion to RDF should skip values with invalid language tags.
    """
    input = {
        '@id': 'http://example.com/foo',
        'http://example.com/bar': {
            '@value': 'bar',
            '@language': 'a b',
        },
    }

    nquads = jsonld.to_rdf(input, options={'format': 'application/n-quads'})
    assert nquads == '\n'

# Issue 204
def test_conflicting_property_names():
    """
    Conversion to RDF should allow a node in the root @context with
    a conflicting property name in its own @context
    """
    input = {
        "@context": {
            "dublinCore": {
                "@id": "http://foo.bar/dc",
                "@context": {"title": "http://purl.org/dc/terms/title"},
            },
            "title": "http://foo.bar/title",
        },
        "@id": "http://foo.bar/obj/test",
        "title": "test",
        "dublinCore": {"title": "Chapter 1: Jonathan Harker's Journal"},
    }

    expected = """<http://foo.bar/obj/test> <http://foo.bar/title> "test"^^<http://www.w3.org/2001/XMLSchema#string>  .
<http://foo.bar/obj/test> <http://foo.bar/dc> _:b0  .
_:b0 <http://purl.org/dc/terms/title> "Chapter 1: Jonathan Harker's Journal"^^<http://www.w3.org/2001/XMLSchema#string>  .

"""

    nquads = jsonld.to_rdf(input, options={'format': 'application/n-quads'})
    # TODO: move this into a helper function for comparing nquads
    assert sorted(nquads.splitlines()) == sorted(expected.splitlines())

def test_conflicting_property_names_in_nested_node():
    """
    Conversion to RDF should not ignore a @nest'ed node in the root @context
    a conflicting property name in its own @context
    """
    input = {
        "@context": {
            "dublinCore": {
                "@id": "@nest",
                "@context": {"title": "http://purl.org/dc/terms/title"},
            },
            "title": "http://foo.bar/title",
        },
        "@id": "http://foo.bar/obj/test",
        "title": "test",
        "dublinCore": {"title": "Chapter 1: Jonathan Harker's Journal"},
    }

    expected = """<http://foo.bar/obj/test> <http://foo.bar/title> "test"^^<http://www.w3.org/2001/XMLSchema#string>  .
<http://foo.bar/obj/test> <http://purl.org/dc/terms/title> "Chapter 1: Jonathan Harker's Journal"^^<http://www.w3.org/2001/XMLSchema#string>  .

"""

    nquads = jsonld.to_rdf(input, options={'format': 'application/n-quads'})
    # TODO: move this into a helper function for comparing nquads
    assert sorted(nquads.splitlines()) == sorted(expected.splitlines())

# Issue 177
def test_fractional():
    """
    Number with 0 fractional part should parse to an xsd:integer
    """
    input = { "ex:value": 42.0 }

    expected = """_:b0 <ex:value> "42"^^<http://www.w3.org/2001/XMLSchema#integer>  .

"""

    nquads = jsonld.to_rdf(input, options={'format': 'application/n-quads'})
    assert nquads == expected

# Issue 175
def test_truncate_zeros_with_negative_exponent_numbers():
    """
    Numeric values with negative exponent should truncate zeros
    """
    input = { "ex:value": 0.97 }

    expected = """_:b0 <ex:value> "9.7E-1"^^<http://www.w3.org/2001/XMLSchema#double>  .

"""

    nquads = jsonld.to_rdf(input, options={'format': 'application/n-quads'})
    assert nquads == expected

def test_list_skips_invalid_iri_items():
    """
    Conversion to RDF should skip invalid list item IRIs without dropping
    the list node.
    """
    input = {
        "@context": {
            "@base": "http://invalid/<>/",
            "list": {
                "@id": "foo:bar",
                "@container": "@list",
                "@type": "@id",
            },
        },
        "list": ["test"],
    }

    expected = """_:b0 <foo:bar> _:b1  .
_:b1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#rest> <http://www.w3.org/1999/02/22-rdf-syntax-ns#nil>  .

"""

    nquads = jsonld.to_rdf(input, options={'format': 'application/n-quads'})
    assert sorted(nquads.splitlines()) == sorted(expected.splitlines())
