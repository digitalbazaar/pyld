import pytest

import pyld.jsonld as jsonld
from pyld.identifier_issuer import IdentifierIssuer

# Issue 11 - PR: https://github.com/digitalbazaar/pyld/issues/149

def test_processing_id_in_inner_context():
    input = {
        "@type": "Package",
        "system": [
            {
                "namespace": "http://purl.obolibrary.org/obo/",
                "contents": [{"uri": "ncit:C147557", "label": "Stuff"}],
            }
        ],
    }

    context = {
        "@context": {
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "obo": "https://purl.obolibrary.org/obo/",
            "termci": "https://hotecosystem.org/termci/",
            "ncit": {"@id": "http://purl.obolibrary.org/obo/NCI_", "@prefix": True},
            "system": {
                "@type": "@id",
                "@id": "termci:system",
                "@container": "@set",
                "@context": {
                    "@id": "skos:ConceptScheme",
                    "@context": {
                        "namespace": "@id",
                        "contents": {
                            "@type": "@id",
                            "@id": "skos:hasConcept",
                            "@container": "@set",
                            "@context": {"uri": "@id", "label": "skos:label"},
                        },
                    },
                },
            },
        },
        "@type": "https://hotecosystem.org/termci/Package",
    }

    # Convert the RDF back into vanilla JSON
    output_json = jsonld.frame(
        input,
        context,
        options={
            "expandContext": context,
            "base": "https://hotecosystem.org/termci/",
        },
    )

    # Observe that system.contents.uri did not change to system.contents.namespace
    assert "namespace" in output_json["system"][0]
    assert "uri" in output_json["system"][0]["contents"][0]

def test_frame_uses_identifier_issuer_option():
    input = {'http://example.org/p': {'@id': '_:old'}}

    result = jsonld.frame(
        input,
        {},
        options={'identifierIssuer': IdentifierIssuer('_:custom')},
    )

    assert result == {
        '@graph': [
            {'http://example.org/p': {'@id': '_:custom1'}},
            {'@id': '_:custom1'},
        ]
    }

# PR: https://github.com/digitalbazaar/pyld/pull/31

FRAME_0001_IN = {
    "@context": {
        "dc": "http://purl.org/dc/elements/1.1/",
        "ex": "http://example.org/vocab#",
        "ex:contains": {"@type": "@id"},
    },
    "@graph": [
        {
            "@id": "http://example.org/test/#library",
            "@type": "ex:Library",
            "ex:contains": "http://example.org/test#book",
        },
        {
            "@id": "http://example.org/test#book",
            "@type": "ex:Book",
            "dc:contributor": "Writer",
            "dc:title": "My Book",
            "ex:contains": "http://example.org/test#chapter",
        },
        {
            "@id": "http://example.org/test#chapter",
            "@type": "ex:Chapter",
            "dc:description": "Fun",
            "dc:title": "Chapter One",
        },
    ],
}

FRAME_0001_FRAME = {
    "@context": {
        "dc": "http://purl.org/dc/elements/1.1/",
        "ex": "http://example.org/vocab#",
    },
    "@type": "ex:Library",
    "ex:contains": {"@type": "ex:Book", "ex:contains": {"@type": "ex:Chapter"}},
}

FRAME_0001_FRAME_WITHOUT_CONTEXT = {
    "@type": "ex:Library",
    "ex:contains": {"@type": "ex:Book", "ex:contains": {"@type": "ex:Chapter"}},
}

FRAME_0001_FRAME_WITH_PARTIAL_CONTEXT = {
    "@context": {"dc": "http://purl.org/dc/elements/1.1/"},
    "@type": "ex:Library",
    "ex:contains": {"@type": "ex:Book", "ex:contains": {"@type": "ex:Chapter"}},
}

FRAME_0001_FRAME_CONTEXT = {
    "@context": {
        "dc": "http://purl.org/dc/elements/1.1/",
        "ex": "http://example.org/vocab#",
    }
}

