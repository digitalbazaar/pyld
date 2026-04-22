import copy
import hashlib

import rdflib
from rdflib import XSD, BNode, Dataset, Literal, Node, URIRef
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID
from rdflib.plugins.serializers.nt import _quote_encode

from pyld.identifier_issuer import IdentifierIssuer
from pyld.util import from_legacy_dataset, to_legacy_dataset


class URDNA2015:
    """
    URDNA2015 implements the URDNA2015 RDF Dataset Normalization Algorithm.
    """

    def __init__(self):
        self.blank_node_info = {}
        self.hash_to_blank_nodes = {}
        self.canonical_issuer = IdentifierIssuer('_:c14n')
        self.dataset = None

    # 4.4) Normalization Algorithm
    def main(self, dataset: str | dict | Dataset, options) -> str | dict:
        # handle invalid output format
        if 'format' in options and (
            options['format'] != 'application/n-quads'
            and options['format'] != 'application/nquads'
        ):
            raise UnknownFormatError('Unknown output format.', options['format'])
        
        # handle differtent input types: nquads string, dict (legacy ), or rdflib Dataset
        rdflib_dataset = Dataset()
        if isinstance(dataset, str):
            # Only support N-Quads string input for now
            if (
                options['inputFormat'] != 'application/n-quads'
                and options['inputFormat'] != 'application/nquads'
            ):
                raise UnknownFormatError('Unknown input format.', options['format'])
            rdflib.NORMALIZE_LITERALS = False
            rdflib_dataset.parse(data=dataset, format='nquads')
        elif isinstance(dataset, dict):
            rdflib_dataset = from_legacy_dataset(dataset)
        elif isinstance(dataset, Dataset):
            rdflib_dataset = dataset
        else:
            raise ValueError(f'Unsupported dataset type: {type(dataset)}')
        
        normalized = self._main(rdflib_dataset)
        with open(options.get('algorithm') + '.nq', 'w') as f:
            print(normalized, file=f)
    
        # 8) Return the normalized dataset.
        if (
            options.get('format') == 'application/n-quads'
            or options.get('format') == 'application/nquads'
        ):
            return normalized
        
        result = Dataset().parse(data=normalized, format='nquads')
        return to_legacy_dataset(result)
        
    def _main(self, dataset: Dataset) -> str:
        self.dataset = dataset
        # 1) Create the normalization state.

        # 2) For every quad in input dataset:
        for s, p, o, g in dataset.quads((None, None, None, None)):
            # 2.1) For each blank node that occurs in the quad, add a
            # reference to the quad using the blank node identifier in the
            # blank node to quads map, creating a new entry if necessary.
            for component in (s, o, g if g else None):
                if isinstance(component, BNode):
                    id_ = str(component)
                    self.blank_node_info.setdefault(id_, {'quads': []})['quads'].append((s, p, o, g))

        # 3) Create a list of non-normalized blank node identifiers and
        # populate it using the keys from the blank node to quads map.
        non_normalized = set(self.blank_node_info.keys())

        # 4) Initialize simple, a boolean flag, to true.
        simple = True

        # 5) While simple is true, issue canonical identifiers for blank nodes:
        while simple:
            # 5.1) Set simple to false.
            simple = False

            # 5.2) Clear hash to blank nodes map.
            self.hash_to_blank_nodes = {}

            # 5.3) For each blank node identifier identifier in non-normalized
            # identifiers:
            for id_ in non_normalized:
                # 5.3.1) Create a hash, hash, according to the Hash First
                # Degree Quads algorithm.
                hash = self.hash_first_degree_quads(id_)

                # 5.3.2) Add hash and identifier to hash to blank nodes map,
                # creating a new entry if necessary.
                self.hash_to_blank_nodes.setdefault(hash, []).append(id_)

            # 5.4) For each hash to identifier list mapping in hash to blank
            # nodes map, lexicographically-sorted by hash:
            for hash, id_list in sorted(self.hash_to_blank_nodes.items()):
                # 5.4.1) If the length of identifier list is greater than 1,
                # continue to the next mapping.
                if len(id_list) > 1:
                    continue

                # 5.4.2) Use the Issue Identifier algorithm, passing canonical
                # issuer and the single blank node identifier in identifier
                # list, identifier, to issue a canonical replacement identifier
                # for identifier.
                # TODO: consider changing `get_id` to `issue`
                id_ = id_list[0]
                self.canonical_issuer.get_id(id_)

                # 5.4.3) Remove identifier from non-normalized identifiers.
                non_normalized.remove(id_)

                # 5.4.4) Remove hash from the hash to blank nodes map.
                del self.hash_to_blank_nodes[hash]

                # 5.4.5) Set simple to true.
                simple = True

        # 6) For each hash to identifier list mapping in hash to blank nodes
        # map, lexicographically-sorted by hash:
        for _hash, id_list in sorted(self.hash_to_blank_nodes.items()):
            # 6.1) Create hash path list where each item will be a result of
            # running the Hash N-Degree Quads algorithm.
            hash_path_list = []

            # 6.2) For each blank node identifier identifier in identifier
            # list:
            for id_ in id_list:
                # 6.2.1) If a canonical identifier has already been issued for
                # identifier, continue to the next identifier.
                if self.canonical_issuer.has_id(id_):
                    continue

                # 6.2.2) Create temporary issuer, an identifier issuer
                # initialized with the prefix _:b.
                issuer = IdentifierIssuer('_:b')

                # 6.2.3) Use the Issue Identifier algorithm, passing temporary
                # issuer and identifier, to issue a new temporary blank node
                # identifier for identifier.
                issuer.get_id(id_)

                # 6.2.4) Run the Hash N-Degree Quads algorithm, passing
                # temporary issuer, and append the result to the hash path
                # list.
                hash_path_list.append(self.hash_n_degree_quads(id_, issuer))

            # 6.3) For each result in the hash path list,
            # lexicographically-sorted by the hash in result:
            for result in sorted(hash_path_list, key=lambda r: r['hash']):
                # 6.3.1) For each blank node identifier, existing identifier,
                # that was issued a temporary identifier by identifier issuer
                # in result, issue a canonical identifier, in the same order,
                # using the Issue Identifier algorithm, passing canonical
                # issuer and existing identifier.
                for existing in result['issuer'].order:
                    self.canonical_issuer.get_id(existing)

        # Note: At this point all blank nodes in the set of RDF quads have been
        # assigned canonical identifiers, which have been stored in the
        # canonical issuer. Here each quad is updated by assigning each of its
        # blank nodes its new identifier.

        # 7) For each quad, quad, in input dataset:
        normalized = []
        for s, p, o, g in self.dataset.quads((None, None, None, None)):
            # 7.1) Create a copy, quad copy, of quad and replace any existing
            # blank node identifiers using the canonical identifiers previously
            # issued by canonical issuer. Note: We optimize away the copy here.

            # Helper to map nodes
            def map_node(node):
                if isinstance(node, BNode):
                    node_id = str(node)
                    # Only issue a new ID if it's not already canonicalized
                    cid = self.canonical_issuer.get_id(node_id)
                    if cid.startswith('_:'):
                        cid = cid[2:]  # Strip '_:' prefix for rdflib BNode compatibility

                    return BNode(cid)
                return node

            # Transform Subject, Object, and Graph Name (Predicate is never a BNode in RDFC1.0)
            s_n = map_node(s)
            p_n = p # Predicates are never BNodes in standard RDF
            o_n = map_node(o)
            g_n = map_node(g)
            
            # Use modified version of rdflib's internal _nq_row for standardized string output
            line = self._nq_row((s_n, p_n, o_n),g_n)

            # 7.2) Add quad copy to the normalized dataset.
            normalized.append(line)

        # sort normalized output
        normalized.sort()

        # return nquads string
        return ''.join(normalized)

    # 4.6) Hash First Degree Quads
    def hash_first_degree_quads(self, id_):
        # return cached hash
        info = self.blank_node_info[id_]
        if 'hash' in info:
            return info['hash']

        # 1) Initialize nquads to an empty list. It will be used to store quads
        # in N-Quads format.
        nquads = []

        # 2) Get the list of quads quads associated with the reference blank
        # node identifier in the blank node to quads map.
        quads = info['quads']

        # 3) For each quad quad in quads:
        for s, p, o, g in quads:
            # 3.1) Serialize the quad in N-Quads format with the following
            # special rule:

            # 3.1.1) If any component in quad is an blank node, then serialize
            # it using a special identifier as follows:
            p_n = p # Predicates are never BNodes in standard RDF

            # 3.1.2) If the blank node's existing blank node identifier
            # matches the reference blank node identifier then use the
            # blank node identifier _:a, otherwise, use the blank node
            # Replace current BNode with _:a, others with _:z for hashing
            s_n = self.modify_first_degree_component(id_, s)
            o_n = self.modify_first_degree_component(id_, o)
            g_n = self.modify_first_degree_component(id_, g)
            
            # Use rdflib's internal _nt_row for standardized string output
            line = self._nq_row((s_n, p_n, o_n), g_n)
            nquads.append(line)

        # 4) Sort nquads in lexicographical order.
        nquads.sort()

        # 5) Return the hash that results from passing the sorted, joined
        # nquads through the hash algorithm.
        info['hash'] = self.hash_nquads(nquads)
        return info['hash']

    # helper for modifying component during Hash First Degree Quads
    def modify_first_degree_component(self, id_: str, component: Node, key: str = None):
        if not isinstance(component, BNode):
            return component
        return BNode("a") if str(component) == id_ else BNode("z")

    # helper for getting a related predicate
    def get_related_predicate(self, quad):
        # quad is (s, p, o, g)
        return f"<{str(quad[1])}>"

    # 4.7) Hash Related Blank Node
    def hash_related_blank_node(self, related, quad, issuer, position):
        # 1) Set the identifier to use for related, preferring first the
        # canonical identifier for related if issued, second the identifier
        # issued by issuer if issued, and last, if necessary, the result of
        # the Hash First Degree Quads algorithm, passing related.
        if self.canonical_issuer.has_id(related):
            id_ = self.canonical_issuer.get_id(related)
        elif issuer.has_id(related):
            id_ = issuer.get_id(related)
        else:
            id_ = self.hash_first_degree_quads(related)

        # 2) Initialize a string input to the value of position.
        # Note: We use a hash object instead.
        md = self.create_hash()
        md.update(position.encode('utf8'))

        # 3) If position is not g, append <, the value of the predicate in
        # quad, and > to input.
        if position != 'g':
            md.update(self.get_related_predicate(quad).encode('utf8'))

        # 4) Append identifier to input.
        md.update(id_.encode('utf8'))

        # 5) Return the hash that results from passing input through the hash
        # algorithm.
        return md.hexdigest()

    # 4.8) Hash N-Degree Quads
    def hash_n_degree_quads(self, id_, issuer):
        # 1) Create a hash to related blank nodes map for storing hashes that
        # identify related blank nodes.
        # Note: 2) and 3) handled within `createHashToRelated`
        hash_to_related = self.create_hash_to_related(id_, issuer)

        # 4) Create an empty string, data to hash.
        # Note: We create a hash object instead.
        md = self.create_hash()

        # 5) For each related hash to blank node list mapping in hash to
        # related blank nodes map, sorted lexicographically by related hash:
        for hash, blank_nodes in sorted(hash_to_related.items()):
            # 5.1) Append the related hash to the data to hash.
            md.update(hash.encode('utf8'))

            # 5.2) Create a string chosen path.
            chosen_path = ''

            # 5.3) Create an unset chosen issuer variable.
            chosen_issuer = None

            # 5.4) For each permutation of blank node list:
            for permutation in permutations(blank_nodes):
                # 5.4.1) Create a copy of issuer, issuer copy.
                issuer_copy = copy.deepcopy(issuer)

                # 5.4.2) Create a string path.
                path = ''

                # 5.4.3) Create a recursion list, to store blank node
                # identifiers that must be recursively processed by this
                # algorithm.
                recursion_list = []

                # 5.4.4) For each related in permutation:
                skip_to_next_permutation = False
                for related in permutation:
                    # 5.4.4.1) If a canonical identifier has been issued for
                    # related, append it to path.
                    if self.canonical_issuer.has_id(related):
                        path += self.canonical_issuer.get_id(related)
                    # 5.4.4.2) Otherwise:
                    else:
                        # 5.4.4.2.1) If issuer copy has not issued an
                        # identifier for related, append related to recursion
                        # list.
                        if not issuer_copy.has_id(related):
                            recursion_list.append(related)

                        # 5.4.4.2.2) Use the Issue Identifier algorithm,
                        # passing issuer copy and related and append the result
                        # to path.
                        path += issuer_copy.get_id(related)

                    # 5.4.4.3) If chosen path is not empty and the length of
                    # path is greater than or equal to the length of chosen
                    # path and path is lexicographically greater than chosen
                    # path, then skip to the next permutation.
                    if (
                        len(chosen_path) != 0
                        and len(path) >= len(chosen_path)
                        and path > chosen_path
                    ):
                        skip_to_next_permutation = True
                        break

                if skip_to_next_permutation:
                    continue

                # 5.4.5) For each related in recursion list:
                for related in recursion_list:
                    # 5.4.5.1) Set result to the result of recursively
                    # executing the Hash N-Degree Quads algorithm, passing
                    # related for identifier and issuer copy for path
                    # identifier issuer.
                    result = self.hash_n_degree_quads(related, issuer_copy)

                    # 5.4.5.2) Use the Issue Identifier algorithm, passing
                    # issuer copy and related and append the result to path.
                    path += issuer_copy.get_id(related)

                    # 5.4.5.3) Append <, the hash in result, and > to path.
                    path += '<' + result['hash'] + '>'

                    # 5.4.5.4) Set issuer copy to the identifier issuer in
                    # result.
                    issuer_copy = result['issuer']

                    # 5.4.5.5) If chosen path is not empty and the length of
                    # path is greater than or equal to the length of chosen
                    # path and path is lexicographically greater than chosen
                    # path, then skip to the next permutation.
                    if (
                        len(chosen_path) != 0
                        and len(path) >= len(chosen_path)
                        and path > chosen_path
                    ):
                        skip_to_next_permutation = True
                        break

                if skip_to_next_permutation:
                    continue

                # 5.4.6) If chosen path is empty or path is lexicographically
                # less than chosen path, set chosen path to path and chosen
                # issuer to issuer copy.
                if len(chosen_path) == 0 or path < chosen_path:
                    chosen_path = path
                    chosen_issuer = issuer_copy

            # 5.5) Append chosen path to data to hash.
            md.update(chosen_path.encode('utf8'))

            # 5.6) Replace issuer, by reference, with chosen issuer.
            issuer = chosen_issuer

        # 6) Return issuer and the hash that results from passing data to hash
        # through the hash algorithm.
        return {'hash': md.hexdigest(), 'issuer': issuer}

    # helper for creating hash to related blank nodes map
    def create_hash_to_related(self, id_, issuer):
        # 1) Create a hash to related blank nodes map for storing hashes that
        # identify related blank nodes.
        hash_to_related = {}

        # 2) Get a reference, quads, to the list of quads in the blank node to
        # quads map for the key identifier.
        quads = self.blank_node_info[id_]['quads']

        # 3) For each quad in quads:
        for quad in quads:
            # 3.1) For each component in quad, if component is the subject,
            # object, and graph name and it is a blank node that is not
            # identified by identifier:
            for i, component in enumerate(quad):
                if i != 1 and isinstance(component, BNode) and str(component) != id_:
                    # 3.1.1) Set hash to the result of the Hash Related Blank
                    # Node algorithm, passing the blank node identifier for
                    # component as related, quad, path identifier issuer as
                    # issuer, and position as either s, o, or g based on
                    # whether component is a subject, object, graph name,
                    # respectively.

                    related = str(component)
                    # correct position codes: subject='s', object='o', graph='g'
                    position = ('s', None, 'o', 'g')[i]
                    hash = self.hash_related_blank_node(related, quad, issuer, position)

                    # 3.1.2) Add a mapping of hash to the blank node identifier
                    # for component to hash to related blank nodes map, adding
                    # an entry as necessary.
                    hash_to_related.setdefault(hash, []).append(related)

        return hash_to_related

    # helper to create appropriate hash object
    def create_hash(self):
        return hashlib.sha256()

    # helper to hash a list of nquads
    def hash_nquads(self, nquads):
        md = self.create_hash()
        for nquad in nquads:
            md.update(nquad.encode('utf8'))
        return md.hexdigest()

    # TODO: use drop-in replacements to not serialize with xsd:string; better to solve this at the rdflib level
    def _nq_row(self, triple, context):
        graph_name = (
            context.n3() + " "
            if context and context != DATASET_DEFAULT_GRAPH_ID
            else ""
        )
        if isinstance(triple[2], Literal):
            return f"{triple[0].n3()} {triple[1].n3()} {self._quoteLiteral(triple[2])} {graph_name}.\n"
        else:
            return f"{triple[0].n3()} {triple[1].n3()} {triple[2].n3()} {graph_name}.\n"

    def _quoteLiteral(self, l_: Literal) -> str:  # noqa: N802
        """A simpler version of term.Literal.n3()"""

        encoded = _quote_encode(l_)

        if l_.language:
            if l_.datatype:
                raise Exception("Literal has datatype AND language!")
            return f"{encoded}@{l_.language}"
        elif l_.datatype and l_.datatype != XSD.string:
            return f"{encoded}^^<{l_.datatype}>"
        else:
            return f"{encoded}"


