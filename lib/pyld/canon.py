
import hashlib
from pyld.nquads import parse_nquads, serialize_nquad
from pyld.identifier_issuer import IdentifierIssuer
import copy


class URDNA2015(object):
    """
    URDNA2015 implements the URDNA2015 RDF Dataset Normalization Algorithm.
    """

    def __init__(self):
        self.blank_node_info = {}
        self.hash_to_blank_nodes = {}
        self.canonical_issuer = IdentifierIssuer('_:c14n')
        self.quads = []
        self.POSITIONS = {'subject': 's', 'object': 'o', 'name': 'g'}

    # 4.4) Normalization Algorithm
    def main(self, dataset, options):
        # handle invalid output format
        if 'format' in options:
            if (options['format'] != 'application/n-quads' and
                    options['format'] != 'application/nquads'):
                raise UnknownFormatError(
                    'Unknown output format.', options['format'])

        # 1) Create the normalization state.

        # 2) For every quad in input dataset:
        for graph_name, triples in dataset.items():
            if graph_name == '@default':
                graph_name = None
            for triple in triples:
                quad = triple
                if graph_name is not None:
                    if graph_name.startswith('_:'):
                        quad['name'] = {'type': 'blank node'}
                    else:
                        quad['name'] = {'type': 'IRI'}
                    quad['name']['value'] = graph_name
                self.quads.append(quad)

                # 2.1) For each blank node that occurs in the quad, add a
                # reference to the quad using the blank node identifier in the
                # blank node to quads map, creating a new entry if necessary.
                for key, component in quad.items():
                    if key == 'predicate' or component['type'] != 'blank node':
                        continue
                    id_ = component['value']
                    self.blank_node_info.setdefault(
                        id_, {'quads': []})['quads'].append(quad)

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
        for hash, id_list in sorted(self.hash_to_blank_nodes.items()):
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
        for quad in self.quads:
            # 7.1) Create a copy, quad copy, of quad and replace any existing
            # blank node identifiers using the canonical identifiers previously
            # issued by canonical issuer. Note: We optimize away the copy here.
            for key, component in quad.items():
                if key == 'predicate':
                    continue
                if(component['type'] == 'blank node' and not
                    component['value'].startswith(
                        self.canonical_issuer.prefix)):
                    component['value'] = self.canonical_issuer.get_id(
                        component['value'])

            # 7.2) Add quad copy to the normalized dataset.
            normalized.append(serialize_nquad(quad))

        # sort normalized output
        normalized.sort()

        # 8) Return the normalized dataset.
        if (options.get('format') == 'application/n-quads' or
                options.get('format') == 'application/nquads'):
            return ''.join(normalized)
        return parse_nquads(''.join(normalized))

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
        for quad in quads:
            # 3.1) Serialize the quad in N-Quads format with the following
            # special rule:

            # 3.1.1) If any component in quad is an blank node, then serialize
            # it using a special identifier as follows:
            copy = {}
            for key, component in quad.items():
                if key == 'predicate':
                    copy[key] = component
                    continue
                # 3.1.2) If the blank node's existing blank node identifier
                # matches the reference blank node identifier then use the
                # blank node identifier _:a, otherwise, use the blank node
                # identifier _:z.
                copy[key] = self.modify_first_degree_component(
                    id_, component, key)
            nquads.append(serialize_nquad(copy))

        # 4) Sort nquads in lexicographical order.
        nquads.sort()

        # 5) Return the hash that results from passing the sorted, joined
        # nquads through the hash algorithm.
        info['hash'] = self.hash_nquads(nquads)
        return info['hash']

    # helper for modifying component during Hash First Degree Quads
    def modify_first_degree_component(self, id_, component, key):
        if component['type'] != 'blank node':
            return component
        component = copy.deepcopy(component)
        component['value'] = '_:a' if component['value'] == id_ else '_:z'
        return component

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

    # helper for getting a related predicate
    def get_related_predicate(self, quad):
        return '<' + quad['predicate']['value'] + '>'

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
                    if(self.canonical_issuer.has_id(related)):
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
                    if(len(chosen_path) != 0 and
                            len(path) >= len(chosen_path) and
                            path > chosen_path):
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
                    if(len(chosen_path) != 0 and
                            len(path) >= len(chosen_path) and
                            path > chosen_path):
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
            for key, component in quad.items():
                if(key != 'predicate' and
                        component['type'] == 'blank node' and
                        component['value'] != id_):
                    # 3.1.1) Set hash to the result of the Hash Related Blank
                    # Node algorithm, passing the blank node identifier for
                    # component as related, quad, path identifier issuer as
                    # issuer, and position as either s, o, or g based on
                    # whether component is a subject, object, graph name,
                    # respectively.
                    related = component['value']
                    position = self.POSITIONS[key]
                    hash = self.hash_related_blank_node(
                        related, quad, issuer, position)

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


