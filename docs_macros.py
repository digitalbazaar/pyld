import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml
from mkdocs.utils.meta import YAML_RE
from yaml import SafeLoader

ROOT_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = ROOT_DIR / 'docs' / 'examples'
sys.path.insert(0, str(ROOT_DIR / 'lib'))
sys.path.insert(0, str(ROOT_DIR / 'tests'))

MANIFEST_BASES = {
    'frame-manifest': 'https://w3c.github.io/json-ld-framing/tests',
    'manifest-urgna2012': 'https://w3c.github.io/rdf-canon/tests',
    'manifest-urdna2015': 'https://w3c.github.io/rdf-canon/tests',
}
DEFAULT_TEST_BASE = 'https://w3c.github.io/json-ld-api/tests'

_SKIP_ID_PATTERN = re.compile(r'^\.\*(?P<manifest>[^#]+)#(?P<test_id>[^$]+)\$$')
_MANIFEST_PATHS = (
    ROOT_DIR / 'specifications' / 'json-ld-api' / 'tests',
    ROOT_DIR / 'specifications' / 'json-ld-framing' / 'tests',
)


def _parse_skip_id_regex(pattern):
    match = _SKIP_ID_PATTERN.fullmatch(pattern)
    if not match:
        return None
    return match.group('manifest'), match.group('test_id')


def _test_url(manifest, test_id):
    base = MANIFEST_BASES.get(manifest, DEFAULT_TEST_BASE)
    return f'{base}/{manifest}.html#{test_id}'


def _jsonld_values(data, key):
    if key not in data:
        return []
    value = data[key]
    return value if isinstance(value, list) else [value]


def _entry_test_types(entry):
    values = []
    values.extend(_jsonld_values(entry, '@type'))
    values.extend(_jsonld_values(entry, 'type'))
    return values


def _manifest_entries():
    for manifest_dir in _MANIFEST_PATHS:
        if not manifest_dir.exists():
            continue
        for path in sorted(manifest_dir.glob('*-manifest.jsonld')):
            data = json.loads(path.read_text())
            manifest = path.stem
            for entry in _jsonld_values(data, 'sequence'):
                if not isinstance(entry, dict):
                    continue
                test_id = entry.get('@id', entry.get('id', ''))
                if test_id.startswith('#'):
                    test_id = test_id[1:]
                yield {
                    'entry': entry,
                    'id': f'{manifest}#{test_id}',
                    'link': f'[{test_id}]({_test_url(manifest, test_id)})',
                    'types': _entry_test_types(entry),
                }


def _skip_reason(test_type, skip, test):
    test_id = test['id']
    entry = test['entry']
    for pattern in skip.get('idRegex', []):
        if re.match(pattern, test_id):
            return f'Explicit skip (`{test_type}`)'

    for pattern in skip.get('descriptionRegex', []):
        if re.match(pattern, entry.get('description', '')):
            return f'Description skip (`{test_type}`)'

    processing_mode = entry.get('option', {}).get('processingMode')
    if processing_mode in skip.get('processingMode', []):
        return f'Processing mode `{processing_mode}` (`{test_type}`)'

    spec_version = entry.get('option', {}).get('specVersion')
    if spec_version in skip.get('specVersion', []):
        return f'Spec version `{spec_version}` (`{test_type}`)'

    return None


def _pending_reason(test_type, pending, test):
    test_id = test['id']
    for pattern in pending.get('idRegex', []):
        if re.match(pattern, test_id):
            return f'Pending expected failure (`{test_type}`)'

    return None


def _example_path(name):
    path = (EXAMPLES_DIR / name).resolve()
    if not path.is_relative_to(EXAMPLES_DIR.resolve()):
        raise ValueError(f'Invalid example path: {name}')
    return path


