def resolve(relative_iri: str, base_iri: str | None = None) -> str:
    # TODO: implement
    return ''

def remove_dot_segments(path: str) -> str:
    """
    Removes dot segments from a URL path.

    :param path: the path to remove dot segments from.

    :return: a path with normalized dot segments.
    """

    # RFC 3986 5.2.4 (reworked)

    # empty path shortcut
    if len(path) == 0:
        return ''

    input = path.split('/')
    output = []

    while len(input) > 0:
        next = input.pop(0)
        done = len(input) == 0

        if next == '.':
            if done:
                # ensure output has trailing /
                output.append('')
            continue

        if next == '..':
            if len(output) > 0:
                output.pop()
            if done:
                # ensure output has trailing /
                output.append('')
            continue

        output.append(next)

    # ensure output has leading /
    # merge path segments from section 5.2.3
    # note that if the path includes no segments, the entire path is removed
    if len(output) > 0 and path.startswith('/') and output[0] != '':
        output.insert(0, '')
    if len(output) == 1 and output[0] == '':
        return '/'

    return '/'.join(output)
