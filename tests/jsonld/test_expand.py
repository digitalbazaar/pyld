import pytest

import pyld.jsonld as jsonld


def raise_this(value):
    raise ValueError(value)


# Issue 50 - PR: https://github.com/digitalbazaar/pyld/pull/51
def test_silently_ignored():
    """
    Simple example with keys not in the context should silently ignore
    dropped keys during expansion when no on_property_dropped handler was
    passed.
    """
    input = {"fooo": "bar"}
    context = {"foo": {"@id": "http://example.com/foo"}}
    got = jsonld.expand(input, {"expandContext": context, "base": None})
    assert got == []

def test_silently_ignored_complex():
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

def test_dropped_keys_fails():
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

def test_dropped_keys_fails_complex():
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

def test_dropped_keys():
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

def test_value_object_type_array_fails():
    """
    Value objects must not allow array values for @type during expansion.
    """
    input = {
        "@context": {"ex": "http://example.com/"},
        "ex:prop": {"@value": "value", "@type": ["ex:a", "ex:b"]},
    }

    with pytest.raises(jsonld.JsonLdError) as exc:
        jsonld.expand(input)

    assert exc.value.code == 'invalid typed value'

def test_value_object_type_null_expands():
    """
    Value objects with @type set to null should expand without @type.
    """
    input = {
        "@context": {"ex": "http://example.com/"},
        "ex:prop": {"@value": "value", "@type": None},
    }

    assert jsonld.expand(input) == [
        {"http://example.com/prop": [{"@value": "value"}]}
    ]

def test_context_keyword_redefinition_fails():
    """
    A local context must not define @context as a term.
    """
    input = {
        "@context": {
            "@context": {
                "p": "ex:p",
            },
        },
        "@id": "ex:1",
        "p": "value",
    }

    with pytest.raises(jsonld.JsonLdError) as exc:
        jsonld.expand(input)

    assert exc.value.code == 'keyword redefinition'

def test_dropped_keys_complex():
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
def test_missing_base():
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

def test_base_does_not_expand_property_terms():
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

# Issue 143
def test_expand_with_base_from_context():
    """Expand with set or not should rely upon @base inside its @context."""

    input = {
        "@context": {
            "name": "https://www.exmaple.com/name",
            "@base": "https://www.example.com/",
        },
        "@id": "c/123",
        "name": "alice",
    }
    expected = [
        {
            "@id": "https://www.example.com/c/123",
            "https://www.exmaple.com/name": [{"@value": "alice"}],
        }
    ]
    assert jsonld.expand(input, options={'base': ''}) == expected
    assert jsonld.expand(input) == expected
    assert jsonld.expand(input, options={'base': 'abc'}) == expected

def _make_context(num_terms):
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

def test_single_vocab_term_expands_correctly():
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
    assert result[0]["https://example.org/Color"] == [
        {"@id": "https://example.org/Red"}
    ]

def test_many_shared_scoped_contexts_expand_correctly():
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
    ctx = _make_context(num_terms=30)
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

def test_last_vocab_term_expands_with_large_context():
    """The LAST @type:@vocab term in a large context must also expand correctly.

    This is the most likely to fail because all prior scoped context
    pre-validations have already populated the cache.
    """
    ctx = _make_context(num_terms=27)
    # Only test the last term
    doc = {"@context": ctx, "EnumProp26": "TestValue"}
    result = jsonld.expand(doc)
    assert result[0]["https://example.org/EnumProp26"] == [
        {"@id": "https://example.org/TestValue"}
    ]

def test_structured_value_still_works_with_scoped_context():
    """Structured values (objects) should still use the scoped context mappings."""
    ctx = _make_context(num_terms=10)
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

# Issue 204
def test_scoped_context_on_nest_term_expands_nested_properties():
    """A scoped context on a @nest term should apply to nested properties."""
    input = {
        "@context": {
            "@vocab": "http://example.org/vocab#",
            "p1": {
                "@id": "@nest",
                "@context": {"p2": "http://example.org/ns#P2"},
            },
        },
        "p1": {"p2": "foo"},
    }

    expected = [
        {
            "http://example.org/ns#P2": [
                {
                    "@value": "foo",
                }
            ],
        }
    ]

    result = jsonld.expand(input)

    assert result == expected

# Issue 204
def test_scoped_context_on_nest_term_expands_nested_type_scoped_context():
    """
    A scoped context on a @nest term should be in effect when expanding the
    nested node, including when processing any type-scoped contexts found on
    that node.
    """
    input = {
        "@context": {
            "@vocab": "http://example.org/outer#",
            # p1 is an @nest term with a property-scoped context. That context defines
            # Type and gives Type its own type-scoped context.
            "p1": {
                "@id": "@nest",
                "@context": {
                    # The nested node uses Type and then uses p2 from Type's scoped context.
                    "Type": {
                        "@id": "http://example.org/ns#Type",
                        "@context": {
                            "p2": "http://example.org/ns#P2",
                        },
                    },
                },
            },
        },
        "p1": {
            "@type": "Type",
            "p2": "foo",
        },
    }

    # The @nest term context is active before @type is expanded and before Type's scoped
    # context is applied.
    expected = [
        {
            # If nested values are expanded by directly walking their keys instead of
            # running the normal expansion setup for the nested node, Type and p2 fall
            # back to the outer @vocab.
            "@type": ["http://example.org/ns#Type"],
            "http://example.org/ns#P2": [
                {
                    "@value": "foo",
                }
            ],
        }
    ]

    result = jsonld.expand(input)

    assert result == expected

