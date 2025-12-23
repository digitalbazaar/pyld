import pytest
import json

import pyld.jsonld as jsonld


class TestExpand:
    # Issue 50 - PR: https://github.com/digitalbazaar/pyld/pull/51
    def test_silently_ignored(self):
        input = {"fooo": "bar"}
        context = {"foo": {"@id": "http://example.com/foo"}}
        got = jsonld.expand(input, {"expandContext": context})
        assert got == []

    def test_silently_ignored_complex(self):
        input = {
            "@id": "foo",
            "foo": "bar",
            "fooo": "baz",
            "http://example.com/other": "blah",
        }
        expected = [
            {
                "@id": "foo",
                "http://example.com/foo": [{"@value": "bar"}],
                "http://example.com/other": [{"@value": "blah"}],
            }
        ]
        context = {"foo": {"@id": "http://example.com/foo"}}
        got = jsonld.expand(input, {"expandContext": context})
        assert got == expected

    def test_strict_fails(self):
        input = {"fooo": "bar"}
        context = {"foo": {"@id": "http://example.com/foo"}}
        with pytest.raises(ValueError):
            jsonld.expand(input, {"expandContext": context, "strict": True})

    def test_strict_fails_complex(self):
        input = {
            "@id": "foo",
            "foo": "bar",
            "fooo": "baz",
            "http://example.com/other": "blah",
        }
        context = {"foo": {"@id": "http://example.com/foo"}}
        with pytest.raises(ValueError):
            jsonld.expand(input, {"expandContext": context, "strict": True})

    def test_dropped_keys(self):
        input = {"fooo": "bar"}
        context = {"foo": {"@id": "http://example.com/foo"}}
        dk = set()
        got = jsonld.expand(input, {"expandContext": context, "droppedKeys": dk})
        assert got == []
        assert dk == {"fooo"}

    def test_dropped_keys_complex(self):
        input = {
            "@id": "foo",
            "foo": "bar",
            "fooo": "baz",
            "http://example.com/other": "blah",
        }
        expected = [
            {
                "@id": "foo",
                "http://example.com/foo": [{"@value": "bar"}],
                "http://example.com/other": [{"@value": "blah"}],
            }
        ]
        context = {"foo": {"@id": "http://example.com/foo"}}
        dk = set()
        got = jsonld.expand(input, {"expandContext": context, "droppedKeys": dk})
        assert got == expected
        assert dk == {"fooo"}

    # Issue 187
    def test_missing_base(self):
        input = {
            "@context": {"property": "http://example.com/vocab#property"},
            "@id": "../document-relative",
            "@type": "#document-relative",
            "property": {
                "@context": {"@base": "http://example.org/test/"},
                "@id": "../document-base-overwritten",
                "@type": "#document-base-overwritten",
                "property": [
                    {
                        "@context": None,
                        "@id": "../document-relative",
                        "@type": "#document-relative",
                        "property": "context completely reset, drops property",
                    },
                    {
                        "@context": {"@base": None},
                        "@id": "../document-relative",
                        "@type": "#document-relative",
                        "property": "only @base is cleared",
                    },
                ],
            },
        }

        expected = [
            {
                "@id": "https://w3c.github.io/json-ld-api/tests/document-relative",
                "@type": [
                    "https://w3c.github.io/json-ld-api/tests/expand/0060-in.jsonld#document-relative"
                ],
                "http://example.com/vocab#property": [
                    {
                        "@id": "http://example.org/document-base-overwritten",
                        "@type": ["http://example.org/test/#document-base-overwritten"],
                        "http://example.com/vocab#property": [
                            {
                                "@id": "https://w3c.github.io/json-ld-api/tests/document-relative",
                                "@type": [
                                    "https://w3c.github.io/json-ld-api/tests/expand/0060-in.jsonld#document-relative"
                                ],
                            },
                            {
                                "@id": "../document-relative",
                                "@type": ["#document-relative"],
                                "http://example.com/vocab#property": [
                                    {"@value": "only @base is cleared"}
                                ],
                            },
                        ],
                    }
                ],
            }
        ]
        got = jsonld.expand(input)
        assert got == expected


