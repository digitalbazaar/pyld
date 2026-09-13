import pytest

import pyld.jsonld as jsonld


# Issue 59 - PR: https://github.com/digitalbazaar/pyld/pull/60
def test_compaction_with_and_without_explicit_datatypes():
    """
    Values with explicit datatypes should be compacted during compaction while values
    without explicit dataypes should not.
    """
    input = {
        "http://example.org/a": "A",
        "http://example.org/b": "B",
        "http://example.org/c": {"@value": "C", "@type": "urn:C"},
    }

    context = {
        "@context": {
            "ex": "http://example.org/",
            "a": {"@id": "http://example.org/a"},
            "b": {"@id": "http://example.org/b", "@type": "urn:B"},
            "c": {"@id": "http://example.org/c", "@type": "urn:C"},
        }
    }

    expected = {
        "@context": {
            "ex": "http://example.org/",
            "a": {"@id": "http://example.org/a"},
            "b": {"@id": "http://example.org/b", "@type": "urn:B"},
            "c": {"@id": "http://example.org/c", "@type": "urn:C"},
        },
        "a": "A",
        "ex:b": "B",
        "c": "C",
    }

    compacted = jsonld.compact(input, context)
    assert compacted == expected

# Issue 247 - term selection order during compaction
def test_compact_prefers_shortest_term():
    """
    When two terms map to the same IRI, compaction should prefer the
    shorter term, per the Inverse Context Creation algorithm (spec
    section 4.3 step 3: "ordered by shortest term first").
    """
    context = {
        "schema": "https://schema.org/",
        "name": "schema:name",
        "full_name": "schema:name",
    }
    doc = {"https://schema.org/name": [{"@value": "Alice"}]}
    result = jsonld.compact(doc, context)
    assert "name" in result
    assert "full_name" not in result

def test_compact_shortest_wins_over_underscore_prefix():
    """
    A shorter term should be preferred even when a longer
    underscore-prefixed term sorts lexicographically first.
    """
    context = {
        "schema": "https://schema.org/",
        "name": "schema:name",
        "_internal_name": {"@id": "schema:name"},
    }
    doc = {"https://schema.org/name": [{"@value": "Alice"}]}
    result = jsonld.compact(doc, context)
    assert "name" in result
    assert "_internal_name" not in result

def test_compact_same_length_uses_lexicographic_tiebreak():
    """
    When two terms of the same length map to the same IRI, the
    lexicographically least term (by code point order) should win.
    """
    context = {
        "schema": "https://schema.org/",
        "name": "schema:name",
        "nick": "schema:name",
    }
    doc = {"https://schema.org/name": [{"@value": "Alice"}]}
    result = jsonld.compact(doc, context)
    assert "name" in result
    assert "nick" not in result

def test_index_map_with_compact_iri_index_round_trips():
    """
    When an @index container uses a compact IRI as its @index mapping,
    compaction should use the indexed property value as the map key and
    preserve the expanded representation on round-trip.
    """
    context = {
        "@context": {
            "ex": "http://example.com/",
            "items": {
                "@id": "ex:items",
                "@container": "@index",
                "@index": "ex:rank",
            },
        }
    }
    expanded = [
        {
            "http://example.com/items": [
                {
                    "http://example.com/rank": [{"@value": "first"}],
                    "http://example.com/name": [{"@value": "Alice"}],
                }
            ]
        }
    ]

    compacted = jsonld.compact(expanded, context, {"skipExpansion": True})

    assert compacted == {
        "@context": context["@context"],
        "items": {"first": {"ex:name": "Alice"}},
    }
    assert jsonld.expand(compacted) == expanded

def test_reverse_index_map_with_term_index_uses_property_value_as_key():
    """
    When an @index container uses a term as its @index mapping, compaction
    should still find the property key selected using the indexed value.
    """
    context = {
        "@context": {
            "@version": 1.1,
            "@base": "https://example.org/",
            "@vocab": "https://example.net/ns#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "statement": {
                "@reverse": "rdf:subject",
                "@container": "@index",
                "@index": "predicate",
            },
            "predicate": {"@id": "rdf:predicate", "@type": "@vocab"},
            "term": {"@id": "rdf:object", "@type": "@vocab"},
            "addedIn": {"@type": "@id"},
        }
    }
    expanded = [
        {
            "@id": "https://example.org/item/1",
            "@reverse": {
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#subject": [
                    {
                        "https://example.net/ns#addedIn": [
                            {"@id": "https://example.org/v1"}
                        ],
                        "http://www.w3.org/1999/02/22-rdf-syntax-ns#object": [
                            {"@id": "https://example.net/ns#A"}
                        ],
                        "http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate": [
                            {
                                "@id": (
                                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                                    "type"
                                )
                            }
                        ],
                    }
                ]
            },
        }
    ]

    compacted = jsonld.compact(expanded, context, {"skipExpansion": True})

    assert compacted == {
        "@context": context["@context"],
        "@id": "item/1",
        "statement": {"rdf:type": {"term": "A", "addedIn": "v1"}},
    }