FRAME_0001_FRAME_PARTIAL_CONTEXT = {"@context": {"ex": "http://example.org/vocab#"}}

SCHEMA_ORG_DATE_CONTEXT = {
    "@context": {
        "schema": "http://schema.org/",
        "name": "http://schema.org/name",
        "birthDate": {
            "@id": "http://schema.org/birthDate",
            "@type": "schema:Date",
        },
        "deathDate": {
            "@id": "http://schema.org/deathDate",
            "@type": "schema:Date",
        },
    }
}


def _frame_with_remote_context(input, frame, context):
    def fake_loader(url, options):
        if url == "http://example.com/frame.json":
            return {
                "contextUrl": "http://example.com/frame-context.json",
                "document": frame,
                "documentUrl": url,
                "contentType": "application/json+ld",
            }
        elif url == "http://example.com/frame-context.json":
            return {
                "contextUrl": None,
                "document": context,
                "documentUrl": url,
                "contentType": "application/json+ld",
            }
        else:
            raise Exception(f"Unknown URL: {url}")

    options = {"documentLoader": fake_loader, "omitGraph": False}
    return jsonld.frame(input, "http://example.com/frame.json", options=options)

def test_remote_context_local_and_remote_context_equal():
    """
    Example with both local and remote context should combine both contexts
    correctly when framing.
    """
    expected = {
        "@context": [
            {
                "dc": "http://purl.org/dc/elements/1.1/",
                "ex": "http://example.org/vocab#",
            },
            "http://example.com/frame-context.json",
        ],
        "@graph": [
            {
                "@id": "http://example.org/test/#library",
                "@type": "ex:Library",
                "ex:contains": {
                    "@id": "http://example.org/test#book",
                    "@type": "ex:Book",
                    "dc:contributor": "Writer",
                    "dc:title": "My Book",
                    "ex:contains": {
                        "@id": "http://example.org/test#chapter",
                        "@type": "ex:Chapter",
                        "dc:description": "Fun",
                        "dc:title": "Chapter One",
                    },
                },
            }
        ],
    }

    framed = _frame_with_remote_context(
        FRAME_0001_IN, FRAME_0001_FRAME, FRAME_0001_FRAME_CONTEXT
    )

    assert framed == expected

def test_remote_context_remote_context_only():
    """
    Example with only remote context should use remote context correctly
    when framing.
    """
    expected = {
        "@context": "http://example.com/frame-context.json",
        "@graph": [
            {
                "@id": "http://example.org/test/#library",
                "@type": "ex:Library",
                "ex:contains": {
                    "@id": "http://example.org/test#book",
                    "@type": "ex:Book",
                    "dc:contributor": "Writer",
                    "dc:title": "My Book",
                    "ex:contains": {
                        "@id": "http://example.org/test#chapter",
                        "@type": "ex:Chapter",
                        "dc:description": "Fun",
                        "dc:title": "Chapter One",
                    },
                },
            }
        ],
    }

    framed = _frame_with_remote_context(
        FRAME_0001_IN,
        FRAME_0001_FRAME_WITHOUT_CONTEXT,
        FRAME_0001_FRAME_CONTEXT,
    )

    assert framed == expected

def test_remote_context_half_context_local_and_half_remote():
    """
    Example with partial local and partial remote context should combine both contexts
    correctly when framing.
    """
    expected = {
        "@context": [
            {"dc": "http://purl.org/dc/elements/1.1/"},
            "http://example.com/frame-context.json",
        ],
        "@graph": [
            {
                "@id": "http://example.org/test/#library",
                "@type": "ex:Library",
                "ex:contains": {
                    "@id": "http://example.org/test#book",
                    "@type": "ex:Book",
                    "dc:contributor": "Writer",
                    "dc:title": "My Book",
                    "ex:contains": {
                        "@id": "http://example.org/test#chapter",
                        "@type": "ex:Chapter",
                        "dc:description": "Fun",
                        "dc:title": "Chapter One",
                    },
                },
            }
        ],
    }

    framed = _frame_with_remote_context(
        FRAME_0001_IN,
        FRAME_0001_FRAME_WITH_PARTIAL_CONTEXT,
        FRAME_0001_FRAME_PARTIAL_CONTEXT,
    )

    assert framed == expected


