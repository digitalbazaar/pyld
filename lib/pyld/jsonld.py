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
        'a': ns['rdf'] + 'type',
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
        if not key.startswith('@'):
            # compact to a term
            if iri == ctx[key]:
                rval = key
                if usedCtx is not None:
                    usedCtx[key] = ctx[key]
                break

    # term not found, check the context for a CURIE prefix
    if rval is None:
        for key in ctx:
            # skip special context keys (start with '@')
            if not key.startswith('@'):
                # see if IRI begins with the next IRI from the context
                ctxIri = ctx[key]
                idx = iri.find(ctxIri)
                
                
                # compact to a CURIE
                if idx == 0 and len(iri) > len(ctxIri):
                    # create the compacted IRI
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
    
    # 3. The property is the special-case '@'.
    elif term == "@":
        rval = "@"
    
    # 4. The property is a relative IRI, prepend the default vocab.
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
        s[p] = o;

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
    if p == '@' or p == ns['rdf'] + 'type':
        rval = xsd['anyURI']
    # check type coercion for property
    else:
        # force compacted property
        p = _compactIri(ctx, p, None)
        
        for cType in ctx['@coerce']:
            # get coerced properties (normalize to an array)
            props = ctx['@coerce'][cType]
            if not isinstance(props, list):
                props = [props]
            
            # look for the property in the array
            for i in props:
                # property found
                if i == p:
                    rval = _expandTerm(ctx, cType, usedCtx)
                    if usedCtx is not None:
                        if not ('@coerce' in usedCtx):
                            usedCtx['@coerce'] = {}
                        
                        if not (cType in usedCtx['@coerce']):
                            usedCtx['@coerce'][cType] = p
                        else:
                            c = usedCtx['@coerce'][cType]
                            if ((isinstance(c, list) and c.find(p) == -1) or
                                (isinstance(c, (str, unicode)) and c != p)):
                                _setProperty(usedCtx['@coerce'], cType, p)
                    break
    
    return rval

