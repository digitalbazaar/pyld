"""
Python implementation of JSON-LD processor

This implementation is ported from the Javascript implementation of
JSON-LD.

.. module:: pyld
  :synopsis: Python implementation of JSON-LD

.. moduleauthor:: Dave Longley 
.. moduleauthor:: Mike Johnson
.. moduleauthor:: Tim McNamara <tim.mcnamara@okfn.org>
"""

__copyright__ = "Copyright (c) 2011 Digital Bazaar, Inc."
__license__ = "New BSD licence"

__all__ = ["compact", "expand", "frame", "normalize"]

import copy

ns = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#'
}

xsd = {
    'boolean': ns['xsd'] + 'boolean',
    'double': ns['xsd'] + 'double',
    'integer': ns['xsd'] + 'integer'
}

def _setProperty(s, p, o):
    """
    Sets a subject's property to the given object value. If a value already
    exists, it will be appended to an array.

    :param s: the subjet.
    :param p: the property.
    :param o: the object.
    """
    if p in s:
        if isinstance(s[p], list):
            s[p].append(o)
        else:
            s[p] = [s[p], o]
    else:
        s[p] = o

def _getKeywords(ctx):
    """
    Gets the keywords from a context.

    :param ctx: the context.

    :return: the keywords.
    """
    # TODO: reduce calls to this function by caching keywords in processor
    # state

    rval = {
       '@datatype': '@datatype',
       '@iri': '@iri',
       '@language': '@language',
       '@literal': '@literal',
       '@subject': '@subject',
       '@type': '@type'
    }

    if ctx:
       # gather keyword aliases from context
       keywords = {}
       for key, value in ctx.items():
          if isinstance(value, basestring) and value in rval:
             keywords[value] = key

       # overwrite keywords
       for key in keywords:
          rval[key] = keywords[key]

    return rval

def _compactIri(ctx, iri, usedCtx):
    """
    Compacts an IRI into a term or CURIE if it can be. IRIs will not be
    compacted to relative IRIs if they match the given context's default
    vocabulary.

    :param ctx: the context to use.
    :param iri: the IRI to compact.
    :param usedCtx: a context to update if a value was used from "ctx".

    :return: the compacted IRI as a term or CURIE or the original IRI.
    """
    rval = None

    # check the context for a term that could shorten the IRI
    # (give preference to terms over CURIEs)
    for key in ctx:
        # skip special context keys (start with '@')
        if len(key) > 0 and not key.startswith('@'):
            # compact to a term
            if iri == ctx[key]:
                rval = key
                if usedCtx is not None:
                    usedCtx[key] = ctx[key]
                break

    # term not found, if term is rdf type, use built-in keyword
    if rval is None and iri == ns['rdf'] + 'type':
        rval = _getKeywords(ctx)['@type']

    # term not found, check the context for a CURIE prefix
    if rval is None:
        for key in ctx:
            # skip special context keys (start with '@')
            if len(key) > 0 and not key.startswith('@'):
                # see if IRI begins with the next IRI from the context
                ctxIri = ctx[key]
                idx = iri.find(ctxIri)

                # compact to a CURIE
                if idx == 0 and len(iri) > len(ctxIri):
                    rval = key + ':' + iri[len(ctxIri):]
                    if usedCtx is not None:
                        usedCtx[key] = ctxIri
                    break

    # could not compact IRI
    if rval is None:
        rval = iri

    return rval


def _expandTerm(ctx, term, usedCtx):
    """
    Expands a term into an absolute IRI. The term may be a regular term, a
    CURIE, a relative IRI, or an absolute IRI. In any case, the associated
    absolute IRI will be returned.

    :param ctx: the context to use.
    :param term: the term to expand.
    :param usedCtx: a context to update if a value was used from "ctx".

    :return: the expanded term as an absolute IRI.
    """
    rval = None

    # get JSON-LD keywords
    keywords = _getKeywords(ctx)

    # 1. If the property has a colon, then it is a CURIE or an absolute IRI:
    idx = term.find(':')
    if idx != -1:
        # get the potential CURIE prefix
        prefix = term[0:idx]

        # 1.1 See if the prefix is in the context
        if prefix in ctx:
            # prefix found, expand property to absolute IRI
            rval = ctx[prefix] + term[idx + 1:]
            if usedCtx is not None:
                usedCtx[prefix] = ctx[prefix]
        # 1.2. Prefix is not in context, property is already an absolute IRI:
        else:
            rval = term
    # 2. If the property is in the context, then it's a term.
    elif term in ctx:
        rval = ctx[term]
        if usedCtx is not None:
            usedCtx[term] = rval
    # 3. The property is the special-case subject.
    elif term == keywords['@subject']:
        rval = keywords['@subject']
    # 4. The property is the special-case rdf type.
    elif term == keywords['@type']:
        rval = ns['rdf'] + 'type'
    # 5. The property is a relative IRI, prepend the default vocab.
    else:
        rval = term
        if '@vocab' in ctx:
            rval = ctx['@vocab'] + rval
            if usedCtx is not None:
                usedCtx['@vocab'] = ctx['@vocab']

    return rval

def _isBlankNodeIri(v):
    """
    Checks if an IRI is a blank node.
    """
    return v.find('_:') == 0

def _isNamedBlankNode(v):
    """
    Checks if a named node is blank.
    """
    # look for "_:" at the beginning of the subject
    return (isinstance(v, dict) and '@subject' in v and
        '@iri' in v['@subject'] and _isBlankNodeIri(v['@subject']['@iri']))

def _isBlankNode(v):
    """
    Checks if the node is blank.
    """
    # look for no subject or named blank node
    return (isinstance(v, dict) and not ('@iri' in v or '@literal' in v) and
        ('@subject' not in v or _isNamedBlankNode(v)))

def _compare(v1, v2):
    """
    Compares two values.

    :param v1: the first value.
    :param v2: the second value.

    :return: -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2.
    """
    rval = 0

    if isinstance(v1, list) and isinstance(v2, list):
        for i in range(0, len(v1)):
            rval = _compare(v1[i], v2[i])
            if rval != 0:
                break
    else:
        rval = -1 if v1 < v2 else (1 if v1 > v2 else 0)

    return rval

def _compareObjectKeys(o1, o2, key):
    """
    Compares two keys in an object. If the key exists in one object
    and not the other, that object is less. If the key exists in both objects,
    then the one with the lesser value is less.
    
    :param o1: the first object.
    :param o2: the second object.
    :param key: the key.

    :return: -1 if o1 < o2, 0 if o1 == o2, 1 if o1 > o2.
    """
    rval = 0
    if key in o1:
        if key in o2:
            rval = _compare(o1[key], o2[key])
        else:
            rval = -1
    elif key in o2:
        rval = 1
    return rval

