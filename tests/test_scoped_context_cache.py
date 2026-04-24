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
"""
from pyld import jsonld


NS = "https://example.org/vocab/"

# A context with multiple terms sharing the same scoped @context.
# This triggers the bug: the first scoped context pre-validation caches
# a result with partial mappings, and subsequent expansion-time lookups
# get a stale cache hit.
SHARED_SCOPED_CTX = {
    "@vocab": NS,
    "text": "http://www.w3.org/2004/02/skos/core#notation",
    "description": "http://www.w3.org/2004/02/skos/core#prefLabel",
    "meaning": "@id",
}


def _make_context(num_terms):
    """Build a context with `num_terms` @type:@vocab terms sharing a scoped context."""
    ctx = {"ex": NS}
    for i in range(num_terms):
        ctx[f"EnumProp{i}"] = {
            "@id": f"ex:EnumProp{i}",
            "@type": "@vocab",
            "@context": dict(SHARED_SCOPED_CTX),
        }
    # Add some plain string terms to increase context size
    for i in range(80):
        ctx[f"prop{i}"] = f"ex:prop{i}"
    return ctx


def test_single_vocab_term_expands_correctly():
    """Single @type:@vocab term should expand bare string to @id."""
    ctx = {
        "ex": NS,
        "Color": {
            "@id": "ex:Color",
            "@type": "@vocab",
            "@context": {"@vocab": NS},
        },
    }
    doc = {"@context": ctx, "Color": "Red"}
    result = jsonld.expand(doc)
    assert result[0][f"{NS}Color"] == [{"@id": f"{NS}Red"}]


def test_many_shared_scoped_contexts_expand_correctly():
    """Multiple @type:@vocab terms with identical scoped contexts should all expand."""
    ctx = _make_context(num_terms=30)
    doc = {"@context": ctx}
    # Set a value for each enum property
    for i in range(30):
        doc[f"EnumProp{i}"] = f"Value{i}"

    result = jsonld.expand(doc)
    expanded = result[0]

    for i in range(30):
        prop_iri = f"{NS}EnumProp{i}"
        assert prop_iri in expanded, f"EnumProp{i} not in expanded result"
        assert expanded[prop_iri] == [{"@id": f"{NS}Value{i}"}], (
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
    assert result[0][f"{NS}EnumProp26"] == [{"@id": f"{NS}TestValue"}]


def test_structured_value_still_works_with_scoped_context():
    """Structured values (objects) should still use the scoped context mappings."""
    ctx = _make_context(num_terms=10)
    doc = {
        "@context": ctx,
        "EnumProp5": {
            "text": "MyLabel",
            "description": "A description",
            "meaning": f"{NS}SomeValue",
        },
    }
    result = jsonld.expand(doc)
    prop_val = result[0][f"{NS}EnumProp5"][0]
    # text -> skos:notation
    assert "http://www.w3.org/2004/02/skos/core#notation" in prop_val
    # meaning -> @id
    assert "@id" in prop_val


def test_mixed_plain_and_vocab_terms():
    """Contexts with both plain and @type:@vocab terms should work correctly."""
    ctx = {
        "ex": NS,
        "name": "ex:name",
        "Color": {
            "@id": "ex:Color",
            "@type": "@vocab",
            "@context": {"@vocab": NS},
        },
        "Shape": {
            "@id": "ex:Shape",
            "@type": "@vocab",
            "@context": {"@vocab": NS},
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
    assert expanded[f"{NS}Color"] == [{"@id": f"{NS}Blue"}]
    assert expanded[f"{NS}Shape"] == [{"@id": f"{NS}Circle"}]
    assert expanded[f"{NS}name"] == [{"@value": "test"}]