class URGNA2012(URDNA2015):
    """
    URGNA2012 implements the URGNA2012 RDF Graph Normalization Algorithm.
    """

    def __init__(self):
        URDNA2015.__init__(self)

    # helper for modifying component during Hash First Degree Quads
    def modify_first_degree_component(self, id_: str, component: Node, key: str = None):
        if not isinstance(component, BNode):
            return component
        if key == 'name':
            return BNode("g")
        return BNode("a") if str(component) == id_ else BNode("z")

    # helper for getting a related predicate
    def get_related_predicate(self, quad):
        return str(quad[1])

    # helper for creating hash to related blank nodes map
    def create_hash_to_related(self, id_, issuer):
        # 1) Create a hash to related blank nodes map for storing hashes that
        # identify related blank nodes.
        hash_to_related = {}

        # 2) Get a reference, quads, to the list of quads in the blank node to
        # quads map for the key identifier.
        quads = self.blank_node_info[id_]['quads']

        # 3) For each quad in quads:
        for quad in quads:
            s, p , o, g = quad
            # 3.1) If the quad's subject is a blank node that does not match
            # identifier, set hash to the result of the Hash Related Blank Node
            # algorithm, passing the blank node identifier for subject as
            # related, quad, path identifier issuer as issuer, and p as
            # position.
            if (
                isinstance(s, BNode)
                and str(s) != id_
            ):
                related = str(s)
                position = 'p'
            # 3.2) Otherwise, if quad's object is a blank node that does
            # not match identifier, to the result of the Hash Related Blank
            # Node algorithm, passing the blank node identifier for object
            # as related, quad, path identifier issuer as issuer, and r
            # as position.
            elif (
                isinstance(o, BNode)
                and str(o) != id_
            ):
                related = str(o)
                position = 'r'
            # 3.3) Otherwise, continue to the next quad.
            else:
                continue

            # 3.4) Add a mapping of hash to the blank node identifier for the
            # component that matched (subject or object) to hash to related
            # blank nodes map, adding an entry as necessary.
            hash = self.hash_related_blank_node(related, quad, issuer, position)
            hash_to_related.setdefault(hash, []).append(related)

        return hash_to_related

    # helper to create appropriate hash object
    def create_hash(self):
        return hashlib.sha1()

