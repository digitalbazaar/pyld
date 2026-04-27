from rdflib import BNode, Dataset, Literal, URIRef
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID


# Helpers for converting between rdflib.Dataset and legacy dict structure used in pyld
def to_legacy_dataset(dataset: Dataset) -> dict:
    """
    Transforms an rdflib.Dataset into the RDF.js-style dictionary structure,
    ensuring Blank Node values start with '_:'.
    """
    compat_dataset = {'@default':[]}

    for s, p, o, g in dataset.quads((None, None, None, None)):
        # 1. Determine Graph Key
        graph_id = '@default'
        if g is not None and g != DATASET_DEFAULT_GRAPH_ID:
            graph_id = f"_:{str(g)}" if isinstance(g, BNode) else str(g)

        if graph_id not in compat_dataset:
            compat_dataset[graph_id] = []

        # 2. Helper to convert nodes
        def term_to_dict(node):
            if isinstance(node, BNode):
                # Ensure the value starts with _:
                val = str(node)
                if not val.startswith('_:'):
                    val = f"_:{val}"
                return {'type': 'blank node', 'value': val}

            elif isinstance(node, URIRef):
                return {'type': 'IRI', 'value': str(node)}

            elif isinstance(node, Literal):
                res = {'type': 'literal', 'value': str(node)}
                if node.language:
                    res['language'] = node.language
                if node.datatype:
                    res['datatype'] = str(node.datatype)
                return res
            raise ValueError(f'Illegal node type {type(node)}')

        # 3. Build legacy quad
        compat_dataset[graph_id].append(
            {
                'subject': term_to_dict(s),
                'predicate': term_to_dict(p),
                'object': term_to_dict(o),
            }
        )

    return compat_dataset


def from_legacy_dataset(dataset: dict) -> Dataset:
    """
    Converts legacy dict structure back into an rdflib.Dataset.
    """
    ds = Dataset()

    for graph_name, triples in dataset.items():
        # Handle graph name
        try:
            g = from_legacy_graph(graph_name, ds.default_graph)
        except Exception as err:
            raise ValueError(f'Illegal graph name: {graph_name}') from err

        for t in triples:
            s, p, o = from_legacy_triple(t)
            ds.add((s, p, o, g))

    return ds

def from_legacy_graph(graph: str, default_graph = DATASET_DEFAULT_GRAPH_ID) -> URIRef | BNode:
    """
    Converts a legacy graph name into an rdflib URIRef or BNode.
    """
    if graph == '@default':
        return default_graph
    # Check if graph name is a blank node or IRI
    elif graph.startswith('_:'):
        return BNode(graph[2:])
    else:
        return URIRef(graph)

def from_legacy_triple(triple: dict, normalize=False) -> tuple:
    """
    Converts a legacy triple dict into an rdflib triple tuple.
    """
    if not all(k in triple for k in ('subject', 'predicate', 'object')):
        raise ValueError(f'Illegal quad structure: {triple}')

    def to_node(comp):
        if not isinstance(comp, dict) or 'type' not in comp or 'value' not in comp:
            raise ValueError(f'Illegal quad structure: {comp}')

        val = comp['value']
        if comp['type'] == 'blank node':
            # Strip '_:' because RDFLib adds it back internally
            return BNode(val[2:] if val.startswith('_:') else val)
        elif comp['type'] == 'IRI':
            return URIRef(val)
        elif comp['type'] == 'literal':
            return Literal(
                val,
                lang=comp.get('language'),
                datatype=URIRef(comp['datatype'])
                if comp.get('datatype') and not comp.get('language')
                else None,
                # Don't normalize literal values to prevent datetime issues
                # TODO: this means only rdflib.Dataset() created with normalization turned off will work properly.
                normalize=normalize,
            )
        raise ValueError('Illegal component type {}'.format(comp['type']))

    s = to_node(triple['subject'])
    p = to_node(triple['predicate'])
    o = to_node(triple['object'])

    return (s, p, o)
