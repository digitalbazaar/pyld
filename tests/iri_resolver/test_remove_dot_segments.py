from pyld.iri_resolver import remove_dot_segments

# Tests ported from relative-to-absolute-iri.js: https://github.com/rubensworks/relative-to-absolute-iri.js/blob/master/test/Resolve-test.ts
# (c) Ruben Taelman <stevenlevithan.com>


# ---------- Tests for remove_dot_segments() ----------
def test_no_slash():
    assert remove_dot_segments('abc') == '/abc'


def test_single_slash_end():
    assert remove_dot_segments('abc/') == '/abc/'


def test_leading_slash():
    assert remove_dot_segments('/abc') == '/abc'


def test_leading_and_trailing_slash():
    assert remove_dot_segments('/abc/') == '/abc/'


def test_dot():
    assert remove_dot_segments('/.') == '/'


def test_dotdot():
    assert remove_dot_segments('/..') == '/'


def test_parent_directory():
    assert remove_dot_segments('/abc/..') == '/'


def test_too_many_parents():
    assert remove_dot_segments('/abc/../../..') == '/'


def test_current_directory():
    assert remove_dot_segments('/abc/.') == '/abc/'


def test_inbetween_parent_directory():
    assert remove_dot_segments('/abc/../def/') == '/def/'


def test_inbetween_parent_directory_2():
    assert remove_dot_segments('mid/content=5/../6') == '/mid/6'


def test_inbetween_current_directory():
    assert remove_dot_segments('/abc/./def/') == '/abc/def/'


def test_multiple_parents():
    assert remove_dot_segments('/abc/def/ghi/../..') == '/abc/'


def test_multiple_currents():
    assert remove_dot_segments('/abc/././.') == '/abc/'


def test_mixed_current_and_parent():
    assert remove_dot_segments('/abc/def/./ghi/../..') == '/abc/'


def test_another_mixed_current_and_parent():
    assert remove_dot_segments('/a/b/c/./../../g') == '/a/g'


def test_not_modify_fragments():
    assert remove_dot_segments('/abc#abcdef') == '/abc#abcdef'


def test_not_modify_paths_in_fragments():
    assert remove_dot_segments('/abc#a/bc/def') == '/abc#a/bc/def'


def test_not_modify_current_paths_in_fragments():
    assert remove_dot_segments('/abc#a/./bc/def') == '/abc#a/./bc/def'


def test_not_modify_parent_paths_in_fragments():
    assert remove_dot_segments('/abc#a/../bc/def') == '/abc#a/../bc/def'


def test_not_modify_queries():
    assert remove_dot_segments('/abc?abcdef') == '/abc?abcdef'


def test_not_modify_paths_in_queries():
    assert remove_dot_segments('/abc?a/bc/def') == '/abc?a/bc/def'


def test_not_modify_current_paths_in_queries():
    assert remove_dot_segments('/abc?a/./bc/def') == '/abc?a/./bc/def'


def test_not_modify_parent_paths_in_queries():
    assert remove_dot_segments('/abc?a/../bc/def') == '/abc?a/../bc/def'


def test_mixed_current_and_parent_with_fragment():
    assert remove_dot_segments('/abc/def/./ghi/../..#abc') == '/abc#abc'


def test_fragment_without_another_path():
    assert remove_dot_segments('#abc') == '/#abc'


def test_not_remove_zerolength_segments():
    assert remove_dot_segments('/abc//def/') == '/abc//def/'


def test_parent_into_zerolength_segments():
    assert remove_dot_segments('/abc//def//../') == '/abc//def/'


def test_current_over_zerolength_segments():
    assert remove_dot_segments('/abc//def//./') == '/abc//def//'


def test_resolve_query_against_non_slash():
    assert remove_dot_segments('/def/ghi?a=b') == '/def/ghi?a=b'


def test_resolve_query_against_slash():
    assert remove_dot_segments('/def/?a=b') == '/def/?a=b'


def test_resolve_double_dot_and_query():
    assert remove_dot_segments('/def/..?a=b') == '/?a=b'


def test_append_dot_g_after_slash():
    assert remove_dot_segments('/a/bb/ccc/.g') == '/a/bb/ccc/.g'


def test_append_g_dot_after_slash():
    assert remove_dot_segments('/a/bb/ccc/g.') == '/a/bb/ccc/g.'


def test_append_double_dot_g_after_slash():
    assert remove_dot_segments('/a/bb/ccc/..g') == '/a/bb/ccc/..g'


def test_append_g_double_dot_after_slash():
    assert remove_dot_segments('/a/bb/ccc/g..') == '/a/bb/ccc/g..'


def test_end_with_slash_if_trailing_slash_dot():
    assert remove_dot_segments('/a/bb/ccc/./g/.') == '/a/bb/ccc/g/'


def test_triple_dots_as_normal_segment():
    assert remove_dot_segments('/invalid/...') == '/invalid/...'


def test_triple_dots_as_normal_segment_followed_by_double_dots():
    assert remove_dot_segments('/invalid/.../..') == '/invalid/'


def test_four_dots_as_normal_segment():
    assert (
        remove_dot_segments('/invalid/../..../../../.../.htaccess') == '/.../.htaccess'
    )


def test_segment_with_dot_and_invalid_char_as_normal_segment():
    assert remove_dot_segments('/invalid/../.a/../../.../.htaccess') == '/.../.htaccess'
