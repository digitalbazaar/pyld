import pytest
from rdflib import BNode, Dataset, Literal, URIRef
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID

from pyld.util import from_legacy_dataset, to_legacy_dataset


class TestToLegacyDataset:
    """A comprehensive class-based test suite for `to_legacy_dataset` split into granular tests."""

    def setup_method(self):
        """Initialize a clean Dataset before each test."""
        self.dataset = Dataset()

    def test_to_legacy_dataset_empty_dataset_returns_minimal_structure(self):
        """Ensure an empty dataset produces a minimal dict with exactly one graph ('@default') and no quads."""
        result = to_legacy_dataset(Dataset())
        assert len(result) == 1
        assert '@default' in result
        assert len(result['@default']) == 0

    def test_to_legacy_dataset_handles_blank_subject(self):
        """Ensure blank node subjects are correctly converted to dict with type 'blank node' and value prefixed by '_:'."""
        self.dataset.add((BNode('b1'), URIRef('p1'), Literal('o1', lang='en')))
        result = to_legacy_dataset(self.dataset)

        # Get the quad from @default graph
        quads_in_graph = result['@default']
        assert len(quads_in_graph) == 1

        subject_entry = quads_in_graph[0]['subject']
        assert subject_entry['type'] == 'blank node'
        assert subject_entry['value'].startswith('_:')
        assert (
            subject_entry['value'][2:] == 'b1'
        )  # Check that the original BNode identifier is preserved after prefix

    def test_to_legacy_dataset_handles_blank_object(self):
        """Ensure blank node objects are correctly converted to dict with type 'blank node' and prefixed value."""
        self.dataset.add((URIRef('s2'), URIRef('p2'), BNode('b3')))
        result = to_legacy_dataset(self.dataset)

        # Get the quad from @default graph
        quads_in_graph = result['@default']
        assert len(quads_in_graph) == 1

        object_entry = quads_in_graph[0]['object']
        assert object_entry['type'] == 'blank node'
        assert object_entry['value'].startswith('_:')
        assert (
            object_entry['value'][2:] == 'b3'
        )  # Check that the original BNode identifier is preserved after prefix

    def test_to_legacy_dataset_preserves_literal_language(self):
        """Ensure literal objects with language are preserved in the output as a 'language' field."""

        self.dataset.add((URIRef('s1'), URIRef('p2'), Literal('o3', lang='fr')))
        result = to_legacy_dataset(self.dataset)

        # Get the quad from @default graph
        quads_in_graph = result['@default']
        assert len(quads_in_graph) == 1

        object_entry = quads_in_graph[0]['object']
        assert object_entry.get('language') is not None
        assert object_entry['language'] == 'fr'

    def test_to_legacy_dataset_preserves_literal_datatype(self):
        """Ensure literal objects with a datatype are preserved in the output as 'datatype' field."""
        self.dataset.add(
            (
                URIRef('s1'),
                URIRef('p2'),
                Literal("x", datatype="http://example.org/float"),
            ),
        )
        result = to_legacy_dataset(self.dataset)

        # Get the quad from @default graph
        quads_in_graph = result['@default']
        assert len(quads_in_graph) == 1

        object_entry = quads_in_graph[0]['object']
        assert object_entry.get('datatype') is not None
        assert object_entry['datatype'] == "http://example.org/float"

    def test_to_legacy_dataset_correctly_maps_graph(self):
        """Ensure graph key is correctly derived."""
        self.dataset.add(
            (
                URIRef('s1'),
                URIRef('p2'),
                Literal('o3'),
                URIRef('http://example.org/graph'),
            )
        )
        result = to_legacy_dataset(self.dataset)

        # There should be two graphs: '@default' (empty) and 'http://example.org/graph' (with one quad)
        assert len(result.keys()) == 2

        # Check that '@default' graph exists and is empty
        assert '@default' in result
        assert len(result['@default']) == 0

        # Check that 'http://example.org/graph' exists and contains the quad
        assert 'http://example.org/graph' in result
        assert len(result['http://example.org/graph']) == 1

    def test_to_legacy_dataset_correctly_maps_bnode_graph(self):
        """Ensure graph key is correctly prefixed with '_' for BNodes"""
        self.dataset.add((URIRef('s1'), URIRef('p2'), Literal('o3'), BNode('g4')))
        result = to_legacy_dataset(self.dataset)

        # There should be two graphs: '@default' (empty) and '_:g4' (with one quad)
        assert len(result.keys()) == 2

        # Check that '@default' graph exists and is empty
        assert '@default' in result
        assert len(result['@default']) == 0

        # Check that '_:g4' graph exists and contains the quad
        assert '_:g4' in result
        assert len(result['_:g4']) == 1

    def test_to_legacy_dataset_correctly_maps_default_graph(self):
        """Ensure graph key is correctly derived '@default' for None or default graph."""
        self.dataset.add(
            (URIRef('s1'), URIRef('p2'), Literal('o3'), DATASET_DEFAULT_GRAPH_ID)
        )
        self.dataset.add((URIRef('s2'), URIRef('p2'), Literal('o3'), None))
        print(list(self.dataset.quads((None, None, None, None))))
        result = to_legacy_dataset(self.dataset)

        assert len(result.keys()) == 1
        assert '@default' in result
        assert (
            len(result['@default']) == 1
        )  # Only first quad should be in the @default graph


class TestFromLegacyDataset:
    """A comprehensive class-based test suite for `from_legacy_dataset`, split into granular tests."""

    def test_from_legacy_dataset_restores_default_graph(self):
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
    def test_from_legacy_dataset_restores_blank_subject(self, legacy_data):
        """Ensure from_legacy_dataset correctly reconstructs a blank node subject."""
        restored_dataset = from_legacy_dataset(legacy_data)

        for quad in restored_dataset.quads((None, None, None, None)):
            s, p, o, g = quad
            if isinstance(s, BNode):
                assert not s.startswith('_:')
                assert (
                    str(s)
                    == legacy_data['_:' + str(g) if isinstance(g, BNode) else str(g)][
                        0
                    ]['subject']['value'][2:]
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
    def test_from_legacy_dataset_restores_blank_predicate(self, legacy_data):
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
    def test_from_legacy_dataset_restores_literal_with_language(self, legacy_data):
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
    def test_from_legacy_dataset_restores_literal_with_datatype(self, legacy_data):
        """Ensure from_legacy_dataset correctly restores a literal with datatype."""
        restored_dataset = from_legacy_dataset(legacy_data)
        quads = list(restored_dataset.quads((None, None, None, None)))

        for quad in quads:
            s, p, o, g = quad
            if isinstance(o, Literal) and hasattr(o, 'datatype'):
                assert (
                    str(o.datatype) == legacy_data['@default'][0]['object']['datatype']
                )

    def test_from_legacy_dataset_invalid_graph_raises_value_error(self):
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

    def test_from_legacy_dataset_incomplete_quad_raises_value_error(self):
        """Ensure from_legacy_dataset raises ValueError when given invalid input (e.g., missing structure)."""
        with pytest.raises(ValueError, match="Illegal quad structure"):
            from_legacy_dataset({"@default": [{"subject": {'type': 'IRI', 'value': 's1'}}]})

    def test_from_legacy_dataset_invalid_quad_term_raises_value_error(self):
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
