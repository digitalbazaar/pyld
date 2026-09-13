import pytest

from pyld.iri_resolver import resolve

# Tests ported from relative-to-absolute-iri.js: https://github.com/rubensworks/relative-to-absolute-iri.js/blob/master/test/Resolve-test.ts
# (c) Ruben Taelman <stevenlevithan.com>


# ---------- Tests for resolve() ----------
def test_absolute_iri_no_base():
    assert resolve('http://example.org/') == 'http://example.org/'


def test_absolute_iri_empty_base():
    assert resolve('http://example.org/', '') == 'http://example.org/'


def test_absolute_iri_with_base():
    assert resolve('http://example.org/', 'http://base.org/') == 'http://example.org/'


def test_empty_value_uses_base():
    assert resolve('', 'http://base.org/') == 'http://base.org/'


def test_relative_with_scheme_no_base():
    assert resolve('ex:abc') == 'ex:abc'


def test_relative_without_scheme_no_base_error():
    with pytest.raises(
        ValueError, match=r"Found invalid relative IRI 'abc' for a missing baseIRI"
    ):
        resolve('abc')


def test_relative_without_dot_segments_no_base():
    assert resolve('http://abc/../../') == 'http://abc/'


def test_relative_with_base():
    assert resolve('abc', 'http://base.org/') == 'http://base.org/abc'


def test_relative_with_fragment_base():
    assert resolve('abc', 'http://base.org/#frag') == 'http://base.org/abc'


def test_hash_relative():
    assert resolve('#abc', 'http://base.org/') == 'http://base.org/#abc'


def test_colon_in_value_ignores_base():
    assert resolve('http:abc', 'http://base.org/') == 'http:abc'


def test_colon_in_value_removes_dots():
    assert resolve('http://abc/../../', 'http://base.org/') == 'http://abc/'


def test_non_absolute_base_error():
    with pytest.raises(
        ValueError, match=r"Found invalid baseIRI 'def' for value 'abc'"
    ):
        resolve('abc', 'def')


def test_non_absolute_base_empty_value_error():
    with pytest.raises(ValueError, match=r"Found invalid baseIRI 'def' for value ''"):
        resolve('', 'def')


def test_scheme_from_base_if_value_starts_with_slash_slash():
    assert resolve('//abc', 'http://base.org/') == 'http://abc'


def test_base_without_path_slash():
    assert resolve('abc', 'http://base.org') == 'http://base.org/abc'


def test_base_without_path_dot_segments():
    assert resolve('abc/./', 'http://base.org') == 'http://base.org/abc/'


def test_base_only_scheme_slash_slash():
    assert resolve('abc', 'http://') == 'http:abc'


def test_base_only_scheme_slash_slash_dot_segments():
    assert resolve('abc/./', 'http://') == 'http:abc/'


def test_base_with_char_after_colon():
    assert resolve('abc', 'http:a') == 'http:abc'


def test_base_with_char_after_colon_dot_segments():
    assert resolve('abc/./', 'http:a') == 'http:abc/'


def test_base_only_scheme():
    assert resolve('abc', 'http:') == 'http:abc'


def test_base_only_scheme_dot_segments():
    assert resolve('abc/./', 'http:') == 'http:abc/'


def test_absolute_path_ignores_base_path():
    assert (
        resolve('/abc/def/', 'http://base.org/123/456/') == 'http://base.org/abc/def/'
    )


def test_base_with_last_slash_replacement():
    assert resolve('xyz', 'http://aa/a') == 'http://aa/xyz'


def test_base_collapse_parent_paths():
    assert resolve('xyz', 'http://aa/parent/parent/../../a') == 'http://aa/xyz'


def test_base_remove_current_dir():
    assert resolve('xyz', 'http://aa/././a') == 'http://aa/xyz'


def test_base_dot():
    assert resolve('.', 'http://aa/') == 'http://aa/'


def test_base_double_dot():
    assert resolve('..', 'http://aa/b/') == 'http://aa/'