# Issue 59 - PR: https://github.com/digitalbazaar/pyld/pull/60
def test_do_not_compact_dates_without_datatype():
    """
    Dates without explicit datatype should not be compacted during framing,
    """
    input = {
        "http://schema.org/name": "Buster the Cat",
        "http://schema.org/birthDate": "2012",
        "http://schema.org/deathDate": "2015-02-25",
    }

    frame = {"@context": "https://schema.org/"}

    expected = {
        "@context": "https://schema.org/",
        "name": "Buster the Cat",
        "schema:birthDate": "2012",
        "schema:deathDate": "2015-02-25",
    }

    def loader(url, options):
        if url == "https://schema.org/":
            return {
                "contextUrl": None,
                "document": SCHEMA_ORG_DATE_CONTEXT,
                "documentUrl": url,
                "contentType": "application/ld+json",
            }
        raise Exception(f"Unknown URL: {url}")

    framed = jsonld.frame(input, frame, options={"documentLoader": loader})

    assert framed == expected


def test_compact_dates_with_datatype():
    """
    Dates with explicit datatype should be compacted during framing.
    """
    input = {
        "http://schema.org/name": "Buster the Cat",
        "http://schema.org/birthDate": {
            "@value": "2012",
            "@type": "http://schema.org/Date",
        },
        "http://schema.org/deathDate": {
            "@value": "2015-02-25",
            "@type": "http://schema.org/Date",
        },
    }

    frame = {"@context": "https://schema.org/"}

    expected = {
        "@context": "https://schema.org/",
        "name": "Buster the Cat",
        "birthDate": "2012",
        "deathDate": "2015-02-25",
    }

    def loader(url, options):
        if url == "https://schema.org/":
            return {
                "contextUrl": None,
                "document": SCHEMA_ORG_DATE_CONTEXT,
                "documentUrl": url,
                "contentType": "application/ld+json",
            }
        raise Exception(f"Unknown URL: {url}")

    framed = jsonld.frame(input, frame, options={"documentLoader": loader})

    assert framed == expected

def test_circular_references_link_and_embed():
    input = {
        "@context": "http://schema.org/",
        "@type": "Person",
        "name": "Jane Doe",
        "jobTitle": "Professor",
        "telephone": "(425) 123-4567",
        "@id": "http://www.janedoe.com",
        "knows": {
            "name": "John Smith",
            "@type": "Person",
            "@id": "http://www.johnsmith.me",
            "knows": {"@id": "http://www.janedoe.com"},
        },
    }

    expected = {
        "@context": "http://schema.org",
        "@graph": [
            {
                "id": "http://www.janedoe.com",
                "type": "Person",
                "jobTitle": "Professor",
                "knows": {
                    "id": "http://www.johnsmith.me",
                    "type": "Person",
                    "knows": {"id": "http://www.janedoe.com"},
                    "name": "John Smith",
                },
                "name": "Jane Doe",
                "telephone": "(425) 123-4567",
            },
            {
                "id": "http://www.johnsmith.me",
                "type": "Person",
                "knows": {
                    "id": "http://www.janedoe.com",
                    "type": "Person",
                    "jobTitle": "Professor",
                    "knows": {"id": "http://www.johnsmith.me"},
                    "name": "Jane Doe",
                    "telephone": "(425) 123-4567",
                },
                "name": "John Smith",
            },
        ],
    }

    frame = {'@context': 'http://schema.org', '@embed': '@once'}
    assert expected == jsonld.frame(input, frame)

    # this should result in a RuntimeError for exceeding recursion depth
    frame = {'@context': 'http://schema.org', '@embed': '@link'}
    with pytest.raises(RecursionError):
        jsonld.frame(input, frame)