def _compareObjects(o1, o2):
    """
    Compares two object values.

    :param o1: the first object.
    :param o2: the second object.

    :return: -#1 if o1 < o2, 0 if o1 == o2, 1 if o1 > o2.
    """
    rval = 0

    if isinstance(o1, basestring):
        if isinstance(o2, basestring):
            rval = -1
        else:
            rval = _compare(o1, o2)
    elif isinstance(o2, basestring):
        rval = 1
    else:
        rval = _compareObjectKeys(o1, o2, '@literal')
        if rval == 0:
            if '@literal' in o1:
                rval = _compareObjectKeys(o1, o2, '@datatype')
                if rval == 0:
                    rval = _compareObjectKeys(o1, o2, '@language')
            # both are '@iri' objects
            else:
                rval = _compare(o1['@iri'], o2['@iri'])

    return rval

def _compareBlankNodeObjects(a, b):
    """
    Compares the object values between two bnodes.

    :param a: the first bnode.
    :param b: the second bnode.
    
    :return: -1 if a < b, 0 if a == b, 1 if a > b.
    """
    rval = 0

    # 3.     For each property, compare sorted object values.
    # 3.1.   The bnode with fewer objects is first.
    # 3.2.   For each object value, compare only literals and non-bnodes.
    # 3.2.1. The bnode with fewer non-bnodes is first.
    # 3.2.2. The bnode with a string object is first.
    # 3.2.3. The bnode with the alphabetically-first string is first.
    # 3.2.4. The bnode with a @literal is first.
    # 3.2.5. The bnode with the alphabetically-first @literal is first.
    # 3.2.6. The bnode with the alphabetically-first @datatype is first.
    # 3.2.7. The bnode with a @language is first.
    # 3.2.8. The bnode with the alphabetically-first @language is first.
    # 3.2.9. The bnode with the alphabetically-first @iri is first.

    for p in a:
        # step #3.1
        lenA = len(a[p]) if isinstance(a[p], list) else 1
        lenB = len(b[p]) if isinstance(b[p], list) else 1
        rval = _compare(lenA, lenB)

        # step #3.2.1
        if rval == 0:
            # normalize objects to an array
            objsA = a[p]
            objsB = b[p]
            if not isinstance(objsA, list):
                objsA = [objsA]
                objsB = [objsB]

            def bnodeFilter(e):
                return (isinstance(e, basestring) or
                    not ('@iri' in e and _isBlankNodeIri(e['@iri'])))

            # filter non-bnodes (remove bnodes from comparison)
            objsA = filter(bnodeFilter, objsA)
            objsB = filter(bnodeFilter, objsB)
            rval = _compare(len(objsA), len(objsB))

        # steps #3.2.2-3.2.9
        if rval == 0:
            objsA.sort(_compareObjects)
            objsB.sort(_compareObjects)
            for i in range(0, len(objsA)):
                rval = _compareObjects(objsA[i], objsB[i])
                if rval != 0:
                    break

        if rval != 0:
            break

    return rval

class NameGenerator:
    """
    Creates a blank node name generator using the given prefix for the
    blank nodes.

    :param prefix: the prefix to use.

    :return: the blank node name generator.
    """
    def __init__(self, prefix):
        self.count = -1
        self.prefix = prefix

    def next(self):
        self.count += 1
        return self.current()

    def current(self):
        return '_:%s%s' % (self.prefix, self.count)

    def inNamespace(self, iri):
        return iri.startswith('_:' + self.prefix)

def _collectSubjects(input, subjects, bnodes):
    """
    Populates a map of all named subjects from the given input and an array
    of all unnamed bnodes (includes embedded ones).

    :param input: the input (must be expanded, no context).
    :param subjects: the subjects map to populate.
    :param bnodes: the bnodes array to populate.
    """
    if input is None:
        # nothing to collect
        pass
    elif isinstance(input, list):
        for i in input:
            _collectSubjects(i, subjects, bnodes)
    elif isinstance(input, dict):
        if '@subject' in input:
            # graph literal
            if isinstance(input['@subject'], list):
                _collectSubjects(input['@subject'], subjects, bnodes)
            # named subject
            else:
                subjects[input['@subject']['@iri']] = input
        # unnamed blank node
        elif _isBlankNode(input):
            bnodes.append(input)

        # recurse through subject properties
        for key in input:
            _collectSubjects(input[key], subjects, bnodes)

def _flatten(parent, parentProperty, value, subjects):
    """
    Flattens the given value into a map of unique subjects. It is assumed that
    all blank nodes have been uniquely named before this call. Array values for
    properties will be sorted.

    :param parent: the value's parent, NULL for none.
    :param parentProperty: the property relating the value to the parent.
    :param value: the value to flatten.
    :param subjects: the map of subjects to write to.
    """
    flattened = None

    if value is None:
        # drop null values
        pass
    elif isinstance(value, list):
        # list of objects or a disjoint graph
        for i in value:
            _flatten(parent, parentProperty, i, subjects)
    elif isinstance(value, dict):
        # graph literal/disjoint graph
        if '@subject' in value and isinstance(value['@subject'], list):
            # cannot flatten embedded graph literals
            if parent is not None:
                raise Exception('Embedded graph literals cannot be flattened.')

            # top-level graph literal
            for key in value['@subject']:
                _flatten(parent, parentProperty, key, subjects)
        # already-expanded value
        elif '@literal' in value or '@iri' in value:
            flattened = copy.copy(value)
        # subject
        else:
            # create or fetch existing subject
            subject = None
            if value['@subject']['@iri'] in subjects:
                # FIXME: '@subject' might be a graph literal (as {})
                subject = subjects[value['@subject']['@iri']]
            else:
                subject = {}
                if '@subject' in value:
                    # FIXME: '@subject' might be a graph literal (as {})
                    subjects[value['@subject']['@iri']] = subject
            flattened = subject

            # flatten embeds
            for key, v in value.items():
                # drop null values
                if v is not None:
                    if key in subject:
                        if not isinstance(subject[key], list):
                            subject[key] = [subject[key]]
                    else:
                        subject[key] = []

                    _flatten(subject[key], None, v, subjects)
                    if len(subject[key]) == 1:
                        # convert subject[key] to object if it has only 1
                        subject[key] = subject[key][0]
    # string value
    else:
        flattened = value

    # add flattened value to parent
    if flattened is not None and parent is not None:
        # remove top-level '@subject' for subjects
        # 'http://mypredicate': {'@subject': {'@iri': 'http://mysubject'}}
        # becomes
        # 'http://mypredicate': {'@iri': 'http://mysubject'}
        if isinstance(flattened, dict) and '@subject' in flattened:
            flattened = flattened['@subject']

        if isinstance(parent, list):
            # do not add duplicate IRIs for the same property
            duplicate = False
            if isinstance(flattened, dict) and '@iri' in flattened:
                def parentFilter(e):
                    return (isinstance(e, dict) and '@iri' in e and
                        e['@iri'] == flattened['@iri'])

                duplicate = len(filter(parentFilter, parent)) > 0
            if not duplicate:
                parent.append(flattened)
        else:
            parent[parentProperty] = flattened

