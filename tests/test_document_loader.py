"""
Tests for document loaders: Accept header content negotiation and Link rel=alternate.

- PR #170: load_document and Accept header content negotiation (e.g. ActivityStreams).
- Issue #128: When a context URL returns non-JSON-LD (e.g. text/html), the loader must
  follow a Link header with rel="alternate" and type="application/ld+json" to get the
  actual JSON-LD. Example: https://schema.org responds with text/html and provides the
  JSON-LD context via Link: </docs/jsonldcontext.jsonld>; rel="alternate"; type="application/ld+json"
"""

import pytest

from pyld import jsonld


@pytest.mark.network
def test_activitystreams_context_loads_as_json():
    """
    The ActivityStreams context URL should return JSON-LD, not the HTML spec.

    This was the original bug report for PR #170.

    This test requires network access and may be slow or flaky.
    """
    options = {'documentLoader': jsonld.requests_document_loader()}

    result = jsonld.load_document('https://www.w3.org/ns/activitystreams', options)

    # Should be JSON-LD context, not HTML spec
    assert isinstance(result['document'], dict)
    assert '@context' in result['document']


# Minimal JSON-LD document that uses https://schema.org as context.
# schema.org serves text/html with Link rel="alternate" to the JSON-LD context.
_DOC_CONTEXT_VIA_LINK_ALTERNATE = {
    "@context": "https://schema.org",
    "@type": "Person",
    "name": "Jane Doe",
    "jobTitle": "Professor",
    "telephone": "(425) 123-4567",
    "url": "http://www.janedoe.com",
}


def _expand_with_loader(loader):
    """Expand _DOC_CONTEXT_VIA_LINK_ALTERNATE with the given loader."""
    return jsonld.expand(
        _DOC_CONTEXT_VIA_LINK_ALTERNATE,
        options={"documentLoader": loader},
    )


def _assert_expanded_link_alternate_result(result):
    """Verify expansion produced the expected structure (context loaded via Link rel=alternate)."""
    assert isinstance(result, list)
    assert len(result) == 1
    item = result[0]
    assert "http://schema.org/name" in item
    assert item["http://schema.org/name"] == [{"@value": "Jane Doe"}]
    assert "@type" in item
    assert "http://schema.org/Person" in item["@type"]


_LOADERS = {
    "requests": jsonld.requests_document_loader,
    "aiohttp": jsonld.aiohttp_document_loader,
}


@pytest.fixture(params=["requests", "aiohttp"])
def document_loader(request):
    """Parametrizing fixture: yields requests and aiohttp document loaders."""
    return _LOADERS[request.param]()


@pytest.mark.network
def test_remote_context_via_link_alternate(document_loader):
    """
    When context URL returns non-JSON-LD (e.g. text/html) with Link rel=alternate
    type=application/ld+json, the loader follows that link to load the context.
    """
    result = _expand_with_loader(document_loader)
    _assert_expanded_link_alternate_result(result)
