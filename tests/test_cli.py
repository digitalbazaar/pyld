"""Tests for the PyLD command-line interface."""

import io
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from pyld import cli

runner = CliRunner()

PERSON = {
    '@context': {'name': 'http://schema.org/name'},
    'name': 'Ada Lovelace',
}


def write_json(tmp_path: Path, name: str, input: Any) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(input), encoding='utf-8')
    return path


@pytest.fixture
def person_file(tmp_path: Path) -> Path:
    return write_json(tmp_path, 'person.jsonld', PERSON)


@pytest.fixture(autouse=True)
def _cli_cache_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv('PYLD_CACHE_FILE', str(tmp_path / 'http_cache.sqlite'))


def test_get_local_file(person_file: Path):
    result = runner.invoke(cli.pyld, ['get', str(person_file)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == PERSON


def test_get_from_stdin():
    result = runner.invoke(cli.pyld, ['get', '-'], input=json.dumps(PERSON))
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == PERSON


def test_get_requires_input():
    result = runner.invoke(cli.pyld, ['get'])
    assert result.exit_code == 2
    assert 'Missing argument' in result.output


def test_get_missing_file_exits_without_traceback(tmp_path: Path, capsys):
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
    with pytest.raises(SystemExit):
        cli.main(['expand', str(missing), '--context', '{"a": "http://a"}'])
    err = capsys.readouterr().err
    assert (
        f"pyld --traceback expand {missing} --context '{{\"a\": \"http://a\"}}'"
    ) in err


def test_expand_local_file(person_file: Path):
    result = runner.invoke(cli.pyld, ['expand', str(person_file)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [
        {'http://schema.org/name': [{'@value': 'Ada Lovelace'}]},
    ]


def test_expand_from_stdin():
    result = runner.invoke(cli.pyld, ['expand', '-'], input=json.dumps(PERSON))
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [
        {'http://schema.org/name': [{'@value': 'Ada Lovelace'}]},
    ]


def test_expand_with_base(tmp_path: Path):
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


def test_expand_with_inline_context():
    input = {'name': 'Ada Lovelace'}
    result = runner.invoke(
        cli.pyld,
        [
            'expand',
            '-',
            '--context',
            '{"name": "http://schema.org/name"}',
        ],
        input=json.dumps(input),
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [
        {'http://schema.org/name': [{'@value': 'Ada Lovelace'}]},
    ]


def test_expand_with_context_file(tmp_path: Path):
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
    assert 'expand' in result.stdout
    assert 'get' in result.stdout


def test_expand_requires_input():
    result = runner.invoke(cli.pyld, ['expand'])
    assert result.exit_code == 2
    assert 'Missing argument' in result.output


def test_cache_clear(tmp_path: Path):
    cache_file = tmp_path / 'http_cache.sqlite'
    cache_file.write_text('cache', encoding='utf-8')
    result = runner.invoke(cli.pyld, ['cache', 'clear'])
    assert result.exit_code == 0, result.output
    assert 'Cache cleared' in result.stdout
    assert not cache_file.exists()


def test_cache_clear_uses_env_var_cache_file(tmp_path: Path):
    cache_file = tmp_path / 'http_cache.sqlite'
    cache_file.write_text('cache', encoding='utf-8')
    result = runner.invoke(cli.pyld, ['cache', 'clear'])
    assert result.exit_code == 0, result.output
    assert not cache_file.exists()


def test_cache_file_option_overrides_env_var(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
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


def test_parse_location_treats_windows_drive_as_path():
    for path in (
        r'C:\Users\ada\doc.jsonld',
        'C:/Users/ada/doc.jsonld',
        'd:/tmp/x.jsonld',
    ):
        result = cli.parse_location(path)
        assert isinstance(result, Path), path


def test_parse_location_preserves_http_urls():
    assert cli.parse_location('https://example.com/x.jsonld') == (
        'https://example.com/x.jsonld'
    )


def test_parse_location_resolves_local_path(tmp_path: Path):
    path = write_json(tmp_path, 'person.jsonld', {})
    result = cli.parse_location(str(path))
    assert result == path.resolve()
    assert isinstance(result, Path)


def test_document_url_converts_local_path_to_file_url(tmp_path: Path):
    path = write_json(tmp_path, 'person.jsonld', {})
    assert cli.document_url(str(path)) == path.as_uri()


def test_document_url_preserves_http_url():
    assert cli.document_url('https://example.com/x.jsonld') == (
        'https://example.com/x.jsonld'
    )


def test_configured_cache_file_resolves_relative_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    cli.pyld.state = cli.State(cache_file=Path('rel.sqlite'))  # type: ignore[attr-defined]
    assert cli.configured_cache_file() == (tmp_path / 'rel.sqlite').resolve()


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