class MappingBuilder:
    """
    A MappingBuilder is used to build a mapping of existing blank node names
    to a form for serialization. The serialization is used to compare blank
    nodes against one another to determine a sort order.
    """
    def __init__(self):
        """
        Initialize the MappingBuilder.
        """
        self.count = 1
        self.processed = {}
        self.mapping = {}
        self.adj = {}
        self.keyStack = [{ 'keys': ['s1'], 'idx': 0 }]
        self.done = {}
        self.s = ''

    def copy(self):
        """
        Copies this MappingBuilder.

        :return: the MappingBuilder copy.
        """
        rval = MappingBuilder()
        rval.count = self.count
        rval.processed = copy.copy(self.processed)
        rval.mapping = copy.copy(self.mapping)
        rval.adj = copy.copy(self.adj)
        rval.keyStack = copy.copy(self.keyStack)
        rval.done = copy.copy(self.done)
        rval.s = self.s
        return rval

    def mapNode(self, iri):
        """
        Maps the next name to the given bnode IRI if the bnode IRI isn't already
        in the mapping. If the given bnode IRI is canonical, then it will be
        given a shortened form of the same name.

        :param iri: the blank node IRI to map the next name to.

        :return: the mapped name.
        """
        if iri not in self.mapping:
            if iri.startswith('_:c14n'):
                self.mapping[iri] = 'c%s' % iri[0:6]
            else:
                self.mapping[iri] = 's%s' % self.count
                self.count += 1
        return self.mapping[iri]

