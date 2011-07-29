##
# Python implementation of JSON-LD processor
# 
# This implementation is ported from the Javascript implementation of
# JSON-LD, authored by Dave Longley.
#
# @author Dave Longley 
# @author Mike Johnson
#
# Copyright (c) 2011 Digital Bazaar, Inc. All rights reserved.
import copy

# DEBUG:
import json

_s = '@subject'
_t = '@type'

ns = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#'
}

xsd = {
    'anyType': ns['xsd'] + 'anyType',
    'boolean': ns['xsd'] + 'boolean',
    'double': ns['xsd'] + 'double',
    'integer': ns['xsd'] + 'integer',
    'anyURI': ns['xsd'] + 'anyURI'
}

##
# Creates the JSON-LD default context.
#
# @return the JSON-LD default context.
def _createDefaultContext():
    return {
        'rdf': ns['rdf'],
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'dcterms': 'http://purl.org/dc/terms/',
        'foaf': 'http://xmlns.com/foaf/0.1/',
        'cal': 'http://www.w3.org/2002/12/cal/ical#',
        'vcard': 'http://www.w3.org/2006/vcard/ns#',
        'geo': 'http://www.w3.org/2003/01/geo/wgs84_pos#',
        'cc': 'http://creativecommons.org/ns#',
        'sioc': 'http://rdfs.org/sioc/ns#',
        'doap': 'http://usefulinc.com/ns/doap#',
        'com': 'http://purl.org/commerce#',
        'ps': 'http://purl.org/payswarm#',
        'gr': 'http://purl.org/goodrelations/v1#',
        'sig': 'http://purl.org/signature#',
        'ccard': 'http://purl.org/commerce/creditcard#',
        '@coerce':
        {
            'xsd:anyURI': ['foaf:homepage', 'foaf:member'],
            'xsd:integer': 'foaf:age'
        },
        '@vocab': ''
    }

##
# Compacts an IRI into a term or CURIE if it can be. IRIs will not be
# compacted to relative IRIs if they match the given context's default
# vocabulary.
# 
# @param ctx the context to use.
# @param iri the IRI to compact.
# @param usedCtx a context to update if a value was used from "ctx".
# 
# @return the compacted IRI as a term or CURIE or the original IRI.
def _compactIri(ctx, iri, usedCtx):
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
        rval = _t

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

##
# Expands a term into an absolute IRI. The term may be a regular term, a
# CURIE, a relative IRI, or an absolute IRI. In any case, the associated
# absolute IRI will be returned.
#
# @param ctx the context to use.
# @param term the term to expand.
# @param usedCtx a context to update if a value was used from "ctx".
#
# @return the expanded term as an absolute IRI.
def _expandTerm(ctx, term, usedCtx):
    rval = None

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
    elif term == _s:
        rval = _s
    # 4. The property is the special-case rdf type.
    elif term == _t:
        rval = ns['rdf'] + 'type'
    # 5. The property is a relative IRI, prepend the default vocab.
    else:
        rval = ctx['@vocab'] + term
        if usedCtx is not None:
            usedCtx['@vocab'] = ctx['@vocab']

    return rval

##
# Sets a subject's property to the given object value. If a value already
# exists, it will be appended to an array.
#
# @param s the subject.
# @param p the property.
# @param o the object.
def _setProperty(s, p, o):
    if p in s:
        if isinstance(s[p], list):
            s[p].append(o)
        else:
            s[p] = [s[p], o]
    else:
        s[p] = o

##
# Gets the coerce type for the given property.
#
# @param ctx the context to use.
# @param property the property to get the coerced type for.
# @param usedCtx a context to update if a value was used from "ctx".
#
# @return the coerce type, None for none.
def _getCoerceType(ctx, property, usedCtx):
    rval = None

    # get expanded property
    p = _expandTerm(ctx, property, None)

    # built-in type coercion JSON-LD-isms
    if p == _s or p == ns['rdf'] + 'type':
        rval = xsd['anyURI']

    # check type coercion for property
    else:
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
                                (isinstance(c, (str, unicode)) and c != p)):
                                _setProperty(usedCtx['@coerce'], type, p)
                    break

    return rval