class URGNA2012(URDNA2015):
    """
    URGNA2012 implements the URGNA2012 RDF Graph Normalization Algorithm.
    """

    def __init__(self):
        URDNA2015.__init__(self)

    # helper for modifying component during Hash First Degree Quads
    def modify_first_degree_component(self, id_, component, key):
        if component['type'] != 'blank node':
            return component
        component = copy.deepcopy(component)
        if key == 'name':
            component['value'] = '_:g'
        else:
            component['value'] = '_:a' if component['value'] == id_ else '_:z'
        return component

    # helper for getting a related predicate
    def get_related_predicate(self, quad):
        return quad['predicate']['value']

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
            # 3.1) If the quad's subject is a blank node that does not match
            # identifier, set hash to the result of the Hash Related Blank Node
            # algorithm, passing the blank node identifier for subject as
            # related, quad, path identifier issuer as issuer, and p as
            # position.
            if(quad['subject']['type'] == 'blank node' and
                    quad['subject']['value'] != id_):
                related = quad['subject']['value']
                position = 'p'
            # 3.2) Otherwise, if quad's object is a blank node that does
            # not match identifier, to the result of the Hash Related Blank
            # Node algorithm, passing the blank node identifier for object
            # as related, quad, path identifier issuer as issuer, and r
            # as position.
            elif(quad['object']['type'] == 'blank node' and
                    quad['object']['value'] != id_):
                related = quad['object']['value']
                position = 'r'
            # 3.3) Otherwise, continue to the next quad.
            else:
                continue

            # 3.4) Add a mapping of hash to the blank node identifier for the
            # component that matched (subject or object) to hash to related
            # blank nodes map, adding an entry as necessary.
            hash = self.hash_related_blank_node(
                related, quad, issuer, position)
            hash_to_related.setdefault(hash, []).append(related)

        return hash_to_related

    # helper to create appropriate hash object
    def create_hash(self):
        return hashlib.sha1()


def permutations(elements):
    """
    Generates all of the possible permutations for the given list of elements.

    :param elements: the list of elements to permutate.
    """
    # begin with sorted elements
    elements.sort()
    # initialize directional info for permutation algorithm
    left = {}
    for v in elements:
        left[v] = True

    length = len(elements)
    last = length - 1
    while True:
        yield elements

        # Calculate the next permutation using the Steinhaus-Johnson-Trotter
        # permutation algorithm.

        # get largest mobile element k
        # (mobile: element is greater than the one it is looking at)
        k, pos = None, 0
        for i in range(length):
            e = elements[i]
            is_left = left[e]
            if((k is None or e > k) and
                    ((is_left and i > 0 and e > elements[i - 1]) or
                        (not is_left and i < last and e > elements[i + 1]))):
                k, pos = e, i

        # no more permutations
        if k is None:
            return

        # swap k and the element it is looking at
        swap = pos - 1 if left[k] else pos + 1
        elements[pos], elements[swap] = elements[swap], k

        # reverse the direction of all elements larger than k
        for i in range(length):
            if elements[i] > k:
                left[elements[i]] = not left[elements[i]]


class UnknownFormatError(ValueError):
    """
    Base class for unknown format errors.
    """

    def __init__(self, message, format):
        Exception.__init__(self, message)
        self.format = format