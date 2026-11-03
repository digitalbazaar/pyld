"""Manifest fixture loading and fallback delegation."""

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from pyld import DocumentLoader
from tests import runtests
from tests.runtests import TestDocumentLoader

BASE = 'https://w3c.github.io/json-ld-api/tests'


@dataclass
class RecordingDocumentLoader(DocumentLoader):
    calls: list = field(default_factory=list)
    document: dict = field(
        default_factory=lambda: {
            'document': {}, 'documentUrl': 'https://example.org/'
        }
    )

    def __call__(self, url, options=None):
        self.calls.append((url, options))
        return self.document


@pytest.fixture
def fixture_test(tmp_path):
    return SimpleNamespace(
        data={},
        base=f'{BASE}/input.jsonld',
        dirname=str(tmp_path),
        manifest=SimpleNamespace(data={'name': 'Local fixtures', 'baseIri': BASE + '/'}),
    )


def test_reads_fixture_text_and_preserves_fragment(fixture_test, tmp_path):
    (tmp_path / 'input.jsonld').write_text('{"@id": "item"}')
    fallback = RecordingDocumentLoader()
    loader = TestDocumentLoader(fixture_test, fallback)

    document = loader(fixture_test.base + '#item', {})

    assert document == {
        'document': '{"@id": "item"}',
        'documentUrl': fixture_test.base + '#item',
        'contentType': 'application/ld+json',
        'contextUrl': None,
    }
    assert fallback.calls == []


@pytest.mark.parametrize('remote_manifest', [False, True])
def test_forwards_options_to_fallback(fixture_test, remote_manifest):
    url = 'https://example.org/document'
    if remote_manifest:
        fixture_test.manifest.data['name'] = 'Remote document'
        url = fixture_test.base
    fallback = RecordingDocumentLoader()
    loader = TestDocumentLoader(fixture_test, fallback)
    options = {'headers': {'Accept': 'application/ld+json'}}

    assert loader(url, options) is fallback.document
    assert fallback.calls == [(url, options)]
    assert fallback.calls[0][1] is options


def test_remote_manifest_run_local_reads_fixture(fixture_test, tmp_path):
    fixture_test.manifest.data['name'] = 'Remote document'
    fixture_test.data['runLocal'] = True
    (tmp_path / 'input.jsonld').write_text('{}')
    fallback = RecordingDocumentLoader()

    result = TestDocumentLoader(fixture_test, fallback)(fixture_test.base)

    assert result['document'] == '{}'
    assert fallback.calls == []


@pytest.mark.parametrize(
    ('options', 'expected_type', 'expected_context', 'expected_filename'),
    [
        ({'contentType': 'text/plain'}, 'text/plain', None, 'input.jsonld'),
        (
            {
                'contentType': 'application/json',
                'httpLink': '<context.jsonld>; rel="http://www.w3.org/ns/json-ld#context"',
            },
            'application/json', 'context.jsonld', 'input.jsonld',
        ),
        (
            {
                'contentType': 'text/plain',
                'httpLink': '<alternate.jsonld>; rel="alternate"; type="application/ld+json"',
            },
            'application/ld+json', None, 'alternate.jsonld',
        ),
        (
            {'httpStatus': 302, 'redirectTo': 'redirect.jsonld'},
            'application/ld+json', None, 'redirect.jsonld',
        ),
    ],
)
def test_applies_manifest_http_metadata(
    fixture_test, tmp_path, options, expected_type, expected_context, expected_filename
):
    fixture_test.data['option'] = options
    (tmp_path / expected_filename).write_text('{"fixture": true}')

    result = TestDocumentLoader(fixture_test, RecordingDocumentLoader())(
        fixture_test.base
    )

    assert result['document'] == '{"fixture": true}'
    assert result['contentType'] == expected_type
    assert result['contextUrl'] == expected_context
    assert result['documentUrl'] == f'{BASE}/{expected_filename}'


def test_relative_fixture_uses_root_manifest_directory(fixture_test, tmp_path, monkeypatch):
    monkeypatch.setattr(runtests, 'ROOT_MANIFEST_DIR', str(tmp_path))
    (tmp_path / 'relative.json').write_text('{}')

    result = TestDocumentLoader(fixture_test, RecordingDocumentLoader())('relative.json')

    assert result['document'] == '{}'
    assert result['documentUrl'] == (tmp_path / 'relative.json').as_uri()
    assert result['contentType'] == 'application/json'
