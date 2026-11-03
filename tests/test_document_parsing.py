"""Shared format selection for processor documents and test fixtures."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from pyld.document_parsing import (
    content_type_from_path,
    parse_content_type,
    parse_document,
    parse_document_text,
)
from tests.runtests import read_test_property


@pytest.mark.parametrize(
    ('filename', 'content_type', 'document'),
    [
        ('document.jsonld', 'application/ld+json', '{"value": "item"}'),
        ('document.json', 'application/json', '{"value": "item"}'),
        ('document.yamlld', 'application/ld+yaml', 'value: item\n'),
        ('document.yaml', 'application/ld+yaml', 'value: item\n'),
    ],
)
def test_structured_formats_share_processor_and_fixture_parsing(
    tmp_path, filename, content_type, document
):
    (tmp_path / filename).write_text(document)
    fixture_test = SimpleNamespace(data={'expect': filename}, dirname=str(tmp_path))
    remote_document = {
        'document': document,
        'contentType': content_type,
        'documentUrl': 'https://example.org/document',
        'contextUrl': 'https://example.org/context',
        'tag': {'version': 1},
    }

    parsed_document = parse_document(remote_document)

    assert content_type_from_path(Path(filename)) == content_type
    assert parsed_document == {**remote_document, 'document': {'value': 'item'}}
    assert parsed_document is not remote_document
    assert remote_document['document'] == document
    assert parsed_document['tag'] is remote_document['tag']
    assert read_test_property('expect')(fixture_test) == {'value': 'item'}


@pytest.mark.parametrize(
    'filename', ['result.nq', 'result.html', 'result.htm', 'result.xhtml', 'result.txt']
)
def test_unstructured_fixtures_retain_raw_text(tmp_path, filename):
    document = '<https://example.org/subject> <https://example.org/predicate> "item" .\n'
    (tmp_path / filename).write_text(document)
    fixture_test = SimpleNamespace(data={'expect': filename}, dirname=str(tmp_path))

    assert read_test_property('expect')(fixture_test) == document


def test_unknown_media_type_keeps_json_fallback():
    assert parse_document_text('{"value": "item"}', 'application/octet-stream') == {
        'value': 'item'
    }


def test_content_type_normalizes_essence_and_decodes_profile():
    assert parse_content_type(
        'Application/LD+YAML ; PROFILE="https://example.org/one https://example.org/two"'
    ) == (
        'application/ld+yaml',
        'https://example.org/one https://example.org/two',
    )
    assert parse_document_text(
        'value: item\n', 'Application/LD+YAML ; CHARSET="UTF-8"'
    ) == {'value': 'item'}
    assert parse_content_type(
        "application/ld+json; profile*=utf-8''https%3A%2F%2Fexample.org%2Fprofile"
    ) == ('application/ld+json', 'https://example.org/profile')


def test_unknown_extension_has_no_registered_format():
    assert content_type_from_path(Path('result.nq')) is None


@pytest.mark.parametrize(
    ('filename', 'content_type'),
    [
        ('document.JSONLD', 'application/ld+json'),
        ('document.YAMLLD', 'application/ld+yaml'),
        ('document.YAML', 'application/ld+yaml'),
        ('document.HTM', 'text/html'),
        ('document.XHTML', 'application/xhtml+xml'),
    ],
)
def test_extension_lookup_is_case_insensitive(filename, content_type):
    assert content_type_from_path(Path(filename)) == content_type