##
# Recursively compacts a value. This method will compact IRIs to CURIEs or
# terms and do reverse type coercion to compact a value.
# 
# @param ctx the context to use.
# @param prop the property that points to the value, NULL for none.
# @param value the value to compact.
# @param usedCtx a context to update if a value was used from "ctx".
# 
# @return the compacted value.
def _compact(ctx, prop, value, usedCtx):
    rval = None
    
    if value is None:
        rval = None
    elif isinstance(value, list):
        # recursively add compacted values to array
        rval = []
        for i in value:
            rval.append(_compact(ctx, prop, i, usedCtx))
    # graph literal/disjoint graph
    elif (isinstance(value, dict) and '@' in value and
        isinstance(value['@'], list)):
        rval = {}
        rval['@'] = _compact(ctx, prop, value['@'], usedCtx)
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
        cType = _getCoerceType(ctx, prop, usedCtx)

        # get type from value, to ensure coercion is valid
        vType = None
        if isinstance(value, dict):
            # type coercion can only occur if language is not specified
            if not ('@language' in value):
                # datatype must match coerce type if specified
                if '@datatype' in value:
                    vType = value['@datatype']
                # datatype is IRI
                elif '@iri' in value:
                    vType = xsd['anyURI']
                # can be coerced to any type
                else:
                    vType = cType
        # value type can be coerced to anything
        elif isinstance(value, (str, unicode)):
            vType = cType

        # types that can be auto-coerced from a JSON-builtin
        if cType is None and (vType == xsd['boolean'] or
            vType == xsd['integer'] or vType == xsd['double']):
            cType = vType

        # do reverse type-coercion
        if cType is not None:
            # type is only None if a language was specified, which is an error
            # if type coercion is specified
            if vType is None:
                raise Exception('Cannot coerce type when a language is specified. The language information would be lost.')
            # if the value type does not match the coerce type, it is an error
            elif vType != cType:
                raise Exception('Cannot coerce type because the datatype does not match.')
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
                if cType == xsd['boolean']:
                    rval = (rval == 'true' or rval != 0)
                elif cType == xsd['double']:
                    rval = float(rval)
                elif cType == xsd['integer']:
                    rval = int(rval)
                    
        # no type-coercion, just copy value
        else:
            rval = copy.copy(value)

        # compact IRI
        if vType == xsd['anyURI']:
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
# @param prop the property that points to the value, NULL for none.
# @param value the value to expand.
# @param expandSubjects True to expand subjects (normalize), False not to.
# 
# @return the expanded value.
def _expand(ctx, prop, value, expandSubjects):
    rval = None
    
    # TODO: add data format error detection?
    
    # if no property is specified and the value is a string (this means the
    # value is a property itself), expand to an IRI
    if prop is None and isinstance(value, (str, unicode)):
        #print '  none'
        rval = _expandTerm(ctx, value, None)
    elif isinstance(value, list):
        # recursively add expanded values to array
        rval = []
        for i in value:
            rval.append(_expand(ctx, prop, i, expandSubjects))
    elif isinstance(value, dict):
        # value has sub-properties if it doesn't define a literal or IRI value
        if not ('@literal' in value or '@iri' in value):
            # if value has a context, use it
            if '@context' in value:
                ctx = mergeContexts(ctx, value['@context'])

            # recursively handle sub-properties that aren't a sub-context
            rval = {}
            for key in value:
                if len(key) == 1 or key.find('@') != 0:
                    # set object to expanded property
                    _setProperty(rval, _expandTerm(ctx, key, None),
                        _expand(ctx, key, value[key], expandSubjects))
                elif key != '@context':
                    # preserve non-context json-ld keywords
                    _setProperty(rval, key, copy.copy(value[key]))
        # value is already expanded
        else:
            rval = copy.copy(value)
    else:
        # do type coercion
        coerce = _getCoerceType(ctx, prop, None)
        
        # automatic coercion for basic JSON types
        if coerce is None and isinstance(value, (int, long, float, bool)):
            if isinstance(value, bool):
                coerce = xsd['boolean']
            elif isinstance(value, float):
                coerce = xsd['double']
            else:
                coerce = xsd['integer']

        # coerce to appropriate datatype, only expand subjects if requested
        if coerce is not None and (prop != '@' or expandSubjects):
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
    
    #print '-- _expand done --'
    return rval

##
# Checks if is blank node IRI.
def _isBlankNodeIri(v):
    return v.find('_:') == 0

##
# Checks if is named blank node.
def _isNamedBlankNode(v):
    # look for "_:" at the beginning of the subject
    return (isinstance(v, dict) and '@' in v and
        '@iri' in v['@'] and _isBlankNodeIri(v['@']['@iri']))

