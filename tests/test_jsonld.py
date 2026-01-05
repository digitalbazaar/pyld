import pytest

import pyld.jsonld as jsonld

def raise_this(value):
    raise ValueError(value)

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

    def test_dropped_keys_fails(self):
        input = {"fooo": "bar"}
        context = {"foo": {"@id": "http://example.com/foo"}}
        with pytest.raises(ValueError):
            jsonld.expand(input, {"expandContext": context}, on_key_dropped=raise_this)

    def test_dropped_keys_fails_complex(self):
        input = {
            "@id": "foo",
            "foo": "bar",
            "fooo": "baz",
            "http://example.com/other": "blah",
        }
        context = {"foo": {"@id": "http://example.com/foo"}}
        with pytest.raises(ValueError):
            jsonld.expand(input, {"expandContext": context}, on_key_dropped=raise_this)

    def test_dropped_keys(self):
        input = {"fooo": "bar"}
        context = {"foo": {"@id": "http://example.com/foo"}}
        dropped_keys = set()
        got = jsonld.expand(input, {"expandContext": context}, on_key_dropped=dropped_keys.add)
        assert got == []
        assert dropped_keys == {"fooo"}

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
        dropped_keys = set()
        got = jsonld.expand(input, {"expandContext": context}, on_key_dropped=dropped_keys.add)
        assert got == expected
        assert dropped_keys == {"fooo"}

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

        options = dict(expandContext=context, base="https://hotecosystem.org/termci/")

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

    def _test_remote_context_with(self, input, frame, context, expected):
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
                raise Exception("Unknown URL: {}".format(url))

        options = {"documentLoader": fake_loader, "omitGraph": False}
        framed = jsonld.frame(input, "http://example.com/frame.json", options=options)

        assert framed == expected

    def test_remote_context_local_and_remote_context_equal(self):
        self._test_remote_context_with(
            self.FRAME_0001_IN,
            self.FRAME_0001_FRAME,
            self.FRAME_0001_FRAME_CONTEXT,
            self.FRAME_0001_OUT_WITH_LOCAL_AND_REMOTE_CONTEXT,
        )

    def test_remote_context_remote_context_only(self):
        self._test_remote_context_with(
            self.FRAME_0001_IN,
            self.FRAME_0001_FRAME_WITHOUT_CONTEXT,
            self.FRAME_0001_FRAME_CONTEXT,
            self.FRAME_0001_OUT_WITH_REMOTE_CONTEXT,
        )

    def test_remote_context_half_context_local_and_half_remote(self):
        self._test_remote_context_with(
            self.FRAME_0001_IN,
            self.FRAME_0001_FRAME_WITH_PARTIAL_CONTEXT,
            self.FRAME_0001_FRAME_PARTIAL_CONTEXT,
            self.FRAME_0001_OUT_WITH_HALF_LOCAL_AND_HALF_REMOTE_CONTEXT,
        )

    # Issue 59 - PR: https://github.com/digitalbazaar/pyld/pull/60
    def test_do_not_compact_dates_without_datatype(self):
        input = {
            "http://schema.org/name": "Buster the Cat",
            "http://schema.org/birthDate": "2012",
            "http://schema.org/deathDate": "2015-02-25",
        }

        frame = {"@context": "https://schema.org/docs/jsonldcontext.jsonld"}

        expected = {
            "@context": "https://schema.org/docs/jsonldcontext.jsonld",
            "name": "Buster the Cat",
            "schema:birthDate": "2012",
            "schema:deathDate": "2015-02-25",
        }

        framed = jsonld.frame(input, frame)
        assert framed == expected

    def test_compact_dates_with_datatype(self):
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

        frame = {"@context": "https://schema.org/docs/jsonldcontext.jsonld"}

        expected = {
            "@context": "https://schema.org/docs/jsonldcontext.jsonld",
            "name": "Buster the Cat",
            "birthDate": "2012",
            "deathDate": "2015-02-25",
        }

        framed = jsonld.frame(input, frame)
        assert framed == expected


class TestToRdf:
    # PR: https://github.com/digitalbazaar/pyld/pull/202

    def test_double_and_float_values(self):
        """
        Test case for to_rdf functionality with double/float values.
        String values with @type: "xsd:double" should be converted to float.
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
                    "subject": {
                        "type": "IRI",
                        "value": "ex:1",
                    },
                    "predicate": {
                        "type": "IRI",
                        "value": "ex:p",
                    },
                    "object": {
                        "type": "literal",
                        "value": "4.5E1",
                        "datatype": "http://www.w3.org/2001/XMLSchema#double",
                    },
                }
            ]
        }

        result = jsonld.to_rdf(input)
        assert result == expected


class TestCompact:
    # Issue 59 - PR: https://github.com/digitalbazaar/pyld/pull/60

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
