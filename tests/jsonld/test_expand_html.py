import pytest

from pyld import jsonld
from pyld.documentloader.file import FileDocumentLoader


def _expand_html(tmp_path, document, fragment='', **options):
    path = tmp_path / 'document.html'
    path.write_text(document)
    return jsonld.expand(
        path.as_uri() + fragment,
        {'documentLoader': FileDocumentLoader(), **options},
    )


def test_expands_first_yaml_script_and_ignores_later_invalid_scripts(tmp_path):
    assert _expand_html(
        tmp_path,
        '''<script type="application/ld+yaml">
https://example.org/value: first
</script>
<script type="application/ld+yaml">invalid: [</script>
<script type="application/ld+json">invalid</script>''',
    ) == [{'https://example.org/value': [{'@value': 'first'}]}]


def test_fragment_selects_yaml_script_and_ignores_other_scripts(tmp_path):
    assert _expand_html(
        tmp_path,
        '''<script type="application/ld+yaml">invalid: [</script>
<script id="selected" type="application/ld+yaml">
https://example.org/value: selected
</script>''',
        fragment='#selected',
        extractAllScripts=True,
    ) == [{'https://example.org/value': [{'@value': 'selected'}]}]


def test_extracts_mixed_script_types_in_document_order(tmp_path):
    assert _expand_html(
        tmp_path,
        '''<script type="application/ld+yaml">
- https://example.org/value: first
- https://example.org/value: second
</script>
<script type="application/ld+json">
{"https://example.org/value": "third"}
</script>
<script type="application/ld+yaml">null</script>''',
        extractAllScripts=True,
    ) == [
        {'https://example.org/value': [{'@value': value}]}
        for value in ['first', 'second', 'third']
    ]


@pytest.mark.parametrize('extract_all_scripts', [False, True])
def test_empty_yaml_script_expands_to_empty_array(tmp_path, extract_all_scripts):
    assert _expand_html(
        tmp_path,
        '<script type="application/ld+yaml"></script>',
        extractAllScripts=extract_all_scripts,
    ) == []


@pytest.mark.parametrize('extract_all_scripts', [False, True])
def test_unsupported_mime_prefix_does_not_select_script(tmp_path, extract_all_scripts):
    assert _expand_html(
        tmp_path,
        '''<script type="application/ld+yaml-template">invalid: [</script>
<script type="application/ld+json">{"https://example.org/value": "selected"}</script>''',
        extractAllScripts=extract_all_scripts,
    ) == [{'https://example.org/value': [{'@value': 'selected'}]}]


def test_fragment_rejects_unsupported_mime_prefix(tmp_path):
    with pytest.raises(jsonld.JsonLdError) as caught:
        _expand_html(
            tmp_path,
            '<script id="selected" type="application/ld+yaml-template">{}</script>',
            fragment='#selected',
        )
    assert caught.value.code == 'loading document failed'


def test_parameterized_yaml_script_uses_yaml_parser(tmp_path):
    assert _expand_html(
        tmp_path,
        '''<script type='Application/LD+YAML ; CHARSET="UTF-8"'>
https://example.org/value: selected
</script>''',
    ) == [{'https://example.org/value': [{'@value': 'selected'}]}]


@pytest.mark.parametrize('content_type', ['application/ld+json', 'application/ld+yaml'])
def test_profile_selects_matching_script(tmp_path, content_type):
    path = tmp_path / 'document.html'
    path.write_text(
        f'''<script type="application/ld+yaml">invalid: [</script>
<script type="{content_type};profile=https://example.org/profile">
{{"https://example.org/value": "selected"}}
</script>'''
    )
    document = jsonld.load_document(
        path.as_uri(),
        {'documentLoader': FileDocumentLoader()},
        profile='https://example.org/profile',
    )
    assert jsonld.expand(document['document']) == [
        {'https://example.org/value': [{'@value': 'selected'}]}
    ]


@pytest.mark.parametrize('content_type', ['application/ld+json', 'application/ld+yaml'])
def test_profile_matches_exact_iri_in_quoted_parameter(tmp_path, content_type):
    path = tmp_path / 'document.html'
    path.write_text(
        f'''<script type="{content_type};profile=https://example.org/profile-extra">
{{"https://example.org/value": "wrong"}}</script>
<script type='{content_type.upper()}; PROFILE="https://example.org/other https://example.org/profile"'>
{{"https://example.org/value": "selected"}}</script>'''
    )
    document = jsonld.load_document(
        path.as_uri(),
        {'documentLoader': FileDocumentLoader()},
        profile='https://example.org/profile',
    )
    assert jsonld.expand(document['document']) == [
        {'https://example.org/value': [{'@value': 'selected'}]}
    ]


def test_profile_selects_rfc2231_encoded_parameter(tmp_path):
    path = tmp_path / 'document.html'
    path.write_text(
        '''<script type="application/ld+json">invalid</script>
<script type="application/ld+json; profile*=utf-8''https%3A%2F%2Fexample.org%2Fprofile">
{"https://example.org/value": "selected"}</script>'''
    )
    document = jsonld.load_document(
        path.as_uri(),
        {'documentLoader': FileDocumentLoader()},
        profile='https://example.org/profile',
    )
    assert jsonld.expand(document['document']) == [
        {'https://example.org/value': [{'@value': 'selected'}]}
    ]


@pytest.mark.parametrize(
    ('content_type', 'content', 'code'),
    [
        ('application/ld+json', 'invalid', 'invalid script element'),
        ('application/ld+json', '', 'invalid script element'),
        ('application/ld+yaml', 'invalid: [', 'loading document failed'),
        (
            'application/ld+yaml',
            'one: two\n---\nthree: four',
            'loading document failed',
        ),
        ('application/ld+yaml', '1: value', 'mapping-key-error'),
    ],
)
@pytest.mark.parametrize('fragment', ['', '#selected'])
def test_selected_script_reports_format_error(
    tmp_path, content_type, content, code, fragment
):
    with pytest.raises(jsonld.JsonLdError) as caught:
        _expand_html(
            tmp_path,
            f'<script id="selected" type="{content_type}">{content}</script>',
            fragment=fragment,
        )
    assert caught.value.code == code