class RDFC10(URDNA2015):
    """
    RDFC10 implements the RDF Canonicalization algorithm version 1.0.
    """

    def __init__(self):
        URDNA2015.__init__(self)

    def _quoteLiteral(self, l_: Literal) -> str:  # noqa: N802
        """A simpler version of term.Literal.n3()"""

        encoded = self._quote_encode(l_)

        if l_.language:
            if l_.datatype:
                raise Exception("Literal has datatype AND language!")
            return f"{encoded}@{l_.language}"
        elif l_.datatype and l_.datatype != XSD.string:
            return f"{encoded}^^<{l_.datatype}>"
        else:
            return f"{encoded}"

    def _quote_encode(self, l_: str) -> str:
        return '"{}"'.format(
            l_.replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace('"', '\\"')
            .replace("\r", "\\r")
        )


def permutations(elements):
    """
    Generates all of the possible permutations for the given list of elements.
    Uses itertools.permutations on a sorted copy.

    :param elements: the list of elements to permutate.
    """
    from itertools import permutations as _it_permutations
    els = sorted(elements)
    for perm in _it_permutations(els):
        yield list(perm)

class UnknownFormatError(ValueError):
    """
    Base class for unknown format errors.
    """

    def __init__(self, message, format):
        Exception.__init__(self, message)
        self.format = format