def test_node_reference_compacts_to_string_value_of_type_map():
    """
    A node reference in a type map can compact to a string when the term
    is type-coerced to @id. In that case the type map should use @none.
    """
    input = {
        "@context": {"@vocab": "http://schema.org/"},
        "@type": "Event",
        "location": {"@id": "http://kg.artsdata.ca/resource/K11-200"},
    }
    context = {
        "@context": {
            "@vocab": "http://schema.org/",
            "location": {"@type": "@id", "@container": "@type"},
        }
    }

    compacted = jsonld.compact(input, context)

    assert compacted == {
        "@context": context["@context"],
        "@type": "Event",
        "location": {"@none": "http://kg.artsdata.ca/resource/K11-200"},
    }

def test_empty_property_scoped_context_preserves_outer_terms():
    """
    An empty property-scoped context should not reset the active context
    during compaction.
    """
    expanded = [
        {
            "http://example.com/title": [{"@value": "top"}],
            "http://example.com/thing": [
                {
                    "http://example.com/title": [{"@value": "sub"}],
                }
            ],
        }
    ]
    context = {
        "@context": {
            "ex": "http://example.com/",
            "thing": {"@id": "ex:thing", "@context": {}},
            "title": "ex:title",
        }
    }

    compacted = jsonld.compact(expanded, context, {"skipExpansion": True})

    assert compacted == {
        "@context": context["@context"],
        "title": "top",
        "thing": {"title": "sub"},
    }

# Issue 91
def test_empty_context():
    """
    Compacting with an empty context should return the input unchanged.
    """
    input = {'http://schema.org/codeRepository': {'@id': 'http:'}}
    compacted = jsonld.compact(input, {})
    assert compacted == input

# Issue 82
def test_no_initial_context_drops_property():
    """
    Compacting without initial context should drop the original input.
    """

    input = {'name': 'Bob'}

    compacted = jsonld.compact(input, {"@vocab": "http://example.org#"})
    expected = {"@context": {"@vocab": "http://example.org#"}}

    assert compacted == expected

@pytest.mark.xfail
def test_no_initial_context_and_with_skip_expand_does_not_drop_property_whe_not_array(
    ):
    """
    Compacting document with singular value and without initial context should
    output the original input when skipExpansion is enabled.
    """

    input = {'name': 'Bob'}

    compacted = jsonld.compact(
        input, {"@vocab": "http://example.org#"}, {"skipExpansion": True}
    )
    expected = {"@context": {"@vocab": "http://example.org#"}, "name": "Bob"}
    assert compacted == expected

def test_no_initial_context_and_with_skip_expand_does_not_drop_property_when_array(
    ):
    """
    Compacting document with array value and without initial context should
    output the original input when skipExpansion is enabled.
    """

    input = {'name': ['Bob']}

    compacted = jsonld.compact(
        input, {"@vocab": "http://example.org#"}, {"skipExpansion": True}
    )
    expected = {"@context": {"@vocab": "http://example.org#"}, "name": "Bob"}
    assert compacted == expected

# Issue 83
def test_with_vocab_no_id():
    """
    Compacting with @vocab should not compact a plain string value
    """
    ctx = {'@vocab': 'http://ex.org/#', 'path': {'@type': '@id'}}
    input = {
        'http://ex.org/#path': 'http://ex.org/#shortname',
    }
    expected = {
        "@context": {"@vocab": "http://ex.org/#", "path": {"@type": "@id"}},
        "http://ex.org/#path": "http://ex.org/#shortname",
    }

    compacted = jsonld.compact(input, ctx)

    assert compacted == expected

def test_with_vocab_with_id():
    """
    Compacting with @vocab should compact an @id value
    """
    ctx = {'@vocab': 'http://ex.org/#', 'path': {'@type': '@id'}}
    input = {
        'http://ex.org/#path': {'@id': 'http://ex.org/#shortname'},
    }
    expected = {
        "@context": {"@vocab": "http://ex.org/#", "path": {"@type": "@id"}},
        "path": "http://ex.org/#shortname",
    }

    compacted = jsonld.compact(input, ctx)

    assert compacted == expected
