"""
The functions 'remove_dot_segments()', 'resolve()' and 'is_character_allowed_after_relative_path_segment()' are direct ports from [relative-to-absolute-iri.js](https://github.com/rubensworks/relative-to-absolute-iri.js)
"""

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

def resolve(relative_iri: str, base_iri: str = "") -> str:
    #     """
    #     Resolves a given relative IRI to an absolute IRI.

    #     :param base_iri: the base IRI.
    #     :param relative_iri: the relative IRI.

    #     :return: the absolute IRI.
    #     """

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