class Processor:
    """
    A JSON-LD processor.
    """
    def __init__(self):
        """
        Initialize the JSON-LD processor.
        """
        pass

    def compact(self, ctx, property, value, usedCtx):
        """
        Recursively compacts a value. This method will compact IRIs to CURIEs or
        terms and do reverse type coercion to compact a value.

        :param ctx: the context to use.
        :param property: the property that points to the value, NULL for none.
        :param value: the value to compact.
        :param usedCtx: a context to update if a value was used from "ctx".

        :return: the compacted value.
        """
        rval = None

        # get JSON-LD keywords
        keywords = _getKeywords(ctx)

        if value is None:
            # return None, but check coerce type to add to usedCtx
            rval = None
            self.getCoerceType(ctx, property, usedCtx)
        elif isinstance(value, list):
            # recursively add compacted values to array
            rval = []
            for i in value:
                rval.append(self.compact(ctx, property, i, usedCtx))
        # graph literal/disjoint graph
        elif (isinstance(value, dict) and '@subject' in value and
            isinstance(value['@subject'], list)):
            rval = {}
            rval[keywords['@subject']] = self.compact(
                ctx, property, value['@subject'], usedCtx)
        # value has sub-properties if it doesn't define a literal or IRI value
        elif (isinstance(value, dict) and '@literal' not in value and
            '@iri' not in value):
            # recursively handle sub-properties that aren't a sub-context
            rval = {}
            for key in value:
                if value[key] != '@context':
                    # set object to compacted property, only overwrite existing
                    # properties if the property actually compacted
                    p = _compactIri(ctx, key, usedCtx)
                    if p != key or p not in rval:
                       rval[p] = self.compact(ctx, key, value[key], usedCtx)
        else:
            # get coerce type
            coerce = self.getCoerceType(ctx, property, usedCtx)

            # get type from value, to ensure coercion is valid
            type = None
            if isinstance(value, dict):
                # type coercion can only occur if language is not specified
                if '@language' not in value:
                    # datatype must match coerce type if specified
                    if '@datatype' in value:
                        type = value['@datatype']
                    # datatype is IRI
                    elif '@iri' in value:
                        type = '@iri'
                    # can be coerced to any type
                    else:
                        type = coerce
            # type can be coerced to anything
            elif isinstance(value, basestring):
                type = coerce

            # types that can be auto-coerced from a JSON-builtin
            if coerce is None and (type == xsd['boolean'] or
                type == xsd['integer'] or type == xsd['double']):
                coerce = type

            # do reverse type-coercion
            if coerce is not None:
                # type is only None if a language was specified, which is an
                # error if type coercion is specified
                if type is None:
                    raise Exception('Cannot coerce type when a language is ' +
                        'specified. The language information would be lost.')
                # if the value type does not match the coerce type, it is an
                # error
                elif type != coerce:
                    raise Exception('Cannot coerce type because the ' +
                        'datatype does not match.')
                # do reverse type-coercion
                else:
                    if isinstance(value, dict):
                        if '@iri' in value:
                            rval = value['@iri']
                        elif '@literal' in value:
                            rval = value['@literal']
                    else:
                        rval = value

                    # do basic JSON types conversion
                    if coerce == xsd['boolean']:
                        rval = (rval == 'true' or rval != 0)
                    elif coerce == xsd['double']:
                        rval = float(rval)
                    elif coerce == xsd['integer']:
                        rval = int(rval)

            # no type-coercion, just change keywords/copy value
            elif isinstance(value, dict):
                rval = {}
                for key, v in value.items():
                    rval[keywords[key]] = v
            else:
                rval = copy.copy(value)

            # compact IRI
            if type == '@iri':
                if isinstance(rval, dict):
                    rval[keywords['@iri']] = _compactIri(
                        ctx, rval[keywords['@iri']], usedCtx)
                else:
                    rval = _compactIri(ctx, rval, usedCtx)

        return rval

    def expand(self, ctx, property, value, expandSubjects):
        """
        Recursively expands a value using the given context. Any context in
        the value will be removed.

        :param ctx: the context.
        :param property: the property that points to the value, NULL for none.
        :param value: the value to expand.
        :param expandSubjects: True to expand subjects (normalize), False not to.

        :return: the expanded value.
        """
        rval = None

        # TODO: add data format error detection?

        # value is null, nothing to expand
        if value is None:
            rval = None
        # if no property is specified and the value is a string (this means the
        # value is a property itself), expand to an IRI
        elif property is None and isinstance(value, basestring):
            rval = _expandTerm(ctx, value, None)
        elif isinstance(value, list):
            # recursively add expanded values to array
            rval = []
            for i in value:
                rval.append(self.expand(ctx, property, i, expandSubjects))
        elif isinstance(value, dict):
            # if value has a context, use it
            if '@context' in value:
                ctx = mergeContexts(ctx, value['@context'])

            # get JSON-LD keywords
            keywords = _getKeywords(ctx)

            # value has sub-properties if it doesn't define a literal or IRI
            # value
            if not (keywords['@literal'] in value or keywords['@iri'] in value):
                # recursively handle sub-properties that aren't a sub-context
                rval = {}
                for key in value:
                    # preserve frame keywords
                    if (key == '@embed' or key == '@explicit' or
                        key == '@default' or key == '@omitDefault'):
                        _setProperty(rval, key, copy.copy(value[key]))
                    elif key != '@context':
                        # set object to expanded property
                        _setProperty(rval, _expandTerm(ctx, key, None),
                            self.expand(ctx, key, value[key], expandSubjects))
            # only need to expand keywords
            else:
                rval = {}
                if keywords['@iri'] in value:
                    rval['@iri'] = value[keywords['@iri']]
                else:
                    rval['@literal'] = value[keywords['@literal']]
                    if keywords['@language'] in value:
                        rval['@language'] = value[keywords['@language']]
                    elif keywords['@datatype'] in value:
                        rval['@datatype'] = value[keywords['@datatype']]
        else:
            # do type coercion
            coerce = self.getCoerceType(ctx, property, None)

            # get JSON-LD keywords
            keywords = _getKeywords(ctx)

            # automatic coercion for basic JSON types
            if coerce is None and isinstance(value, (int, long, float, bool)):
                if isinstance(value, bool):
                    coerce = xsd['boolean']
                elif isinstance(value, float):
                    coerce = xsd['double']
                else:
                    coerce = xsd['integer']

            # coerce to appropriate datatype, only expand subjects if requested
            if coerce is not None and (
                property != keywords['@subject'] or expandSubjects):
                rval = {}

                # expand IRI
                if coerce == '@iri':
                    rval['@iri'] = _expandTerm(ctx, value, None)
                # other datatype
                else:
                    rval['@datatype'] = coerce
                    if coerce == xsd['double']:
                        # do special JSON-LD double format
                        value = '%1.6e' % value
                    elif coerce == xsd['boolean']:
                        value = 'true' if value else 'false'
                    else:
                        value = '%s' % value
                    rval['@literal'] = value
            # nothing to coerce
            else:
                rval = '' + value

        return rval

    ##
    def normalize(self, input):
        """
        Normalizes a JSON-LD object.

        :param input: the JSON-LD object to normalize.

        :return: the normalized JSON-LD object.
        """
        rval = []

        # TODO: validate context

        if input is not None:
            # create name generator state
            self.tmp = None
            self.c14n = None

            # expand input
            expanded = self.expand({}, None, input, True)

            # assign names to unnamed bnodes
            self.nameBlankNodes(expanded)

            # flatten
            subjects = {}
            _flatten(None, None, expanded, subjects)

            # append subjects with sorted properties to array
            for s in subjects.values():
                sorted = {}
                keys = s.keys()
                keys.sort()
                for k in keys:
                    sorted[k] = s[k]
                rval.append(sorted)

            # canonicalize blank nodes
            self.canonicalizeBlankNodes(rval)

            def normalizeSort(a, b):
                return _compare(a['@subject']['@iri'], b['@subject']['@iri'])

            # sort output
            rval.sort(cmp=normalizeSort)

        return rval


    def getCoerceType(self, ctx, property, usedCtx):
        """
        Gets the coerce type for the given property.

        :param ctx: the context to use.
        :param property: the property to get the coerced type for.
        :param usedCtx: a context to update if a value was used from "ctx".

        :return: the coerce type, None for none.
        """
        rval = None

        # get expanded property
        p = _expandTerm(ctx, property, None)

        # built-in type coercion JSON-LD-isms
        if p == '@subject' or p == ns['rdf'] + 'type':
            rval = '@iri'

        # check type coercion for property
        elif '@coerce' in ctx:
            # force compacted property
            p = _compactIri(ctx, p, None)

            for type in ctx['@coerce']:
                # get coerced properties (normalize to an array)
                props = ctx['@coerce'][type]
                if not isinstance(props, list):
                    props = [props]

                # look for the property in the array
                for i in props:
                    # property found
                    if i == p:
                        rval = _expandTerm(ctx, type, usedCtx)
                        if usedCtx is not None:
                            if '@coerce' not in usedCtx:
                                usedCtx['@coerce'] = {}

                            if type not in usedCtx['@coerce']:
                                usedCtx['@coerce'][type] = p
                            else:
                                c = usedCtx['@coerce'][type]
                                if ((isinstance(c, list) and c.find(p) == -1) or
                                    (isinstance(c, basestring) and c != p)):
                                    _setProperty(usedCtx['@coerce'], type, p)
                        break

        return rval

    def nameBlankNodes(self, input):
        """
        Assigns unique names to blank nodes that are unnamed in the given input.

        :param input: the input to assign names to.
        """
        # create temporary blank node name generator
        ng = self.tmp = NameGenerator('tmp')

        # collect subjects and unnamed bnodes
        subjects = {}
        bnodes = []
        _collectSubjects(input, subjects, bnodes)

        # uniquely name all unnamed bnodes
        for bnode in bnodes:
            if not ('@subject' in bnode):
                # generate names until one is unique
                while(ng.next() in subjects):
                    pass
                bnode['@subject'] = { '@iri': ng.current() }
                subjects[ng.current()] = bnode

    def renameBlankNode(self, b, id):
        """
        Renames a blank node, changing its references, etc. The method assumes
        that the given name is unique.

        :param b: the blank node to rename.
        :param id: the new name to use.
        """
        old = b['@subject']['@iri']

        # update bnode IRI
        b['@subject']['@iri'] = id

        # update subjects map
        subjects = self.subjects
        subjects[id] = subjects[old]
        del subjects[old]

        # update reference and property lists
        self.edges['refs'][id] = self.edges['refs'][old]
        self.edges['props'][id] = self.edges['props'][old]
        del self.edges['refs'][old]
        del self.edges['props'][old]

        # update references to this bnode
        refs = self.edges['refs'][id]['all']
        for i in refs:
            iri = i['s']
            if iri == old:
                iri = id
            ref = subjects[iri]
            props = self.edges['props'][iri]['all']
            for i2 in props:
                if i2['s'] == old:
                    i2['s'] = id

                    # normalize property to array for single code-path
                    p = i2['p']
                    tmp = ([ref[p]] if isinstance(ref[p], dict) else
                        (ref[p] if isinstance(ref[p], list) else []))
                    for n in tmp:
                        if (isinstance(n, dict) and '@iri' in n and
                            n['@iri'] == old):
                            n['@iri'] = id

        # update references from this bnode
        props = self.edges['props'][id]['all']
        for i in props:
            iri = i['s']
            refs = self.edges['refs'][iri]['all']
            for r in refs:
                if r['s'] == old:
                    r['s'] = id

    def canonicalizeBlankNodes(self, input):
        """
        Canonically names blank nodes in the given input.

        :param input: the flat input graph to assign names to.
        """
        # create serialization state
        self.renamed = {}
        self.mappings = {}
        self.serializations = {}

        # collect subject and bnodes from flat input graph
        edges = self.edges = {
            'refs': {},
            'props': {}
        }
        subjects = self.subjects = {}
        bnodes = []
        for s in input:
            iri = s['@subject']['@iri']
            subjects[iri] = s
            edges['refs'][iri] = {
                'all': [],
                'bnodes': []
            }
            edges['props'][iri] = {
                'all': [],
                'bnodes': []
            }
            if _isBlankNodeIri(iri):
                bnodes.append(s)

        # collect edges in the graph
        self.collectEdges()

        # create canonical blank node name generator
        c14n = self.c14n = NameGenerator('c14n')
        ngTmp = self.tmp

        # rename all bnodes that happen to be in the c14n namespace
        # and initialize serializations
        for bnode in bnodes:
            iri = bnode['@subject']['@iri']
            if c14n.inNamespace(iri):
                while ngTmp.next() in subjects:
                    pass
                self.renameBlankNode(bnode, ngTmp.current())
                iri = bnode['@subject']['@iri']
            self.serializations[iri] = {
                'props': None,
                'refs': None
            }

        # keep sorting and naming blank nodes until they are all named
        while len(bnodes) > 0:
            # define bnode sorting function
            def bnodeSort(a, b):
                return self.deepCompareBlankNodes(a, b)

            bnodes.sort(cmp=bnodeSort)

            # name all bnodes accoring to the first bnodes relation mappings
            bnode = bnodes.pop(0)
            iri = bnode['@subject']['@iri']
            dirs = ['props', 'refs']
            for dir in dirs:
                # if no serialization has been computed,
                # name only the first node
                if self.serializations[iri][dir] is None:
                    mapping = {}
                    mapping[iri] = 's1'
                else:
                    mapping = self.serializations[iri][dir]['m']

                # define key sorting function
                def sortKeys(a, b):
                    return _compare(mapping[a], mapping[b])

                # sort keys by value to name them in order
                keys = mapping.keys()
                keys.sort(sortKeys)

                # name bnodes in mapping
                renamed = []
                for iriK in keys:
                    if not c14n.inNamespace(iri) and iriK in subjects:
                        self.renameBlankNode(subjects[iriK], c14n.next())
                        renamed.append(iriK)

                # only keep non-canonically named bnodes
                tmp = bnodes
                bnodes = []
                for b in tmp:
                    iriB = b['@subject']['@iri']
                    if not c14n.inNamespace(iriB):
                        for i2 in renamed:
                            self.markSerializationDirty(iriB, i2, dir)
                        bnodes.append(b)

        # sort property lists that now have canonically named bnodes
        for key in edges['props']:
            if len(edges['props'][key]['bnodes']) > 0:
                bnode = subjects[key]
                for p in bnode:
                    if p.find('@') != 0 and isinstance(bnode[p], list):
                        bnode[p].sort(_compareObjects)

    def markSerializationDirty(self, iri, changed, dir):
        """
        Marks a relation serialization as dirty if necessary.

        :param iri: the IRI of the bnode to check.
        :param changed: the old IRI of the bnode that changed.
        :param dir: the direction to check ('props' or 'refs').
        """
        s = self.serializations[iri]
        if s[dir] is not None and changed in s[dir]['m']:
            s[dir] = None

    def serializeMapping(self, mb):
        """
        Recursively increments the relation serialization for a mapping.

        :param mb: the mapping builder to update.
        """
        if len(mb.keyStack) > 0:
            # continue from top of key stack
            next = mb.keyStack.pop()
            while next['idx'] < len(next['keys']):
                k = next['keys'][next['idx']]
                if k not in mb.adj:
                    mb.keyStack.append(next)
                    break
                next['idx'] += 1

                if k in mb.done:
                    # mark cycle
                    mb.s += '_' + k
                else:
                    # mark key as serialized
                    mb.done[k] = True

                    # serialize top-level key and its details
                    s = k
                    adj = mb.adj[k]
                    iri = adj['i']
                    if iri in self.subjects:
                        b = self.subjects[iri]

                        # serialize properties
                        s += '[' + _serializeProperties(b) + ']'

                        # serialize references
                        s += '['
                        first = True
                        refs = self.edges['refs'][iri]['all']
                        for r in refs:
                            if first:
                                first = False
                            else:
                                s += '|'
                            s += '<' + r['p'] + '>'
                            s += ('_:' if _isBlankNodeIri(r['s']) else
                               ('<' + r['s'] + '>'))
                        s += ']'

                    # serialize adjacent node keys
                    s += ''.join(adj['k'])
                    mb.s += s
                    mb.keyStack.append({ 'keys': adj['k'], 'idx': 0 })
                    self.serializeMapping(mb)

    def serializeCombos(self, s, iri, siri, mb, dir, mapped, notMapped):
        """
        Recursively serializes adjacent bnode combinations.

        :param s: the serialization to update.
        :param iri: the IRI of the bnode being serialized.
        :param siri: the serialization name for the bnode IRI.
        :param mb: the MappingBuilder to use.
        :param dir: the edge direction to use ('props' or 'refs').
        :param mapped: all of the already-mapped adjacent bnodes.
        :param notMapped: all of the not-yet mapped adjacent bnodes.
        """
        # handle recursion
        if len(notMapped) > 0:
            # copy mapped nodes
            mapped = copy.copy(mapped)

            # map first bnode in list
            mapped[mb.mapNode(notMapped[0]['s'])] = notMapped[0]['s']

            # recurse into remaining possible combinations
            original = mb.copy()
            notMapped = notMapped[1:]
            rotations = max(1, len(notMapped))
            for r in range(0, rotations):
                m = mb if r == 0 else original.copy()
                self.serializeCombos(s, iri, siri, m, dir, mapped, notMapped)

                # rotate not-mapped for next combination
                _rotate(notMapped)
        # no more adjacent bnodes to map, update serialization
        else:
            keys = mapped.keys()
            keys.sort()
            mb.adj[siri] = { 'i': iri, 'k': keys, 'm': mapped }
            self.serializeMapping(mb)

            # optimize away mappings that are already too large
            if (s[dir] is None or
                _compareSerializations(mb.s, s[dir]['s']) <= 0):
                # recurse into adjacent alues
                for k in keys:
                    self.serializeBlankNode(s, mapped[k], mb, dir)

                # update least serialization if new one has been found
                self.serializeMapping(mb)
                if (s[dir] is None or
                    (_compareSerializations(mb.s, s[dir]['s']) <= 0 and
                    len(mb.s) >= len(s[dir]['s']))):
                    s[dir] = { 's': mb.s, 'm': mb.mapping }

    def serializeBlankNode(self, s, iri, mb, dir):
        """
        Computes the relation serialization for the given blank node IRI.

        :param s: the serialization to update.
        :param iri: the current bnode IRI to be mapped.
        :param mb: the MappingBuilder to use.
        :param dir: the edge direction to use ('props' or 'refs').
        """
        # only do mapping if iri not already processed
        if iri not in mb.processed:
            # iri now processed
            mb.processed[iri] = True
            siri = mb.mapNode(iri)

            # copy original mapping builder
            original = mb.copy()

            # split adjacent bnodes on mapped and not-mapped
            adj = self.edges[dir][iri]['bnodes']
            mapped = {}
            notMapped = []
            for i in adj:
                if i['s'] in mb.mapping:
                    mapped[mb.mapping[i['s']]] = i['s']
                else:
                    notMapped.append(i)

            # TODO: ensure this optimization does not alter canonical order

            # if the current bnode already has a serialization, reuse it
            #hint = (self.serializations[iri][dir] if iri in
            #   self.serializations else None)
            #if hint is not None:
            #    hm = hint['m']
            #    
            #    def notMappedSort(a, b):
            #        return _compare(hm[a['s']], hm[b['s']])
            #    
            #    notMapped.sort(cmp=notMappedSort)
            #    for i in notMapped:
            #        mapped[mb.mapNode(notMapped[i]['s'])] = notMapped[i]['s']
            #    notMapped = []

            # loop over possible combinations
            combos = max(1, len(notMapped))
            for i in range(0, combos):
                m = mb if i == 0 else original.copy()
                self.serializeCombos(s, iri, siri, mb, dir, mapped, notMapped)

    def deepCompareBlankNodes(self, a, b):
        """
        Compares two blank nodes for equivalence.

        :param a: the first blank node.
        :param b: the second blank node.

        :return: -1 if a < b, 0 if a == b, 1 if a > b.
        """
        rval = 0

        # compare IRIs
        iriA = a['@subject']['@iri']
        iriB = b['@subject']['@iri']
        if iriA == iriB:
            rval = 0
        else:
            # do shallow compare first
            rval = self.shallowCompareBlankNodes(a, b)

            # deep comparison is necessary
            if rval == 0:
                # compare property edges then reference edges
                dirs = ['props', 'refs']
                for i in range(0, len(dirs)):
                    # recompute 'a' and 'b' serializations as necessary
                    dir = dirs[i]
                    sA = self.serializations[iriA]
                    sB = self.serializations[iriB]
                    if sA[dir] is None:
                        mb = MappingBuilder()
                        if dir == 'refs':
                            # keep same mapping and count from 'props'
                            # serialization
                            mb.mapping = copy.copy(sA['props']['m'])
                            mb.count = len(mb.mapping.keys()) + 1
                        self.serializeBlankNode(sA, iriA, mb, dir)
                    if sB[dir] is None:
                        mb = MappingBuilder()
                        if dir == 'refs':
                            # keep same mapping and count from 'props'
                            # serialization
                            mb.mapping = copy.copy(sB['props']['m'])
                            mb.count = len(mb.mapping.keys()) + 1
                        self.serializeBlankNode(sB, iriB, mb, dir)

                    # compare serializations
                    rval = _compare(sA[dir]['s'], sB[dir]['s'])

                    if rval != 0:
                        break
        return rval

    def shallowCompareBlankNodes(self, a, b):
        """
        Performs a shallow sort comparison on the given bnodes.

        :param a: the first bnode.
        :param b: the second bnode.

        :return: -1 if a < b, 0 if a == b, 1 if a > b.
        """
        rval = 0

        # ShallowSort Algorithm (when comparing two bnodes):
        # 1.   Compare the number of properties.
        # 1.1. The bnode with fewer properties is first.
        # 2.   Compare alphabetically sorted-properties.
        # 2.1. The bnode with the alphabetically-first property is first.
        # 3.   For each property, compare object values.
        # 4.   Compare the number of references.
        # 4.1. The bnode with fewer references is first.
        # 5.   Compare sorted references.
        # 5.1. The bnode with the reference iri (vs. bnode) is first.
        # 5.2. The bnode with the alphabetically-first reference iri is first.
        # 5.3. The bnode with the alphabetically-first reference property is
        #      first.

        pA = a.keys()
        pB = b.keys()

        # step #1
        rval = _compare(len(pA), len(pB))

        # step #2
        if rval == 0:
            pA.sort()
            pB.sort()
            rval = _compare(pA, pB)

        # step #3
        if rval == 0:
            rval = _compareBlankNodeObjects(a, b)

        # step #4
        if rval == 0:
            edgesA = self.edges['refs'][a['@subject']['@iri']]['all']
            edgesB = self.edges['refs'][b['@subject']['@iri']]['all']
            rval = _compare(len(edgesA), len(edgesB))

        # step #5
        if rval == 0:
            for i in range(0, len(edgesA)):
                rval = self.compareEdges(edgesA[i], edgesB[i])
                if rval != 0:
                    break

        return rval

    ##
    def compareEdges(self, a, b):
        """
        Compares two edges. Edges with an IRI (vs. a bnode ID) come first, then
        alphabetically-first IRIs, then alphabetically-first properties. If a
        blank node has been canonically named, then blank nodes will be compared
        after properties (with a preference for canonically named over
        non-canonically named), otherwise they won't be.

        :param a: the first edge.
        :param b: the second edge.

        :return: -1 if a < b, 0 if a == b, 1 if a > b.
        """
        rval = 0

        bnodeA = _isBlankNodeIri(a['s'])
        bnodeB = _isBlankNodeIri(b['s'])
        c14n = self.c14n

        # if not both bnodes, one that is a bnode is greater
        if bnodeA != bnodeB:
            rval = 1 if bnodeA else - 1
        else:
            if not bnodeA:
                rval = _compare(a['s'], b['s'])
            if rval == 0:
                rval = _compare(a['p'], b['p'])

            # do bnode IRI comparison if canonical naming has begun
            if rval == 0 and c14n is not None:
                c14nA = c14n.inNamespace(a['s'])
                c14nB = c14n.inNamespace(b['s'])
                if c14nA != c14nB:
                    rval = 1 if c14nA else - 1
                elif c14nA:
                    rval = _compare(a['s'], b['s'])

        return rval

    def collectEdges(self):
        """
        Populates the given reference map with all of the subject edges in the
        graph. The references will be categorized by the direction of the edges,
        where 'props' is for properties and 'refs' is for references to a subject
        as an object. The edge direction categories for each IRI will be sorted
        into groups 'all' and 'bnodes'.
        """
        refs = self.edges['refs']
        props = self.edges['props']

        # collect all references and properties
        for iri in self.subjects:
            subject = self.subjects[iri]
            for key in subject:
                if key != '@subject':
                    # normalize to array for single codepath
                    object = subject[key]
                    tmp = [object] if not isinstance(object, list) else object
                    for o in tmp:
                        if (isinstance(o, dict) and '@iri' in o and
                            o['@iri'] in self.subjects):
                            objIri = o['@iri']

                            # map object to this subject
                            refs[objIri]['all'].append({ 's': iri, 'p': key })

                            # map this subject to object
                            props[iri]['all'].append({ 's': objIri, 'p': key })

        # create node filter function
        def filterNodes(edge):
            return _isBlankNodeIri(edge['s'])

        # create sorted categories
        for iri in refs:
            refs[iri]['all'].sort(cmp=self.compareEdges)
            refs[iri]['bnodes'] = filter(filterNodes, refs[iri]['all'])
        for iri in props:
            props[iri]['all'].sort(cmp=self.compareEdges)
            props[iri]['bnodes'] = filter(filterNodes, props[iri]['all'])

    def frame(self, input, frame, options=None):
        """
        Frames JSON-LD input.

        :param input: the JSON-LD input.
        :param frame: the frame to use.
        :param options: framing options to use.

        :return: the framed output.
        """
        rval = None

        # normalize input
        input = self.normalize(input)

        # save frame context
        ctx = None
        if '@context' in frame:
            ctx = copy.copy(frame['@context'])

        # remove context from frame
        frame = expand(frame)

        # create framing options
        # TODO: merge in options from function parameter
        options = {
            'defaults':
            {
                'embedOn': True,
                'explicitOn': False,
                'omitDefaultOn': False
            }
        }

        # build map of all subjects
        subjects = {}
        for i in input:
            subjects[i['@subject']['@iri']] = i

        # frame input
        rval = _frame(subjects, input, frame, {}, options)

        # apply context
        if ctx is not None and rval is not None:
            rval = compact(ctx, rval)

        return rval


