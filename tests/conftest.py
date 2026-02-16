import os
import unittest
from contextlib import suppress

import pytest

# Import the existing test runner module so we can reuse Manifest/Test
# implementations with minimal changes.
from . import runtests


def pytest_addoption(parser):
    # Do only long options for pytest integration; pytest reserves
    # lowercase single-letter short options for its own CLI flags.
    parser.addoption(
        '--tests', nargs='*', default=[], help='A manifest or directory to test'
    )
    parser.addoption(
        '--earl', dest='earl', help='The filename to write an EARL report to'
    )
    parser.addoption(
        '--loader',
        dest='loader',
        default='requests',
        help='The remote URL document loader: requests, aiohttp',
    )
    parser.addoption(
        '--number',
        dest='number',
        help='Limit tests to those containing the specified test identifier',
    )


def pytest_configure(config):
    # Register custom markers
    config.addinivalue_line(
        "markers", "network: marks tests as requiring network access (may be slow)"
    )

    # Apply loader choice and selected test number globally so that the
    # existing `runtests` helpers behave the same as the CLI runner.
    loader = config.getoption('loader')
    if loader == 'requests':
        runtests.jsonld._default_document_loader = (
            runtests.jsonld.requests_document_loader()
        )
    elif loader == 'aiohttp':
        runtests.jsonld._default_document_loader = (
            runtests.jsonld.aiohttp_document_loader()
        )

    number = config.getoption('number')
    if number:
        runtests.ONLY_IDENTIFIER = number
    # If an EARL output file was requested, create a session-level
    # EarlReport instance we will populate per-test.
    earl_fn = config.getoption('earl')
    if earl_fn:
        config._earl_report = runtests.EarlReport()
    else:
        config._earl_report = None


def _flatten_suite(suite):
    """Yield TestCase instances from a unittest TestSuite (recursively)."""
    if isinstance(suite, unittest.TestSuite):
        for s in suite:
            yield from _flatten_suite(s)
    elif isinstance(suite, unittest.TestCase):
        yield suite


def pytest_generate_tests(metafunc):
    # Parametrize tests using the existing manifest loader if the test
    # function needs a `manifest_test` argument.
    if 'manifest_test' not in metafunc.fixturenames:
        return

    config = metafunc.config
    tests_arg = config.getoption('tests') or []

    if len(tests_arg):
        test_targets = tests_arg
    else:
        # Default sibling directories used by the original runner. Keep the
        # original relative strings but resolve them relative to this
        # `conftest.py` so tests can be discovered regardless of cwd.
        base_path = os.path.abspath(os.path.dirname(__file__))

        test_targets = []
        for d in runtests.SPEC_DIRS:
            d_path = os.path.abspath(os.path.join(base_path, d))
            if os.path.exists(d_path):
                test_targets.append(d_path)

    if len(test_targets) == 0:
        pytest.skip('No test manifest or directory specified (use --tests)')

    # Build a root manifest structure with target files and dirs (equivalent to the original runner).
    root_manifest = {
        '@context': 'https://w3c.github.io/tests/context.jsonld',
        '@id': '',
        '@type': 'mf:Manifest',
        'description': 'Top level PyLD test manifest',
        'name': 'PyLD',
        'sequence': [],
        'filename': '/',
    }

    for test in test_targets:
        if os.path.isfile(test):
            root, ext = os.path.splitext(test)
            if ext in ['.json', '.jsonld']:
                root_manifest['sequence'].append(os.path.abspath(test))
            else:
                raise Exception('Unknown test file ext', root, ext)
        elif os.path.isdir(test):
            filename = os.path.join(test, 'manifest.jsonld')
            if os.path.exists(filename):
                root_manifest['sequence'].append(os.path.abspath(filename))

    # Use the existing Manifest loader to create a TestSuite and flatten it
    suite = runtests.Manifest(root_manifest, root_manifest['filename']).load()
    tests = list(_flatten_suite(suite))

    # Parametrize the test function with Test instances and use their
    # string representation as test ids for readability in pytest output.
    metafunc.parametrize('manifest_test', tests, ids=[str(t) for t in tests])


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item):
    # Hookwrapper gives us the final test report via `outcome.get_result()`.
    outcome = yield
    rep = outcome.get_result()

    # We only handle the main call phase to match
    # the behaviour of the original runner which only reported passes
    # and failures/errors.
    if rep.when not in ('call'):
        return

    # The parametrized pytest test attaches the original runtests.Test
    # instance as the `manifest_test` fixture; retrieve it here.
    manifest_test = item.funcargs.get('manifest_test')
    if manifest_test is None:
        return

    # If an EARL report was requested at configure time, add an assertion
    # for this test based on the pytest outcome.
    earl_report = getattr(item.config, '_earl_report', None)
    if earl_report is None:
        return

    # Map pytest outcomes to whether the test should be recorded as
    # succeeded or failed. We skip 'skipped' outcomes to avoid polluting
    # the EARL report with non-asserted tests.
    if rep.outcome == 'skipped':
        return

    success = rep.outcome == 'passed'

    # Don't let EARL bookkeeping break test execution; be quiet on error.
    with suppress(Exception):
        earl_report.add_assertion(manifest_test, success)


def pytest_sessionfinish(session, exitstatus):
    # If the user requested an EARL report, write it using the existing
    # `EarlReport` helper. We can't collect per-test assertions here
    # The per-test assertions (if any) were appended to config._earl_report
    # during test execution; write the report now if present.
    earl = session.config.getoption('earl')
    earl_report = getattr(session.config, '_earl_report', None)
    if earl and earl_report is not None:
        earl_report.write(os.path.abspath(earl))
