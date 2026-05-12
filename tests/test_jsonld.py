import pytest

import pyld.jsonld as jsonld


def raise_this(value):
    raise ValueError(value)


class TestExpand:
    # Issue 50 - PR: https://github.com/digitalbazaar/pyld/pull/51
    def test_silently_ignored(self):
        """
        Simple example with keys not in the context should silently ignore
        dropped keys during expansion when no on_property_dropped handler was
        passed.
        """
        input = {"fooo": "bar"}
        context = {"foo": {"@id": "http://example.com/foo"}}
        got = jsonld.expand(input, {"expandContext": context, "base": None})
        assert got == []

    def test_silently_ignored_complex(self):
        """
        Complex example with keys not in the context should silently ignore
        dropped keys during expansion when no on_property_dropped handler was
        passed.
        """
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
        got = jsonld.expand(input, {"expandContext": context, "base": None})
        assert got == expected

    def test_dropped_keys_fails(self):
        """
        Simple example with keys not in the context should fail during
        expansion when on_property_dropped handler raises error.
        """
        input = {"fooo": "bar"}
        context = {"foo": {"@id": "http://example.com/foo"}}
        with pytest.raises(ValueError):
            jsonld.expand(
                input,
                {"expandContext": context, "base": None},
                on_property_dropped=raise_this,
            )

    def test_dropped_keys_fails_complex(self):
        """
        Complex example with keys not in the context should fail during
        expansion when on_property_dropped handler raises error.
        """
        input = {
            "@id": "foo",
            "foo": "bar",
            "fooo": "baz",
            "http://example.com/other": "blah",
        }
        context = {"foo": {"@id": "http://example.com/foo"}}
        with pytest.raises(ValueError):
            jsonld.expand(
                input,
                {"expandContext": context, "base": None},
                on_property_dropped=raise_this,
            )

    def test_dropped_keys(self):
        """
        Simple example with keys not in the context should correctly store
        dropped keys during expansion using the on_property_dropped handler.
        """
        input = {"fooo": "bar"}
        context = {"foo": {"@id": "http://example.com/foo"}}
        dropped_keys = set()
        got = jsonld.expand(
            input,
            {"expandContext": context, "base": None},
            on_property_dropped=dropped_keys.add,
        )
        assert got == []
        assert dropped_keys == {"fooo"}

    def test_dropped_keys_complex(self):
        """
        Complex example with keys not in the context should correctly store
        dropped keys during expansion using the on_property_dropped handler.
        """
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
        got = jsonld.expand(
            input,
            {"expandContext": context, "base": None},
            on_property_dropped=dropped_keys.add,
        )
        assert got == expected
        assert dropped_keys == {"fooo"}

    # Issue 187
    def test_missing_base(self):
        """
        Document where `@base` is absent or explicitely set to `null` should
        use the default base IRI 'http://example.org/base/'
        when no base parameter is set during expansion .
        """
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
                "@id": "http://example.org/document-relative",
                "@type": ["http://example.org/base/#document-relative"],
                "http://example.com/vocab#property": [
                    {
                        "@id": "http://example.org/document-base-overwritten",
                        "@type": ["http://example.org/test/#document-base-overwritten"],
                        "http://example.com/vocab#property": [
                            {
                                "@id": "http://example.org/document-relative",
                                "@type": ["http://example.org/base/#document-relative"],
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

    def test_base_does_not_expand_property_terms(self):
        """
        Regression test: @base must not be used to expand property keys.

        Property names are expanded vocabulary-relative: @vocab, term
        definitions, compact IRIs with a defined prefix, etc. The active
        context's @base is for document-relative IRI resolution where the
        algorithms pass that flag (e.g. certain @id and @type values), not
        for turning arbitrary keys into absolute IRIs. Here the context sets
        only @base; `name` has no term definition and no @vocab, so it
        cannot become an absolute property IRI and must be dropped.

        See: https://www.w3.org/TR/json-ld11-api/#iri-expansion
        """
        doc = {
            '@context': {'@base': 'https://schema.org/'},
            '@id': 'https://w3.org/yaml-ld/',
            '@type': 'WebContent',
            'name': 'YAML-LD',
        }
        result = jsonld.expand(doc)
        # `name` has no vocabulary-relative mapping (@vocab or term
        # definition); @base must not supply one. The key is dropped.
        assert result == [
            {
                '@id': 'https://w3.org/yaml-ld/',
                '@type': ['https://schema.org/WebContent'],
            }
        ]


    def _make_context(self, num_terms):
        """Build a context with `num_terms` @type:@vocab terms sharing a scoped context."""
        ctx = {"ex": "https://example.org/"}

        # A context with multiple terms sharing the same scoped @context.
        # This triggers the bug: the first scoped context pre-validation caches
        # a result with partial mappings, and subsequent expansion-time lookups
        # get a stale cache hit.
        shared_scoped_ctx = {
            "@vocab": "https://example.org/",
            "text": "http://www.w3.org/2004/02/skos/core#notation",
            "description": "http://www.w3.org/2004/02/skos/core#prefLabel",
            "meaning": "@id",
        }
        for i in range(num_terms):
            ctx[f"EnumProp{i}"] = {
                "@id": f"ex:EnumProp{i}",
                "@type": "@vocab",
                "@context": dict(shared_scoped_ctx),
            }
        # Add some plain string terms to increase context size
        for i in range(80):
            ctx[f"prop{i}"] = f"ex:prop{i}"
        return ctx


    def test_single_vocab_term_expands_correctly(self):
        """Single @type:@vocab term should expand bare string to @id."""
        ctx = {
            "ex": "https://example.org/",
            "Color": {
                "@id": "ex:Color",
                "@type": "@vocab",
                "@context": {"@vocab": "https://example.org/"},
            },
        }
        doc = {"@context": ctx, "Color": "Red"}
        result = jsonld.expand(doc)
        assert result[0]["https://example.org/Color"] == [{"@id": "https://example.org/Red"}]


    def test_many_shared_scoped_contexts_expand_correctly(self):
        """
        Regression test for scoped context cache pollution during context processing.

        When a JSON-LD context has multiple terms that share the same scoped @context
        (e.g., enum-typed properties using @type: @vocab with a scoped @vocab), the
        pre-validation of scoped contexts during _process_context would cache the
        processed result keyed by rval['_uuid']. Since rval is mutated (mappings added)
        during the loop, later expansion-time lookups of the same scoped context would
        get a stale cache hit with incomplete mappings, causing @type coercion to fail.

        The fix regenerates rval['_uuid'] after all term definitions are created,
        ensuring expansion-time lookups miss the pre-validation cache.

        Multiple @type:@vocab terms with identical scoped contexts should all expand.
        """
        ctx = self._make_context(num_terms=30)
        doc = {"@context": ctx}
        # Set a value for each enum property
        for i in range(30):
            doc[f"EnumProp{i}"] = f"Value{i}"

        result = jsonld.expand(doc)
        expanded = result[0]

        for i in range(30):
            prop_iri = f"https://example.org/EnumProp{i}"
            assert prop_iri in expanded, f"EnumProp{i} not in expanded result"
            assert expanded[prop_iri] == [{"@id": f"https://example.org/Value{i}"}], (
                f"EnumProp{i} did not expand to @id"
            )


    def test_last_vocab_term_expands_with_large_context(self):
        """The LAST @type:@vocab term in a large context must also expand correctly.

        This is the most likely to fail because all prior scoped context
        pre-validations have already populated the cache.
        """
        ctx = self._make_context(num_terms=27)
        # Only test the last term
        doc = {"@context": ctx, "EnumProp26": "TestValue"}
        result = jsonld.expand(doc)
        assert result[0]["https://example.org/EnumProp26"] == [{"@id": "https://example.org/TestValue"}]


    def test_structured_value_still_works_with_scoped_context(self):
        """Structured values (objects) should still use the scoped context mappings."""
        ctx = self._make_context(num_terms=10)
        doc = {
            "@context": ctx,
            "EnumProp5": {
                "text": "MyLabel",
                "description": "A description",
                "meaning": "https://example.org/SomeValue",
            },
        }
        result = jsonld.expand(doc)
        prop_val = result[0]["https://example.org/EnumProp5"][0]
        # text -> skos:notation
        assert "http://www.w3.org/2004/02/skos/core#notation" in prop_val
        # meaning -> @id
        assert "@id" in prop_val


    def test_mixed_plain_and_vocab_terms(self):
        """Contexts with both plain and @type:@vocab terms should work correctly."""
        ctx = {
            "ex": "https://example.org/",
            "name": "ex:name",
            "Color": {
                "@id": "ex:Color",
                "@type": "@vocab",
                "@context": {"@vocab": "https://example.org/"},
            },
            "Shape": {
                "@id": "ex:Shape",
                "@type": "@vocab",
                "@context": {"@vocab": "https://example.org/"},
            },
        }
        # Add many plain terms to make context large enough to trigger caching
        for i in range(100):
            ctx[f"field{i}"] = f"ex:field{i}"

        doc = {
            "@context": ctx,
            "name": "test",
            "Color": "Blue",
            "Shape": "Circle",
        }
        result = jsonld.expand(doc)
        expanded = result[0]
        assert expanded["https://example.org/Color"] == [{"@id": "https://example.org/Blue"}]
        assert expanded["https://example.org/Shape"] == [{"@id": "https://example.org/Circle"}]
        assert expanded["https://example.org/name"] == [{"@value": "test"}]


class TestFrame:
    # Issue 11 - PR: https://github.com/digitalbazaar/pyld/issues/149
    """
    Example with @id alias in an inner context should not change when framing.
    """

    def test_processing_id_in_inner_context(self):
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

    def _frame_with_remote_context(self, input, frame, context):
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

    def test_remote_context_local_and_remote_context_equal(self):
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

        framed = self._frame_with_remote_context(
            self.FRAME_0001_IN, self.FRAME_0001_FRAME, self.FRAME_0001_FRAME_CONTEXT
        )

        assert framed == expected

    def test_remote_context_remote_context_only(self):
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

        framed = self._frame_with_remote_context(
            self.FRAME_0001_IN,
            self.FRAME_0001_FRAME_WITHOUT_CONTEXT,
            self.FRAME_0001_FRAME_CONTEXT,
        )

        assert framed == expected

    def test_remote_context_half_context_local_and_half_remote(self):
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

        framed = self._frame_with_remote_context(
            self.FRAME_0001_IN,
            self.FRAME_0001_FRAME_WITH_PARTIAL_CONTEXT,
            self.FRAME_0001_FRAME_PARTIAL_CONTEXT,
        )

        assert framed == expected

    # Issue 59 - PR: https://github.com/digitalbazaar/pyld/pull/60
    @pytest.mark.network
    def test_do_not_compact_dates_without_datatype(self):
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

        framed = jsonld.frame(input, frame)
        assert framed == expected

    @pytest.mark.network
    def test_compact_dates_with_datatype(self):
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

        framed = jsonld.frame(input, frame)
        assert framed == expected


class TestToRdf:
    # PR: https://github.com/digitalbazaar/pyld/pull/202

    def test_double_and_float_values(self):
        """
        String values with @type: "xsd:double" should be converted to float value during to_rdf.
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
    def test_compaction_with_and_without_explicit_datatypes(self):
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
    def test_compact_prefers_shortest_term(self):
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

    def test_compact_shortest_wins_over_underscore_prefix(self):
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

    def test_compact_same_length_uses_lexicographic_tiebreak(self):
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

    def test_index_map_with_compact_iri_index_round_trips(self):
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

    def test_reverse_index_map_with_term_index_uses_property_value_as_key(self):
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

    def test_node_reference_compacts_to_string_value_of_type_map(self):
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

    def test_empty_property_scoped_context_preserves_outer_terms(self):
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
    def test_empty_context(self):
        """
        Compacting with an empty context should return the input unchanged.
        """
        input = {'http://schema.org/codeRepository': {'@id': 'http:'}}
        compacted = jsonld.compact(input, {})
        assert compacted == input

    # Issue 82
    def test_no_initial_context_drops_property(self):
        """
        Compacting without initial context should drop the original input.
        """

        input = {'name': 'Bob'}

        compacted = jsonld.compact(input, {"@vocab": "http://example.org#"})
        expected = {"@context": {"@vocab": "http://example.org#"}}

        assert compacted == expected

    @pytest.mark.xfail
    def test_no_initial_context_and_with_skip_expand_does_not_drop_property_whe_not_array(self):
        """
        Compacting document with singular value and without initial context should
        output the original input when skipExpansion is enabled.
        """

        input = {'name': 'Bob'}

        compacted = jsonld.compact(input, {"@vocab": "http://example.org#"}, {"skipExpansion": True})
        expected = {"@context": {"@vocab": "http://example.org#"}, "name": "Bob"}
        assert compacted == expected

    def test_no_initial_context_and_with_skip_expand_does_not_drop_property_when_array(self):
        """
        Compacting document with array value and without initial context should
        output the original input when skipExpansion is enabled.
        """

        input = {'name': ['Bob']}

        compacted = jsonld.compact(input, {"@vocab": "http://example.org#"}, {"skipExpansion": True})
        expected = {"@context": {"@vocab": "http://example.org#"}, "name": "Bob"}
        assert compacted == expected

    # Issue 83
    def test_with_vocab_no_id(self):
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

    def test_with_vocab_with_id(self):
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
