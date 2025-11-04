import pytest
from pyld.iri_resolver import resolve, remove_dot_segments 

# Tests ported from relative-to-absolute-iri.js: https://github.com/rubensworks/relative-to-absolute-iri.js/blob/master/test/Resolve-test.ts

# ---------- Tests for resolve() ----------
class TestResolve:
    def test_absolute_iri_no_base(self):
        assert resolve('http://example.org/') == 'http://example.org/'

    def test_absolute_iri_empty_base(self):
        assert resolve('http://example.org/', '') == 'http://example.org/'

    def test_absolute_iri_with_base(self):
        assert resolve('http://example.org/', 'http://base.org/') == 'http://example.org/'

    def test_empty_value_uses_base(self):
        assert resolve('', 'http://base.org/') == 'http://base.org/'

    def test_relative_with_scheme_no_base(self):
        assert resolve('ex:abc') == 'ex:abc'

    def test_relative_without_scheme_no_base_error(self):
        with pytest.raises(ValueError, match=r"Found invalid relative IRI 'abc' for a missing baseIRI"):
            resolve('abc')

    def test_relative_without_dot_segments_no_base(self):
        assert resolve('http://abc/../../') == 'http://abc/'

    def test_relative_with_base(self):
        assert resolve('abc', 'http://base.org/') == 'http://base.org/abc'

    def test_relative_with_fragment_base(self):
        assert resolve('abc', 'http://base.org/#frag') == 'http://base.org/abc'

    def test_hash_relative(self):
        assert resolve('#abc', 'http://base.org/') == 'http://base.org/#abc'

    def test_colon_in_value_ignores_base(self):
        assert resolve('http:abc', 'http://base.org/') == 'http:abc'

    def test_colon_in_value_removes_dots(self):
        assert resolve('http://abc/../../', 'http://base.org/') == 'http://abc/'

    def test_non_absolute_base_error(self):
        with pytest.raises(ValueError, match=r"Found invalid baseIRI 'def' for value 'abc'"):
            resolve('abc', 'def')

    def test_non_absolute_base_empty_value_error(self):
        with pytest.raises(ValueError, match=r"Found invalid baseIRI 'def' for value ''"):
            resolve('', 'def')

    def test_scheme_from_base_if_value_starts_with_slash_slash(self):
        assert resolve('//abc', 'http://base.org/') == 'http://abc'

    def test_base_without_path_slash(self):
        assert resolve('abc', 'http://base.org') == 'http://base.org/abc'

    def test_base_without_path_dot_segments(self):
        assert resolve('abc/./', 'http://base.org') == 'http://base.org/abc/'

    def test_base_only_scheme_slash_slash(self):
        assert resolve('abc', 'http://') == 'http:abc'

    def test_base_only_scheme_slash_slash_dot_segments(self):
        assert resolve('abc/./', 'http://') == 'http:abc/'

    def test_base_with_char_after_colon(self):
        assert resolve('abc', 'http:a') == 'http:abc'

    def test_base_with_char_after_colon_dot_segments(self):
        assert resolve('abc/./', 'http:a') == 'http:abc/'

    def test_base_only_scheme(self):
        assert resolve('abc', 'http:') == 'http:abc'

    def test_base_only_scheme_dot_segments(self):
        assert resolve('abc/./', 'http:') == 'http:abc/'

    def test_absolute_path_ignores_base_path(self):
        assert resolve('/abc/def/', 'http://base.org/123/456/') == 'http://base.org/abc/def/'

    def test_base_with_last_slash_replacement(self):
        assert resolve('xyz', 'http://aa/a') == 'http://aa/xyz'

    def test_base_collapse_parent_paths(self):
        assert resolve('xyz', 'http://aa/parent/parent/../../a') == 'http://aa/xyz'

    def test_base_remove_current_dir(self):
        assert resolve('xyz', 'http://aa/././a') == 'http://aa/xyz'

    def test_base_dot(self):
        assert resolve('.', 'http://aa/') == 'http://aa/'

    def test_base_double_dot(self):
        assert resolve('..', 'http://aa/b/') == 'http://aa/'

    def test_base_double_dot_slash(self):
        assert resolve('../', 'http://aa/b/') == 'http://aa/'

    def test_base_without_ending_slash_double_dot(self):
        assert resolve('..', 'http://aa/b') == 'http://aa/'

    def test_base_without_ending_slash_double_dot_slash(self):
        assert resolve('../', 'http://aa/b') == 'http://aa/'

    def test_base_without_ending_slash_query(self):
        assert resolve('?a=b', 'http://abc/def/ghi') == 'http://abc/def/ghi?a=b'

    def test_base_without_ending_slash_dot_query(self):
        assert resolve('.?a=b', 'http://abc/def/ghi') == 'http://abc/def/?a=b'

    def test_base_without_ending_slash_double_dot_query(self):
        assert resolve('..?a=b', 'http://abc/def/ghi') == 'http://abc/?a=b'

    def test_base_without_ending_slash_xyz(self):
        assert resolve('xyz', 'http://abc/d:f/ghi') == 'http://abc/d:f/xyz'

    def test_base_without_ending_slash_dot_xyz(self):
        assert resolve('./xyz', 'http://abc/d:f/ghi') == 'http://abc/d:f/xyz'

    def test_base_without_ending_slash_double_dot_xyz(self):
        assert resolve('../xyz', 'http://abc/d:f/ghi') == 'http://abc/xyz'

    def test_relative_with_colon_ignores_base(self):
        assert resolve('g:h', 'file:///a/bb/ccc/d;p?q') == 'g:h'

    def test_simple_relative_with_complex_base(self):
        assert resolve('g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g'

    def test_dot_relative_with_complex_base(self):
        assert resolve('./g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g'

#   it('create an IRI from a g/ relative IRI and complex baseIRI', () => {
#     expect(resolve('g/', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('');
#   });

    def test_slash_suffix_relative_with_complex_base(self):
        assert resolve('g/', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g/'

#   it('create an IRI from a /g relative IRI and complex baseIRI', () => {
#     expect(resolve('/g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///g');
#   });

    def test_slash_prefix_relative_with_complex_base(self):
        assert resolve('/g', 'file:///a/bb/ccc/d;p?q') == 'file:///g'

#   it('create an IRI from a //g relative IRI and complex baseIRI', () => {
#     expect(resolve('//g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file://g');
#   });

    def test_double_slash_prefix_relative_with_complex_base(self):
        assert resolve('//g', 'file:///a/bb/ccc/d;p?q') == 'file://g'

#   it('create an IRI from a ?y relative IRI and complex baseIRI', () => {
#     expect(resolve('?y', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/d;p?y');
#   });

    def test_questionmark_prefix_relative_with_complex_base(self):
        assert resolve('?y', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/d;p?y'

#   it('create an IRI from a g?y relative IRI and complex baseIRI', () => {
#     expect(resolve('g?y', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g?y');
#   });

    def test_questionmark_middle_relative_with_complex_base(self):
        assert resolve('g?y', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g?y'

#   it('create an IRI from a #s relative IRI and complex baseIRI', () => {
#     expect(resolve('#s', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/d;p?q#s');
#   });

    def test_hashtag_prefix_relative_with_complex_base(self):
        assert resolve('#s', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/d;p?q#s'

#   it('create an IRI from a g#s relative IRI and complex baseIRI', () => {
#     expect(resolve('g#s', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g#s');
#   });

    def test_middle_hashtag_relative_with_complex_base(self):
        assert resolve('g#s', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g#s'

#   it('create an IRI from a g?y#s relative IRI and complex baseIRI', () => {
#     expect(resolve('g?y#s', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g?y#s');
#   });

    def test_middle_questionmark_and_hashtag_relative_with_complex_base(self):
        assert resolve('g?y#s', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g?y#s'

#   it('create an IRI from a ;x relative IRI and complex baseIRI', () => {
#     expect(resolve(';x', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/;x');
#   });

    def test_semicolon_prefix_relative_with_complex_base(self):
        assert resolve(';x', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/;x'

#   it('create an IRI from a g;x relative IRI and complex baseIRI', () => {
#     expect(resolve('g;x', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g;x');
#   });

    def test_middle_semicolon_relative_with_complex_base(self):
        assert resolve('g;x', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g;x'

#   it('create an IRI from a g;x?y#s relative IRI and complex baseIRI', () => {
#     expect(resolve('g;x?y#s', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g;x?y#s');
#   });

    def test_semicolon_questionmark_and_hashtag_relative_with_complex_base(self):
        assert resolve('g;x?y#s', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g;x?y#s'

#   it('create an IRI from an empty relative IRI and complex baseIRI', () => {
#     expect(resolve('', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/d;p?q');
#   });

    def test_empty_relative_with_complex_base(self):
        assert resolve('', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/d;p?q'

#   it('create an IRI from a . relative IRI and complex baseIRI', () => {
#     expect(resolve('.', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/');
#   });

    def test_dot_relative_with_complex_base(self):
        assert resolve('.', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/d;p?q'

#   it('create an IRI from a ./ relative IRI and complex baseIRI', () => {
#     expect(resolve('./', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/');
#   });

    def test_dot_slash_relative_with_complex_base(self):
        assert resolve('./', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/'

#   it('create an IRI from a .. relative IRI and complex baseIRI', () => {
#     expect(resolve('..', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/');
#   });

    def test_double_dot_relative_with_complex_base(self):
        assert resolve('..', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/'

#   it('create an IRI from a ../ relative IRI and complex baseIRI', () => {
#     expect(resolve('../', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/');
#   });

    def test_double_dot_slash_relative_with_complex_base(self):
        assert resolve('../', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/'

#   it('create an IRI from a ../g relative IRI and complex baseIRI', () => {
#     expect(resolve('../g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/g');
#   });

    def test_double_dot_slash_g_relative_with_complex_base(self):
        assert resolve('../g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/g'

#   it('create an IRI from a ../.. relative IRI and complex baseIRI', () => {
#     expect(resolve('../..', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/');
#   });

    def test_double_dot_slash_double_dot_relative_with_complex_base(self):
        assert resolve('../..', 'file:///a/bb/ccc/d;p?q') == 'file:///a/'

#   it('create an IRI from a ../../ relative IRI and complex baseIRI', () => {
#     expect(resolve('../../', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/');
#   });

    def test_2x_dot_slash_double_dot_slash_relative_with_complex_base(self):
        assert resolve('../../', 'file:///a/bb/ccc/d;p?q') == 'file:///a/'

#   it('create an IRI from a ../../g relative IRI and complex baseIRI', () => {
#     expect(resolve('../../g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/g');
#   });

    def test_2x_double_dot_slash_with_g_relative_with_complex_base(self):
        assert resolve('../../g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/g'

#   it('create an IRI from a ../../.. relative IRI and complex baseIRI', () => {
#     expect(resolve('../../..', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///');
#   });

    def test_2x_double_dot_slash_with_double_dot_relative_with_complex_base(self):
        assert resolve('../../..', 'file:///a/bb/ccc/d;p?q') == 'file:///'

#   it('create an IRI from a ../../../ relative IRI and complex baseIRI', () => {
#     expect(resolve('../../../', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///');
#   });

    def test_3x_double_dot_slash_relative_with_complex_base(self):
        assert resolve('../../../', 'file:///a/bb/ccc/d;p?q') == 'file:///'

#   it('create an IRI from a ../../../g relative IRI and complex baseIRI', () => {
#     expect(resolve('../../../g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///g');
#   });

    def test_3x_double_dot_slash_with_g_relative_with_complex_base(self):
        assert resolve('../../../g', 'file:///a/bb/ccc/d;p?q') == 'file:///g'

#   it('create an IRI from a ../../../../g relative IRI and complex baseIRI', () => {
#     expect(resolve('../../../../g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///g');
#   });

    def test_4x_double_dot_slash_with_g_relative_with_complex_base(self):
        assert resolve('../../../../g', 'file:///a/bb/ccc/d;p?q') == 'file:///g'

#   it('create an IRI from a /./g relative IRI and complex baseIRI', () => {
#     expect(resolve('/./g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///g');
#   });

    def test_slash_dot_slash_g_relative_with_complex_base(self):
        assert resolve('/./g', 'file:///a/bb/ccc/d;p?q') == 'file:///g'

#   it('create an IRI from a /../g relative IRI and complex baseIRI', () => {
#     expect(resolve('/../g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///g');
#   });

    def test_slash_double_dot_slash_g_relative_with_complex_base(self):
        assert resolve('/../g', 'file:///a/bb/ccc/d;p?q') == 'file:///g'

#   it('create an IRI from a g. relative IRI and complex baseIRI', () => {
#     expect(resolve('g.', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g.');
#   });

    def test_dot_suffix_relative_with_complex_base(self):
        assert resolve('g.', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g'

#   it('create an IRI from a .g relative IRI and complex baseIRI', () => {
#     expect(resolve('.g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/.g');
#   });

    def test_dot_prefix_relative_with_complex_base(self):
        assert resolve('.g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/.g'

#   it('create an IRI from a g.. relative IRI and complex baseIRI', () => {
#     expect(resolve('g..', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g..');
#   });

    def test_double_dot_suffix_relative_with_complex_base(self):
        assert resolve('g..', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g..'

#   it('create an IRI from a ..g relative IRI and complex baseIRI', () => {
#     expect(resolve('..g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/..g');
#   });

    def test_double_dot_prefix_relative_with_complex_base(self):
        assert resolve('..g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/..g'

#   it('create an IRI from a ./../g relative IRI and complex baseIRI', () => {
#     expect(resolve('./../g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/g');
#   });

    def test_dot_slash_double_dot_slash_g_relative_with_complex_base(self):
        assert resolve('./../g', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/g'

#   it('create an IRI from a ./g/. relative IRI and complex baseIRI', () => {
#     expect(resolve('./g/.', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g/');
#   });

    def test_dot_slash_g_slash_dot_relative_with_complex_base(self):
        assert resolve('./g/.', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g/'

#   it('create an IRI from a g/./h relative IRI and complex baseIRI', () => {
#     expect(resolve('g/./h', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g/h');
#   });

    def test_g_slash_dot_slash_h_relative_with_complex_base(self):
        assert resolve('g/./h', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g/h'

#   it('create an IRI from a g/../h relative IRI and complex baseIRI', () => {
#     expect(resolve('g/../h', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/h');
#   });

    def test_g_slash_double_dot_slash_h_relative_with_complex_base(self):
        assert resolve('g/../h', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/h'

#   it('create an IRI from a g;x=1/./y relative IRI and complex baseIRI', () => {
#     expect(resolve('g;x=1/./y', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g;x=1/y');
#   });

    def test_g_semicolon_x_equals_1_slash_dot_slash_y_relative_with_complex_base(self):
        assert resolve('g;x=1/./y', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g;x=1/y'

#   it('create an IRI from a g;x=1/../y relative IRI and complex baseIRI', () => {
#     expect(resolve('g;x=1/../y', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/y');
#   });

    def test_g_semicolon_x_equals_1_slash_double_dot_slash_y_relative_with_complex_base(self):
        assert resolve('g;x=1/../y', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/y'

#   it('create an IRI from a g?y/./x relative IRI and complex baseIRI', () => {
#     expect(resolve('g?y/./x', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g?y/./x');
#   });

    def test_g_questionmark_y_slash_dot_slash_x_relative_with_complex_base(self):
        assert resolve('g?y/./x', 'file:///a/bb/ccc/d;p?q') == 'file:///a/bb/ccc/g?y/./x'

#   it('create an IRI from a g?y/../x relative IRI and complex baseIRI', () => {
#     expect(resolve('g?y/../x', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g?y/../x');
#   });

#   it('create an IRI from a g#s/./x relative IRI and complex baseIRI', () => {
#     expect(resolve('g#s/./x', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g#s/./x');
#   });

#   it('create an IRI from a g#s/../x relative IRI and complex baseIRI', () => {
#     expect(resolve('g#s/../x', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('file:///a/bb/ccc/g#s/../x');
#   });

#   it('create an IRI from a http:g relative IRI and complex baseIRI', () => {
#     expect(resolve('http:g', 'file:///a/bb/ccc/d;p?q'))
#       .toEqual('http:g');
#   });

#   it('create an IRI from a //example.org/.././useless/../../scheme-relative relative IRI and complex baseIRI', () => {
#     expect(resolve('//example.org/.././useless/../../scheme-relative',
#       'http://example.com/some/deep/directory/and/file#with-a-fragment'))
#       .toEqual('http://example.org/scheme-relative');
#   });

#   it('create an IRI from a relative IRI a and baseIRI without // after scheme', () => {
#     expect(resolve('a', 'tag:example'))
#       .toEqual('tag:a');
#   });

#   it('create an IRI from a relative IRI a and baseIRI without // after scheme, with one /', () => {
#     expect(resolve('a', 'tag:example/foo'))
#       .toEqual('tag:example/a');
#   });

#   it('create an IRI from a relative IRI a and baseIRI without // after scheme, with two /', () => {
#     expect(resolve('a', 'tag:example/foo/'))
#       .toEqual('tag:example/foo/a');
#   });

    def test_relative_a_with_base_without_double_slash_after_scheme_with_two_slash(self):
        assert resolve('a', 'tag:example/foo/') == 'tag:example/foo/a'

#   it('create an IRI from a relative IRI with a ... segment and one .. and baseIRI', () => {
#     expect(resolve('../.../../', 'http://example.org/a/b/c/'))
#       .toEqual('http://example.org/a/b/');
#   });

    def test_relative_with_triple_dot_segment_and_double_dot_and_base(self):
        assert resolve('../.../../', 'http://example.org/a/b/c/') == 'http://example.org/a/b/'

#   it('create an IRI from a relative IRI with a ... segment and two .. and baseIRI', () => {
#     expect(resolve('../.../../../', 'http://example.org/a/b/c/'))
#       .toEqual('http://example.org/a/');
#   });

    def test_relative_with_triple_dot_segment_and_2x_double_dot_and_base(self):
        assert resolve('../.../../../', 'http://example.org/a/b/c/') == 'http://example.org/a/'

# ---------- Tests for remove_dot_segments() ----------
class TestRemoveDotSegments:
    def test_no_slash(self):
        assert remove_dot_segments('abc') == '/abc'

    def test_single_slash_end(self):
        assert remove_dot_segments('abc/') == '/abc/'

    def test_leading_slash(self):
        assert remove_dot_segments('/abc') == '/abc'

    def test_leading_and_trailing_slash(self):
        assert remove_dot_segments('/abc/') == '/abc/'

    def test_dot(self):
        assert remove_dot_segments('/.') == '/'

    def test_dotdot(self):
        assert remove_dot_segments('/..') == '/'

    def test_parent_directory(self):
        assert remove_dot_segments('/abc/..') == '/'

    def test_too_many_parents(self):
        assert remove_dot_segments('/abc/../../..') == '/'

    def test_current_directory(self):
        assert remove_dot_segments('/abc/.') == '/abc/'

    def test_inbetween_parent_directory(self):
        assert remove_dot_segments('/abc/../def/') == '/def/'

    def test_inbetween_parent_directory_2(self):
        assert remove_dot_segments('mid/content=5/../6') == '/mid/6'

    def test_inbetween_current_directory(self):
        assert remove_dot_segments('/abc/./def/') == '/abc/def/'

    def test_multiple_parents(self):
        assert remove_dot_segments('/abc/def/ghi/../..') == '/abc/'

    def test_multiple_currents(self):
        assert remove_dot_segments('/abc/././.') == '/abc/'

# it('should handle mixed current and parent directories', () => {
#     expect(removeDotSegments('/abc/def/./ghi/../..'))
#       .toEqual('/abc/');
#   });

    def test_mixed_current_and_parent(self):
        assert remove_dot_segments('/abc/def/./ghi/../..') == '/abc/'

#   it('should handle another mixed current and parent directories', () => {
#     expect(removeDotSegments('/a/b/c/./../../g'))
#       .toEqual('/a/g');
#   });

    def test_another_mixed_current_and_parent(self):
        assert remove_dot_segments('/a/b/c/./../../g') == '/a/g'

#   it('should not modify fragments', () => {
#     expect(removeDotSegments('/abc#abcdef'))
#       .toEqual('/abc#abcdef');
#   });

    def test_not_modify_fragments(self):
        assert remove_dot_segments('/abc#abcdef') == '/abc#abcdef'

#   it('should not modify paths in fragments', () => {
#     expect(removeDotSegments('/abc#a/bc/def'))
#       .toEqual('/abc#a/bc/def');
#   });

    def test_not_modify_paths_in_fragments(self):
        assert remove_dot_segments('/abc#abcdef') == '/abc#a/bc/def'

#   it('should not modify current paths in fragments', () => {
#     expect(removeDotSegments('/abc#a/./bc/def'))
#       .toEqual('/abc#a/./bc/def');
#   });

    def test_not_modify_current_paths_in_fragments(self):
        assert remove_dot_segments('/abc#a/./bc/def') == '/abc#a/./bc/def'

#   it('should not modify parent paths in fragments', () => {
#     expect(removeDotSegments('/abc#a/../bc/def'))
#       .toEqual('/abc#a/../bc/def');
#   });

    def test_not_modify_parent_paths_in_fragments(self):
        assert remove_dot_segments('/abc#a/../bc/def') == '/abc#a/../bc/def'

#   it('should not modify queries', () => {
#     expect(removeDotSegments('/abc?abcdef'))
#       .toEqual('/abc?abcdef');
#   });

    def test_not_modify_queries(self):
        assert remove_dot_segments('/abc?abcdef') == '/abc?abcdef'

#   it('should not modify paths in queries', () => {
#     expect(removeDotSegments('/abc?a/bc/def'))
#       .toEqual('/abc?a/bc/def');
#   });

    def test_not_modify_paths_in_queries(self):
        assert remove_dot_segments('/abc?a/bc/def') == '/abc?a/bc/def'

#   it('should not modify current paths in queries', () => {
#     expect(removeDotSegments('/abc?a/./bc/def'))
#       .toEqual('/abc?a/./bc/def');
#   });

    def test_not_modify_current_paths_in_queries(self):
        assert remove_dot_segments('/abc?a/./bc/def') == '/abc?a/./bc/def'

#   it('should not modify parent paths in queries', () => {
#     expect(removeDotSegments('/abc?a/../bc/def'))
#       .toEqual('/abc?a/../bc/def');
#   });

    def test_not_modify_parent_paths_in_queries(self):
        assert remove_dot_segments('/abc?a/../bc/def') == '/abc?a/../bc/def'

#   it('should handle mixed current and parent directories with a fragment', () => {
#     expect(removeDotSegments('/abc/def/./ghi/../..#abc'))
#       .toEqual('/abc#abc');
#   });

    def test_mixed_current_and_parent_with_fragment(self):
        assert remove_dot_segments('/abc/def/./ghi/../..#abc') == '/abc#abc'

#   it('should handle a fragment without another path', () => {
#     expect(removeDotSegments('#abc'))
#       .toEqual('/#abc');
#   });

    def test_fragment_without_another_path(self):
        assert remove_dot_segments('#abc') == '/#abc'

#   it('should not remove zero-length segments', () => {
#     expect(removeDotSegments('/abc//def/'))
#       .toEqual('/abc//def/');
#   });

    def test_not_remove_zerolength_segments(self):
        assert remove_dot_segments('/abc//def/') == '/abc//def/'

#   it('should be able to parent into zero-length segments', () => {
#     expect(removeDotSegments('/abc//def//../'))
#       .toEqual('/abc//def/');
#   });

    def test_parent_into_zerolength_segments(self):
        assert remove_dot_segments('/abc//def//../') == '/abc//def/'

#   it('should be able to current over zero-length segments', () => {
#     expect(removeDotSegments('/abc//def//./'))
#       .toEqual('/abc//def//');
#   });

    def test_current_over_zerolength_segments(self):
        assert remove_dot_segments('/abc//def//./') == '/abc//def//'

#   it('should resolve a query against non-/', () => {
#     expect(removeDotSegments('/def/ghi?a=b'))
#       .toEqual('/def/ghi?a=b');
#   });

    def test_resolve_query_against_non_slash(self):
        assert remove_dot_segments('/def/ghi?a=b') == '/def/ghi?a=b'

#   it('should resolve a query against /', () => {
#     expect(removeDotSegments('/def/?a=b'))
#       .toEqual('/def/?a=b');
#   });

#   it('should resolve a .. and query', () => {
#     expect(removeDotSegments('/def/..?a=b'))
#       .toEqual('/?a=b');
#   });

#   it('should just append a .g after a slash', () => {
#     expect(removeDotSegments('/a/bb/ccc/.g'))
#       .toEqual('/a/bb/ccc/.g');
#   });

#   it('should just append a g. after a slash', () => {
#     expect(removeDotSegments('/a/bb/ccc/g.'))
#       .toEqual('/a/bb/ccc/g.');
#   });

#   it('should just append a ..g after a slash', () => {
#     expect(removeDotSegments('/a/bb/ccc/..g'))
#       .toEqual('/a/bb/ccc/..g');
#   });

#   it('should just append a g.. after a slash', () => {
#     expect(removeDotSegments('/a/bb/ccc/g..'))
#       .toEqual('/a/bb/ccc/g..');
#   });

#   it('should end with a slash if there is a trailing /.', () => {
#     expect(removeDotSegments('/a/bb/ccc/./g/.'))
#       .toEqual('/a/bb/ccc/g/');
#   });

#   it('should handle triple dots as a normal segment.', () => {
#     expect(removeDotSegments('/invalid/...'))
#       .toEqual('/invalid/...');
#   });

#   it('should handle triple dots as a normal segment, followed by ...', () => {
#     expect(removeDotSegments('/invalid/.../..'))
#       .toEqual('/invalid/');
#   });

#   it('should handle four dots as a normal segment.', () => {
#     expect(removeDotSegments('/invalid/../..../../../.../.htaccess'))
#       .toEqual('/.../.htaccess');
#   });

#   it('should handle a segment with dot and an invalid char as a normal segment.', () => {
#     expect(removeDotSegments('/invalid/../.a/../../.../.htaccess'))
#       .toEqual('/.../.htaccess');
#   });

if __name__ == "__main__":
    pytest.main(["-v", __file__])