class TestFrame:
    # Issue 11 - PR: https://github.com/digitalbazaar/pyld/issues/149

    # Conversion to json-ld: https://tinyurl.com/yyw2ktyf
    # Reverse conversion: https://tinyurl.com/y6fo3clj

    def test_processing_id_with_expand_then_frame(self):
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

        options = dict(
            expandContext=context, base=str("https://hotecosystem.org/termci/")
        )

        # Start with system 'namespace' and contents 'uri'
        assert "namespace" in input["system"][0]
        assert "uri" in input["system"][0]["contents"][0]

        # Take the vanilla JSON and convert it to RDF
        expanded = jsonld.expand(input, options=options)

        # Convert the RDF back into vanilla JSON
        output_json = jsonld.frame(expanded, context, options=options)

        # Observe that system.contents.uri has changed to system.contents.namespace
        assert "namespace" in output_json["system"][0]
        assert "uri" in output_json["system"][0]["contents"][0]

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

    FRAME_0001_OUT_WITH_REMOTE_CONTEXT = {
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

    FRAME_0001_OUT_WITH_LOCAL_AND_REMOTE_CONTEXT = {
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

    FRAME_0001_OUT_WITH_HALF_LOCAL_AND_HALF_REMOTE_CONTEXT = {
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

    def _test_remote_context_with(self, frame_doc, frame_context_doc, out_doc):
        input_ = json.loads(self.FRAME_0001_IN)

        def fake_loader(url, options):
            if url == "http://example.com/frame.json":
                return {
                    "contextUrl": "http://example.com/frame-context.json",
                    "document": frame_doc,
                    "documentUrl": url,
                    "contentType": "application/json+ld",
                }
            elif url == "http://example.com/frame-context.json":
                return {
                    "contextUrl": None,
                    "document": frame_context_doc,
                    "documentUrl": url,
                    "contentType": "application/json+ld",
                }
            else:
                raise Exception("Unknown URL: {}".format(url))

        options = {"documentLoader": fake_loader}
        framed = jsonld.frame(input_, "http://example.com/frame.json", options=options)

        assert framed == json.loads(out_doc)

    def test_remote_context_local_and_remote_context_equal(self):
        self._test_remote_context_with(
            self.FRAME_0001_FRAME,
            self.FRAME_0001_FRAME_CONTEXT,
            self.FRAME_0001_OUT_WITH_LOCAL_AND_REMOTE_CONTEXT,
        )

    def test_remote_context_remote_context_only(self):
        self._test_remote_context_with(
            self.FRAME_0001_FRAME_WITHOUT_CONTEXT,
            self.FRAME_0001_FRAME_CONTEXT,
            self.FRAME_0001_OUT_WITH_REMOTE_CONTEXT,
        )

    def test_remote_context_half_context_local_and_half_remote(self):
        self._test_remote_context_with(
            self.FRAME_0001_FRAME_WITH_PARTIAL_CONTEXT,
            self.FRAME_0001_FRAME_PARTIAL_CONTEXT,
            self.FRAME_0001_OUT_WITH_HALF_LOCAL_AND_HALF_REMOTE_CONTEXT,
        )

    # PR: https://github.com/digitalbazaar/pyld/pull/60
    def test_compact_dates(self):
        input = {
            "http://schema.org/name": "Buster the Cat",
            "http://schema.org/birthDate": "2012",
            "http://schema.org/deathDate": "2015-02-25",
        }

        frame = {"@context": "http://schema.org/"}

        framed = jsonld.frame(input, frame)
        contents = framed["@graph"][0]

        assert "name" in contents  # fine
        assert "birthDate" in contents  # not fine, schema:birthDate instead
        assert "deathDate" in contents  # not fine, schema:deathDate instead


class TestToRdf:
    # PR: https://github.com/digitalbazaar/pyld/pull/202

    def test_offline_pyld_bug_reproduction(self):
        """Test case for to_rdf functionality with double/float values."""
        # This is the exact problematic data structure captured from Wikidata Q399
        # The bug occurs when PyLD tries to convert this to RDF
        input = {
            "@context": {
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "geoLongitude": "http://www.w3.org/2003/01/geo/wgs84_pos#longitude",
            },
            "@graph": [
                {
                    "@id": "http://www.wikidata.org/entity/Q399",
                    "geoLongitude": {
                        "@type": "xsd:double",
                        "@value": "45",  # This string number causes the PyLD bug
                    },
                }
            ],
        }

        # Expected result after bug fix
        expected = {
            "@default": [
                {
                    "subject": {
                        "type": "IRI",
                        "value": "http://www.wikidata.org/entity/Q399",
                    },
                    "predicate": {
                        "type": "IRI",
                        "value": "http://www.w3.org/2003/01/geo/wgs84_pos#longitude",
                    },
                    "object": {
                        "type": "literal",
                        "value": "4.5E1",
                        "datatype": "http://www.w3.org/2001/XMLSchema#double",
                    },
                }
            ]
        }

        # This should work now that the bug is fixed
        # The bug was in PyLD's _object_to_rdf method where string values
        # with @type: "xsd:double" were not being converted to float
        result = jsonld.to_rdf(input)
        assert result == expected


class TestCompact:
    # PR: https://github.com/digitalbazaar/pyld/pull/60

    def test_simple_compaction(self):
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