##
# Recursively compacts a value. This method will compact IRIs to CURIEs or
# terms and do reverse type coercion to compact a value.
# 
# @param ctx the context to use.
# @param property the property that points to the value, NULL for none.
# @param value the value to compact.
# @param usedCtx a context to update if a value was used from "ctx".
# 
# @return the compacted value.
def _compact(ctx, property, value, usedCtx):
    rval = None

    if value is None:
        rval = None
    elif isinstance(value, list):
        # recursively add compacted values to array
        rval = []
        for i in value:
            rval.append(_compact(ctx, property, i, usedCtx))
    # graph literal/disjoint graph
    elif (isinstance(value, dict) and _s in value and
        isinstance(value[_s], list)):
        rval = {}
        rval[_s] = _compact(ctx, property, value[_s], usedCtx)
    # value has sub-properties if it doesn't define a literal or IRI value
    elif (isinstance(value, dict) and '@literal' not in value and
        '@iri' not in value):
        # recursively handle sub-properties that aren't a sub-context
        rval = {}
        for key in value:
            if value[key] != '@context':
                # set object to compacted property
                _setProperty(rval, _compactIri(ctx, key, usedCtx),
                    _compact(ctx, key, value[key], usedCtx))
    else:
        # get coerce type
        coerce = _getCoerceType(ctx, property, usedCtx)

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
                    type = xsd['anyURI']
                # can be coerced to any type
                else:
                    type = coerce
        # type can be coerced to anything
        elif isinstance(value, (str, unicode)):
            type = coerce

        # types that can be auto-coerced from a JSON-builtin
        if coerce is None and (type == xsd['boolean'] or
            type == xsd['integer'] or type == xsd['double']):
            coerce = type

        # do reverse type-coercion
        if coerce is not None:
            # type is only None if a language was specified, which is an error
            # if type coercion is specified
            if type is None:
                raise Exception('Cannot coerce type when a language is ' +
                    'specified. The language information would be lost.')
            # if the value type does not match the coerce type, it is an error
            elif type != coerce:
                raise Exception('Cannot coerce type because the datatype ' +
                    'does not match.')
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

        # no type-coercion, just copy value
        else:
            rval = copy.copy(value)

        # compact IRI
        if type == xsd['anyURI']:
            if isinstance(rval, dict):
                rval['@iri'] = _compactIri(ctx, rval['@iri'], usedCtx)
            else:
                rval = _compactIri(ctx, rval, usedCtx)

    return rval

##
# Recursively expands a value using the given context. Any context in
# the value will be removed.
# 
# @param ctx the context.
# @param property the property that points to the value, NULL for none.
# @param value the value to expand.
# @param expandSubjects True to expand subjects (normalize), False not to.
# 
# @return the expanded value.
def _expand(ctx, property, value, expandSubjects):
    rval = None

    # TODO: add data format error detection?

    # value is null, nothing to expand
    if value is None:
        rval = None
    # if no property is specified and the value is a string (this means the
    # value is a property itself), expand to an IRI
    elif property is None and isinstance(value, (str, unicode)):
        rval = _expandTerm(ctx, value, None)
    elif isinstance(value, list):
        # recursively add expanded values to array
        rval = []
        for i in value:
            rval.append(_expand(ctx, property, i, expandSubjects))
    elif isinstance(value, dict):
        # value has sub-properties if it doesn't define a literal or IRI value
        if not ('@literal' in value or '@iri' in value):
            # if value has a context, use it
            if '@context' in value:
                ctx = mergeContexts(ctx, value['@context'])

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
                        _expand(ctx, key, value[key], expandSubjects))
        # value is already expanded
        else:
            rval = copy.copy(value)
    else:
        # do type coercion
        coerce = _getCoerceType(ctx, property, None)

        # automatic coercion for basic JSON types
        if coerce is None and isinstance(value, (int, long, float, bool)):
            if isinstance(value, bool):
                coerce = xsd['boolean']
            elif isinstance(value, float):
                coerce = xsd['double']
            else:
                coerce = xsd['integer']

        # coerce to appropriate datatype, only expand subjects if requested
        if coerce is not None and (property != _s or expandSubjects):
            rval = {}

            # expand IRI
            if coerce == xsd['anyURI']:
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
# Checks if is blank node IRI.
def _isBlankNodeIri(v):
    return v.find('_:') == 0