def test_base_double_dot_slash():
    assert resolve('../', 'http://aa/b/') == 'http://aa/'


def test_base_without_ending_slash_double_dot():
    assert resolve('..', 'http://aa/b') == 'http://aa/'


def test_base_without_ending_slash_double_dot_slash():
    assert resolve('../', 'http://aa/b') == 'http://aa/'


def test_base_without_ending_slash_query():
    assert resolve('?a=b', 'http://abc/def/ghi') == 'http://abc/def/ghi?a=b'


def test_base_without_ending_slash_dot_query():
    assert resolve('.?a=b', 'http://abc/def/ghi') == 'http://abc/def/?a=b'


def test_base_without_ending_slash_double_dot_query():
    assert resolve('..?a=b', 'http://abc/def/ghi') == 'http://abc/?a=b'


def test_base_without_ending_slash_xyz():
    assert resolve('xyz', 'http://abc/d:f/ghi') == 'http://abc/d:f/xyz'


def test_base_without_ending_slash_dot_xyz():
    assert resolve('./xyz', 'http://abc/d:f/ghi') == 'http://abc/d:f/xyz'


def test_base_without_ending_slash_double_dot_xyz():
    assert resolve('../xyz', 'http://abc/d:f/ghi') == 'http://abc/xyz'


def test_relative_with_colon_ignores_base():
    assert resolve('g:h', 'file:///a/bb/ccc/d;p?q') == 'g:h'


