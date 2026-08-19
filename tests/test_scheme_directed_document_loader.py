"""Tests for SchemeDirectedDocumentLoader."""

import json
from pathlib import Path

import pytest

from pyld import (
    FileDocumentLoader,
    FrozenDocumentLoader,
    SchemeDirectedDocumentLoader,
    jsonld,
)
from pyld.jsonld import JsonLdError

_CONTEXT_URL = 'https://example.com/context'
_CONTEXT = {'@context': {'name': 'http://schema.org/name'}}
_PERSON = {
    '@context': _CONTEXT_URL,
    'name': 'Ada Lovelace',
}


def _file_url(path: Path) -> str:
    return path.resolve().as_uri()


def test_dispatches_file_url(tmp_path):
    """A file: URL is dispatched to the file loader."""
    path = tmp_path / 'person.jsonld'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')
    loader = SchemeDirectedDocumentLoader(file=FileDocumentLoader())

    result = loader(_file_url(path), {})

    assert result['contentType'] == 'application/ld+json'
    assert json.loads(result['document']) == _PERSON


def test_dispatches_https_url():
    """An https: URL is dispatched to the https loader."""
    http = FrozenDocumentLoader(documents={_CONTEXT_URL: _CONTEXT})
    loader = SchemeDirectedDocumentLoader(https=http)

    result = loader(_CONTEXT_URL, {})

    assert result['document'] == _CONTEXT
    assert result['documentUrl'] == _CONTEXT_URL


def test_scheme_less_url_raises():
    """A scheme-less URL raises when no empty-scheme loader is registered."""
    loader = SchemeDirectedDocumentLoader(file=FileDocumentLoader())

    with pytest.raises(JsonLdError) as exc:
        loader('/tmp/person.jsonld', {})

    assert exc.value.code == 'loading document failed'
    assert exc.value.details['schemes'] == ['file']


def test_unregistered_scheme_raises():
    """An unregistered scheme raises JsonLdError naming registered schemes."""
    loader = SchemeDirectedDocumentLoader(file=FileDocumentLoader())

    with pytest.raises(JsonLdError) as exc:
        loader('https://example.com/person.jsonld', {})

    assert exc.value.code == 'loading document failed'
    assert exc.value.type == 'jsonld.InvalidUrl'
    assert exc.value.details['schemes'] == ['file']


def test_scheme_matching_is_case_insensitive():
    """Registered scheme keys match uppercase URL schemes."""
    http = FrozenDocumentLoader(documents={_CONTEXT_URL: _CONTEXT})
    loader = SchemeDirectedDocumentLoader(HTTPS=http)

    result = loader(_CONTEXT_URL, {})

    assert result['document'] == _CONTEXT


def test_expand_local_file_with_remote_context(tmp_path):
    """Expand a local file whose @context is an https URL via composed loaders."""
    path = tmp_path / 'person.jsonld'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')
    http = FrozenDocumentLoader(documents={_CONTEXT_URL: _CONTEXT})
    loader = SchemeDirectedDocumentLoader(
        file=FileDocumentLoader(),
        http=http,
        https=http,
    )

    expanded = jsonld.expand(
        _file_url(path),
        options={'documentLoader': loader},
    )

    assert expanded == [{'http://schema.org/name': [{'@value': 'Ada Lovelace'}]}]
