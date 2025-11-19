import pytest
import unittest

# Reuse the existing Test wrapper from `runtests.py`. The pytest test
# simply calls `setUp()` and `runTest()` on the original Test instance
# so that all existing behavior and comparison logic remains unchanged.


def _call_test(testcase):
    """Call setUp and runTest on a `runtests.Test` instance.

    Convert unittest.SkipTest to pytest.skip so pytest reports skipped
    tests correctly.
    """
    try:
        testcase.setUp()
    except unittest.SkipTest as e:
        pytest.skip(str(e))

    try:
        testcase.runTest()
    except unittest.SkipTest as e:
        pytest.skip(str(e))


def test_manifest_case(manifest_test):
    # manifest_test is a `runtests.Test` instance provided by the
    # parametrization implemented in `conftest.py`.
    _call_test(manifest_test)