def test_simple_relative_with_complex_base():
    assert resolve('g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g'


def test_dot_slash_g_relative_with_complex_base():
    assert resolve('./g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g'


def test_slash_suffix_relative_with_complex_base():
    assert resolve('g/', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g/'


def test_slash_prefix_relative_with_complex_base():
    assert resolve('/g', 'file:///a/bb/ccc/d;p?q') == 'file:///g'


def test_double_slash_prefix_relative_with_complex_base():
    assert resolve('//g', 'file:///a/bb/ccc/d;p?q') == 'file://g'


def test_questionmark_prefix_relative_with_complex_base():
    assert resolve('?y', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/d;p?y'


def test_questionmark_middle_relative_with_complex_base():
    assert resolve('g?y', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g?y'


def test_hashtag_prefix_relative_with_complex_base():
    assert resolve('#s', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/d;p?q#s'


def test_middle_hashtag_relative_with_complex_base():
    assert resolve('g#s', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g#s'


def test_middle_questionmark_and_hashtag_relative_with_complex_base():
    assert resolve('g?y#s', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g?y#s'


def test_semicolon_prefix_relative_with_complex_base():
    assert resolve(';x', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/;x'


def test_middle_semicolon_relative_with_complex_base():
    assert resolve('g;x', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g;x'


def test_semicolon_questionmark_and_hashtag_relative_with_complex_base():
    assert resolve('g;x?y#s', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g;x?y#s'


def test_empty_relative_with_complex_base():
    assert resolve('', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/d;p?q'


def test_dot_relative_with_complex_base():
    assert resolve('.', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/'


def test_dot_slash_relative_with_complex_base():
    assert resolve('./', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/'


def test_double_dot_relative_with_complex_base():
    assert resolve('..', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/'


def test_double_dot_slash_relative_with_complex_base():
    assert resolve('../', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/'


def test_double_dot_slash_g_relative_with_complex_base():
    assert resolve('../g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/g'


def test_double_dot_slash_double_dot_relative_with_complex_base():
    assert resolve('../..', 'file:///a/bb/ccc/d;p?q') == 'file:///a/'


def test_2x_dot_slash_double_dot_slash_relative_with_complex_base():
    assert resolve('../../', 'file:///a/bb/ccc/d;p?q') == 'file:///a/'


def test_2x_double_dot_slash_with_g_relative_with_complex_base():
    assert resolve('../../g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/g'


def test_2x_double_dot_slash_with_double_dot_relative_with_complex_base():
    assert resolve('../../..', 'file:///a/bb/ccc/d;p?q') == 'file:///'


def test_3x_double_dot_slash_relative_with_complex_base():
    assert resolve('../../../', 'file:///a/bb/ccc/d;p?q') == 'file:///'


def test_3x_double_dot_slash_with_g_relative_with_complex_base():
    assert resolve('../../../g', 'file:///a/bb/ccc/d;p?q') == 'file:///g'


def test_4x_double_dot_slash_with_g_relative_with_complex_base():
    assert resolve('../../../../g', 'file:///a/bb/ccc/d;p?q') == 'file:///g'


def test_slash_dot_slash_g_relative_with_complex_base():
    assert resolve('/./g', 'file:///a/bb/ccc/d;p?q') == 'file:///g'


def test_slash_double_dot_slash_g_relative_with_complex_base():
    assert resolve('/../g', 'file:///a/bb/ccc/d;p?q') == 'file:///g'


def test_dot_suffix_relative_with_complex_base():
    assert resolve('g.', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g.'


def test_dot_prefix_relative_with_complex_base():
    assert resolve('.g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/.g'


def test_double_dot_suffix_relative_with_complex_base():
    assert resolve('g..', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g..'


def test_double_dot_prefix_relative_with_complex_base():
    assert resolve('..g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/..g'


def test_dot_slash_double_dot_slash_g_relative_with_complex_base():
    assert resolve('./../g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/g'


def test_dot_slash_g_slash_dot_relative_with_complex_base():
    assert resolve('./g/.', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g/'


def test_g_slash_dot_slash_h_relative_with_complex_base():
    assert resolve('g/./h', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g/h'


def test_g_slash_double_dot_slash_h_relative_with_complex_base():
    assert resolve('g/../h', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/h'


def test_g_semicolon_x_equals_1_slash_dot_slash_y_relative_with_complex_base():
    assert resolve('g;x=1/./y', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g;x=1/y'


def test_g_semicolon_x_equals_1_slash_double_dot_slash_y_relative_with_complex_base():
    assert resolve('g;x=1/../y', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/y'


def test_g_questionmark_y_slash_dot_slash_x_relative_with_complex_base():
    assert resolve('g?y/./x', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g?y/./x'


def test_g_questionmark_y_slash_double_dot_slash_x_relative_with_complex_base():
    assert resolve('g?y/../x', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g?y/../x'


def test_g_hash_s_slash_dot_slash_x_relative_with_complex_base():
    assert resolve('g#s/./x', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g#s/./x'


def test_g_hash_s_slash_double_dot_slash_x_relative_with_complex_base():
    assert resolve('g#s/../x', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g#s/../x'


def test_http_colon_g_relative_with_complex_base():
    assert resolve('http:g', 'file:///a/bb/ccc/d;p?q') == 'http:g'


def test_complex_relative_with_complex_base():
    assert (
        resolve(
            '//example.org/.././useless/../../scheme-relative',
            'http://example.com/some/deep/directory/and/file#with-a-fragment',
        )
        == 'http://example.org/scheme-relative'
    )


def test_relative_with_complex_base_without_double_slash_after_scheme():
    assert resolve('a', 'tag:example') == 'tag:a'


def test_relative_with_complex_base_without_double_slash_after_scheme_with_one_slash():
    assert resolve('a', 'tag:example/foo') == 'tag:example/a'


def test_relative_a_with_base_without_double_slash_after_scheme_with_two_slash():
    assert resolve('a', 'tag:example/foo/') == 'tag:example/foo/a'


def test_relative_with_triple_dot_segment_and_double_dot_and_base():
    assert (
        resolve('../.../../', 'http://example.org/a/b/c/') == 'http://example.org/a/b/'
    )


def test_relative_with_triple_dot_segment_and_2x_double_dot_and_base():
    assert (
        resolve('../.../../../', 'http://example.org/a/b/c/') == 'http://example.org/a/'
    )


def test_questionmark_prefix_relative_with_complex_base_with_dot():
    assert resolve('?y', 'http://a/bb/ccc/./d;p?q') == 'http://a/bb/ccc/./d;p?y'
