from pyld import jsonld

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

    expected = """<http://foo.bar/obj/test> <http://foo.bar/dc> _:b0 .
<http://foo.bar/obj/test> <http://foo.bar/title> "test" .
_:b0 <http://purl.org/dc/terms/title> "Chapter 1: Jonathan Harker's Journal" .
"""

    nquads = jsonld.to_rdf(input, options={'format': 'application/n-quads'})
    assert nquads == expected


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

    expected = """<http://foo.bar/obj/test> <http://foo.bar/title> "test" .
<http://foo.bar/obj/test> <http://purl.org/dc/terms/title> "Chapter 1: Jonathan Harker's Journal" .
"""

    nquads = jsonld.to_rdf(input, options={'format': 'application/n-quads'})
    assert nquads == expected
