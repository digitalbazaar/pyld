"""
Test cases for XSD integer-derived datatype constants (XSD_INT, XSD_LONG, XSD_INTEGER_DERIVED).

These tests verify that the XSD integer type constants are correctly defined and
properly used during RDF to JSON-LD conversion with native type conversion.
"""

from pyld import jsonld


import pytest


@pytest.mark.parametrize(
    "data,context,frame,expected",
    [
        [
            {
                "int_max": {"@type": "xsd#int", "@value": "2147483647"},
                "int_min": {"@type": "xsd#int", "@value": "-2147483648"},
                "int_val": {"@type": "xsd#int", "@value": "789"},
            },
            {
                "p_int_max": {
                    "@id": "int_max",
                    "@type": "xsd#int",
                },
                "p_int_min": {
                    "@id": "int_min",
                    "@type": "xsd#int",
                },
                "p_int_val": {
                    "@id": "int_val",
                    "@type": "xsd#int",
                },
            },
            {
                "p_int_max": {},
                "p_int_min": {},
                "p_int_val": {},
            },
            {
                "p_int_max": "2147483647",
                "p_int_min": "-2147483648",
                "p_int_val": "789",
            },
        ],
        [
            {"integer": {"@type": "xsd#integer", "@value": "42"}},
            {
                "p_integer": {
                    "@id": "integer",
                    "@type": "xsd#integer",
                },
            },
            {
                "p_integer": {},
            },
            {
                "p_integer": "42",
            },
        ],
        [
            {
                "long_max": {"@type": "xsd#long", "@value": "9223372036854775807"},
                "long_min": {"@type": "xsd#long", "@value": "-9223372036854775808"},
                "long_val": {"@type": "xsd#long", "@value": "456"},
            },
            {
                "p_long_max": {
                    "@id": "long_max",
                    "@type": "xsd#long",
                },
                "p_long_min": {
                    "@id": "long_min",
                    "@type": "xsd#long",
                },
                "p_long_val": {
                    "@id": "long_val",
                    "@type": "xsd#long",
                },
            },
            {
                "p_long_max": {},
                "p_long_min": {},
                "p_long_val": {},
            },
            {
                "p_long_max": "9223372036854775807",
                "p_long_min": "-9223372036854775808",
                "p_long_val": "456",
            },
        ],
        [
            {"zero": {"@type": "xsd#integer", "@value": "0"}},
            {
                "p_zero": {
                    "@id": "zero",
                    "@type": "xsd#integer",
                },
            },
            {
                "p_zero": {},
            },
            {
                "p_zero": "0",
            },
        ],
    ],
)
def test_frame_with_integer_types(data, context, frame, expected):
    """
    Given:
        A RDF dataset containing values with XSD integer-derived types.
    When:
        Framing RDF data with XSD integer-derived types.
    Then:
        The framed output should correctly represent the integer values
        according to their XSD types.
    """
    rdf = [
        {
            "@context": {
                "@vocab": "http://example.org/",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
            },
            **data,
        }
    ]

    framed = jsonld.frame(
        rdf,
        frame={
            "@context": {
                "@vocab": "http://example.org/",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                **context,
            },
            **frame,
        },
    )
    # Remove @context for comparison
    framed.pop("@context")
    assert expected == framed