def _github_branch():
    branch = os.environ.get('GITHUB_REF_NAME')
    if branch:
        return branch
    result = subprocess.run(
        ['git', 'symbolic-ref', '--short', 'HEAD'],
        capture_output=True,
        text=True,
        cwd=ROOT_DIR,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return 'master'


def _example_github_url(name, repo_url):
    rel_path = Path('docs/examples') / name
    branch = 'master'
    return f'{repo_url.rstrip("/")}/blob/{branch}/{rel_path.as_posix()}'


def _human_date(value):
    if not value:
        return ''
    parsed = date.fromisoformat(value) if isinstance(value, str) else value
    return f'{parsed.day} {parsed.strftime("%B %Y")}'


_ADR_STATUS = {
    'draft': (':material-pencil-outline:', 'Draft'),
    'undecided': (':question:', 'Undecided'),
    'decided': (':white_check_mark:', 'Decided'),
}


_ADR_STATUS_ADMONITION = {
    'draft': 'note',
    'undecided': 'warning',
    'decided': 'success',
}


def _adr_status_label(value):
    if not value:
        return ''
    key = str(value).lower()
    return _ADR_STATUS.get(key, (None, str(value).replace('_', ' ').title()))[1]


def _adr_metadata_date(value):
    if not value:
        return ''
    return f':material-calendar-clock: {_human_date(value)}'


def _adr_metadata(date, status):
    kind = _ADR_STATUS_ADMONITION.get(str(status).lower(), 'note')
    parts = []
    label = _adr_status_label(status)
    if label:
        parts.append(label)
    date_part = _adr_metadata_date(date)
    if date_part:
        parts.append(date_part)
    title = ' · '.join(parts)
    return f'!!! {kind} "{title}"\n'


def _adr_status(value):
    if not value:
        return ''
    key = str(value).lower()
    icon, label = _ADR_STATUS.get(
        key,
        (':material-information-outline:', str(value).replace('_', ' ').title()),
    )
    return f'{icon} {label}'


def _adr_status_icon(value):
    if not value:
        return ':material-information-outline:'
    key = str(value).lower()
    return _ADR_STATUS.get(
        key,
        (':material-information-outline:', ''),
    )[0]


def _parse_frontmatter(path):
    text = path.read_text(encoding='utf-8-sig')
    match = YAML_RE.match(text)
    if not match:
        return {}
    return yaml.load(match.group(1), SafeLoader) or {}


def define_env(env):
    @env.filter
    def human_date(value):
        return _human_date(value)

    @env.filter
    def adr_status(value):
        return _adr_status(value)

    @env.macro
    def adr_metadata(date, status):
        return _adr_metadata(date, status)

    @env.macro
    def bundled_contexts_table():
        from pyld import BUNDLED_CONTEXTS

        rows = [
            '| Context URL | Bundled file |',
            '| --- | --- |',
        ]
        for url, path in sorted(BUNDLED_CONTEXTS.items()):
            rows.append(f'| `{url}` | `{Path(path).name}` |')
        return '\n'.join(rows)

    @env.macro
    def skipped_tests_table():
        from runtests import TEST_TYPES

        skipped_or_pending = {}
        seen_links = set()
        tests = list(_manifest_entries())

        for test_type, config in sorted(TEST_TYPES.items()):
            skip = config.get('skip', {})
            pending = config.get('pending', {})

            for test in tests:
                if test_type not in test['types']:
                    continue
                reason = _skip_reason(test_type, skip, test) or _pending_reason(
                    test_type, pending, test
                )
                if not reason or test['link'] in seen_links:
                    continue
                skipped_or_pending.setdefault(reason, []).append(test['link'])
                seen_links.add(test['link'])

            for pattern in skip.get('idRegex', []):
                parsed = _parse_skip_id_regex(pattern)
                if not parsed:
                    continue
                manifest, test_id = parsed
                link = f'[{test_id}]({_test_url(manifest, test_id)})'
                if link in seen_links:
                    continue
                skipped_or_pending.setdefault(
                    f'Explicit skip (`{test_type}`)', []
                ).append(link)
                seen_links.add(link)

            for pattern in pending.get('idRegex', []):
                parsed = _parse_skip_id_regex(pattern)
                if not parsed:
                    continue
                manifest, test_id = parsed
                link = f'[{test_id}]({_test_url(manifest, test_id)})'
                if link in seen_links:
                    continue
                skipped_or_pending.setdefault(
                    f'Pending expected failure (`{test_type}`)', []
                ).append(link)
                seen_links.add(link)

        rows = [
            '| Reason | Tests |',
            '| --- | --- |',
        ]

        for reason, links in sorted(skipped_or_pending.items()):
            rows.append(f'| {reason} | {", ".join(sorted(links))} |')

        return '\n'.join(rows)

    @env.macro
    def example(name, output_syntax=None, indent=0):
        path = _example_path(name)
        source = path.read_text()
        result = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT_DIR,
            env={**os.environ, 'PYTHONPATH': str(ROOT_DIR / 'lib')},
        )
        github_url = _example_github_url(name, env.conf['repo_url'])
        display_name = path.name
        title = (
            f'Example<span class="example-source-link" markdown>'
            f':fontawesome-brands-github: [`{display_name}`]({github_url})'
            f'</span>'
        )
        output_lang = output_syntax or 'console'
        body = (
            f'```python\n{source}```\n\n'
            f'```{output_lang} title="Output"\n{result.stdout}```'
        )
        content_indent = indent + 4
        pad = ' ' * content_indent
        indented = '\n'.join(f'{pad}{line}' for line in body.splitlines())
        return f'!!! example "{title}"\n\n{indented}\n'
