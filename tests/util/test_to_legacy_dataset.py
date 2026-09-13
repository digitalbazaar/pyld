import pytest
from rdflib import BNode, Dataset, Literal, URIRef
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID

from pyld.util import to_legacy_dataset


@pytest.fixture
def dataset():
    return Dataset()


def test_to_legacy_dataset_empty_dataset_returns_minimal_structure():
    """Ensure an empty dataset produces a minimal dict with exactly one graph ('@default') and no quads."""
    result = to_legacy_dataset(Dataset())
    assert len(result) == 1
    assert '@default' in result
    assert len(result['@default']) == 0


def test_to_legacy_dataset_handles_blank_subject(dataset):
    """Ensure blank node subjects are correctly converted to dict with type 'blank node' and value prefixed by '_:'."""
    dataset.add((BNode('b1'), URIRef('p1'), Literal('o1', lang='en')))
    result = to_legacy_dataset(dataset)

    # Get the quad from @default graph
    quads_in_graph = result['@default']
    assert len(quads_in_graph) == 1

    subject_entry = quads_in_graph[0]['subject']
    assert subject_entry['type'] == 'blank node'
    assert subject_entry['value'].startswith('_:')
    assert (
        subject_entry['value'][2:] == 'b1'
    )  # Check that the original BNode identifier is preserved after prefix


def test_to_legacy_dataset_handles_blank_object(dataset):
    """Ensure blank node objects are correctly converted to dict with type 'blank node' and prefixed value."""
    dataset.add((URIRef('s2'), URIRef('p2'), BNode('b3')))
    result = to_legacy_dataset(dataset)

    # Get the quad from @default graph
    quads_in_graph = result['@default']
    assert len(quads_in_graph) == 1

    object_entry = quads_in_graph[0]['object']
    assert object_entry['type'] == 'blank node'
    assert object_entry['value'].startswith('_:')
    assert (
        object_entry['value'][2:] == 'b3'
    )  # Check that the original BNode identifier is preserved after prefix


def test_to_legacy_dataset_preserves_literal_language(dataset):
    """Ensure literal objects with language are preserved in the output as a 'language' field."""

    dataset.add((URIRef('s1'), URIRef('p2'), Literal('o3', lang='fr')))
    result = to_legacy_dataset(dataset)

    # Get the quad from @default graph
    quads_in_graph = result['@default']
    assert len(quads_in_graph) == 1

    object_entry = quads_in_graph[0]['object']
    assert object_entry.get('language') is not None
    assert object_entry['language'] == 'fr'


def test_to_legacy_dataset_preserves_literal_datatype(dataset):
    """Ensure literal objects with a datatype are preserved in the output as 'datatype' field."""
    dataset.add(
        (
            URIRef('s1'),
            URIRef('p2'),
            Literal("x", datatype="http://example.org/float"),
        ),
    )
    result = to_legacy_dataset(dataset)

    # Get the quad from @default graph
    quads_in_graph = result['@default']
    assert len(quads_in_graph) == 1

    object_entry = quads_in_graph[0]['object']
    assert object_entry.get('datatype') is not None
    assert object_entry['datatype'] == "http://example.org/float"


def test_to_legacy_dataset_correctly_maps_graph(dataset):
    """Ensure graph key is correctly derived."""
    dataset.add(
        (
            URIRef('s1'),
            URIRef('p2'),
            Literal('o3'),
            URIRef('http://example.org/graph'),
        )
    )
    result = to_legacy_dataset(dataset)

    # There should be two graphs: '@default' (empty) and 'http://example.org/graph' (with one quad)
    assert len(result.keys()) == 2

    # Check that '@default' graph exists and is empty
    assert '@default' in result
    assert len(result['@default']) == 0

    # Check that 'http://example.org/graph' exists and contains the quad
    assert 'http://example.org/graph' in result
    assert len(result['http://example.org/graph']) == 1


def test_to_legacy_dataset_correctly_maps_bnode_graph(dataset):
    """Ensure graph key is correctly prefixed with '_' for BNodes"""
    dataset.add((URIRef('s1'), URIRef('p2'), Literal('o3'), BNode('g4')))
    result = to_legacy_dataset(dataset)

    # There should be two graphs: '@default' (empty) and '_:g4' (with one quad)
    assert len(result.keys()) == 2

    # Check that '@default' graph exists and is empty
    assert '@default' in result
    assert len(result['@default']) == 0

    # Check that '_:g4' graph exists and contains the quad
    assert '_:g4' in result
    assert len(result['_:g4']) == 1


def test_to_legacy_dataset_correctly_maps_default_graph(dataset):
    """Ensure graph key is correctly derived '@default' for None or default graph."""
    dataset.add((URIRef('s1'), URIRef('p2'), Literal('o3'), DATASET_DEFAULT_GRAPH_ID))
    dataset.add((URIRef('s2'), URIRef('p2'), Literal('o3'), None))
    print(list(dataset.quads((None, None, None, None))))
    result = to_legacy_dataset(dataset)

    assert len(result.keys()) == 1
    assert '@default' in result
    assert (
        len(result['@default']) == 1
    )  # Only first quad should be in the @default graph