##
# Checks if is named blank node.
def _isNamedBlankNode(v):
    # look for "_:" at the beginning of the subject
    return (isinstance(v, dict) and _s in v and
        '@iri' in v[_s] and _isBlankNodeIri(v[_s]['@iri']))

##
# Checks if is blank node.
def _isBlankNode(v):
    # look for no subject or named blank node
    return (isinstance(v, dict) and not ('@iri' in v or '@literal' in v) and
        (_s not in v or _isNamedBlankNode(v)))

##
# Compares two values.
# 
# @param v1 the first value.
# @param v2 the second value.
# 
# @return -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2.
def _compare(v1, v2):
    rval = 0

    if isinstance(v1, list) and isinstance(v2, list):
        for i in range(0, len(v1)):
            rval = _compare(v1[i], v2[i])
            if rval != 0:
                break
    else:
        rval = -1 if v1 < v2 else (1 if v1 > v2 else 0)

    return rval

##
# Compares two keys in an object. If the key exists in one object
# and not the other, that object is less. If the key exists in both objects,
# then the one with the lesser value is less.
# 
# @param o1 the first object.
# @param o2 the second object.
# @param key the key.
# 
# @return -1 if o1 < o2, 0 if o1 == o2, 1 if o1 > o2.
def _compareObjectKeys(o1, o2, key):
    rval = 0
    if key in o1:
        if key in o2:
            rval = _compare(o1[key], o2[key])
        else:
            rval = -1
    elif key in o2:
        rval = 1
    return rval

##
# Compares two object values.
# 
# @param o1 the first object.
# @param o2 the second object.
# 
# @return -1 if o1 < o2, 0 if o1 == o2, 1 if o1 > o2.
def _compareObjects(o1, o2):
    rval = 0

    if isinstance(o1, (str, unicode)):
        if isinstance(o2, (str, unicode)):
            rval = -1
        else:
            rval = _compare(o1, o2)
    elif isinstance(o2, (str, unicode)):
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

