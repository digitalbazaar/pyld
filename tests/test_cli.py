"""Tests for the PyLD command-line interface."""

import io
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from pyld import cli, jsonld
from pyld.cli import input as cli_input
from pyld.cli import state as cli_state
from pyld.cli.state import State

runner = CliRunner()

PERSON = {
    '@context': {'name': 'http://schema.org/name'},
    'name': 'Ada Lovelace',
}
IDENTIFIED_PERSON = {
    '@context': {'name': 'http://schema.org/name'},
    '@id': 'http://example.com/ada',
    'name': 'Ada Lovelace',
}
CONTEXT = {'name': 'http://schema.org/name'}
FRAME = {
    '@context': CONTEXT,
    '@type': 'http://schema.org/Person',
}
NQUADS = (
    '<http://example.com/ada> '
    '<http://schema.org/name> "Ada Lovelace" .\n'
)


def write_json(tmp_path: Path, name: str, input: Any) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(input), encoding='utf-8')
    return path


def write_text(tmp_path: Path, name: str, input: str) -> Path:
    path = tmp_path / name
    path.write_text(input, encoding='utf-8')
    return path


@pytest.fixture
def person_file(tmp_path: Path) -> Path:
    return write_json(tmp_path, 'person.jsonld', PERSON)


@pytest.fixture(autouse=True)
def _cli_cache_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv('PYLD_CACHE_FILE', str(tmp_path / 'http_cache.sqlite'))