def _isType(src, frame):
    """
    Returns True if the given source is a subject and has one of the given
    types in the given frame.

    :param src: the input.
    :param frame: the frame with types to look for.

    :return: True if the src has one of the given types.
    """
    rval = False

    # check if type(s) are specified in frame and src
    rType = ns['rdf'] + 'type'
    if (rType in frame and isinstance(src, dict) and '@subject' in src and
        rType in src):
        tmp = src[rType] if isinstance(src[rType], list) else [src[rType]]
        types = (frame[rType] if isinstance(frame[rType], list)
            else [frame[rType]])

        for t in range(0, len(types)):
            rType = types[t]['@iri']
            for i in tmp:
                if i['@iri'] == rType:
                    rval = True
                    break
            if rval:
                break

    return rval

def _filterNonKeywords(e):
    """
    Returns True if the given element is not a keyword.

    :param e: the element.

    :return True: if the given element is not a keyword.
    """
    return e.find('@') != 0


def _isDuckType(src, frame):
    """
    Returns True if the given src matches the given frame via duck-typing.

    :param src: the input.
    :param frame: the frame to check against.

    :return: True if the src matches the frame.
    """
    rval = False

    # frame must not have a specific type
    rType = ns['rdf'] + 'type'
    if rType not in frame:
        # get frame properties that must exist on src
        props = frame.keys()
        props = filter(_filterNonKeywords, props)
        if not props:
            # src always matches if there are no properties
            rval = True
        # src must be a subject with all the given properties
        elif isinstance(src, dict) and '@subject' in src:
            rval = True
            for i in props:
                if i not in src:
                    rval = False
                    break

    return rval

