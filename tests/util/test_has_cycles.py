import sys

import pytest

from pyld.util import has_cycles


@pytest.mark.parametrize('cyclic', [False, True])
def test_checks_graphs_deeper_than_python_recursion_limit(cyclic):
    document = []
    current = document
    for _ in range(sys.getrecursionlimit() + 50):
        child = {'items': []}
        current.append(child)
        current = child['items']
    if cyclic:
        current.append(document)

    assert has_cycles(document) is cyclic


def test_shared_containers_are_acyclic():
    shared = {'items': [1, 2]}

    assert not has_cycles([shared, shared, {'shared': shared}])