##
# Compares the object values between two bnodes.
# 
# @param a the first bnode.
# @param b the second bnode.
# 
# @return -1 if a < b, 0 if a == b, 1 if a > b.
def _compareBlankNodeObjects(a, b):
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
                return (isinstance(e, (str, unicode)) or
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

##
# Creates a blank node name generator using the given prefix for the
# blank nodes. 
# 
# @param prefix the prefix to use.
# 
# @return the blank node name generator.
class NameGenerator:
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

##
# Populates a map of all named subjects from the given input and an array
# of all unnamed bnodes (includes embedded ones).
# 
# @param input the input (must be expanded, no context).
# @param subjects the subjects map to populate.
# @param bnodes the bnodes array to populate.
def _collectSubjects(input, subjects, bnodes):
    if input is None:
        # nothing to collect
        pass
    elif isinstance(input, list):
        for i in input:
            _collectSubjects(i, subjects, bnodes)
    elif isinstance(input, dict):
        if _s in input:
            # graph literal
            if isinstance(input[_s], list):
                _collectSubjects(input[_s], subjects, bnodes)
            # named subject
            else:
                subjects[input[_s]['@iri']] = input
        # unnamed blank node
        elif _isBlankNode(input):
            bnodes.append(input)

        # recurse through subject properties
        for key in input:
            _collectSubjects(input[key], subjects, bnodes)

##
# Flattens the given value into a map of unique subjects. It is assumed that
# all blank nodes have been uniquely named before this call. Array values for
# properties will be sorted.
# 
# @param parent the value's parent, NULL for none.
# @param parentProperty the property relating the value to the parent.
# @param value the value to flatten.
# @param subjects the map of subjects to write to.
def _flatten(parent, parentProperty, value, subjects):
    flattened = None

    if isinstance(value, list):
        # list of objects or a disjoint graph
        for i in value:
            _flatten(parent, parentProperty, i, subjects)

    elif isinstance(value, dict):
        # graph literal/disjoint graph
        if _s in value and isinstance(value[_s], list):
            # cannot flatten embedded graph literals
            if parent is not None:
                raise Exception('Embedded graph literals cannot be flattened.')

            # top-level graph literal
            for key in value[_s]:
                _flatten(parent, parentProperty, key, subjects)
        # already-expanded value
        elif '@literal' in value or '@iri' in value:
            flattened = copy.copy(value)
        # subject
        else:
            # create or fetch existing subject
            subject = None
            if value[_s]['@iri'] in subjects:
                # FIXME: _s might be a graph literal (as {})
                subject = subjects[value[_s]['@iri']]
            else:
                subject = {}
                if _s in value:
                    # FIXME: _s might be a graph literal (as {})
                    subjects[value[_s]['@iri']] = subject
            flattened = subject

            # flatten embeds
            for key,v in value.items():
                # drop null values
                if v is not None:
                    if isinstance(v, list):
                        subject[key] = []
                        _flatten(subject[key], None, v, subjects)
                        if len(subject[key]) == 1:
                            # convert subject[key] to object if it has only 1
                            subject[key] = subject[key][0]
                    else:
                        _flatten(subject, key, v, subjects)
    # string value
    else:
        flattened = value

    # add flattened value to parent
    if flattened is not None and parent is not None:
        # remove top-level _s for subjects
        # 'http://mypredicate': {'@subject': {'@iri': 'http://mysubject'}}
        # becomes
        # 'http://mypredicate': {'@iri': 'http://mysubject'}
        if isinstance(flattened, dict) and _s in flattened:
            flattened = flattened[_s]

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

##
# A MappingBuilder is used to build a mapping of existing blank node names
# to a form for serialization. The serialization is used to compare blank
# nodes against one another to determine a sort order.
class MappingBuilder:
    ##
    # Initialize the MappingBuilder.
    def __init__(self):
        self.count = 1
        self.mapped = {}
        self.mapping = {}
        self.output = {}

    ##
    # Copies this MappingBuilder.
    #
    # @return the MappingBuilder copy.
    def copy(self):
        rval = MappingBuilder()
        rval.count = self.count
        rval.mapped = copy.copy(self.mapped)
        rval.mapping = copy.copy(self.mapping)
        rval.output = copy.copy(self.output)
        return rval

    ##
    # Maps the next name to the given bnode IRI if the bnode IRI isn't already
    # in the mapping. If the given bnode IRI is canonical, then it will be
    # given a shortened form of the same name.
    # 
    # @param iri the blank node IRI to map the next name to.
    #
    # @return the mapped name.
    def mapNode(self, iri):
        if iri not in self.mapping:
            if iri.startswith('_:c14n'):
                self.mapping[iri] = 'c%s' % iri[0:6]
            else:
                self.mapping[iri] = 's%s' % self.count
                self.count += 1
        return self.mapping[iri]

##
# A JSON-LD processor.
class Processor:
    ##
    # Initialize the JSON-LD processor.
    def __init__(self):
        self.tmp = None
        self.c14n = None

    ##
    # Normalizes a JSON-LD object.
    # 
    # @param input the JSON-LD object to normalize.
    # 
    # @return the normalized JSON-LD object.
    def normalize(self, input):
        rval = []

        # TODO: validate context

        if input is not None:
            # get default context
            ctx = _createDefaultContext()

            # expand input
            expanded = _expand(ctx, None, input, True)

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
                return _compare(a[_s]['@iri'], b[_s]['@iri'])

            # sort output
            rval.sort(cmp=normalizeSort)

        return rval

    ##
    # Assigns unique names to blank nodes that are unnamed in the given input.
    # 
    # @param input the input to assign names to.
    def nameBlankNodes(self, input):
        # create temporary blank node name generator
        ng = self.tmp = NameGenerator('tmp')

        # collect subjects and unnamed bnodes
        subjects = {}
        bnodes = []
        _collectSubjects(input, subjects, bnodes)

        # uniquely name all unnamed bnodes
        for bnode in bnodes:
            if not (_s in bnode):
                # generate names until one is unique
                while(ng.next() in subjects):
                    pass
                bnode[_s] = { '@iri': ng.current() }
                subjects[ng.current()] = bnode

    ##
    # Renames a blank node, changing its references, etc. The method assumes
    # that the given name is unique.
    # 
    # @param b the blank node to rename.
    # @param id the new name to use.
    def renameBlankNode(self, b, id):
        old = b[_s]['@iri']

        # update bnode IRI
        b[_s]['@iri'] = id

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

    ##
    # Canonically names blank nodes in the given input.
    # 
    # @param input the flat input graph to assign names to.
    def canonicalizeBlankNodes(self, input):
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
            iri = s[_s]['@iri']
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
            iri = bnode[_s]['@iri']
            if c14n.inNamespace(iri):
                while ngTmp.next() in subjects:
                    pass
                self.renameBlankNode(bnode, ngTmp.current())
                iri = bnode[_s]['@iri']
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
            iri = bnode[_s]['@iri']
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
                    iriB = b[_s]['@iri']
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

    ##
    # Marks a relation serialization as dirty if necessary.
    #
    # @param iri the IRI of the bnode to check.
    # @param changed the old IRI of the bnode that changed.
    # @param dir the direction to check ('props' or 'refs').
    def markSerializationDirty(self, iri, changed, dir):
        s = self.serializations[iri]
        if s[dir] is not None and changed in s[dir]['m']:
            s[dir] = None

    ##
    # Recursively creates a relation serialization (partial or full).
    # 
    # @param keys the keys to serialize in the current output.
    # @param output the current mapping builder output.
    # @param done the already serialized keys.
    # 
    # @return the relation serialization.
    def recursiveSerializeMapping(self, keys, output, done):
        rval = ''
        for k in keys:
            if k not in output:
                break
            if k in done:
                # mark cycle
                rval += '_' + k
            else:
                done[k] = True
                tmp = output[k]
                for s in tmp['k']:
                    rval += s
                    iri = tmp['m'][s]
                    if iri in self.subjects:
                        b = self.subjects[iri]

                        # serialize properties
                        rval += '<'
                        rval += _serializeProperties(b)
                        rval += '>'

                        # serialize references
                        rval += '<'
                        first = True
                        refs = self.edges['refs'][iri]['all']
                        for r in refs:
                            if first:
                                first = False
                            else:
                                rval += '|'
                            rval += '_:' if _isBlankNodeIri(r['s']) else r['s']
                        rval += '>'
                rval += self.recursiveSerializeMapping(tmp['k'], output, done)
        return rval

    ##
    # Creates a relation serialization (partial or full).
    # 
    # @param output the current mapping builder output.
    # 
    # @return the relation serialization.
    def serializeMapping(self, output):
        return self.recursiveSerializeMapping(['s1'], output, {})

    ##
    # Recursively serializes adjacent bnode combinations.
    # 
    # @param s the serialization to update.
    # @param top the top of the serialization.
    # @param mb the MappingBuilder to use.
    # @param dir the edge direction to use ('props' or 'refs').
    # @param mapped all of the already-mapped adjacent bnodes.
    # @param notMapped all of the not-yet mapped adjacent bnodes.
    def serializeCombos(self, s, top, mb, dir, mapped, notMapped):
        # copy mapped nodes
        mapped = copy.copy(mapped)

        # handle recursion
        if len(notMapped) > 0:
            # map first bnode in list
            mapped[mb.mapNode(notMapped[0]['s'])] = notMapped[0]['s']

            # recurse into remaining possible combinations
            original = mb.copy()
            notMapped = notMapped[1:]
            rotations = max(1, len(notMapped))
            for r in range(0, rotations):
                m = mb if r == 0 else original.copy()
                self.serializeCombos(s, top, m, dir, mapped, notMapped)

                # rotate not-mapped for next combination
                _rotate(notMapped)
        # handle final adjacent node in current combination
        else:
            keys = mapped.keys()
            keys.sort()
            mb.output[top] = { 'k': keys, 'm': mapped }

            # optimize away mappings that are already too large
            _s = self.serializeMapping(mb.output)
            if s[dir] is None or _compareSerializations(_s, s[dir]['s']) <= 0:
                oldCount = mb.count

                # recurse into adjacent alues
                for k in keys:
                    self.serializeBlankNode(s, mapped[k], mb, dir)

                # reserialize if more nodes were mapped
                if mb.count > oldCount:
                    _s = self.serializeMapping(mb.output)

                # update least serialization if new one has been found
                if (s[dir] is None or
                    (_compareSerializations(_s, s[dir]['s']) <= 0 and
                    len(_s) >= len(s[dir]['s']))):
                    s[dir] = { 's': _s, 'm': mb.mapping }

    ##
    # Computes the relation serialization for the given blank node IRI.
    # 
    # @param s the serialization to update.
    # @param iri the current bnode IRI to be mapped.
    # @param mb the MappingBuilder to use.
    # @param dir the edge direction to use ('props' or 'refs').
    def serializeBlankNode(self, s, iri, mb, dir):
        # only do mapping if iri not already mapped
        if iri not in mb.mapped:
            # iri now mapped
            mb.mapped[iri] = True
            top = mb.mapNode(iri)

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
                self.serializeCombos(s, top, mb, dir, mapped, notMapped)

    ##
    # Compares two blank nodes for equivalence.
    # 
    # @param a the first blank node.
    # @param b the second blank node.
    # 
    # @return -1 if a < b, 0 if a == b, 1 if a > b.
    def deepCompareBlankNodes(self, a, b):
        rval = 0

        # compare IRIs
        iriA = a[_s]['@iri']
        iriB = b[_s]['@iri']
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

    ##
    # Performs a shallow sort comparison on the given bnodes.
    # 
    # @param a the first bnode.
    # @param b the second bnode.
    # 
    # @return -1 if a < b, 0 if a == b, 1 if a > b.
    def shallowCompareBlankNodes(self, a, b):
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
            edgesA = self.edges['refs'][a[_s]['@iri']]['all']
            edgesB = self.edges['refs'][b[_s]['@iri']]['all']
            rval = _compare(len(edgesA), len(edgesB))

        # step #5
        if rval == 0:
            for i in range(0, len(edgesA)):
                rval = self.compareEdges(edgesA[i], edgesB[i])
                if rval != 0:
                    break

        return rval

    ##
    # Compares two edges. Edges with an IRI (vs. a bnode ID) come first, then
    # alphabetically-first IRIs, then alphabetically-first properties. If a
    # blank node has been canonically named, then blank nodes will be compared
    # after properties (with a preference for canonically named over
    # non-canonically named), otherwise they won't be.
    # 
    # @param a the first edge.
    # @param b the second edge.
    # 
    # @return -1 if a < b, 0 if a == b, 1 if a > b.
    def compareEdges(self, a, b):
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

    ##
    # Populates the given reference map with all of the subject edges in the
    # graph. The references will be categorized by the direction of the edges,
    # where 'props' is for properties and 'refs' is for references to a subject
    # as an object. The edge direction categories for each IRI will be sorted
    # into groups 'all' and 'bnodes'.
    def collectEdges(self):
        refs = self.edges['refs']
        props = self.edges['props']

        # collect all references and properties
        for iri in self.subjects:
            subject = self.subjects[iri]
            for key in subject:
                if key != _s:
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

    ##
    # Frames JSON-LD input.
    # 
    # @param input the JSON-LD input.
    # @param frame the frame to use.
    # @param options framing options to use.
    # 
    # @return the framed output.
    def frame(self, input, frame, options=None):
        rval = None

        # normalize input
        input = self.normalize(input)

        # save frame context
        ctx = None
        if '@context' in frame:
            ctx = mergeContexts(_createDefaultContext(), frame['@context'])

        # remove context from frame
        frame = removeContext(frame)

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
            subjects[i[_s]['@iri']] = i

        # frame input
        rval = _frame(subjects, input, frame, {}, options)

        # apply context
        if ctx is not None and rval is not None:
            rval = addContext(ctx, rval)

        return rval


##
# Returns True if the given source is a subject and has one of the given
# types in the given frame.
# 
# @param src the input.
# @param frame the frame with types to look for.
# 
# @return True if the src has one of the given types.
def _isType(src, frame):
    rval = False

    # check if type(s) are specified in frame and src
    rType = ns['rdf'] + 'type'
    if (rType in frame and isinstance(src, dict) and _s in src and
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

##
# Returns True if the given element is not a keyword.
#
# @param e the element.
#
# @return True if the given element is not a keyword.
def _filterNonKeywords(e):
    return e.find('@') != 0

##
# Returns True if the given src matches the given frame via duck-typing.
# 
# @param src the input.
# @param frame the frame to check against.
# 
# @return True if the src matches the frame.
def _isDuckType(src, frame):
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
        elif isinstance(src, dict) and _s in src:
            rval = True
            for i in props:
                if i not in src:
                    rval = False
                    break

    return rval

##
# Recursively frames the given input according to the given frame.
# 
# @param subjects a map of subjects in the graph.
# @param input the input to frame.
# @param frame the frame to use.
# @param embeds a map of previously embedded subjects, used to prevent cycles.
# @param options the framing options.
# 
# @return the framed input.
def _frame(subjects, input, frame, embeds, options):
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
                if isinstance(value, dict) and _s in value:
                    value = value[_s]
            elif (isinstance(value, dict) and _s in value and
                value[_s]['@iri'] in embeds):

                # TODO: possibly support multiple embeds in the future ... and
                # instead only prevent cycles?
                raise Exception(
                    'More than one embed of the same subject is not supported.',
                    value[_s]['@iri'])

            # if value is a subject, do embedding and subframing
            elif isinstance(value, dict) and _s in value:
                embeds[value[_s]['@iri']] = True

                # if explicit on, remove keys from value that aren't in frame
                explicitOn = (frame['@explicit'] if '@explicit' in frame
                    else options['defaults']['explicitOn'])
                if explicitOn:
                    for key in value.keys():
                        # do not remove subject or any key in the frame
                        if key != _s and key not in frame:
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
                                else options['defaults']['omitDefaultOn']);
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

##
# Rotates the elements in an array one position.
#
# @param a the array.
def _rotate(a):
    if len(a) > 0:
        a.append(a.pop(0))

##
# Serializes the properties of the given bnode for its relation serialization.
# 
# @param b the blank node.
# 
# @return the serialized properties.
def _serializeProperties(b):
    rval = ''
    for p in b.keys():
        if p != '@subject':
            first = True
            objs = b[p] if isinstance(b[p], list) else [b[p]]
            for o in objs:
                if first:
                    first = False
                else:
                    rval += '|'
                if (isinstance(o, dict) and '@iri' in o and
                    _isBlankNodeIri(o['@iri'])):
                    rval += '_:'
                else:
                    rval += json.dumps(o)
    return rval

##
# Compares two serializations for the same blank node. If the two
# serializations aren't complete enough to determine if they are equal (or if
# they are actually equal), 0 is returned.
# 
# @param s1 the first serialization.
# @param s2 the second serialization.
# 
# @return -1 if s1 < s2, 0 if s1 == s2 (or indeterminate), 1 if s1 > v2.
def _compareSerializations(s1, s2):
    rval = 0
    if len(s1) == len(s2):
        rval = _compare(s1, s2)
    elif len(s1) > len(s2):
        rval = _compare(s1[0:len(s2)], s2)
    else:
        rval = _compare(s1, s2[0:len(s1)])
    return rval

##
# Normalizes a JSON-LD object.
# 
# @param input the JSON-LD object to normalize.
# 
# @return the normalized JSON-LD object.
def normalize(input):
    return  Processor().normalize(input)

##
# Removes the context from a JSON-LD object.
# 
# @param input the JSON-LD object to remove the context from.
# 
# @return the context-neutral JSON-LD object.
def removeContext(input):
    rval = None

    if input is not None:
        ctx = _createDefaultContext()
        rval = _expand(ctx, None, input, False)

    return rval

##
# Expands the JSON-LD object.
#
# @param input the JSON-LD object to expand.
#
# @return the expanded JSON-LD object.
def expand(input):
    return removeContext(input)

##
# Adds the given context to the given context-neutral JSON-LD object.
# 
# @param ctx the new context to use.
# @param input the context-neutral JSON-LD object to add the context to.
# 
# @return the JSON-LD object with the new context.
def addContext(ctx, input):
    rval = None

    # TODO: should context simplification be optional? (ie: remove context
    # entries that are not used in the output)

    ctx = mergeContexts(_createDefaultContext(), ctx)

    # setup output context
    ctxOut = {}

    # compact
    rval = _compact(ctx, None, input, ctxOut)

    # add context if used
    if len(ctxOut.keys()) > 0:
        # add copy of context to every entry in output array
        if isinstance(rval, list):
            for i in rval:
                rval[i]['@context'] = copy.deepcopy(ctxOut)
        else:
            rval['@context'] = ctxOut

    return rval

##
# Changes the context of JSON-LD object "input" to "context", returning the
# output.
# 
# @param ctx the new context to use.
# @param input the input JSON-LD object.
# 
# @return the output JSON-LD object.
def changeContext(ctx, input):
    # remove context and then add new one
    return jsonld.addContext(ctx, jsonld.removeContext(input))

##
# Compacts the JSON-LD obejct.
#
# @param ctx the new context to use.
# @param input the input JSON-LD object.
#
# @return the output JSON-LD object.
def compact(ctx, input):
    return changeContext(ctx, input)

##
# Merges one context with another.
# 
# @param ctx1 the context to overwrite/append to.
# @param ctx2 the new context to merge onto ctx1.
# 
# @return the merged context.
def mergeContexts(ctx1, ctx2):
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
            if isinstance(p, (str, unicode)):
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

##
# Compacts an IRI into a term or CURIE it can be. IRIs will not be
# compacted to relative IRIs if they match the given context's default
# vocabulary.
# 
# @param ctx the context to use.
# @param iri the IRI to compact.
# 
# @return the compacted IRI as a term or CURIE or the original IRI.
def compactIri(ctx, iri):
    return _compactIri(ctx, iri, None)

##
# Frames JSON-LD input.
# 
# @param input the JSON-LD input.
# @param frame the frame to use.
# @param options framing options to use.
# 
# @return the framed output.
def frame(input, frame, options=None):
    return Processor().frame(input, frame, options)

##
# Creates the JSON-LD default context.
#
# @return the JSON-LD default context.
createDefaultContext = _createDefaultContext
