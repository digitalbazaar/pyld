import pytest

from pyld.iri_resolver import unresolve

# Tests ported from relative-to-absolute-iri.js: https://github.com/rubensworks/relative-to-absolute-iri.js/blob/master/test/Resolve-test.ts
# (c) Ruben Taelman <stevenlevithan.com>


# ---------- Tests for unresolve() ----------
def test_absolute_iri_no_base():
    assert unresolve('http://example.org/') == 'http://example.org/'


def test_absolute_iri_empty_base():
    assert unresolve('http://example.org/', '') == 'http://example.org/'


def test_absolute_iri_with_base():
    assert unresolve('http://example.org/', 'http://base.org/') == 'http://example.org/'


def test_empty_value_uses_base():
    assert unresolve('', 'http://base.org/') == ''


def test_absolute_with_base():
    assert unresolve('http://base.org/abc', 'http://base.org/') == 'abc'


def test_absolute_with_fragment_base():
    assert unresolve('http://base.org/abc', 'http://base.org/#frag') == 'abc'


def test_hash_absolute():
    assert unresolve('http://base.org/#abc', 'http://base.org/') == '#abc'


def test_colon_in_value_ignores_base():
    assert unresolve('http:abc', 'http://base.org/') == 'http:abc'


def test_non_absolute_base_error():
    with pytest.raises(
        ValueError,
        match=r"Found invalid baseIRI 'def' for value 'http://base.org/abc'",
    ):
        unresolve('http://base.org/abc', 'def')


def test_non_absolute_base_empty_value_error():
    with pytest.raises(ValueError, match=r"Found invalid baseIRI 'def' for value ''"):
        unresolve('', 'def')


def test_base_without_path_slash():
    assert unresolve('http://base.org/abc', 'http://base.org') == 'abc'


def test_base_with_path_slash():
    assert unresolve('http://base.org/abc/', 'http://base.org') == 'abc/'


def test_absolute_iri_with_keyword():
    assert unresolve('http://base.org/@abc', 'http://base.org/') == './@abc'