def _frame(subjects, input, frame, embeds, options):
    """
    Recursively frames the given input according to the given frame.

    :param subjects: a map of subjects in the graph.
    :param input: the input to frame.
    :param frame: the frame to use.
    :param embeds: a map of previously embedded subjects, used to prevent cycles.
    :param options: the framing options.

    :return: the framed input.
    """
    rval = None

    # prepare output, set limit, get array of frames
    limit = -1
    frames = None
    if isinstance(frame, list):
        rval = []
        frames = frame
        if not frames:
            frames.append({})
    else:
        frames = [frame]
        limit = 1

    # iterate over frames adding input matches to list
    values = []
    for i in range(0, len(frames)):
        # get next frame
        frame = frames[i]
        if not isinstance(frame, (list, dict)):
            raise Exception('Invalid JSON-LD frame. Frame type is not a map' +
               'or array.')

        # create array of values for each frame
        values.append([])
        for n in input:
            # dereference input if it refers to a subject
            if (isinstance(n, dict) and '@iri' in n and
               n['@iri'] in subjects):
               n = subjects[n['@iri']]

            # add input to list if it matches frame specific type or duck-type
            if _isType(n, frame) or _isDuckType(n, frame):
                values[i].append(n)
                limit -= 1
            if limit == 0:
                break
        if limit == 0:
            break

    # for each matching value, add it to the output
    for frame, vals in zip(frames, values):
        for value in vals:
            # determine if value should be embedded or referenced
            embedOn = (frame['@embed'] if '@embed' in frame
                else options['defaults']['embedOn'])

            if not embedOn:
                # if value is a subject, only use subject IRI as reference 
                if isinstance(value, dict) and '@subject' in value:
                    value = value['@subject']
            elif (isinstance(value, dict) and '@subject' in value and
                value['@subject']['@iri'] in embeds):

                # TODO: possibly support multiple embeds in the future ... and
                # instead only prevent cycles?
                raise Exception(
                    'More than one embed of the same subject is not supported.',
                    value['@subject']['@iri'])

            # if value is a subject, do embedding and subframing
            elif isinstance(value, dict) and '@subject' in value:
                embeds[value['@subject']['@iri']] = True

                # if explicit on, remove keys from value that aren't in frame
                explicitOn = (frame['@explicit'] if '@explicit' in frame
                    else options['defaults']['explicitOn'])
                if explicitOn:
                    for key in value.keys():
                        # do not remove subject or any key in the frame
                        if key != '@subject' and key not in frame:
                            del value[key]

                # iterate over frame keys to do subframing
                for key, f in frame.items():
                    # skip keywords and type query
                    if key.find('@') != 0 and key != ns['rdf'] + 'type':
                        if key in value:
                            # build input and do recursion
                            input = (value[key] if isinstance(value[key], list)
                                else [value[key]])
                            for n in range(0, len(input)):
                                # replace reference to subject w/subject
                                if (isinstance(input[n], dict) and
                                    '@iri' in input[n] and
                                    input[n]['@iri'] in subjects):
                                    input[n] = subjects[input[n]['@iri']]
                            result = _frame(subjects, input, f, embeds, options)
                            if result is not None:
                                value[key] = result
                            elif omitOn:
                                # omit is on, remove key
                                del value[key]
                            else:
                                # use specified default from frame if available
                                if isinstance(f, list):
                                    f = f[0] if len(f) > 0 else {}
                                    value[key] = (f['@default'] if
                                        '@default' in f else None)
                        else:
                            # add empty array/null property to value
                            value[key] = [] if isinstance(f, list) else None

                        # handle setting default value
                        if value[key] is None:
                            # use first subframe if frame is an array
                            if isinstance(f, list):
                                f = f[0] if len(f) > 0 else {}

                            # determine if omit default is on
                            omitOn = (f['@omitDefault'] if
                                '@omitDefault' in f
                                else options['defaults']['omitDefaultOn'])
                            if omitOn:
                                del value[key]
                            elif '@default' in f:
                                value[key] = f['@default']

            # add value to output
            if rval is None:
                rval = value
            else:
                rval.append(value)

    return rval

