import pytest
from rdflib import BNode, Literal
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID

from pyld.util import from_legacy_dataset


def test_from_legacy_dataset_restores_default_graph():
    """Ensure from_legacy_dataset correctly reconstructs the default graph."""
    legacy_data = {
        '@default': [
            {
                'subject': {'type': 'blank node', 'value': '_:s1'},
                'predicate': {'type': 'IRI', 'value': 'p1'},
                'object': {'type': 'literal', 'value': 'o1'},
            }
        ]
    }

    restored_dataset = from_legacy_dataset(legacy_data)

    for quad in restored_dataset.quads((None, None, None, None)):
        s, p, o, g = quad
        assert g == DATASET_DEFAULT_GRAPH_ID
        assert isinstance(s, BNode)
        assert str(s) == 's1'


@pytest.mark.parametrize(
    "legacy_data",
    [
        {
            'http://example.org': [
                {
                    'subject': {'type': 'blank node', 'value': '_:s1'},
                    'predicate': {'type': 'IRI', 'value': 'p1'},
                    'object': {'type': 'literal', 'value': 'o1'},
                }
            ]
        },
        {
            '_:g2': [
                {
                    'subject': {'type': 'blank node', 'value': '_:s2'},
                    'predicate': {'type': 'blank node', 'value': '_:p4'},
                    'object': {'type': 'literal', 'value': 'o2'},
                }
            ]
        },
    ],
)
def test_from_legacy_dataset_restores_blank_subject(legacy_data):
    """Ensure from_legacy_dataset correctly reconstructs a blank node subject."""
    restored_dataset = from_legacy_dataset(legacy_data)

    for quad in restored_dataset.quads((None, None, None, None)):
        s, p, o, g = quad
        if isinstance(s, BNode):
            assert not s.startswith('_:')
            assert (
                str(s)
                == legacy_data['_:' + str(g) if isinstance(g, BNode) else str(g)][0][
                    'subject'
                ]['value'][2:]
            )


@pytest.mark.parametrize(
    "legacy_data",
    [
        {
            '@default': [
                {
                    'subject': {'type': 'IRI', 'value': 's1'},
                    'predicate': {'type': 'blank node', 'value': '_:p2'},
                    'object': {'type': 'literal', 'value': 'o3'},
                }
            ]
        }
    ],
)
def test_from_legacy_dataset_restores_blank_predicate(legacy_data):
    """Ensure from_legacy_dataset correctly reconstructs a blank node predicate."""
    restored_dataset = from_legacy_dataset(legacy_data)

    for quad in restored_dataset.quads((None, None, None, None)):
        s, p, o, g = quad
        if isinstance(p, BNode):
            assert not str(p).startswith('_:')
            assert str(p) == legacy_data['@default'][0]['predicate']['value'][2:]


@pytest.mark.parametrize(
    "legacy_data",
    [
        {
            '@default': [
                {
                    'subject': {'type': 'IRI', 'value': 's1'},
                    'predicate': {'type': 'IRI', 'value': 'p2'},
                    'object': {'type': 'literal', 'value': 'o3', 'language': 'en'},
                }
            ]
        }
    ],
)
def test_from_legacy_dataset_restores_literal_with_language(legacy_data):
    """Ensure from_legacy_dataset correctly restores a literal with language."""
    restored_dataset = from_legacy_dataset(legacy_data)

    for quad in restored_dataset.quads((None, None, None, None)):
        s, p, o, g = quad
        assert o.language == legacy_data['@default'][0]['object']['language']


@pytest.mark.parametrize(
    "legacy_data",
    [
        {
            '@default': [
                {
                    'subject': {'type': 'IRI', 'value': 's1'},
                    'predicate': {'type': 'IRI', 'value': 'p2'},
                    'object': {
                        'type': 'literal',
                        'value': 'o3',
                        'datatype': 'http://example.org/float',
                    },
                }
            ]
        }
    ],
)
def test_from_legacy_dataset_restores_literal_with_datatype(legacy_data):
    """Ensure from_legacy_dataset correctly restores a literal with datatype."""
    restored_dataset = from_legacy_dataset(legacy_data)
    quads = list(restored_dataset.quads((None, None, None, None)))

    for quad in quads:
        s, p, o, g = quad
        if isinstance(o, Literal) and hasattr(o, 'datatype'):
            assert str(o.datatype) == legacy_data['@default'][0]['object']['datatype']


def test_from_legacy_dataset_invalid_graph_raises_value_error():
    """Ensure from_legacy_dataset raises ValueError when given invalid graph name."""
    with pytest.raises(ValueError, match="Illegal graph name: None"):
        from_legacy_dataset(
            {
                None: [
                    {
                        'subject': {'type': 'IRI', 'value': 's1'},
                        'predicate': {'type': 'IRI', 'value': 'p2'},
                        'object': {
                            'type': 'literal',
                            'value': 'o3',
                            'datatype': 'http://example.org/float',
                        },
                    }
                ]
            }
        )


def test_from_legacy_dataset_incomplete_quad_raises_value_error():
    """Ensure from_legacy_dataset raises ValueError when given invalid input (e.g., missing structure)."""
    with pytest.raises(ValueError, match="Illegal quad structure"):
        from_legacy_dataset({"@default": [{"subject": {'type': 'IRI', 'value': 's1'}}]})


def test_from_legacy_dataset_invalid_quad_term_raises_value_error():
    """Ensure from_legacy_dataset raises ValueError when given invalid input (e.g., missing structure)."""
    with pytest.raises(ValueError, match="Illegal quad structure"):
        from_legacy_dataset(
            {
                "@default": [
                    {
                        'subject': "bad",
                        'predicate': {'type': 'IRI', 'value': 'p2'},
                        'object': {
                            'type': 'literal',
                            'value': 'o3',
                            'datatype': 'http://example.org/float',
                        },
                    }
                ]
            }
        )
