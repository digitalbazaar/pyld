"""Tests for FileDocumentLoader."""

import json
from pathlib import Path
from urllib.request import pathname2url

import pytest

from pyld import FileDocumentLoader, jsonld
from pyld.jsonld import JsonLdError

_PERSON = {
    '@context': {'name': 'http://schema.org/name'},
    'name': 'Ada Lovelace',
}


def _file_url(path: Path, fragment: str | None = None) -> str:
    url = path.resolve().as_uri()
    if fragment:
        return f'{url}#{fragment}'
    return url


def test_loads_jsonld_file(tmp_path):
    """A .jsonld file is returned as raw text with the ld+json content type."""
    path = tmp_path / 'person.jsonld'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')

    result = FileDocumentLoader()(_file_url(path), {})

    assert result['contentType'] == 'application/ld+json'
    assert result['contextUrl'] is None
    assert result['documentUrl'] == _file_url(path)
    assert json.loads(result['document']) == _PERSON


def test_loads_json_file(tmp_path):
    """A .json file is returned with the application/json content type."""
    path = tmp_path / 'person.json'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')

    result = FileDocumentLoader()(_file_url(path), {})

    assert result['contentType'] == 'application/json'
    assert json.loads(result['document']) == _PERSON


def test_scheme_less_path_is_accepted(tmp_path):
    """A scheme-less absolute path is treated as a file URL."""
    path = tmp_path / 'person.jsonld'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')

    result = FileDocumentLoader()(str(path.resolve()), {})

    assert json.loads(result['document']) == _PERSON
    assert result['documentUrl'].startswith('file:')


def test_pathlib_path_is_accepted(tmp_path):
    """A pathlib.Path is accepted and reported as a file URL."""
    path = tmp_path / 'person.jsonld'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')

    result = FileDocumentLoader()(path, {})

    assert json.loads(result['document']) == _PERSON
    assert result['documentUrl'] == path.resolve().as_uri()


def test_percent_encoded_path_with_space(tmp_path):
    """Percent-encoded spaces in a file URL resolve to the on-disk path."""
    path = tmp_path / 'my person.jsonld'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')
    encoded = path.resolve().as_uri()
    assert '%20' in encoded

    result = FileDocumentLoader()(encoded, {})

    assert json.loads(result['document']) == _PERSON


def test_relative_context_resolves_against_document_url(tmp_path):
    """Relative @context references resolve against the file document URL."""
    context = {'@context': {'name': 'http://schema.org/name'}}
    (tmp_path / 'context.jsonld').write_text(json.dumps(context), encoding='utf-8')
    doc = {'@context': 'context.jsonld', 'name': 'Ada Lovelace'}
    doc_path = tmp_path / 'person.jsonld'
    doc_path.write_text(json.dumps(doc), encoding='utf-8')

    loader = FileDocumentLoader()
    expanded = jsonld.expand(
        _file_url(doc_path),
        options={'documentLoader': loader},
    )

    assert expanded == [{'http://schema.org/name': [{'@value': 'Ada Lovelace'}]}]


def test_html_file_extracts_script(tmp_path):
    """An HTML file with a JSON-LD script is extractable via expand."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<script type="application/ld+json">'
        + json.dumps(_PERSON)
        + '</script></head><body></body></html>'
    )
    path = tmp_path / 'person.html'
    path.write_text(html, encoding='utf-8')

    result = FileDocumentLoader()(_file_url(path), {})
    assert result['contentType'] == 'text/html'

    expanded = jsonld.expand(
        _file_url(path),
        options={'documentLoader': FileDocumentLoader()},
    )
    assert expanded == [{'http://schema.org/name': [{'@value': 'Ada Lovelace'}]}]


def test_fragment_selects_html_script(tmp_path):
    """A fragment id selects the matching script element from an HTML file."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<script type="application/ld+json" id="first">'
        + json.dumps(
            {
                '@context': {'name': 'http://schema.org/name'},
                'name': 'First',
            }
        )
        + '</script>'
        '<script type="application/ld+json" id="second">'
        + json.dumps(
            {
                '@context': {'name': 'http://schema.org/name'},
                'name': 'Second',
            }
        )
        + '</script></head><body></body></html>'
    )
    path = tmp_path / 'person.html'
    path.write_text(html, encoding='utf-8')

    expanded = jsonld.expand(
        _file_url(path, fragment='second'),
        options={'documentLoader': FileDocumentLoader()},
    )
    assert expanded == [{'http://schema.org/name': [{'@value': 'Second'}]}]


def test_missing_file_raises_load_document_error(tmp_path):
    """A missing file raises JsonLdError with code loading document failed."""
    missing = tmp_path / 'missing.jsonld'
    with pytest.raises(JsonLdError) as exc:
        FileDocumentLoader()(_file_url(missing), {})
    assert exc.value.code == 'loading document failed'


def test_directory_raises_load_document_error(tmp_path):
    """A directory path raises JsonLdError with code loading document failed."""
    with pytest.raises(JsonLdError) as exc:
        FileDocumentLoader()(_file_url(tmp_path), {})
    assert exc.value.code == 'loading document failed'


def test_unknown_extension_is_refused(tmp_path):
    """An unsupported file extension is refused."""
    path = tmp_path / 'person.txt'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')

    with pytest.raises(JsonLdError) as exc:
        FileDocumentLoader()(_file_url(path), {})
    assert exc.value.code == 'loading document failed'


def test_http_url_is_refused():
    """HTTP URLs are refused by the file-only loader."""
    with pytest.raises(JsonLdError) as exc:
        FileDocumentLoader()('https://example.com/person.jsonld', {})
    assert exc.value.code == 'loading document failed'
    assert exc.value.type == 'jsonld.InvalidUrl'


def test_root_allows_file_inside_root(tmp_path):
    """A file under the configured root is loadable."""
    allowed = tmp_path / 'allowed'
    allowed.mkdir()
    path = allowed / 'person.jsonld'
    path.write_text(json.dumps(_PERSON), encoding='utf-8')

    result = FileDocumentLoader(root=allowed)(_file_url(path), {})
    assert json.loads(result['document']) == _PERSON


def test_root_rejects_parent_traversal(tmp_path):
    """Paths that escape the configured root via .. are refused."""
    root = tmp_path / 'root'
    root.mkdir()
    outside = tmp_path / 'outside.jsonld'
    outside.write_text(json.dumps(_PERSON), encoding='utf-8')

    # Build a file URL whose path contains a .. segment that resolves outside.
    escape = root / 'nested' / '..' / '..' / 'outside.jsonld'
    url = 'file://' + pathname2url(str(escape))

    with pytest.raises(JsonLdError) as exc:
        FileDocumentLoader(root=root)(url, {})
    assert exc.value.code == 'loading document failed'


def test_root_rejects_symlink_escape(tmp_path):
    """A symlink that points outside the configured root is refused."""
    root = tmp_path / 'root'
    root.mkdir()
    outside = tmp_path / 'secret.jsonld'
    outside.write_text(json.dumps(_PERSON), encoding='utf-8')
    link = root / 'escape.jsonld'
    link.symlink_to(outside)

    with pytest.raises(JsonLdError) as exc:
        FileDocumentLoader(root=root)(_file_url(link), {})
    assert exc.value.code == 'loading document failed'
