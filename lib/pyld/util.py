from rdflib import BNode, Dataset, Literal, URIRef
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID


# Helpers for converting between rdflib.Dataset and legacy dict structure used in pyld
def to_legacy_dataset(dataset: Dataset) -> dict:
    """
    Transforms an rdflib.Dataset into the RDF.js-style dictionary structure,
    ensuring Blank Node values start with '_:'.
    """
    compat_dataset = {}

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
        if graph_name == '@default':
            g = ds.default_graph
        else:
            # Check if graph name is a blank node or IRI
            if graph_name.startswith('_:'):
                g = ds.graph(BNode(graph_name[2:]))
            else:
                g = ds.graph(URIRef(graph_name))

        for t in triples:

            def to_node(comp):
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
                        normalize=False,
                    )
                raise ValueError('Illegal component type {}'.format(comp['type']))

            s = to_node(t['subject'])
            p = to_node(t['predicate'])
            o = to_node(t['object'])

            ds.add((s, p, o, g))

    return ds