##
# Checks if is blank node.
def _isBlankNode(v):
    # look for no subject or named blank node
    return (isinstance(v, dict) and not ('@iri' in v or '@literal' in v) and
        ('@' not in v or _isNamedBlankNode(v)))

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

    # 3. For each property, compare sorted object values.
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
# @param src the input (must be expanded, no context).
# @param subjects the subjects map to populate.
# @param bnodes the bnodes array to populate.
def _collectSubjects(src, subjects, bnodes):
    if isinstance(src, list):
        for i in src:
            _collectSubjects(i, subjects, bnodes)
    elif isinstance(src, dict):
        if '@' in src:
            # graph literal
            if isinstance(src['@'], list):
                _collectSubjects(src['@'], subjects, bnodes)
            # named subject
            else:
                subjects[src['@']['@iri']] = src
        # unnamed blank node
        elif _isBlankNode(src):
            bnodes.append(src)
        
        # recurse through subject properties
        for key in src:
            _collectSubjects(src[key], subjects, bnodes)

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
        
        # if value is a list of objects, sort them
        if (len(value) > 0 and
            (isinstance(value[0], (str, unicode)) or
            (isinstance(value[0], dict) and
            ('@literal' in value[0] or '@iri' in value[0])))):
            # sort values
            value.sort(_compareObjects)

    elif isinstance(value, dict):
        # graph literal/disjoint graph
        if '@' in value and isinstance(value['@'], list):
            # cannot flatten embedded graph literals
            if parent is not None:
                raise('Embedded graph literals cannot be flattened.')
            
            # top-level graph literal
            for key in value['@']:
                _flatten(parent, parentProperty, key, subjects)
        # already-expanded value
        elif '@literal' in value or '@iri' in value:
            flattened = copy.copy(value)
        # subject
        else:
            # create or fetch existing subject
            subject = None
            if value['@']['@iri'] in subjects:
                # FIXME: '@' might be a graph literal (as {})
                subject = subjects[value['@']['@iri']]
            else:
                subject = {}
                if '@' in value:
                    # FIXME: '@' might be a graph literal (as {})
                    subjects[value['@']['@iri']] = subject
            flattened = subject

            # flatten embeds
            for key in value:
                if isinstance(value[key], list):
                    subject[key] = []
                    _flatten(subject[key], None, value[key], subjects)
                    if len(subject[key]) == 1:
                        # convert subject[key] to object if only 1 value was added
                        subject[key] = subject[key][0]
                else:
                    _flatten(subject, key, value[key], subjects)
    # string value
    else:
        flattened = value

    # add flattened value to parent
    if flattened is not None and parent is not None:
        # remove top-level '@' for subjects
        # 'http://mypredicate': {'@': {'@iri': 'http://mysubject'}} becomes
        # 'http://mypredicate': {'@iri': 'http://mysubject'}
        if isinstance(flattened, dict) and '@' in flattened:
            flattened = flattened['@']

        if isinstance(parent, list):
            # do not add duplicate IRIs for the same property
            duplicate = False
            if isinstance(flattened, dict) and '@iri' in flattened:
                def parentFilter(e):
                    return (isinstance(e, dict) and '@iri' in e and e['@iri'] == flattened['@iri'])
                
                duplicate = len(filter(parentFilter, parent)) > 0
            if not duplicate:
                parent.append(flattened)
        else:
            parent[parentProperty] = flattened

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
    if (rType in frame and isinstance(src, dict) and
        '@' in src and rType in src):
        tmp = src[rType] if isinstance(src[rType], list) else [src[rType]]
        types = frame[rType] if isinstance(frame[rType], list) else [frame[rType]]
        
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
        if len(props) == 0:
            # src always matches if there are no properties
            rval = True
        # src must be a subject with all the given properties
        elif isinstance(src, dict) and '@' in src:
            rval = True
            for i in props:
                if i not in src:
                    rval = False
                    break
    
    return rval


