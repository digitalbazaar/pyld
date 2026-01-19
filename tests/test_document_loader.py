"""
Tests for load_document function, specifically Accept header content negotiation.

See: https://github.com/digitalbazaar/pyld/pull/170
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
    options = {
        'documentLoader': jsonld.requests_document_loader()
    }
    
    result = jsonld.load_document(
        'https://www.w3.org/ns/activitystreams',
        options
    )
    
    # Should be JSON-LD context, not HTML spec
    assert isinstance(result['document'], dict)
    assert '@context' in result['document']
