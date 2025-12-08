"""
- The functions 'remove_dot_segments()', 'resolve()' and 'is_character_allowed_after_relative_path_segment()' are direct ports from [relative-to-absolute-iri.js](https://github.com/rubensworks/relative-to-absolute-iri.js) (c) Ruben Taelman <ruben.taelman@ugent.be>
- The 'unresolve()' function is a move and rename of the 'remove_base()' function from 'jsonld.py'
"""

from urllib.parse import ParseResult, urlparse, urlunparse


def is_character_allowed_after_relative_path_segment(ch: str) -> bool:
    """Return True if a character is valid after '.' or '..' in a path segment."""
    return not ch or ch in ('#', '?', '/')


def remove_dot_segments(path: str) -> str:
    """
    Removes dot segments ('.' and '..') from a URL path,
    as described in https://www.ietf.org/rfc/rfc3986.txt (page 32).

    :param path: the IRI path to remove dot segments from.

    :return: a path with normalized dot segments, will always start with a '/'.
    """
    segment_buffers = []
    i = 0
    length = len(path)

    while i < length:
        ch = path[i]

        if ch == '/':
            # Handle '/.' or '/..'
            if i + 1 < length and path[i + 1] == '.':
                # Handle '/..'
                if i + 2 < length and path[i + 2] == '.':
                    next_ch = path[i + 3] if i + 3 < length else ''
                    if not is_character_allowed_after_relative_path_segment(next_ch):
                        segment_buffers.append([])
                        i += 1
                        continue

                    # Go to parent directory
                    if segment_buffers:
                        segment_buffers.pop()

                    # Add trailing slash segment if ends with '/..'
                    if i + 3 >= length:
                        segment_buffers.append([])

                    i += 3
                    continue

                # Handle '/.'
                next_ch = path[i + 2] if i + 2 < length else ''
                if not is_character_allowed_after_relative_path_segment(next_ch):
                    segment_buffers.append([])
                    i += 1
                    continue

                # Add trailing slash if ends with '/.'
                if i + 2 >= length:
                    segment_buffers.append([])

                # Stay in current directory — skip
                i += 2
                continue

            # Regular '/' starts a new segment
            segment_buffers.append([])
            i += 1
            continue

        elif ch in ('#', '?'):
            # Query or fragment → append unchanged and stop
            if not segment_buffers:
                segment_buffers.append([])
            segment_buffers[-1].append(path[i:])

            # Break the while loop
            break

        else:
            # Regular character → append to current segment
            if not segment_buffers:
                segment_buffers.append([])
            segment_buffers[-1].append(ch)
            i += 1

    return '/' + '/'.join(''.join(buffer) for buffer in segment_buffers)


def remove_dot_segments_of_path(iri: str, colon_position: int) -> str:
    """
    Remove dot segments from the path portion of an IRI (RFC 3986 §5.2.4).

    :param iri: an IRI (or part of IRI).
    :param colonPosition: the position of the first ':' in the IRI.

    :return: the IRI where dot segments were removed.
    """
    # Determine where to start looking for the first '/' that indicates the start of the path
    if colon_position >= 0:
        if len(iri) > colon_position + 2 and iri[colon_position + 1] == '/' and iri[colon_position + 2] == '/':
            search_offset = colon_position + 3
        else:
            search_offset = colon_position + 1
    else:
        if len(iri) > 1 and iri[0] == '/' and iri[1] == '/':
            search_offset = 2
        else:
            search_offset = 0

    # Find the start of the path
    path_separator = iri.find('/', search_offset)
    if path_separator < 0:
        return iri

    base = iri[:path_separator]
    path = iri[path_separator:]

    # Remove dot segments from the path
    return base + remove_dot_segments(path)