##
# A JSON-LD processor.
class Processor:

    ##
    # Initialize the JSON-LD processor.
    def __init__(self):
        self.memo = {}

    ##
    # Normalizes a JSON-LD object.
    # 
    # @param src the JSON-LD object to normalize.
    # 
    # @return the normalized JSON-LD object.
    def normalize(self, src):
        rval = []

        # TODO: validate context

        if src is not None:
            # get default context
            ctx = _createDefaultContext()
            
            # expand src
            expanded = _expand(ctx, None, src, True)
            
            # assign names to unnamed bnodes
            self.nameBlankNodes(expanded)
            
            # flatten
            subjects = {}
            _flatten(None, None, expanded, subjects)

            # append subjects to array
            for key in subjects:
                rval.append(subjects[key])

            # canonicalize blank nodes
            self.canonicalizeBlankNodes(rval)
            
            def normalizeSort(a, b):
                return _compare(a['@']['@iri'], b['@']['@iri'])

            # sort output
            rval.sort(cmp=normalizeSort)
        
        return rval

    ##
    # Assigns unique names to blank nodes that are unnamed in the given input.
    # 
    # @param src the input to assign names to.
    def nameBlankNodes(self, src):
        # create temporary blank node name generator
        ng = self.ng = NameGenerator('tmp')
        
        # collect subjects and unnamed bnodes
        subjects = {}
        bnodes = []
        _collectSubjects(src, subjects, bnodes)
        
        # uniquely name all unnamed bnodes
        for bnode in bnodes:
            if not ('@' in bnode):
                # generate names until one is unique
                while(ng.next() in subjects):
                    pass
                bnode['@'] = { '@iri': ng.current() }
                subjects[ng.current()] = bnode

    ##
    # Renames a blank node, changing its references, etc. The method assumes
    # that the given name is unique.
    # 
    # @param b the blank node to rename.
    # @param name the new name to use.
    def renameBlankNode(self, b, name):
        old = b['@']['@iri']
        
        # update bnode IRI
        b['@']['@iri'] = name
        
        # update subjects map
        subjects = self.subjects
        subjects[name] = subjects[old]
        del subjects[old]
        
        # update reference and property lists
        self.edges['refs'][name] = self.edges['refs'][old]
        self.edges['props'][name] = self.edges['props'][old]
        del self.edges['refs'][old]
        del self.edges['props'][old]
        
        # update references to this bnode
        refs = self.edges['refs'][name]['allnodes']
        for i in refs:
            iri = i['s']
            if iri == old:
                iri = name
            ref = subjects[iri]
            props = self.edges['props'][iri]['allnodes']
            for i2 in props:
                if i2['s'] == old:
                    i2['s'] = name
                    
                    # normalize property to array for single code-path
                    p = i2['p']
                    tmp = ([ref[p]] if isinstance(ref[p], dict) else
                        (ref[p] if isinstance(ref[p], list) else []))
                    for n in tmp:
                        if (isinstance(n, dict) and '@iri' in n and
                            n['@iri'] == old):
                            n['@iri'] = name
        
        # update references from this bnode
        props = self.edges['props'][name]['allnodes']
        for i in props:
            iri = i['s']
            refs = self.edges['refs'][iri]['allnodes']
            for r in refs:
                if r['s'] == old:
                    r['s'] = name

    ##
    # Deeply names the given blank node by first naming it if it doesn't already
    # have an appropriate prefix, and then by naming its properties and then
    # references.
    # 
    # @param b the bnode to name.
    def deepNameBlankNode(self, b):
        # rename bnode (if not already renamed)
        iri = b['@']['@iri']
        ng = self.ng
        if not ng.inNamespace(iri):
            self.renameBlankNode(b, ng.next())
            iri = ng.current()
            
            subjects = self.subjects
            
            # FIXME: can bnode edge sorting be optimized out due to sorting them
            # when they are unequal in other parts of this algorithm?
            
            def compareEdges(a, b):
                return self.compareEdges(a, b)
            
            # rename bnode properties
            props = self.edges['props'][iri]['bnodes']
            props.sort(cmp=compareEdges)
            for i in props:
                if i['s'] in subjects:
                    self.deepNameBlankNode(subjects[i['s']])
            
            # rename bnode references
            refs = self.edges['refs'][iri]['bnodes']
            refs.sort(cmp=compareEdges)
            for i in refs:
                if i['s'] in subjects:
                    self.deepNameBlankNode(subjects[i['s']])

    ##
    # Canonically names blank nodes in the given source.
    # 
    # @param src the flat input graph to assign names to.
    def canonicalizeBlankNodes(self, src):
        # collect subjects and bnodes from flat input graph
        memo = self.memo = {}
        edges = self.edges = {
            'refs': {},
            'props': {}
        }
        subjects = self.subjects = {}
        bnodes = []
        for s in src:
            iri = s['@']['@iri']
            subjects[iri] = s
            edges['refs'][iri] = {
                'allnodes': [],
                'bnodes': []
            }
            edges['props'][iri] = {
                'allnodes': [],
                'bnodes': []
            }
            if _isBlankNodeIri(iri):
                bnodes.append(s)
        
        # build map of memoized bnode comparisons
        for bn in bnodes:
            iri1 = bn['@']['@iri']
            memo[iri1] = {}
        
        # collect edges in the graph
        self.collectEdges()
        
        def bnodeSort(a, b):
            return self.deepCompareBlankNodes(a, b, {})
        
        # sort blank nodes
        bnodes.sort(cmp=bnodeSort)
        
        # create canonical blank node name generator
        c14n = NameGenerator('c14n')
        
        # rename all bnodes that have canonical names to temporary names
        tmp = self.ng
        for bnode in bnodes:
            if c14n.inNamespace(bnode['@']['@iri']):
                # generate names until one is unique
                while(tmp.next() in subjects):
                    pass
                self.renameBlankNode(bnode, tmp.current())
        
        # change internal name generator from tmp one to canonical one
        self.ng = c14n
        
        # deeply-iterate over bnodes canonically-naming them
        for bnode in bnodes:
            self.deepNameBlankNode(bnode)
        
        # sort property lists that now have canonically-named bnodes
        for key in edges['props']:
            if len(edges['props'][key]['bnodes']) > 0:
                bnode = subjects[key]
                for p in bnode:
                    if p.find('@') != 0 and isinstance(bnode[p], list):
                        bnode[p].sort(_compareObjects)

    ##
    # Compares the edges between two nodes for equivalence.
    # 
    # @param a the first bnode.
    # @param b the second bnode.
    # @param dir the edge direction ('props' or 'refs').
    # @param iso the current subgraph isomorphism for connected bnodes.
    # 
    # @return -1 if a < b, 0 if a == b, 1 if a > b.
    def deepCompareEdges(self, a, b, dir, iso):
        rval = 0
        
        # Edge comparison algorithm:
        # 1.   Compare adjacent bnode lists for matches.
        # 1.1. If a bnode ID is in the potential isomorphism, then its associated
        #      bnode *must* be in the other bnode under the same property.
        # 1.2. If a bnode ID is not in the potential isomorphism yet, then the
        #      associated bnode *must* have a bnode with the same property from the
        #      same bnode group that isn't in the isomorphism yet to match up.
        #      Iterate over each bnode in the group until an equivalent one is found.
        # 1.3. Recurse to compare the chosen bnodes.
        # 1.4. The bnode with lowest group index amongst bnodes with the same
        #      property name is first.

        # for every bnode edge in A, make sure there's a match in B
        iriA = a['@']['@iri']
        iriB = b['@']['@iri']
        edgesA = self.edges[dir][iriA]['bnodes']
        edgesB = self.edges[dir][iriB]['bnodes']
        for i1 in range(0, len(edgesA)):
            found = False
            edgeA = edgesA[i1]
            
            # step #1.1
            if edgeA['s'] in iso:
                match = iso[edgeA['s']]
                for edgeB in edgesB:
                    if edgeB['p'] > edgeA['p']:
                        break
                    if edgeB['p'] == edgeA['p']:
                        found = (edgeB['s'] == match)
                        break
            # step #1.2
            else:
                for edgeB in edgesB:
                    if edgeB['p'] > edgeA['p']:
                        break
                    if edgeB['p'] == edgeA['p'] and not (edgeB['s'] in iso):
                        # add bnode pair temporarily to iso
                        iso[edgeA['s']] = edgeB['s']
                        iso[edgeB['s']] = edgeA['s']
                        
                        # step #1.3
                        sA = self.subjects[edgeA['s']]
                        sB = self.subjects[edgeB['s']]
                        if self.deepCompareBlankNodes(sA, sB, iso) == 0:
                            found = True
                            break
                        
                        # remove non-matching bnode pair from iso
                        del iso[edgeA['s']]
                        del iso[edgeB['s']]
            # step #1.4
            if not found:
                # no matching bnode pair found, sort order is the bnode with the
                # least bnode for edgeA's property
                rval = self.compareEdgeType(a, b, edgeA['p'], dir, iso)
            
            if rval != 0:
                break
        
        return rval

    ##
    # Compares bnodes along the same edge type to determine which is less.
    # 
    # @param a the first bnode.
    # @param b the second bnode.
    # @param p the property.
    # @param d the direction of the edge ('props' or 'refs').
    # @param iso the current subgraph isomorphism for connected bnodes.
    # 
    # @return -1 if a < b, 0 if a == b, 1 if a > b.
    def compareEdgeType(self, a, b, p, d, iso):
        rval = 0
        
        # compare adjacent bnodes for smallest
        adjA = self.getSortedAdjacents(a, p, d, iso)
        adjB = self.getSortedAdjacents(a, p, d, iso)
        for i in range(0, len(adjA)):
            rval = self.deepCompareBlankNodes(adjA[i], adjB[i], iso)
            if rval != 0:
                break
        
        return rval

    ##
    # Returns the bnode properties for a particular bnode in sorted order.
    # 
    # @param b the bnode.
    # @param p the property (edge type).
    # @param d the direction of the edge ('props' or 'refs').
    # @param iso the current subgraph isomorphism for connected bnodes.
    # 
    # @return the sorted bnodes for the property.
    def getSortedAdjacents(self, b, p, d, iso):
        #print ''
        #print '-- Get Sorted Adjacents --'
        rval = []
        
        # add all bnodes for the given property
        iri = b['@']['@iri']
        edges = self.edges[d][iri]['bnodes']
        for edge in edges:
            if edge['p'] > p:
                break
            if edge['p'] == p:
                rval.append(self.subjects[edge['s']])
        
        def bnodeSort(a, b):
            #print '- bnodeSort -'
            #print 'a: ',a
            #print 'b: ', b
            #print 'iso: ', iso
            return self.deepCompareBlankNodes(a, b, iso)
        
        # sort bnodes
        rval.sort(cmp=bnodeSort)
        #print 'rval: ', rval
        return rval

    ##
    # Compares two blank nodes for equivalence.
    # 
    # @param a the first blank node.
    # @param b the second blank node.
    # @param iso the current subgraph isomorphism for connected bnodes.
    # 
    # @return -1 if a < b, 0 if a == b, 1 if a > b.
    def deepCompareBlankNodes(self, a, b, iso):
        rval = 0
        
        # compare IRIs
        iriA = a['@']['@iri']
        iriB = b['@']['@iri']
        if iriA == iriB:
            rval = 0
        # use memoized comparison if available
        elif iriB in self.memo[iriA]:
            rval = self.memo[iriA][iriB]
        else:
            # do shallow compare first
            rval = self.shallowCompareBlankNodes(a, b)
            if rval != 0:
                # compare done
                self.memo[iriA][iriB] = rval
                self.memo[iriB][iriA] = -rval
            # deep comparison is necessary
            else:
                # compare properties
                rval = self.deepCompareEdges(a, b, 'props', iso)
                
                # compare references
                if rval == 0:
                    rval = self.deepCompareEdges(a, b, 'refs', iso)
                
                # update memo
                if not (iriB in self.memo[iriA]):
                    self.memo[iriA][iriB] = rval
                    self.memo[iriB][iriA] = -rval
        
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
        # 5.3. The bnode with the alphabetically-first reference property is first.
        
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
            edgesA = self.edges['refs'][a['@']['@iri']]['allnodes']
            edgesB = self.edges['refs'][b['@']['@iri']]['allnodes']
            rval = _compare(len(edgesA), len(edgesB))
        
        # step #5
        if rval == 0:
            # FIXME: for loop
            for i in range(0, len(edgesA)):
                rval = self.compareEdges(edgesA[i], edgesB[i])
                if rval != 0:
                    break
        
        return rval

    ##
    # Compares two edges. Edges with an IRI (vs. a bnode ID) come first, then
    # alphabetically-first IRIs, then alphabetically-first properties. If a blank
    # node appears in the blank node equality memo then they will be compared
    # after properties, otherwise they won't be.
    # 
    # @param a the first edge.
    # @param b the second edge.
    # 
    # @return -1 if a < b, 0 if a == b, 1 if a > b.
    def compareEdges(self, a, b):
        rval = 0
        
        bnodeA = _isBlankNodeIri(a['s'])
        bnodeB = _isBlankNodeIri(b['s'])
        memo = self.memo
        
        # if not both bnodes, one that is a bnode is greater
        if bnodeA != bnodeB:
            rval = 1 if bnodeA else -1
        else:
            if not bnodeA:
                rval = _compare(a['s'], b['s'])
            if rval == 0:
                rval = _compare(a['p'], b['p'])
            if rval == 0 and bnodeA and a['s'] in memo and b['s'] in memo[a['s']]:
                rval = memo[a['s']][b['s']]
        
        return rval

    ##
    # Populates the given reference map with all of the subject edges in the
    # graph. The references will be categorized by the direction of the edges,
    # where 'props' is for properties and 'refs' is for references to a subject as
    # an object. The edge direction categories for each IRI will be sorted into
    # groups 'all' and 'bnodes'.
    def collectEdges(self):
        refs = self.edges['refs']
        props = self.edges['props']
        
        # collect all references and properties
        for iri in self.subjects:
            subject = self.subjects[iri]
            for key in subject:
                if key != '@':
                    # normalize to array for single codepath
                    obj = subject[key]
                    tmp = [obj] if not isinstance(obj, list) else obj
                    for o in tmp:
                        if (isinstance(o, dict) and
                            '@iri' in o and
                            o['@iri'] in self.subjects):
                            objIri = o['@iri']
                            
                            # map object to this subject
                            refs[objIri]['allnodes'].append({ 's': iri, 'p': key })
                            
                            # map this subject to object
                            props[iri]['allnodes'].append({ 's': objIri, 'p': key })
        
        def filterNodes(edge):
            return _isBlankNodeIri(edge['s'])
        
        # create sorted categories
        for iri in refs:
            refs[iri]['allnodes'].sort(cmp=self.compareEdges)
            refs[iri]['bnodes'] = filter(filterNodes, refs[iri]['allnodes'])
        for iri in props:
            props[iri]['allnodes'].sort(cmp=self.compareEdges)
            props[iri]['bnodes'] = filter(filterNodes, props[iri]['allnodes'])

    ##
    # Recursively frames the given src according to the given frame.
    # 
    # @param subjects a map of subjects in the graph.
    # @param src the input to frame.
    # @param frame the frame to use.
    # @param embeds a map of previously embedded subjects, used to prevent cycles.
    # @param options the framing options.
    # 
    # @return the framed src.
    def _frame(self, subjects, src, frame, embeds, options):
        rval = None
        
        # prepare output, set limit, get array of frames
        limit = -1
        frames = None
        if isinstance(frame, list):
            rval = []
            frames = frame
        else:
            frames = [frame]
            limit = 1
        
        # iterate over frames adding src matches to list
        values = []
        for i in range(0, len(frames)):
            # get next frame
            frame = frames[i]
            if not isinstance(frame, (list, dict)):
                raise Exception('Invalid JSON-LD frame. Frame type is not a map or array.')
            
            # create array of values for each frame
            values.append([])
            for n in src:
                # add src to list if it matches frame specific type or duck-type
                if _isType(n, frame) or _isDuckType(n, frame):
                    values[i].append(n)
                    limit -= 1
                if limit == 0:
                    break
            if limit == 0:
                break
        
        # FIXME: refactor to use python zip()
        # for each matching value, add it to the output
        for i1 in range(0, len(values)):
            for i2 in range(0, len(values[i1])):
                frame = frames[i1]
                value = values[i1][i2]
                
                # determine if value should be embedded or referenced
                embedOn = frame['@embed'] if '@embed' in frame else options['defaults']['embedOn']
                
                if not embedOn:
                    # if value is a subject, only use subject IRI as reference 
                    if isinstance(value, dict) and '@' in value:
                        value = value['@']
                elif (isinstance(value, dict) and '@' in value and
                    value['@']['@iri'] in embeds):

                    # TODO: possibly support multiple embeds in the future ... and
                    # instead only prevent cycles?
                    raise Exception(
                        'Multiple embeds of the same subject is not supported.',
                        value['@']['@iri'])

                # if value is a subject, do embedding and subframing
                elif isinstance(value, dict) and '@' in value:
                    embeds[value['@']['@iri']] = True
                    
                    # if explicit is on, remove keys from value that aren't in frame
                    explicitOn = frame['@explicit'] if '@explicit' in frame else options['defaults']['explicitOn']
                    if explicitOn:
                        # python - iterate over copy of list to remove key
                        for key in list(value):
                            # always include subject
                            if key != '@' and key not in frame:
                                del value[key]
                    
                    # iterate over frame keys to do subframing
                    for key in frame:
                        # skip keywords and type query
                        if key.find('@') != 0 and key != ns['rdf'] + 'type':
                            if key in value:
                                # build src and do recursion
                                src = value[key] if isinstance(value[key], list) else [value[key]]
                                for n in range(0, len(src)):
                                    # replace reference to subject w/subject
                                    if (isinstance(src[n], dict) and
                                        '@iri' in src[n] and
                                        src[n]['@iri'] in subjects):
                                        src[n] = subjects[src[n]['@iri']]
                                value[key] = self._frame(
                                    subjects, src, frame[key], embeds, options)
                            else:
                                # add None property to value
                                value[key] = None
                
                # add value to output
                if rval is None:
                    rval = value
                else:
                    rval.append(value)
        
        return rval

    ##
    # Frames JSON-LD src.
    # 
    # @param src the JSON-LD input.
    # @param frame the frame to use.
    # @param options framing options to use.
    # 
    # @return the framed output.
    def frame(self, src, frame, options=None):
        rval = None
        
        # normalize src
        src = self.normalize(src)
        
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
                'explicitOn': False
            }
        }
        
        # build map of all subjects
        subjects = {}
        for i in src:
            subjects[i['@']['@iri']] = i
        
        # frame src
        rval = self._frame(subjects, src, frame, {}, options)
        
        # apply context
        if ctx is not None and rval is not None:
            rval = addContext(ctx, rval)
        
        return rval


