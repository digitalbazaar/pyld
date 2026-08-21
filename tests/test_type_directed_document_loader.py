"""Tests for TypeDirectedDocumentLoader."""

import json
from pathlib import Path

import pytest

from pyld import (
    FileDocumentLoader,
    FrozenDocumentLoader,
    SchemeDirectedDocumentLoader,
    TypeDirectedDocumentLoader,
    jsonld,
)
from pyld.jsonld import JsonLdError

_CONTEXT_URL = 'https://example.com/context'
_CONTEXT = {'@context': {'name': 'http://schema.org/name'}}
_PERSON = {
    '@context': _CONTEXT_URL,
    'name': 'Ada Lovelace',
}


def test_dispatches_path_to_file_loader(tmp_path):
    """A pathlib.Path is dispatched to the Path loader."""
    path = tmp_path / 'person.jsonld'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')
    loader = TypeDirectedDocumentLoader(
        {
            Path: FileDocumentLoader(),
        }
    )

    result = loader(path, {})

    assert result['contentType'] == 'application/ld+json'
    assert json.loads(result['document']) == _PERSON
    assert result['documentUrl'] == path.resolve().as_uri()


def test_path_subclass_matches_path_registration(tmp_path):
    """A concrete Path subclass matches a Path registration via isinstance."""
    path = tmp_path / 'person.jsonld'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')
    assert type(path) is not Path
    assert isinstance(path, Path)
    loader = TypeDirectedDocumentLoader(
        {
            Path: FileDocumentLoader(),
        }
    )

    result = loader(path, {})

    assert json.loads(result['document']) == _PERSON


def test_dispatches_str_to_nested_scheme_loader():
    """A str URL is dispatched to the str loader (e.g. by-scheme)."""
    http = FrozenDocumentLoader(documents={_CONTEXT_URL: _CONTEXT})
    loader = TypeDirectedDocumentLoader(
        {
            str: SchemeDirectedDocumentLoader(https=http),
        }
    )

    result = loader(_CONTEXT_URL, {})

    assert result['document'] == _CONTEXT
    assert result['documentUrl'] == _CONTEXT_URL


def test_unregistered_type_raises():
    """An unregistered input type raises JsonLdError naming registered types."""
    loader = TypeDirectedDocumentLoader(
        {
            Path: FileDocumentLoader(),
        }
    )

    with pytest.raises(JsonLdError) as exc:
        loader('https://example.com/person.jsonld', {})

    assert exc.value.code == 'loading document failed'
    assert exc.value.type == 'jsonld.InvalidUrl'
    assert exc.value.details['types'] == ['Path']


def test_load_path_with_remote_context(tmp_path):
    """Load a Path whose @context is an https URL via composed loaders."""
    path = tmp_path / 'person.jsonld'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')
    file_loader = FileDocumentLoader()
    http = FrozenDocumentLoader(documents={_CONTEXT_URL: _CONTEXT})
    loader = TypeDirectedDocumentLoader(
        {
            Path: file_loader,
            str: SchemeDirectedDocumentLoader(
                file=file_loader,
                http=http,
                https=http,
            ),
        }
    )

    remote = jsonld.load_document(path, options={'documentLoader': loader})
    expanded = jsonld.expand(
        remote['document'],
        options={
            'documentLoader': loader,
            'base': remote['documentUrl'],
        },
    )

    assert expanded == [{'http://schema.org/name': [{'@value': 'Ada Lovelace'}]}]
