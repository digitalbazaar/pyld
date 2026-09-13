"""Tests for FrozenDocumentLoader and its bundled context set."""

import json
from pathlib import Path

import pytest

from pyld import (
    BUNDLED_CONTEXTS,
    DocumentLoader,
    FrozenDocumentLoader,
    jsonld,
)
from pyld.jsonld import JsonLdError

_URL = 'https://example.com/ctx'
_INLINE_DOC = {'@context': {'name': 'http://schema.org/name'}}


def test_loader_returns_remote_document_for_dict_entry():
    """Inline documents are returned as JSON-LD remote documents."""
    loader = FrozenDocumentLoader(documents={_URL: _INLINE_DOC})
    result = loader(_URL, {})
    assert result == {
        'contentType': 'application/ld+json',
        'contextUrl': None,
        'documentUrl': _URL,
        'document': _INLINE_DOC,
    }


def test_loader_reads_and_parses_path_entry(tmp_path):
    """Path entries are read lazily and parsed as JSON when requested."""
    payload = {'@context': {'foo': 'http://example.com/foo'}}
    file = tmp_path / 'ctx.jsonld'
    file.write_text(json.dumps(payload), encoding='utf-8')

    loader = FrozenDocumentLoader(documents={_URL: file})
    result = loader(_URL, {})

    assert result['document'] == payload
    assert result['documentUrl'] == _URL


def test_path_entries_are_cached_in_place(tmp_path, monkeypatch):
    """Parsed path entries are cached after the first successful load."""
    payload = {'@context': {'foo': 'http://example.com/foo'}}
    file = tmp_path / 'ctx.jsonld'
    file.write_text(json.dumps(payload), encoding='utf-8')

    loader = FrozenDocumentLoader(documents={_URL: file})

    read_calls = 0
    real_read_text = Path.read_text

    def counting_read_text(self, *args, **kwargs):
        nonlocal read_calls
        read_calls += 1
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', counting_read_text)

    loader(_URL, {})
    loader(_URL, {})

    assert read_calls == 1
    assert loader.documents[_URL] == payload
    assert not isinstance(loader.documents[_URL], Path)


def test_callers_mapping_is_not_mutated(tmp_path):
    """Loader-owned caching does not mutate the caller's original mapping."""
    file = tmp_path / 'ctx.jsonld'
    file.write_text(json.dumps({'@context': {}}), encoding='utf-8')
    caller_mapping = {_URL: file}

    loader = FrozenDocumentLoader(documents=caller_mapping)
    loader(_URL, {})

    assert caller_mapping[_URL] is file
    assert isinstance(caller_mapping[_URL], Path)


def test_unknown_url_raises_load_document_error():
    """URLs outside the allowlist fail with PyLD's load-document error code."""
    loader = FrozenDocumentLoader(documents={})
    with pytest.raises(JsonLdError) as exc:
        loader('https://example.com/unknown', {})
    assert exc.value.code == 'loading document failed'
    assert exc.value.type == 'jsonld.LoadDocumentError'


def test_end_to_end_expand_with_bundled_context():
    """Bundled contexts can be used by jsonld.expand without network access."""
    loader = FrozenDocumentLoader()
    doc = {
        '@context': 'https://www.w3.org/ns/did/v1',
        'id': 'did:example:123',
        'authentication': ['did:example:123#key-1'],
    }
    expanded = jsonld.expand(doc, options={'documentLoader': loader})
    assert expanded[0]['@id'] == 'did:example:123'
    assert any(k.endswith('authenticationMethod') for k in expanded[0])


def test_bundled_contexts_are_valid_jsonld_files():
    """Every bundled context entry points to an existing JSON-LD context file."""
    assert len(BUNDLED_CONTEXTS) == 8
    for url, path in BUNDLED_CONTEXTS.items():
        assert isinstance(path, Path), url
        assert path.exists(), f'missing bundled file for {url}: {path}'
        payload = json.loads(path.read_text(encoding='utf-8'))
        assert '@context' in payload, f'no @context in bundled file for {url}'


def test_document_loader_base_class_is_abstract():
    """The base class documents the class-loader interface without instantiation."""
    with pytest.raises(TypeError):
        DocumentLoader()