##
# Normalizes a JSON-LD object.
# 
# @param src the JSON-LD object to normalize.
# 
# @return the normalized JSON-LD object.
def normalize(src):
    return  Processor().normalize(src)

##
# Removes the context from a JSON-LD object.
# 
# @param src the JSON-LD object to remove the context from.
# 
# @return the context-neutral JSON-LD object.
def removeContext(src):
    rval = None

    if src is not None:
        ctx = _createDefaultContext()
        rval = _expand(ctx, None, src, False)

    return rval

##
# Adds the given context to the given context-neutral JSON-LD object.
# 
# @param ctx the new context to use.
# @param src the context-neutral JSON-LD object to add the context to.
# 
# @return the JSON-LD object with the new context.
def addContext(ctx, src):
    rval = None

    # TODO: should context simplification be optional? (ie: remove context
    # entries that are not used in the output)

    ctx = mergeContexts(_createDefaultContext(), ctx)

    # setup output context
    ctxOut = {}
    
    # compact
    rval = _compact(ctx, None, src, ctxOut)

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
# Changes the context of JSON-LD object "src" to "context", returning the
# output.
# 
# @param ctx the new context to use.
# @param src the input JSON-LD object.
# 
# @return the output JSON-LD object.
def changeContext(ctx, src):
    # remove context and then add new one
    return jsonld.addContext(ctx, jsonld.removeContext(src))

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
    
    if mergeCoerce or copyCoerce:
        # special-merge @coerce
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
# @param src the JSON-LD input.
# @param frame the frame to use.
# @param options framing options to use.
# 
# @return the framed output.
def frame(src, frame, options=None):
    return Processor().frame(src, frame, options)