def _rotate(a):
    """
    Rotates the elements in an array one position.

    :param a: the array.
    """
    if len(a) > 0:
        a.append(a.pop(0))

def _serializeProperties(b):
    """
    Serializes the properties of the given bnode for its relation serialization.

    :param b: the blank node.

    :return: the serialized properties.
    """
    rval = ''
    first = True
    for p in b.keys():
        if p != '@subject':
            if first:
                first = False
            else:
                rval += '|'
            rval += '<' + p + '>'
            objs = b[p] if isinstance(b[p], list) else [b[p]]
            for o in objs:
                if isinstance(o, dict):
                    # iri
                    if '@iri' in o:
                        if _isBlankNodeIri(o['@iri']):
                            rval += '_:'
                        else:
                            rval += '<' + o['@iri'] + '>'
                    # literal
                    else:
                        rval += '"' + o['@literal'] + '"'

                        # datatype literal
                        if '@datatype' in o:
                            rval += '^^<' + o['@datatype'] + '>'
                        # language literal
                        elif '@language' in o:
                            rval += '@' + o['@language']
                # plain literal
                else:
                    rval += '"' + o + '"'
    return rval

def _compareSerializations(s1, s2):
    """
    Compares two serializations for the same blank node. If the two
    serializations aren't complete enough to determine if they are equal (or if
    they are actually equal), 0 is returned.

    :param s1: the first serialization.
    :param s2: the second serialization.

    :return: -1 if s1 < s2, 0 if s1 == s2 (or indeterminate), 1 if s1 > v2.
    """
    rval = 0
    if len(s1) == len(s2):
        rval = _compare(s1, s2)
    elif len(s1) > len(s2):
        rval = _compare(s1[0:len(s2)], s2)
    else:
        rval = _compare(s1, s2[0:len(s1)])
    return rval