def test_mixed_plain_and_vocab_terms():
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
    assert expanded["https://example.org/Color"] == [
        {"@id": "https://example.org/Blue"}
    ]
    assert expanded["https://example.org/Shape"] == [
        {"@id": "https://example.org/Circle"}
    ]
    assert expanded["https://example.org/name"] == [{"@value": "test"}]

# Issue 145
def test_context_contained_with_propagate():
    """
    The same context object contained under the node with @propagate
    should properly expand.
    """
    input = {
        "@context": {
            "@propagate": False,
            "a": {
                "@id": "http://abc/a",
                "@context": {"b": "http://abc/b", "c": "http://abc/c"},
            },
            "d": {
                "@id": "http://abc/d",
                "@context": {"b": "http://abc/b", "c": "http://abc/c"},
            },
        },
        "a": {"b": "bb", "c": "cc"},
        "d": {"b": "bbb", "c": "ccc"},
    }

    expected = [
        {
            "http://abc/a": [
                {
                    "http://abc/b": [{"@value": "bb"}],
                    "http://abc/c": [{"@value": "cc"}],
                }
            ],
            "http://abc/d": [
                {
                    "http://abc/b": [{"@value": "bbb"}],
                    "http://abc/c": [{"@value": "ccc"}],
                }
            ],
        }
    ]

    expanded = jsonld.expand(input)
    assert expanded == expected

def test_expand_stringifies_datetime_date_values():
    """
    Non-JSON scalar objects such as datetime.date should get stringified.
    """
    from datetime import date

    expanded = jsonld.expand({
        '@context': {'@vocab': 'https://schema.org/'},
        '@id': 'https://example.blog/post',
        'publicationDate': date(2021, 1, 11),
    })

    assert expanded == [{
        '@id': 'https://example.blog/post',
        'https://schema.org/publicationDate': [{'@value': '2021-01-11'}],
    }]

# Issue 167
def test_blank_node_prefixes():
    """
    Blank nodes as prefix should be used in IRI expansion.
    """
    input = {"@context": {"t": "_:b"}, "@type": "t:x"}

    expected = [{"@type": ["_:bx"]}]

    expanded = jsonld.expand(input)

    assert expanded == expected


# Issue 337
def test_default_direction_survives_context_layers():
    """
    The default @direction should be kept across context layers, like the
    default @language.
    """
    input = {
        "@context": [
            {"@language": "en", "@direction": "rtl"},
            {"dummy": "http://example.com/dummy"},
        ],
        "http://example.com/p": "v",
    }

    expected = [
        {
            "http://example.com/p": [
                {"@language": "en", "@direction": "rtl", "@value": "v"}
            ],
        }
    ]

    expanded = jsonld.expand(input)

    assert expanded == expected

# Issue 337
def test_default_direction_inherited_into_scoped_context():
    """
    A property-scoped context should inherit the default @direction.
    """
    input = {
        "@context": {
            "@language": "en",
            "@direction": "rtl",
            "thing": {
                "@id": "http://example.com/thing",
                "@context": {"other": "http://example.com/other"},
            },
        },
        "thing": {"http://example.com/label": "hello"},
    }

    expected = [
        {
            "http://example.com/thing": [
                {
                    "http://example.com/label": [
                        {
                            "@language": "en",
                            "@direction": "rtl",
                            "@value": "hello",
                        }
                    ],
                }
            ],
        }
    ]

    expanded = jsonld.expand(input)

    assert expanded == expected

# Issue 337
def test_scoped_context_can_override_or_clear_default_direction():
    """
    A scoped @direction entry should still override or clear the default.
    """
    input = {
        "@context": {
            "@direction": "rtl",
            "ltr": {
                "@id": "http://example.com/ltr",
                "@context": {"@direction": "ltr"},
            },
            "none": {
                "@id": "http://example.com/none",
                "@context": {"@direction": None},
            },
        },
        "ltr": {"http://example.com/label": "a"},
        "none": {"http://example.com/label": "b"},
    }

    expected = [
        {
            "http://example.com/ltr": [
                {
                    "http://example.com/label": [
                        {"@direction": "ltr", "@value": "a"}
                    ],
                }
            ],
            "http://example.com/none": [
                {
                    "http://example.com/label": [{"@value": "b"}],
                }
            ],
        }
    ]

    expanded = jsonld.expand(input)

    assert expanded == expected


# Issue 337
def test_default_direction_null_reset_is_noop_when_unset():
    input = {
        "@context": {"@direction": None},
        "http://example.com/p": "v",
    }

    expected = [
        {
            "http://example.com/p": [
                {"@value": "v"},
            ],
        },
    ]

    assert jsonld.expand(input) == expected
