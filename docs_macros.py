import os
import re
import subprocess
import sys
from pathlib import Path

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


def _parse_skip_id_regex(pattern):
    match = _SKIP_ID_PATTERN.fullmatch(pattern)
    if not match:
        return None
    return match.group('manifest'), match.group('test_id')


def _test_url(manifest, test_id):
    base = MANIFEST_BASES.get(manifest, DEFAULT_TEST_BASE)
    return f'{base}/{manifest}#{test_id}'


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


def define_env(env):
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

        rows = [
            '| Reason | Skipped tests |',
            '| --- | --- |',
        ]

        linked_tests = []
        seen_tests = set()
        for test_type, config in sorted(TEST_TYPES.items()):
            skip = config.get('skip', {})
            spec_versions = skip.get('specVersion', [])
            if 'json-ld-1.0' in spec_versions:
                rows.append(
                    f'| JSON-LD 1.0 processor behavior (`{test_type}`) | '
                    f'All JSON-LD 1.0 tests |'
                )

            for pattern in skip.get('idRegex', []):
                parsed = _parse_skip_id_regex(pattern)
                if not parsed:
                    continue
                manifest, test_id = parsed
                url = _test_url(manifest, test_id)
                if url in seen_tests:
                    continue
                seen_tests.add(url)
                linked_tests.append(f'[{test_id}]({url})')

        if linked_tests:
            rows.append(
                '| Explicitly skipped test cases | ' + ', '.join(linked_tests) + ' |'
            )

        return '\n'.join(rows)

    @env.macro
    def example(name, output_syntax=None):
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
        indented = '\n'.join(f'    {line}' for line in body.splitlines())
        return f'!!! example "{title}"\n\n{indented}\n'