def test_get_local_file(person_file: Path):
    """`pyld get` prints a local JSON-LD file as JSON."""
    result = runner.invoke(cli.pyld, ['get', str(person_file)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == PERSON


def test_get_from_stdin():
    """`pyld get -` reads JSON-LD from standard input and prints it."""
    result = runner.invoke(cli.pyld, ['get', '-'], input=json.dumps(PERSON))
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == PERSON


def test_get_requires_input():
    """`pyld get` without an input argument exits as a usage error."""
    result = runner.invoke(cli.pyld, ['get'])
    assert result.exit_code == 2
    assert 'Missing argument' in result.output


def test_get_missing_file_exits_without_traceback(tmp_path: Path, capsys):
    """A missing get input exits with a traceback hint and no stack trace."""
    missing = tmp_path / 'missing.jsonld'
    with pytest.raises(SystemExit) as exited:
        cli.main(['get', str(missing)])
    assert exited.value.code == 1
    err = capsys.readouterr().err
    assert 'Traceback' not in err
    assert f'pyld --traceback get {missing}' in err


def test_traceback_hint_repeats_the_failed_invocation(tmp_path: Path, capsys):
    """The hint is a copy-pasteable command, quoted where the shell needs it."""
    missing = tmp_path / 'missing.jsonld'
    context_path = write_json(
        tmp_path,
        'context file.jsonld',
        {'@context': CONTEXT},
    )
    with pytest.raises(SystemExit):
        cli.main(['expand', str(missing), '--context', str(context_path)])
    err = capsys.readouterr().err
    assert (
        f"pyld --traceback expand {missing} --context '{context_path}'"
    ) in err


def test_expand_local_file(person_file: Path):
    """`pyld expand` expands a local JSON-LD file."""
    result = runner.invoke(cli.pyld, ['expand', str(person_file)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [
        {'http://schema.org/name': [{'@value': 'Ada Lovelace'}]},
    ]


def test_expand_from_stdin():
    """`pyld expand -` expands JSON-LD from standard input."""
    result = runner.invoke(cli.pyld, ['expand', '-'], input=json.dumps(PERSON))
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [
        {'http://schema.org/name': [{'@value': 'Ada Lovelace'}]},
    ]


def test_expand_with_base(tmp_path: Path):
    """`--base` resolves relative IRIs during expansion."""
    input = {
        '@context': {
            'knows': {'@id': 'http://schema.org/knows', '@type': '@id'},
        },
        'knows': 'bob',
    }
    path = write_json(tmp_path, 'relative.jsonld', input)
    result = runner.invoke(
        cli.pyld,
        ['expand', str(path), '--base', 'http://example.org/'],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [
        {
            'http://schema.org/knows': [
                {'@id': 'http://example.org/bob'},
            ],
        },
    ]


def test_expand_with_context_from_stdin(tmp_path: Path):
    """`--context -` expands using a context read from standard input."""
    input = {'name': 'Ada Lovelace'}
    input_path = write_json(tmp_path, 'person.jsonld', input)
    result = runner.invoke(
        cli.pyld,
        ['expand', str(input_path), '--context', '-'],
        input=json.dumps(CONTEXT),
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [
        {'http://schema.org/name': [{'@value': 'Ada Lovelace'}]},
    ]


def test_expand_with_context_file(tmp_path: Path):
    """`--context` expands using a context loaded from a local file."""
    context_path = write_json(
        tmp_path,
        'context.jsonld',
        {'@context': {'name': 'http://schema.org/name'}},
    )
    result = runner.invoke(
        cli.pyld,
        ['expand', '-', '--context', str(context_path)],
        input=json.dumps({'name': 'Ada Lovelace'}),
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [
        {'http://schema.org/name': [{'@value': 'Ada Lovelace'}]},
    ]


def test_invalid_json_on_stdin_exits_without_traceback(monkeypatch, capsys):
    """Invalid JSON on stdin exits with a traceback hint and no stack trace."""
    monkeypatch.setattr(sys, 'stdin', io.StringIO('{not-json'))
    with pytest.raises(SystemExit) as exited:
        cli.main(['expand', '-'])
    assert exited.value.code == 1
    err = capsys.readouterr().err
    assert 'Traceback' not in err
    assert 'pyld --traceback' in err


def test_bare_pyld_prints_help():
    """Typer's no_args_is_help prints help on stdout and exits as a usage error."""
    result = runner.invoke(cli.pyld, [])
    assert result.exit_code == 2
    for command in (
        'get',
        'expand',
        'compact',
        'flatten',
        'frame',
        'to-rdf',
        'from-rdf',
        'cache',
    ):
        assert command in result.stdout


def test_expand_requires_input():
    """`pyld expand` without an input argument exits as a usage error."""
    result = runner.invoke(cli.pyld, ['expand'])
    assert result.exit_code == 2
    assert 'Missing argument' in result.output


def test_cli_is_jsonld_11_only():
    """The CLI does not expose `--processing-mode` and rejects `json-ld-1.0`."""
    help_result = runner.invoke(cli.pyld, ['expand', '--help'])
    assert help_result.exit_code == 0
    assert '--processing-mode' not in help_result.stdout

    result = runner.invoke(
        cli.pyld,
        ['expand', '-', '--processing-mode', 'json-ld-1.0'],
        input='{}',
    )
    assert result.exit_code == 2
    assert 'No such option' in result.output


@pytest.mark.parametrize(
    'command',
    ['compact', 'flatten', 'frame', 'to-rdf', 'from-rdf'],
)
def test_new_commands_require_input(command: str):
    """Transformation commands without an input argument exit as a usage error."""
    result = runner.invoke(cli.pyld, [command])
    assert result.exit_code == 2
    assert 'Missing argument' in result.output


def test_compact_local_file_with_context_from_stdin(tmp_path: Path):
    """`pyld compact` compacts a local file using a context from stdin."""
    input_path = write_json(tmp_path, 'person.jsonld', PERSON)
    result = runner.invoke(
        cli.pyld,
        ['compact', str(input_path), '-'],
        input=json.dumps(CONTEXT),
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        '@context': CONTEXT,
        'name': 'Ada Lovelace',
    }


def test_compact_from_stdin_with_context_file(tmp_path: Path):
    """`pyld compact` compacts stdin using a context from a local file."""
    context_path = write_json(tmp_path, 'context.jsonld', {'@context': CONTEXT})
    result = runner.invoke(
        cli.pyld,
        ['compact', '-', str(context_path)],
        input=json.dumps(PERSON),
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['name'] == 'Ada Lovelace'


def test_flatten_local_file(person_file: Path):
    """`pyld flatten` flattens a local JSON-LD file."""
    result = runner.invoke(cli.pyld, ['flatten', str(person_file)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)[0]['http://schema.org/name'] == [
        {'@value': 'Ada Lovelace'},
    ]


def test_flatten_with_context_from_stdin(tmp_path: Path):
    """`pyld flatten --context -` flattens using a context from stdin."""
    input_path = write_json(tmp_path, 'person.jsonld', PERSON)
    result = runner.invoke(
        cli.pyld,
        ['flatten', str(input_path), '--context', '-'],
        input=json.dumps(CONTEXT),
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['@context'] == CONTEXT


def test_frame_local_file_with_frame_file(tmp_path: Path):
    """`pyld frame` frames a local document with a local frame file."""
    input_path = write_json(tmp_path, 'person.jsonld', IDENTIFIED_PERSON)
    frame_path = write_json(tmp_path, 'frame.jsonld', FRAME)
    result = runner.invoke(
        cli.pyld,
        ['frame', str(input_path), str(frame_path)],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['@context'] == CONTEXT


def test_frame_with_frame_from_stdin(tmp_path: Path):
    """`pyld frame` frames a local document with a frame from stdin."""
    input_path = write_json(tmp_path, 'person.jsonld', IDENTIFIED_PERSON)
    result = runner.invoke(
        cli.pyld,
        ['frame', str(input_path), '-'],
        input=json.dumps(FRAME),
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['@context'] == CONTEXT


@pytest.mark.parametrize(
    ('command', 'secondary'),
    [
        ('expand', '--context=-'),
        ('compact', '-'),
        ('frame', '-'),
        ('flatten', '--context=-'),
        ('compact', '--expand-context=-'),
        ('flatten', '--expand-context=-'),
        ('frame', '--expand-context=-'),
    ],
)
def test_multiple_operands_reject_stdin(command: str, secondary: str):
    """Commands reject using standard input for more than one operand."""
    args = [command, '-']
    if command in ('compact', 'frame') and not secondary.startswith('--'):
        args.append(secondary)
    elif command in ('compact', 'frame'):
        args.extend(['https://example.com/context.jsonld', secondary])
    else:
        args.append(secondary)
    result = runner.invoke(cli.pyld, args, input=json.dumps(PERSON))
    assert result.exit_code == 2
    assert 'Only one operand may read from standard input' in result.output


def test_to_rdf_local_file_writes_exact_nquads(tmp_path: Path):
    """`pyld to-rdf` writes exact N-Quads for a local JSON-LD file."""
    input_path = write_json(tmp_path, 'person.jsonld', IDENTIFIED_PERSON)
    result = runner.invoke(cli.pyld, ['to-rdf', str(input_path)])
    assert result.exit_code == 0, result.output
    assert result.stdout == NQUADS
    assert '\x1b' not in result.stdout


def test_to_rdf_from_stdin_writes_exact_nquads():
    """`pyld to-rdf -` writes exact N-Quads from standard input."""
    result = runner.invoke(
        cli.pyld,
        ['to-rdf', '-'],
        input=json.dumps(IDENTIFIED_PERSON),
    )
    assert result.exit_code == 0, result.output
    assert result.stdout == NQUADS


def test_from_rdf_local_file(tmp_path: Path):
    """`pyld from-rdf` converts a local N-Quads file to JSON-LD."""
    input_path = write_text(tmp_path, 'person.nq', NQUADS)
    result = runner.invoke(cli.pyld, ['from-rdf', str(input_path)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [
        {
            '@id': 'http://example.com/ada',
            'http://schema.org/name': [{'@value': 'Ada Lovelace'}],
        }
    ]


def test_from_rdf_from_stdin():
    """`pyld from-rdf -` converts N-Quads from standard input to JSON-LD."""
    result = runner.invoke(cli.pyld, ['from-rdf', '-'], input=NQUADS)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)[0]['@id'] == 'http://example.com/ada'


def test_from_rdf_rejects_remote_input():
    """`pyld from-rdf` rejects remote URLs and requires a local path or `-`."""
    result = runner.invoke(
        cli.pyld,
        ['from-rdf', 'https://example.com/person.nq'],
    )
    assert result.exit_code == 2
    assert 'must be a local path or -' in result.output


def test_from_rdf_help_describes_only_local_input():
    """`from-rdf --help` describes local path or stdin input only."""
    result = runner.invoke(cli.pyld, ['from-rdf', '--help'])
    assert result.exit_code == 0, result.output
    assert 'Local path. Pass - to read from standard input.' in result.stdout
    assert 'Path or URL.' not in result.stdout


def test_print_nquads_preserves_empty_output(monkeypatch: pytest.MonkeyPatch):
    """Empty N-Quads output is printed without adding a trailing newline."""
    monkeypatch.setattr(jsonld, 'to_rdf', lambda *args, **kwargs: '')
    result = runner.invoke(cli.pyld, ['to-rdf', '-'], input=json.dumps(PERSON))
    assert result.exit_code == 0, result.output
    assert result.stdout == ''


@pytest.mark.parametrize(
    ('command', 'args', 'function_name', 'expected'),
    [
        (
            'expand',
            [
                '-',
                '--context',
                'https://example.com/context.jsonld',
                '--base',
                'http://example.com/',
                '--extract-all-scripts',
            ],
            'expand',
            {
                'base': 'http://example.com/',
                'processingMode': 'json-ld-1.1',
                'extractAllScripts': True,
                'expandContext': 'https://example.com/context.jsonld',
            },
        ),
        (
            'compact',
            [
                '-',
                'https://example.com/context.jsonld',
                '--base',
                'http://example.com/',
                '--extract-all-scripts',
                '--expand-context',
                'https://example.com/expand-context.jsonld',
                '--no-compact-arrays',
                '--graph',
            ],
            'compact',
            {
                'base': 'http://example.com/',
                'processingMode': 'json-ld-1.1',
                'extractAllScripts': True,
                'expandContext': 'https://example.com/expand-context.jsonld',
                'compactArrays': False,
                'graph': True,
            },
        ),
        (
            'flatten',
            [
                '-',
                '--context',
                'https://example.com/context.jsonld',
                '--expand-context',
                'https://example.com/expand-context.jsonld',
                '--no-extract-all-scripts',
            ],
            'flatten',
            {
                'expandContext': 'https://example.com/expand-context.jsonld',
                'extractAllScripts': False,
            },
        ),
        (
            'frame',
            [
                '-',
                'https://example.com/frame.jsonld',
                '--embed',
                '@once',
                '--explicit',
                '--no-omit-default',
                '--no-prune-blank-node-identifiers',
                '--require-all',
            ],
            'frame',
            {
                'embed': '@once',
                'explicit': True,
                'omitDefault': False,
                'pruneBlankNodeIdentifiers': False,
                'requireAll': True,
            },
        ),
        (
            'to-rdf',
            [
                '-',
                '--produce-generalized-rdf',
                '--rdf-direction',
                'compound-literal',
            ],
            'to_rdf',
            {
                'format': 'application/n-quads',
                'produceGeneralizedRdf': True,
                'rdfDirection': 'compound-literal',
            },
        ),
        (
            'from-rdf',
            [
                '-',
                '--use-rdf-type',
                '--use-native-types',
                '--rdf-direction',
                'i18n-datatype',
            ],
            'from_rdf',
            {
                'format': 'application/n-quads',
                'useRdfType': True,
                'useNativeTypes': True,
                'rdfDirection': 'i18n-datatype',
            },
        ),
    ],
)
def test_command_options_are_mapped_to_api_keys(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    args: list[str],
    function_name: str,
    expected: dict,
):
    """CLI flags are mapped to the corresponding JSON-LD API option keys."""
    captured = {}

    def transform(*positional, options):
        captured.update(options)
        return '' if function_name == 'to_rdf' else {}

    monkeypatch.setattr(jsonld, function_name, transform)
    input_text = NQUADS if command == 'from-rdf' else '{}'
    result = runner.invoke(cli.pyld, [command, *args], input=input_text)
    assert result.exit_code == 0, result.output
    for key, value in expected.items():
        assert captured[key] == value


@pytest.mark.parametrize(
    ('command', 'args', 'function_name', 'forced_keys'),
    [
        ('expand', ['-'], 'expand', set()),
        (
            'compact',
            ['-', 'https://example.com/context.jsonld'],
            'compact',
            set(),
        ),
        ('flatten', ['-'], 'flatten', set()),
        ('frame', ['-', 'https://example.com/frame.jsonld'], 'frame', set()),
        ('to-rdf', ['-'], 'to_rdf', {'format'}),
        ('from-rdf', ['-'], 'from_rdf', {'format'}),
    ],
)
def test_omitted_cli_options_do_not_override_api_defaults(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    args: list[str],
    function_name: str,
    forced_keys: set[str],
):
    """Omitted CLI flags leave API defaults unset except forced keys."""
    captured = {}

    def transform(*positional, options):
        captured.update(options)
        return '' if function_name == 'to_rdf' else {}

    monkeypatch.setattr(jsonld, function_name, transform)
    input_text = NQUADS if command == 'from-rdf' else '{}'
    result = runner.invoke(cli.pyld, [command, *args], input=input_text)
    assert result.exit_code == 0, result.output
    expected_keys = forced_keys
    if command != 'from-rdf':
        expected_keys = {'documentLoader', 'processingMode', *forced_keys}
        assert captured['processingMode'] == 'json-ld-1.1'
    assert set(captured) == expected_keys


@pytest.mark.parametrize(
    ('command', 'args', 'function_name'),
    [
        ('expand', ['https://example.com/input.jsonld'], 'expand'),
        (
            'compact',
            [
                'https://example.com/input.jsonld',
                'https://example.com/context.jsonld',
            ],
            'compact',
        ),
        ('flatten', ['https://example.com/input.jsonld'], 'flatten'),
        (
            'frame',
            [
                'https://example.com/input.jsonld',
                'https://example.com/frame.jsonld',
            ],
            'frame',
        ),
        ('to-rdf', ['https://example.com/input.jsonld'], 'to_rdf'),
    ],
)
def test_jsonld_commands_preserve_remote_input_urls(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    args: list[str],
    function_name: str,
):
    """Remote input URLs are passed through to the JSON-LD API unchanged."""
    captured = {}

    def transform(input_, *positional, options):
        captured['input'] = input_
        return '' if function_name == 'to_rdf' else {}

    monkeypatch.setattr(jsonld, function_name, transform)
    result = runner.invoke(cli.pyld, [command, *args])
    assert result.exit_code == 0, result.output
    assert captured['input'] == 'https://example.com/input.jsonld'


@pytest.mark.parametrize(
    'value',
    [
        'https://example.com/context.jsonld',
        'https://example.com/frame.jsonld',
    ],
)
def test_document_value_preserves_remote_urls(value: str):
    """`document_value` leaves remote URLs unchanged."""
    assert cli_input.document_value(value) == value


def test_document_value_treats_inline_json_as_a_path():
    """`document_value` treats inline JSON text as a local path."""
    assert cli_input.document_value('{}') == Path('{}').resolve().as_uri()


def test_missing_nquads_file_exits_without_traceback(tmp_path: Path, capsys):
    """A missing from-rdf input exits with a traceback hint and no stack trace."""
    missing = tmp_path / 'missing.nq'
    with pytest.raises(SystemExit) as exited:
        cli.main(['from-rdf', str(missing)])
    assert exited.value.code == 1
    err = capsys.readouterr().err
    assert 'Traceback' not in err
    assert f'pyld --traceback from-rdf {missing}' in err


def test_invalid_nquads_exits_without_traceback(monkeypatch, capsys):
    """Invalid N-Quads on stdin exits with a traceback hint and no stack trace."""
    monkeypatch.setattr(sys, 'stdin', io.StringIO('not n-quads'))
    with pytest.raises(SystemExit) as exited:
        cli.main(['from-rdf', '-'])
    assert exited.value.code == 1
    err = capsys.readouterr().err
    assert 'Traceback' not in err
    assert 'pyld --traceback from-rdf -' in err


def test_cache_clear(tmp_path: Path):
    """`pyld cache clear` deletes the configured HTTP cache file."""
    cache_file = tmp_path / 'http_cache.sqlite'
    cache_file.write_text('cache', encoding='utf-8')
    result = runner.invoke(cli.pyld, ['cache', 'clear'])
    assert result.exit_code == 0, result.output
    assert 'Cache cleared' in result.stdout
    assert not cache_file.exists()


def test_cache_clear_uses_env_var_cache_file(tmp_path: Path):
    """`cache clear` deletes the cache file named by `PYLD_CACHE_FILE`."""
    cache_file = tmp_path / 'http_cache.sqlite'
    cache_file.write_text('cache', encoding='utf-8')
    result = runner.invoke(cli.pyld, ['cache', 'clear'])
    assert result.exit_code == 0, result.output
    assert not cache_file.exists()


def test_cache_file_option_overrides_env_var(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """`--cache-file` overrides `PYLD_CACHE_FILE` for cache clear."""
    env_cache = tmp_path / 'from-env.sqlite'
    option_cache = tmp_path / 'from-option.sqlite'
    env_cache.write_text('env', encoding='utf-8')
    option_cache.write_text('option', encoding='utf-8')
    monkeypatch.setenv('PYLD_CACHE_FILE', str(env_cache))
    result = runner.invoke(
        cli.pyld,
        ['--cache-file', str(option_cache), 'cache', 'clear'],
    )
    assert result.exit_code == 0, result.output
    assert not option_cache.exists()
    assert env_cache.exists()


def test_parse_location_treats_windows_drive_as_path(
    monkeypatch: pytest.MonkeyPatch,
):
    """On Windows, drive-letter paths are treated as filesystem paths."""
    monkeypatch.setattr(cli_input.sys, 'platform', 'win32')
    for path in (
        r'C:\Users\ada\doc.jsonld',
        'C:/Users/ada/doc.jsonld',
        'd:/tmp/x.jsonld',
    ):
        result = cli_input.parse_location(path)
        assert isinstance(result, Path), path


def test_parse_location_preserves_single_letter_scheme_outside_windows(
    monkeypatch: pytest.MonkeyPatch,
):
    """Outside Windows, a single-letter scheme is left as a URL."""
    monkeypatch.setattr(cli_input.sys, 'platform', 'linux')
    assert cli_input.parse_location('x:document') == 'x:document'


def test_parse_location_preserves_http_urls():
    """`parse_location` leaves HTTP(S) URLs unchanged."""
    assert cli_input.parse_location('https://example.com/x.jsonld') == (
        'https://example.com/x.jsonld'
    )


def test_parse_location_resolves_local_path(tmp_path: Path):
    """`parse_location` resolves a local path to an absolute Path."""
    path = write_json(tmp_path, 'person.jsonld', {})
    result = cli_input.parse_location(str(path))
    assert result == path.resolve()
    assert isinstance(result, Path)


def test_document_url_converts_local_path_to_file_url(tmp_path: Path):
    """`document_url` converts a local path to a file: URL."""
    path = write_json(tmp_path, 'person.jsonld', {})
    assert cli_input.document_url(str(path)) == path.as_uri()


def test_document_url_preserves_http_url():
    """`document_url` leaves HTTP(S) URLs unchanged."""
    assert cli_input.document_url('https://example.com/x.jsonld') == (
        'https://example.com/x.jsonld'
    )


def test_configured_cache_file_resolves_relative_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """`configured_cache_file` resolves a relative cache path against cwd."""
    monkeypatch.chdir(tmp_path)
    cli_state.current = State(cache_file=Path('rel.sqlite'))
    assert cli_input.configured_cache_file() == (tmp_path / 'rel.sqlite').resolve()


def test_relative_cache_file_works_for_local_expand(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Relative PYLD_CACHE_FILE must not crash loader construction."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('PYLD_CACHE_FILE', 'nested/cache.sqlite')
    result = runner.invoke(cli.pyld, ['expand', '-'], input=json.dumps(PERSON))
    assert result.exit_code == 0, result.output


def test_cli_entry_exits_when_cli_deps_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """Missing CLI dependencies exit with an install hint for `PyLD[cli]`."""
    from pyld.cli import entry

    def fail():
        raise ImportError('simulated missing CLI dependency')

    monkeypatch.setattr(entry, '_load_cli', fail)
    with pytest.raises(SystemExit) as exited:
        entry.main([])
    assert exited.value.code == 1
    assert 'PyLD[cli]' in capsys.readouterr().err


def test_cli_entry_module_imports_without_loading_cli():
    """The console-script module must import even when CLI deps are absent."""
    import pyld.cli.entry as entry

    assert callable(entry.main)


def test_local_input_creates_no_cache_file(person_file: Path, tmp_path: Path):
    """Reading a local document leaves the HTTP cache untouched."""
    result = runner.invoke(cli.pyld, ['expand', str(person_file)])
    assert result.exit_code == 0, result.output
    assert not (tmp_path / 'http_cache.sqlite').exists()


def test_local_input_creates_no_cache_directory(tmp_path: Path, monkeypatch):
    """A nested cache directory is not created just to run a local expansion."""
    cache_dir = tmp_path / 'cache'
    monkeypatch.setenv('PYLD_CACHE_FILE', str(cache_dir / 'http_cache.sqlite'))
    result = runner.invoke(cli.pyld, ['expand', '-'], input=json.dumps(PERSON))
    assert result.exit_code == 0, result.output
    assert not cache_dir.exists()
