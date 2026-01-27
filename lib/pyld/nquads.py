
import re

XSD_STRING = 'http://www.w3.org/2001/XMLSchema#string'
RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
RDF_LANGSTRING = RDF + 'langString'

def escape(value: str):
    return (
        value.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace('"', '\\"')
    )


def unescape(value: str):
    return (
        value.replace('\\"', '"')
        .replace("\\t", "\t")
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\\\", "\\")
    )


def parse_nquads(input_: str):
    """
    Parses RDF in the form of N-Quads.

    :param input_: the N-Quads input to parse.

    :return: an RDF dataset.
    """
    # define partial regexes
    iri = '(?:<([^:]+:[^>]*)>)'
    bnode = '(_:(?:[A-Za-z0-9_][A-Za-z0-9_.-]*))'
    plain = '"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)"'
    datatype = '(?:\\^\\^' + iri + ')'
    language = '(?:@([a-zA-Z]+(?:-[a-zA-Z0-9]+)*))'
    literal = '(?:' + plain + '(?:' + datatype + '|' + language + ')?)'
    ws = '[ \\t]+'
    wso = '[ \\t]*'
    empty = r'^' + wso + '$'

    # define quad part regexes
    subject = '(?:' + iri + '|' + bnode + ')' + ws
    property = iri + ws
    object = '(?:' + iri + '|' + bnode + '|' + literal + ')' + wso
    graph = '(?:\\.|(?:(?:' + iri + '|' + bnode + ')' + wso + '\\.))'

    # Note: Notice that the graph position does not include literals
    # even though they are specified as a possible value in the
    # N-Quads note (http://sw.deri.org/2008/07/n-quads/). This is
    # intentional, as literals in that position are not supported by the
    # RDF data model or the JSON-LD data model.
    # See: https://github.com/digitalbazaar/pyld/pull/19

    # full quad regex
    quad = r'^' + wso + subject + property + object + graph + wso + '$'

    # build RDF dataset
    dataset = {}

    # split N-Quad input into lines
    lines = input_.splitlines(True)
    line_number = 0
    for line in lines:
        line_number += 1

        # skip empty lines
        if re.search(empty, line) is not None:
            continue

        # parse quad
        match = re.search(quad, line)
        if match is None:
            raise ParserError(f'Error while parsing N-Quads invalid quad {line} at line {line_number}.', line_number=line_number)
        match = match.groups()

        # create RDF triple
        triple = {'subject': {}, 'predicate': {}, 'object': {}}

        # get subject
        if match[0] is not None:
            triple['subject'] = {'type': 'IRI', 'value': match[0]}
        else:
            triple['subject'] = {'type': 'blank node', 'value': match[1]}

        # get predicate
        triple['predicate'] = {'type': 'IRI', 'value': match[2]}

        # get object
        if match[3] is not None:
            triple['object'] = {'type': 'IRI', 'value': match[3]}
        elif match[4] is not None:
            triple['object'] = {'type': 'blank node', 'value': match[4]}
        else:
            triple['object'] = {'type': 'literal'}
            unescaped = unescape(match[5])
            if match[6] is not None:
                triple['object']['datatype'] = match[6]
            elif match[7] is not None:
                triple['object']['datatype'] = RDF_LANGSTRING
                triple['object']['language'] = match[7]
            else:
                triple['object']['datatype'] = XSD_STRING
            triple['object']['value'] = unescaped

        # get graph name ('@default' is used for the default graph)
        name = '@default'
        if match[8] is not None:
            name = match[8]
        elif match[9] is not None:
            name = match[9]

        # initialize graph in dataset
        if name not in dataset:
            dataset[name] = [triple]
        # add triple if unique to its graph
        else:
            unique = True
            triples = dataset[name]
            for t in dataset[name]:
                if _compare_rdf_triples(t, triple):
                    unique = False
                    break
            if unique:
                triples.append(triple)

    return dataset

def serialize_nquads(dataset):
    """
    Converts an RDF dataset to N-Quads.

    :param dataset: the RDF dataset to convert.

    :return: the N-Quads string.
    """
    quads = []
    for graph_name, triples in dataset.items():
        for triple in triples:
            if graph_name == '@default':
                graph_name = None
            quads.append(serialize_nquad(triple, graph_name))
    quads.sort()
    return ''.join(quads)

def serialize_nquad(triple, graph_name=None):
    """
    Converts an RDF triple and graph name to an N-Quad string (a single
    quad).

    :param triple: the RDF triple or quad to convert (a triple or quad
        may be passed, if a triple is passed then `graph_name` should be
        given to specify the name of the graph the triple is in, `None`
        for the default graph).
    :param graph_name: the name of the graph containing the triple, None
        for the default graph.

    :return: the N-Quad string.
    """
    s = triple['subject']
    p = triple['predicate']
    o = triple['object']
    g = triple.get('name', {'value': graph_name})['value']

    quad = ''

    # subject is an IRI
    if s['type'] == 'IRI':
        quad += '<' + s['value'] + '>'
    else:
        quad += s['value']
    quad += ' '

    # property is an IRI
    if p['type'] == 'IRI':
        quad += '<' + p['value'] + '>'
    else:
        quad += p['value']
    quad += ' '

    # object is IRI, bnode, or literal
    if o['type'] == 'IRI':
        quad += '<' + o['value'] + '>'
    elif(o['type'] == 'blank node'):
        quad += o['value']
    else:
        escaped = escape(o['value'])
        quad += '"' + escaped + '"'
        if o['datatype'] == RDF_LANGSTRING:
            if o.get('language'):
                quad += '@' + o['language']
        elif o['datatype'] != XSD_STRING:
            quad += '^^<' + o['datatype'] + '>'

    # graph
    if g is not None:
        if not g.startswith('_:'):
            quad += ' <' + g + '>'
        else:
            quad += ' ' + g

    quad += ' .\n'
    return quad
    

def _compare_rdf_triples(t1, t2):
    """
    Compares two RDF triples for equality.

    :param t1: the first triple.
    :param t2: the second triple.

    :return: True if the triples are the same, False if not.
    """
    for attr in ['subject', 'predicate', 'object']:
        if(t1[attr]['type'] != t2[attr]['type'] or
                t1[attr]['value'] != t2[attr]['value']):
            return False

    if t1['object'].get('language') != t2['object'].get('language'):
        return False
    if t1['object'].get('datatype') != t2['object'].get('datatype'):
        return False

    return True

class ParserError(ValueError):
    """
    Base class for parsing errors.
    """

    def __init__(self, message, line_number=None):
        Exception.__init__(self, message)
        self.line_number = line_number
