"""
Tests for loading JSON-LD contexts served via Link rel="alternate" headers.

https://schema.org responds with text/html and provides the JSON-LD context
via a Link header:

    Link: </docs/jsonldcontext.jsonld>; rel="alternate"; type="application/ld+json"

The document loaders must follow that alternate link to retrieve the actual
JSON-LD context.  See: https://github.com/digitalbazaar/pyld/issues/128
"""
import pytest

from pyld import jsonld


# A minimal JSON-LD document that uses https://schema.org as its context.
# schema.org serves text/html with a Link rel="alternate" pointing to the
# JSON-LD context -- the loaders must follow that link.
SCHEMA_ORG_DOC = {
    "@context": "https://schema.org",
    "@type": "Person",
    "name": "Jane Doe",
    "jobTitle": "Professor",
    "telephone": "(425) 123-4567",
    "url": "http://www.janedoe.com",
}


def _expand_with_loader(loader):
    """Expand SCHEMA_ORG_DOC using the given document loader and return the result."""
    return jsonld.expand(
        SCHEMA_ORG_DOC,
        options={"documentLoader": loader},
    )


def _assert_expanded_correctly(result):
    """Verify the expansion produced the expected structure."""
    assert isinstance(result, list)
    assert len(result) == 1

    item = result[0]
    assert "http://schema.org/name" in item
    assert item["http://schema.org/name"] == [{"@value": "Jane Doe"}]
    assert "@type" in item
    assert "http://schema.org/Person" in item["@type"]


@pytest.mark.network
def test_schema_org_expand_requests():
    """Expand a document whose context is https://schema.org using the requests loader."""
    loader = jsonld.requests_document_loader()
    result = _expand_with_loader(loader)
    _assert_expanded_correctly(result)


@pytest.mark.network
def test_schema_org_expand_aiohttp():
    """Expand a document whose context is https://schema.org using the aiohttp loader."""
    loader = jsonld.aiohttp_document_loader()
    result = _expand_with_loader(loader)
    _assert_expanded_correctly(result)