def resolve(relative_iri: str, base_iri: str = None) -> str:
    #     """
    #     Resolves a given relative IRI to an absolute IRI.

    #     :param base_iri: the base IRI.
    #     :param relative_iri: the relative IRI.

    #     :return: the absolute IRI.
    #     """
    base_iri = base_iri or ''
    base_fragment_pos = base_iri.find("#")

    # Ignore any fragments in the base IRI
    if base_fragment_pos > 0:
        base_iri = base_iri[:base_fragment_pos]

    # Convert empty value directly to base IRI
    if not relative_iri:
        if ":" not in base_iri:
            raise ValueError(f"Found invalid baseIRI '{base_iri}' for value '{relative_iri}'")
        return base_iri

    # If the value starts with a query character, concat directly (strip existing query)
    if relative_iri.startswith("?"):
        base_query_pos = base_iri.find("?")
        if base_query_pos > 0:
            base_iri = base_iri[:base_query_pos]
        return base_iri + relative_iri

    # If the value starts with a fragment character, concat directly
    if relative_iri.startswith("#"):
        return base_iri + relative_iri

    # Ignore baseIRI if it is empty
    if not base_iri:
        relative_colon_pos = relative_iri.find(":")
        if relative_colon_pos < 0:
            raise ValueError(f"Found invalid relative IRI '{relative_iri}' for a missing baseIRI")
        return remove_dot_segments_of_path(relative_iri, relative_colon_pos)

    # Ignore baseIRI if the value is absolute
    value_colon_pos = relative_iri.find(":")
    if value_colon_pos >= 0:
        return remove_dot_segments_of_path(relative_iri, value_colon_pos)

    # baseIRI must be absolute
    base_colon_pos = base_iri.find(":")
    if base_colon_pos < 0:
        raise ValueError(f"Found invalid baseIRI '{base_iri}' for value '{relative_iri}'")

    base_scheme = base_iri[:base_colon_pos + 1]

    # Inherit base scheme if relative starts with '//'
    if relative_iri.startswith("//"):
        return base_scheme + remove_dot_segments_of_path(relative_iri, value_colon_pos)

    # Determine where the path of base starts
    if base_iri.find("//", base_colon_pos) == base_colon_pos + 1:
        base_slash_after_colon_pos = base_iri.find("/", base_colon_pos + 3)
        if base_slash_after_colon_pos < 0:
            if len(base_iri) > base_colon_pos + 3:
                return base_iri + "/" + remove_dot_segments_of_path(relative_iri, value_colon_pos)
            else:
                return base_scheme + remove_dot_segments_of_path(relative_iri, value_colon_pos)
    else:
        base_slash_after_colon_pos = base_iri.find("/", base_colon_pos + 1)
        if base_slash_after_colon_pos < 0:
            return base_scheme + remove_dot_segments_of_path(relative_iri, value_colon_pos)

    # If relative starts with '/', append after base authority
    if relative_iri.startswith("/"):
        return base_iri[:base_slash_after_colon_pos] + remove_dot_segments(relative_iri)

    base_path = base_iri[base_slash_after_colon_pos:]
    last_slash = base_path.rfind("/")

    # Ignore everything after last '/' in base path
    if last_slash >= 0 and last_slash < len(base_path) - 1:
        base_path = base_path[:last_slash + 1]
        if (relative_iri.startswith(".") and 
            not relative_iri.startswith("..") and 
            not relative_iri.startswith("./") and 
            len(relative_iri) > 2):
            relative_iri = relative_iri[1:]

    relative_iri = base_path + relative_iri
    relative_iri = remove_dot_segments(relative_iri)

    return base_iri[:base_slash_after_colon_pos] + relative_iri

def unresolve(absolute_iri: str, base_iri: str = ""):
    """
    Unresolves a given absolute IRI to an IRI relative to the given base IRI.

    :param base: the base IRI.
    :param iri: the absolute IRI.

    :return: the relative IRI if relative to base, otherwise the absolute IRI.
    """
    # skip IRI processing
    if not base_iri:
        return absolute_iri

    base = urlparse(base_iri)

    if not base.scheme:
        raise ValueError(f"Found invalid baseIRI '{base_iri}' for value '{absolute_iri}'")

    # compute authority (netloc) and strip default ports
    base_authority = parse_authority(base)

    rel = urlparse(absolute_iri)
    # compute authority (netloc) and strip default ports
    rel_authority = parse_authority(rel)

    # schemes and network locations (authorities) don't match, don't alter IRI
    if not (base.scheme == rel.scheme and base_authority == rel_authority):
        return absolute_iri

    # remove path segments that match (do not remove last segment unless there
    # is a hash or query
    base_segments = remove_dot_segments(base.path).split('/')
    iri_segments = remove_dot_segments(rel.path).split('/')
    last = 0 if (rel.fragment or rel.query) else 1
    while (len(base_segments) and len(iri_segments) > last and
            base_segments[0] == iri_segments[0]):
        base_segments.pop(0)
        iri_segments.pop(0)

    # use '../' for each non-matching base segment
    rval = ''
    if len(base_segments):
        # don't count the last segment (if it ends with '/' last path doesn't
        # count and if it doesn't end with '/' it isn't a path)
        base_segments.pop()
        rval += '../' * len(base_segments)

    # prepend remaining segments
    rval += '/'.join(iri_segments)

    # relative IRIs must not have the form of a keyword
    if rval and rval[0] == '@':
        rval = './' + rval

    # build relative IRI using urlunparse with empty scheme/netloc
    return urlunparse(('', '', rval, '', rel.query or '', rel.fragment or '')) or './'

def parse_authority(parsed_iri: ParseResult) -> str:
    """
    Compute authority (netloc) and strip default ports
    
    :param parsed_iri: Description
    :return: Description
    :rtype: str
    """ 
    base_authority = parsed_iri.netloc or None
    
    try:
        base_port = parsed_iri.port
    except Exception:
        base_port = None
    
    if base_authority is not None and base_port is not None:
        if (parsed_iri.scheme == 'https' and base_port == 443) or (parsed_iri.scheme == 'http' and base_port == 80):
            base_authority = base_authority.rsplit(':', 1)[0]
    return base_authority