def triples(input, callback=None):
    normalized = normalize(input)
    rval = None

    # normalize input
    if (callback == None):
        rval = []
        def callback(s,p,o):
            rval.append({'s':s, 'p':p, 'o':o })
            return True

    quit = False
    for e in normalized:
        s = e['@subject']['@iri']
        for p, obj in e.iteritems():
            if p == '@subject': continue
            if not isinstance(obj, list):
                obj = [obj]
            for o2 in obj:
                quit = callback(s, p, o2)==False
                if quit: break
            if quit: break
        if quit: break
    
    return rval

def normalize(input):
    """
    Normalizes a JSON-LD object.

    :param input: the JSON-LD object to normalize.

    :return: the normalized JSON-LD object.
    """
    return Processor().normalize(input)

def expand(input):
    """
    Removes the context from a JSON-LD object, expanding it to full-form.

    :param input: the JSON-LD object to remove the context from.

    :return: the context-neutral JSON-LD object.
    """
    return Processor().expand({}, None, input, False)

def compact(ctx, input):
    """
    Expands the given JSON-LD object and then compacts it using the
    given context.

    :param ctx: the new context to use.
    :param input: the input JSON-LD object.

    :return: the output JSON-LD object.
    """
    rval = None

    # TODO: should context simplification be optional? (ie: remove context
    # entries that are not used in the output)

    if input is not None:
        # fully expand input
        input = expand(input)

        if isinstance(input, list):
            rval = []
            tmp = input
        else:
            tmp = [input]

        for value in tmp:
            # setup output context
            ctxOut = {}

            # compact
            output = Processor().compact(copy.copy(ctx), None, value, ctxOut)

            # add context if used
            if len(ctxOut.keys()) > 0:
                output["@context"] = ctxOut

            if rval is None:
                rval = output
            else:
                rval.append(output)

    return rval

def mergeContexts(ctx1, ctx2):
    """
    Merges one context with another.

    :param ctx1: the context to overwrite/append to.
    :param ctx2: the new context to merge onto ctx1.

    :return: the merged context.
    """
    # copy contexts
    cMerged = copy.deepcopy(ctx1)
    cCopy = copy.deepcopy(ctx2)

    # if the new context contains any IRIs that are in the merged context,
    # remove them from the merged context, they will be overwritten
    for key in cCopy:
        # ignore special keys starting with '@'
        if key.find('@') != 0:
            for mkey in cMerged:
                if cMerged[mkey] == cCopy[key]:
                    del cMerged[mkey]
                    break

    # @coerce must be specially-merged, remove from context
    mergeCoerce = '@coerce' in cMerged
    copyCoerce = '@coerce' in cCopy
    if mergeCoerce or copyCoerce:
        if mergeCoerce:
            c1 = cMerged['@coerce']
            del cMerged['@coerce']
        else:
            c1 = {}

        if copyCoerce:
            c2 = cCopy['@coerce']
            del cCopy['@coerce']
        else:
            c2 = {}

    # merge contexts
    for key in cCopy:
        cMerged[key] = cCopy[key]

    # special-merge @coerce
    if mergeCoerce or copyCoerce:
        for cType in c1:
            # append existing-type properties that don't already exist
            if cType in c2:
                p1 = c1[cType]
                p2 = c2[cType]

                # normalize props in c2 to array for single-code-path iterating
                if not isinstance(p2, list):
                    p2 = [p2]

                # add unique properties from p2 to p1
                for p in p2:
                    if ((not isinstance(p1, list) and p1 != p) or
                        (isinstance(p1, list) and p not in p1)):
                        if isinstance(p1, list):
                            p1.append(p)
                        else:
                            p1 = c1[cType] = [p1, p]

        # add new types from new @coerce
        for cType in c2:
            if not (cType in c1):
                c1[cType] = c2[cType]

        # ensure there are no property duplicates in @coerce
        unique = {}
        dups = []
        for cType in c1:
            p = c1[cType]
            if isinstance(p, basestring):
                p = [p]
            for i in p:
                if not (i in unique):
                    unique[i] = True
                elif i not in dups:
                    dups.append(i)

        if len(dups) > 0:
            raise Exception(
                'Invalid type coercion specification. More than one type' +
                'specified for at least one property.', dups)

        cMerged['@coerce'] = c1

    return cMerged

##
# Expands a term into an absolute IRI. The term may be a regular term, a
# CURIE, a relative IRI, or an absolute IRI. In any case, the associated
# absolute IRI will be returned.
# 
# @param ctx the context to use.
# @param term the term to expand.
# 
# @return the expanded term as an absolute IRI.
expandTerm = _expandTerm

def compactIri(ctx, iri):
    """
    Compacts an IRI into a term or CURIE it can be. IRIs will not be
    compacted to relative IRIs if they match the given context's default
    vocabulary.

    :param ctx: the context to use.
    :param iri: the IRI to compact.

    :return: the compacted IRI as a term or CURIE or the original IRI.
    """
    return _compactIri(ctx, iri, None)

def frame(input, frame, options=None):
    """
    Frames JSON-LD input.

    :param input: the JSON-LD input.
    :param frame: the frame to use.
    :param options: framing options to use.

    :return: the framed output.
    """
    return Processor().frame(input, frame, options)
