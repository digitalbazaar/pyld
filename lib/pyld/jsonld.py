"""
Python implementation of JSON-LD processor

This implementation is ported from the Javascript implementation of
JSON-LD.

.. module:: jsonld
  :synopsis: Python implementation of JSON-LD

.. moduleauthor:: Dave Longley 
.. moduleauthor:: Mike Johnson
.. moduleauthor:: Tim McNamara <tim.mcnamara@okfn.org>
"""

__copyright__ = 'Copyright (c) 2011-2012 Digital Bazaar, Inc.'
__license__ = 'New BSD license'

__all__ = ['compact', 'expand', 'frame', 'normalize', 'toRDF',
    'JsonLdProcessor']

import copy, hashlib
from functools import cmp_to_key
from numbers import Integral, Real

# XSD constants
XSD_BOOLEAN = 'http://www.w3.org/2001/XMLSchema#boolean'
XSD_DOUBLE = 'http://www.w3.org/2001/XMLSchema#double'
XSD_INTEGER = 'http://www.w3.org/2001/XMLSchema#integer'

# RDF constants
RDF_FIRST = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#first'
RDF_REST = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#rest'
RDF_NIL = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#nil'
RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'

# JSON-LD keywords
KEYWORDS = [
    '@context',
    '@container',
    '@default',
    '@embed',
    '@explicit',
    '@graph',
    '@id',
    '@language',
    '@list',
    '@omitDefault',
    '@preserve',
    '@set',
    '@type',
    '@value']


def compact(input, ctx, options=None):
    """
    Performs JSON-LD compaction.

    :param input: input the JSON-LD input to compact.
    :param ctx: the JSON-LD context to compact with.
    :param [options]: the options to use.
      [base] the base IRI to use.
      [strict] use strict mode (default: True).
      [optimize] True to optimize the compaction (default: False).
      [graph] True to always output a top-level graph (default: False).

    :return: the compacted JSON-LD output.
    """
    return JsonLdProcessor().compact(input, ctx, options)


def expand(input, options=None):
    """
    Performs JSON-LD expansion.

    :param input: the JSON-LD object to expand.
    :param [options]: the options to use.
      [base] the base IRI to use.

    :return: the expanded JSON-LD output.
    """
    return JsonLdProcessor().expand(input, options)


def frame(input, frame, options=None):
    """
    Performs JSON-LD framing.

    :param input: the JSON-LD object to frame.
    :param frame: the JSON-LD frame to use.
    :param [options]: the options to use.
      [base] the base IRI to use.
      [embed] default @embed flag (default: True).
      [explicit] default @explicit flag (default: False).
      [omitDefault] default @omitDefault flag (default: False).
      [optimize] optimize when compacting (default: False).

    :return: the framed JSON-LD output.
    """
    return JsonLdProcessor().frame(input, frame, options)


def normalize(input, options=None):
    """
    Performs JSON-LD normalization.

    :param input: the JSON-LD object to normalize.
    :param [options]: the options to use.
      [base] the base IRI to use.

    :return: the normalized JSON-LD output.
    """
    return JsonLdProcessor().normalize(input, options)


def toRDF(input, options=None):
    """
    Outputs the RDF statements found in the given JSON-LD object.

    :param input: the JSON-LD object.
    :param [options]: the options to use.
      [base] the base IRI to use.

    :return: all RDF statements in the JSON-LD object.
    """
    return JsonLdProcessor().toRDF(input, options)


class JsonLdProcessor:
    """
    A JSON-LD processor.
    """

    def __init__(self):
        """
        Initialize the JSON-LD processor.
        """
        pass

    def compact(self, input, ctx, options):
        """
        Performs JSON-LD compaction.

        :param input: the JSON-LD input to compact.
        :param ctx: the context to compact with.
        :param options: the options to use.
          [base] the base IRI to use.
          [strict] use strict mode (default: True).
          [optimize] True to optimize the compaction (default: False).
          [graph] True to always output a top-level graph (default: False).
          [activeCtx] True to also return the active context used.

        :return: the compacted JSON-LD output.
        """
        # nothing to compact
        if input is None:
            return None

        # set default options
        options = options or {}
        options.setdefault('base', '')
        options.setdefault('strict', True)
        options.setdefault('optimize', False)
        options.setdefault('graph', False)
        options.setdefault('activeCtx', False)

        # expand input
        try:
            expanded = self.expand(input, options)
        except JsonLdError as cause:
            raise JsonLdError('Could not expand input before compaction.',
                'jsonld.CompactError', None, cause)

        # process context
        active_ctx = self._getInitialContext()
        try:
            active_ctx = self.processContext(active_ctx, ctx, options)
        except JsonLdError as cause:
            raise JsonLdError('Could not process context before compaction.',
                'jsonld.CompactError', None, cause)

        # do compaction
        compacted = self._compact(active_ctx, None, expanded, options)

        # always use an array if graph options is on
        if options['graph'] == True:
            compacted = JsonLdProcessor.arrayify(compacted)
        # elif compacted is an array with 1 entry, remove array
        elif _is_array(compacted) and len(compacted) == 1:
            compacted = compacted[0]

        # follow @context key
        if _is_object(ctx) and '@context' in ctx:
            ctx = ctx['@context']

        # build output context
        ctx = copy.deepcopy(ctx)
        ctx = JsonLdProcessor.arrayify(ctx)

        # remove empty contexts
        tmp = ctx
        ctx = []
        for v in tmp:
            if not _is_object(v) or len(v) > 0:
                ctx.append(v)

        # remove array if only one context
        ctx_length = len(ctx)
        has_context = (ctx_length > 0)
        if ctx_length == 1:
            ctx = ctx[0]

        # add context
        if has_context or options['graph']:
            if _is_array(compacted):
                # use '@graph' keyword
                kwgraph = self._compactIri(active_ctx, '@graph')
                graph = compacted
                compacted = {}
                if has_context:
                    compacted['@context'] = ctx
                compacted[kwgraph] = graph
            elif _is_object(compacted):
                # reorder keys so @context is first
                graph = compacted
                compacted = {}
                compacted['@context'] = ctx
                for k, v in graph:
                    compacted[k] = v

        if options['activeCtx']:
            return {'compacted': compacted, 'activeCtx': active_ctx}
        else:
            return compacted

    def expand(self, input, options):
        """
        Performs JSON-LD expansion.

        :param input: the JSON-LD object to expand.
        :param options: the options to use.
          [base] the base IRI to use.

        :return: the expanded JSON-LD output.
        """
        # set default options
        options = options or {}
        options.setdefault('base', '')

        # resolve all @context URLs in the input
        input = copy.deepcopy(input)
        #self._resolveUrls(input, options['resolver'])

        # do expansion
        ctx = self._getInitialContext()
        expanded = self._expand(ctx, None, input, options, False)

        # optimize away @graph with no other properties
        if (_is_object(expanded) and '@graph' in expanded and
            len(expanded) == 1):
            expanded = expanded['@graph']

        # normalize to an array
        return JsonLdProcessor.arrayify(expanded)

    def frame(self, input, frame, options):
        """
        Performs JSON-LD framing.

        :param input: the JSON-LD object to frame.
        :param frame: the JSON-LD frame to use.
        :param options: the options to use.
          [base] the base IRI to use.
          [embed] default @embed flag (default: True).
          [explicit] default @explicit flag (default: False).
          [omitDefault] default @omitDefault flag (default: False).
          [optimize] optimize when compacting (default: False).

        :return: the framed JSON-LD output.
        """
        # set default options
        options = options or {}
        options.setdefault('base', '')
        options.setdefault('embed', True)
        options.setdefault('explicit', False)
        options.setdefault('omitDefault', False)
        options.setdefault('optimize', False)

        # preserve frame context
        ctx = frame['@context'] or {}

        try:
            # expand input
            _input = self.expand(input, options)
        except JsonLdError as cause:
            raise JsonLdError('Could not expand input before framing.',
                'jsonld.FrameError', None, cause)

        try:
            # expand frame
            _frame = self.expand(frame, options)
        except JsonLdError as cause:
            raise JsonLdError('Could not expand frame before framing.',
                'jsonld.FrameError', None, cause)

        # do framing
        framed = self._frame(_input, _frame, options)

        try:
            # compact result (force @graph option to True)
            options['graph'] = True
            options['activeCtx'] = True
            result = self.compact(framed, ctx, options)
        except JsonLdError as cause:
            raise JsonLdError('Could not compact framed output.',
                'jsonld.FrameError', None, cause)

        compacted = result['compacted']
        ctx = result['activeCtx']

        # get graph alias
        graph = self._compactIri(ctx, '@graph')
        # remove @preserve from results
        compacted[graph] = self._removePreserve(ctx, compacted[graph])
        return compacted

    def normalize(self, input, options):
        """
        Performs JSON-LD normalization.

        :param input: the JSON-LD object to normalize.
        :param options: the options to use.
          [base] the base IRI to use.

        :return: the JSON-LD normalized output.
        """
        # set default options
        options = options or {}
        options.setdefault('base', '')

        try:
          # expand input then do normalization
          expanded = self.expand(input, options)
        except JsonLdError as cause:
            raise JsonLdError('Could not expand input before normalization.',
                'jsonld.NormalizeError', None, cause)

        # do normalization
        return self._normalize(expanded)

    def toRDF(self, input, options):
        """
        Outputs the RDF statements found in the given JSON-LD object.

        :param input: the JSON-LD object.
        :param options: the options to use.

        :return: the RDF statements.
        """
        # set default options
        options = options or {}
        options.setdefault('base', '')

        # resolve all @context URLs in the input
        input = copy.deepcopy(input)
        #self._resolveUrls(input, options['resolver'])

        # output RDF statements
        return self._toRDF(input)

    def processContext(self, active_ctx, local_ctx, options):
        """
        Processes a local context, resolving any URLs as necessary, and
        returns a new active context in its callback.

        :param active_ctx: the current active context.
        :param local_ctx: the local context to process.
        :param options: the options to use.

        :return: the new active context.
        """

        # return initial context early for None context
        if local_ctx == None:
            return self._getInitialContext()

        # set default options
        options = options or {}
        options.setdefault('base', '')

        # resolve URLs in local_ctx
        local_ctx = copy.deepcopy(local_ctx)
        if _is_object(local_ctx) and '@context' not in local_ctx:
            local_ctx = {'@context': local_ctx}
        #ctx = self._resolveUrls(local_ctx, options['resolver'])
        ctx = local_ctx

        # process context
        return self._processContext(active_ctx, ctx, options)

    @staticmethod
    def hasProperty(subject, property):
        """
        Returns True if the given subject has the given property.

        :param subject: the subject to check.
        :param property: the property to look for.

        :return: True if the subject has the given property, False if not.
        """
        if property in subject:
            value = subject[property]
            return not _is_array(value) or len(value) > 0
        return False

    @staticmethod
    def hasValue(subject, property, value):
        """
         Determines if the given value is a property of the given subject.

        :param subject: the subject to check.
        :param property: the property to check.
        :param value: the value to check.

        :return: True if the value exists, False if not.
        """
        rval = False
        if JsonLdProcessor.hasProperty(subject, property):
            val = subject[property]
            is_list = _is_list(val)
            if _is_array(val) or is_list:
                if is_list:
                    val = val['@list']
                for v in val:
                    if JsonLdProcessor.compareValues(value, v):
                        rval = True
                        break
            # avoid matching the set of values with an array value parameter
            elif not _is_array(value):
                rval = JsonLdProcessor.compareValues(value, val)
        return rval

    @staticmethod
    def addValue(subject, property, value, property_is_array=False):
        """
        Adds a value to a subject. If the subject already has the value, it
        will not be added. If the value is an array, all values in the array
        will be added.

        Note: If the value is a subject that already exists as a property of
        the given subject, this method makes no attempt to deeply merge
        properties. Instead, the value will not be added.

        :param subject: the subject to add the value to.
        :param property: the property that relates the value to the subject.
        :param value: the value to add.
        :param [property_is_array]: True if the property is always an array,
          False if not (default: False).
        """
        if _is_array(value):
            if (len(value) == 0 and property_is_array and
                property not in subject):
                subject[property] = []
            for v in value:
                JsonLdProcessor.addValue(
                    subject, property, v, property_is_array)
        elif property in subject:
            has_value = JsonLdProcessor.hasValue(subject, property, value)

            # make property an array if value not present or always an array
            if (not _is_array(subject[property]) and
                (not has_value or property_is_array)):
                subject[property] = [subject[property]]

            # add new value
            if not has_value:
                subject[property].append(value)
        else:
            # add new value as set or single value
            subject[property] = [value] if property_is_array else value

    @staticmethod
    def getValues(subject, property):
        """
        Gets all of the values for a subject's property as an array.

        :param subject: the subject.
        :param property: the property.

        :return: all of the values for a subject's property as an array.
        """
        return JsonLdProcessor.arrayify(subject[property] or [])

    @staticmethod
    def removeProperty(subject, property):
        """
        Removes a property from a subject.

        :param subject: the subject.
        :param property: the property.
        """
        del subject[property]

    @staticmethod
    def removeValue(subject, property, value, property_is_array=False):
        """
        Removes a value from a subject.

        :param subject: the subject.
        :param property: the property that relates the value to the subject.
        :param value: the value to remove.
        :param [property_is_array]: True if the property is always an array,
          False if not (default: False).
        """
        # filter out value
        def filter_value(e):
            return not JsonLdProcessor.compareValues(e, value)
        values = JsonLdProcessor.getValues(subject, property)
        values = filter(filter_value, values)

        if len(values) == 0:
            JsonLdProcessor.removeProperty(subject, property)
        elif len(values) == 1 and not property_is_array:
            subject[property] = values[0]
        else:
            subject[property] = values

    @staticmethod
    def compareValues(v1, v2):
        """
        Compares two JSON-LD values for equality. Two JSON-LD values will be
        considered equal if:

        1. They are both primitives of the same type and value.
        2. They are both @values with the same @value, @type, and @language, OR
        3. They both have @ids they are the same.

        :param v1: the first value.
        :param v2: the second value.

        :return: True if v1 and v2 are considered equal, False if not.
        """
        # 1. equal primitives
        if v1 == v2:
            return True

        # 2. equal @values
        if (_is_value(v1) and _is_value(v2) and
            v1['@value'] == v2['@value'] and
            ('@type' in v1) == ('@type' in v2) and
            ('@language' in v1) == ('@language' in v2) and
            ('@type' not in v1 or v1['@type'] == v2['@type']) and
            ('@language' not in v1 or v2['@language'] == v2['@language'])):
            return True

        # 3. equal @ids
        if (_is_object(v1) and '@id' in v1 and
            _is_object(v2) and '@id' in v2):
            return v1['@id'] == v2['@id']

        return False

    @staticmethod
    def compareNormalized(n1, n2):
        """
        Compares two JSON-LD normalized inputs for equality.

        :param n1: the first normalized input.
        :param n2: the second normalized input.

        :return: True if the inputs are equivalent, False if not.
        """
        if not _is_array(n1) or not _is_array(n2):
            raise JsonLdError(
                'Invalid JSON-LD syntax normalized JSON-LD must be an array.',
                'jsonld.SyntaxError')
        # different # of subjects
        if len(n1) != len(n2):
            return False
        # assume subjects are in the same order because of normalization
        for s1, s2 in zip(n1, n2):
            # different @ids
            if s1['@id'] != s2['@id']:
                return False
            # subjects have different properties
            if len(s1) != len(s2):
                return False
            # compare each property
            for p, objects in s1.items():
                # skip @id property
                if p == '@id':
                    continue
                # s2 is missing s1 property
                if not JsonLdProcessor.hasProperty(s2, p):
                    return False
                # subjects have different objects for the property
                if len(objects) != len(s2[p]):
                    return False
                # compare each object
                for oi, o in objects:
                    # s2 is missing s1 object
                    if not JsonLdProcessor.hasValue(s2, p, o):
                        return False
        return True

    @staticmethod
    def getContextValue(ctx, key, type):
        """
        Gets the value for the given active context key and type, None if none
        is set.

        :param ctx: the active context.
        :param key: the context key.
        :param [type]: the type of value to get (eg: '@id', '@type'), if not
          specified gets the entire entry for a key, None if not found.

        :return: mixed the value.
        """
        rval = None

        # return None for invalid key
        if key == None:
          return rval

        # get default language
        if type == '@language' and type in ctx:
          rval = ctx[type]

        # get specific entry information
        if key in ctx['mappings']:
          entry = ctx['mappings'][key]

          # return whole entry
          if type == None:
            rval = entry
          # return entry value for type
          elif type in entry:
            rval = entry[type]

        return rval

    @staticmethod
    def arrayify(value):
        """
        If value is an array, returns value, otherwise returns an array
        containing value as the only element.

        :param value: the value.

        :return: an array.
        """
        return value if _is_array(value) else [value]

    def _compact(self, ctx, property, element, options):
        """
        Recursively compacts an element using the given active context. All values
        must be in expanded form before this method is called.

        :param ctx: the active context to use.
        :param property: the property that points to the element, None for
          none.
        :param element: the element to compact.
        :param options: the compaction options.

        :return: the compacted value.
        """
        # recursively compact array
        if _is_array(element):
            rval = []
            for e in element:
                e = self._compact(ctx, property, e, options)
                # drop None values
                if e is not None:
                    rval.append(e)
            if len(rval) == 1:
                # use single element if no container is specified
                container = JsonLdProcessor.getContextValue(
                    ctx, property, '@container')
                if container != '@list' and container != '@set':
                    rval = rval[0]
            return rval

        # recursively compact object
        if _is_object(element):
            # element is a @value
            if _is_value(element):
                type = JsonLdProcessor.getContextValue(ctx, property, '@type')
                language = JsonLdProcessor.getContextValue(
                    ctx, property, '@language')

                # matching @type specified in context, compact element
                if (type != None and
                    '@type' in element and element['@type'] == type):
                    # use native datatypes for certain xsd types
                    element = element['@value']
                    if type == XSD_BOOLEAN:
                      element = not (element == 'False' or element == '0')
                    elif type == XSD_INTEGER:
                      element = int(element)
                    elif(type == XSD_DOUBLE):
                      element = float(element)
                # matching @language specified in context, compact element
                elif(language is not None and
                     '@language' in element and
                     element['@language'] == language):
                    element = element['@value']
                # compact @type IRI
                elif '@type' in element:
                    element['@type'] = self._compactIri(ctx, element['@type'])
                return element

            # compact subject references
            if _is_subject_reference(element):
                type = JsonLdProcessor.getContextValue(ctx, property, '@type')
                if type == '@id':
                    element = self._compactIri(ctx, element['@id'])
                    return element

            # recursively process element keys
            rval = {}
            for key, value in element:
                # compact @id and @type(s)
                if key == '@id' or key == '@type':
                    # compact single @id
                    if _is_string(value):
                        value = self._compactIri(ctx, value)
                    # value must be a @type array
                    else:
                        types = []
                        for v in value:
                            types.append(self._compactIri(ctx, v))
                        value = types

                    # compact property and add value
                    prop = self._compactIri(ctx, key)
                    is_array = (_is_array(value) and len(value) == 0)
                    JsonLdProcessor.addValue(rval, prop, value, is_array)
                    continue

                # Note: value must be an array due to expansion algorithm.

                # preserve empty arrays
                if len(value) == 0:
                    prop = self._compactIri(ctx, key)
                    JsonLdProcessor.addValue(rval, prop, array(), True)

                # recusively process array values
                for v in value:
                    is_list = _is_list(v)

                    # compact property
                    prop = self._compactIri(ctx, key, v)

                    # remove @list for recursion (will re-add if necessary)
                    if is_list:
                        v = v['@list']

                    # recursively compact value
                    v = self._compact(ctx, prop, v, options)

                    # get container type for property
                    container = JsonLdProcessor.getContextValue(
                        ctx, prop, '@container')

                    # handle @list
                    if is_list and container != '@list':
                        # handle messy @list compaction
                        if prop in rval and options['strict']:
                            raise JsonLdError(
                                'JSON-LD compact error property has a "@list" '
                                '@container rule but there is more than a '
                                'single @list that matches the compacted term '
                                'in the document. Compaction might mix '
                                'unwanted items into the list.',
                                'jsonld.SyntaxError')
                        # reintroduce @list keyword
                        kwlist = self._compactIri(ctx, '@list')
                        v = {kwlist: v}

                    # if @container is @set or @list or value is an empty
                    # array, use an array when adding value
                    is_array = (container == '@set' or container == '@list' or
                      (_is_array(v) and len(v) == 0))

                    # add compact value
                    JsonLdProcessor.addValue(rval, prop, v, is_array)

            return rval

        # only primitives remain which are already compact
        return element

    def _expand(self, ctx, property, element, options, property_is_list):
        """
        Recursively expands an element using the given context. Any context in
        the element will be removed. All context URLs must have been resolved
        before calling this method.

        :param stdClass ctx the context to use.
        :param mixed property the property for the element, None for none.
        :param mixed element the element to expand.
        :param array options the expansion options.
        :param bool property_is_list True if the property is a list, False if
          not.

        :return: mixed the expanded value.
        """
        # recursively expand array
        if _is_array(element):
            rval = []
            for e in element:
                # expand element
                e = self._expand(ctx, property, e, options, property_is_list)
                if _is_array(e) and property_is_list:
                  # lists of lists are illegal
                  raise JsonLdError(
                      'Invalid JSON-LD syntax lists of lists are not '
                      'permitted.', 'jsonld.SyntaxError')
                # drop None values
                elif e is not None:
                    rval.append(e)
            return rval

        # expand non-object element according to value expansion rules
        if not _is_object(element):
            return self._expandValue(ctx, property, element, options['base'])

        # Note: element must be an object, recursively expand it

        # if element has a context, process it
        if '@context' in element:
            ctx = self._processContext(ctx, element['@context'], options)
            del element['@context']

        rval = {}
        for key, value in element.items():
            # expand property
            prop = self._expandTerm(ctx, key)

            # drop non-absolute IRI keys that aren't keywords
            if not _is_absolute_iri(prop) and not _is_keyword(prop, ctx):
                continue
            # if value is None and property is not @value, continue
            value = element[key]
            if value == None and prop != '@value':
                continue

            # syntax error if @id is not a string
            if prop == '@id' and not _is_string(value):
                raise JsonLdError(
                    'Invalid JSON-LD syntax "@id" value must a string.',
                    'jsonld.SyntaxError', {'value': value})

            # @type must be a string, array of strings, or an empty JSON object
            if (prop == '@type' and
                not _is_string(value) or _is_array_of_strings(value) or
                _is_empty_object(value)):
                raise JsonLdError(
                    'Invalid JSON-LD syntax "@type" value must a string, '
                    'an array of strings, or an empty object.',
                    'jsonld.SyntaxError', {'value': value})

            # @graph must be an array or an object
            if (prop == '@graph' and not
                (_is_object(value) or _is_array(value))):
                raise JsonLdError(
                    'Invalid JSON-LD syntax "@value" value must not be an '
                    'object or an array.',
                    'jsonld.SyntaxError', {'value': value})

            # @value must not be an object or an array
            if (prop == '@value' and
                (_is_object(value) or _is_array(value))):
                raise JsonLdError(
                    'Invalid JSON-LD syntax "@value" value must not be an '
                    'object or an array.',
                    'jsonld.SyntaxError', {'value': value})

            # @language must be a string
            if (prop == '@language' and not _is_string(value)):
                raise JsonLdError(
                    'Invalid JSON-LD syntax "@language" value must not be '
                    'a string.', 'jsonld.SyntaxError', {'value': value})

            # recurse into @list, @set, or @graph, keeping active property
            is_list = (prop == '@list')
            if is_list or prop == '@set' or prop == '@graph':
                value = self._expand(ctx, property, value, options, is_list)
                if is_list and _is_list(value):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax lists of lists are not '
                        'permitted.', 'jsonld.SyntaxError')
            else:
                # update active property and recursively expand value
                property = key
                value = self._expand(ctx, property, value, options, False)

            # drop None values if property is not @value (dropped below)
            if value != None or prop == '@value':
                # convert value to @list if container specifies it
                if prop != '@list' and not _is_list(value):
                    container = JsonLdProcessor.getContextValue(
                        ctx, property, '@container')
                    if container == '@list':
                        # ensure value is an array
                        value = {'@list': JsonLdProcessor.arrayify(value)}

                # add value, use an array if not @id, @type, @value, or
                # @language
                use_array = not (prop == '@id' or prop == '@type' or
                    prop == '@value' or prop == '@language')
                JsonLdProcessor.addValue(rval, prop, value, use_array)

        # get property count on expanded output
        count = len(rval)

        # @value must only have @language or @type
        if '@value' in rval:
            if ((count == 2 and '@type' not in rval and
                '@language' not in rval) or count > 2):
                raise JsonLdError(
                    'Invalid JSON-LD syntax an element containing '
                    '"@value" must have at most one other property which '
                    'can be "@type" or "@language".',
                    'jsonld.SyntaxError', {'element': rval})
            # value @type must be a string
            if '@type' in rval and not _is_string(rval['@type']):
                raise JsonLdError(
                    'Invalid JSON-LD syntax the "@type" value of an '
                    'element containing "@value" must be a string.',
                    'jsonld.SyntaxError', {'element': rval})
            # return only the value of @value if there is no @type or @language
            elif count == 1:
                rval = rval['@value']
            # drop None @values
            elif rval['@value'] == None:
                rval = None
        # convert @type to an array
        elif '@type' in rval and not _is_array(rval['@type']):
            rval['@type'] = [rval['@type']]
        # handle @set and @list
        elif '@set' in rval or '@list' in rval:
            if count != 1:
                raise JsonLdError(
                    'Invalid JSON-LD syntax if an element has the '
                    'property "@set" or "@list", then it must be its '
                    'only property.',
                    'jsonld.SyntaxError', {'element': rval})
            # optimize away @set
            if '@set' in rval:
                rval = rval['@set']
        # drop objects with only @language
        elif '@language' in rval and count == 1:
            rval = None

        return rval

    def _frame(self, input, frame, options):
        """
        Performs JSON-LD framing.

        :param input: the expanded JSON-LD to frame.
        :param frame: the expanded JSON-LD frame to use.
        :param options: the framing options.

        :return: the framed output.
        """
        # create framing state
        state = {'options': options, 'subjects': {}}

        # produce a map of all subjects and name each bnode
        namer = UniqueNamer('_:t')
        self._flatten(state['subjects'], input, namer, None, None)

        # frame the subjects
        framed = []
        self._matchFrame(state, state['subjects'].keys(), frame, framed, None)
        return framed

    def _normalize(self, input):
        """
        Performs JSON-LD normalization.

        :param input: the expanded JSON-LD object to normalize.

        :return: the normalized output.
        """
        # get statements
        namer = UniqueNamer('_:t')
        bnodes = {}
        subjects = {}
        self._getStatements(input, namer, bnodes, subjects)

        # create canonical namer
        namer = UniqueNamer('_:c14n')

        # continue to hash bnode statements while bnodes are assigned names
        unnamed = None
        nextUnnamed = bnodes.keys()
        duplicates = None
        while True:
            unnamed = nextUnnamed
            nextUnnamed = []
            duplicates = {}
            unique = {}
            for bnode in unnamed:
                # hash statements for each unnamed bnode
                statements = bnodes[bnode]
                hash = self._hashStatements(statements, namer)

                # store hash as unique or a duplicate
                if hash in duplicates:
                    duplicates[hash].append(bnode)
                    nextUnnamed.append(bnode)
                elif hash in unique:
                    duplicates[hash] = [unique[hash], bnode]
                    nextUnnamed.append(unique[hash])
                    nextUnnamed.append(bnode)
                    del unique[hash]
                else:
                    unique[hash] = bnode

            # name unique bnodes in sorted hash order
            for hash, bnode in sorted(unique.items()):
                namer.getName(bnode)

            # done when no more bnodes named
            if len(unnamed) == len(nextUnnamed):
                break

        # enumerate duplicate hash groups in sorted order
        for hash, group in sorted(duplicates.items()):
            # process group
            results = []
            for bnode in group:
                # skip already-named bnodes
                if namer.isNamed(bnode):
                  continue

                # hash bnode paths
                path_namer = UniqueNamer('_:t')
                path_namer.getName(bnode)
                results.append(self._hashPaths(
                  bnodes, bnodes[bnode], namer, path_namer))

            # name bnodes in hash order
            cmp_hashes = cmp_to_key(lambda x, y: cmp(x['hash'], y['hash']))
            for result in sorted(results, key=cmp_hashes):
                # name all bnodes in path namer in key-entry order
                for bnode in result.pathNamer.order:
                    namer.getName(bnode)

        # create JSON-LD array
        output = []

        # add all bnodes
        for id, statements in bnodes.items():
            # add all property statements to bnode
            bnode = {'@id': namer.getName(id)}
            for statement in statements:
                if statement['s'] == '_:a':
                    z = _get_bnode_name(statement['o'])
                    o = {'@id': namer.getName(z)} if z else statement['o']
                    JsonLdProcessor.addValue(bnode, statement['p'], o, True)
            output.append(bnode)

        # add all non-bnodes
        for id, statements in subjects.items():
            # add all statements to subject
            subject = {'@id': id}
            for statement in statements:
                z = _get_bnode_name(statement['o'])
                o = {'@id': namer.getName(z)} if z else statement['o']
                JsonLdProcessor.addValue(subject, statement['p'], o, True)
            output.append(subject)

        # sort normalized output by @id
        cmp_ids = cmp_to_key(lambda x, y: cmp(x['@id'], y['@id']))
        output.sort(key=cmp_ids)
        return output

    def _toRDF(self, input):
        """
        Outputs the RDF statements found in the given JSON-LD object.

        :param input: the JSON-LD object.

        :return: the RDF statements.
        """
        # FIXME: implement
        raise JsonLdError('Not implemented', 'jsonld.NotImplemented')

    def _processContext(self, active_ctx, local_ctx, options):
        """
        Processes a local context and returns a new active context.

        :param active_ctx: the current active context.
        :param local_ctx: the local context to process.
        :param options: the context processing options.

        :return: the new active context.
        """
        # initialize the resulting context
        rval = copy.deepcopy(active_ctx)

        # normalize local context to an array
        ctxs = JsonLdProcessor.arrayify(local_ctx)

        # process each context in order
        for ctx in ctxs:
            # reset to initial context
            if ctx is None:
                rval = self._getInitialContext()
                continue

            # dereference @context key if present
            if _is_object(ctx) and '@context' in ctx:
                ctx = ctx['@context']

            # context must be an object by now, all URLs resolved before this call
            if not _is_object(ctx):
                raise JsonLdError(
                    'Invalid JSON-LD syntax @context must be an object.',
                    'jsonld.SyntaxError', {'context': ctx})

            # define context mappings for keys in local context
            defined = {}
            for k, v in ctx.items():
                self._defineContextMapping(
                    rval, ctx, k, options['base'], defined)

        return rval

    def _expandValue(self, ctx, property, value, base):
        """
        Expands the given value by using the coercion and keyword rules in the
        given context.

        :param ctx: the active context to use.
        :param property: the property the value is associated with.
        :param value: the value to expand.
        :param base: the base IRI to use.

        :return: the expanded value.
        """
        # default to simple string return value
        rval = value

        # special-case expand @id and @type (skips '@id' expansion)
        prop = self._expandTerm(ctx, property)
        if prop == '@id':
            rval = self._expandTerm(ctx, value, base)
        elif prop == '@type':
            rval = self._expandTerm(ctx, value)
        else:
            # get type definition from context
            type = JsonLdProcessor.getContextValue(ctx, property, '@type')

            # do @id expansion
            if type == '@id':
                rval = {'@id': self._expandTerm(ctx, value, base)}
            # other type
            elif type is not None:
                rval = {'@value': str(value), '@type': type}
            # check for language tagging
            else:
                language = JsonLdProcessor.getContextValue(
                    ctx, property, '@language')
                if language is not None:
                    rval = {'@value': str(value), '@language': language}

        return rval

    def _getStatements(self, input, namer, bnodes, subjects, name=None):
        """
        Recursively gets all statements from the given expanded JSON-LD input.

        :param input: the valid expanded JSON-LD input.
        :param namer: the namer to use when encountering blank nodes.
        :param bnodes: the blank node statements map to populate.
        :param subjects: the subject statements map to populate.
        :param [name]: the name (@id) assigned to the current input.
        """
        # recurse into arrays
        if _is_array(input):
            for e in input:
                self._getStatements(e, namer, bnodes, subjects)
            return
        # Note:safe to assume input is a subject/blank node
        is_bnode = _is_bnode(input)

        # name blank node if appropriate, use passed name if given
        if name is None:
            name = input.get('@id')
            if is_bnode:
                name = namer.getName(name)

        # use a subject of '_:a' for blank node statements
        s = '_:a' if is_bnode else name

        # get statements for the blank node
        if is_bnode:
            entries = bnodes.setdefault(name, [])
        else:
            entries = subjects.setdefault(name, [])

        # add all statements in input
        for p, objects in input.items():
            # skip @id
            if p == '@id':
                continue

            # convert @lists into embedded blank node linked lists
            for i, o in enumerate(objects):
                if _is_list(o):
                    objects[i] = self._makeLinkedList(o)

            for o in objects:
                # convert boolean to @value
                if is_bool(o):
                    o = {'@value': 'True' if o else 'False',
                        '@type': XSD_BOOLEAN}
                # convert double to @value
                elif is_double(o):
                    # do special JSON-LD double format,
                    # printf(' % 1.16e') equivalent
                    o = {'@value': ('%1.6e' % o), '@type': XSD_DOUBLE}
                # convert integer to @value
                elif is_integer(o):
                    o = {'@value': str(o), '@type': XSD_INTEGER}

                # object is a blank node
                if _is_bnode(o):
                    # name object position blank node
                    o_name = namer.getName(o.get('@id'))

                    # add property statement
                    self._addStatement(entries,
                        {'s': s, 'p': p, 'o': {'@id': o_name}})

                    # add reference statement
                    o_entries = bnodes.setdefault(o_name, [])
                    self._addStatement(o_entries,
                        {'s': name, 'p': p, 'o': {'@id': '_:a'}})

                    # recurse into blank node
                    self._getStatements(o, namer, bnodes, subjects, o_name)
                # object is a string, @value, subject reference
                elif (_is_string(o) or _is_value(o) or
                    _is_subject_reference(o)):
                    # add property statement
                    self._addStatement(entries, {'s': s, 'p': p, 'o': o})

                    # ensure a subject entry exists for subject reference
                    if (_is_subject_reference(o) and
                        o['@id'] not in subjects):
                        subjects.setdefault(o['@id'], [])
                # object must be an embedded subject
                else:
                    # add property statement
                    self._addStatement(entries,
                        {'s': s, 'p': p, 'o': {'@id': o['@id']}})

                    # recurse into subject
                    self._getStatements(o, namer, bnodes, subjects)

    def _makeLinkedList(self, value):
        """
        Converts a @list value into an embedded linked list of blank nodes in
        expanded form. The resulting array can be used as an RDF-replacement
        for a property that used a @list.

        :param value: the @list value.

        :return: the head of the linked list of blank nodes.
        """
        # convert @list array into embedded blank node linked list
        # build linked list in reverse
        tail = {'@id': RDF_NIL}
        for e in reversed(value['@list']):
          tail = {RDF_FIRST: e, RDF_REST: tail}
        return tail

    def _addStatement(self, statements, statement):
        """
        Adds a statement to an array of statements. If the statement already
        exists in the array, it will not be added.

        :param statements: the statements array.
        :param statement: the statement to add.
        """
        for s in statements:
            if (s['s'] == statement['s'] and s['p'] == statement['p'] and
                JsonLdProcessor.compareValues(s['o'], statement['o'])):
                return
        statements.append(statement)

    def _hashStatements(self, statements, namer):
        """
        Hashes all of the statements about a blank node.

        :param statements: the statements about the bnode.
        :param namer: the canonical bnode namer.

        :return: the new hash.
        """
        # serialize all statements
        triples = []
        for statement in statements:
            s, p, o = statement['s'], statement['p'], statement['o']

            # serialize triple
            triple = ''

            # serialize subject
            if s == '_:a':
                triple += '_:a'
            elif s.startswith('_:'):
                id = s
                id = namer.getName(id) if namer.isNamed(id) else '_:z'
                triple += id
            else:
                triple += ' <%s> ' % s

            # serialize property
            p = RDF_TYPE if p == '@type' else p
            triple += ' <%s> ' % p

            # serialize object
            if _is_bnode(o):
                if o['@id'] == '_:a':
                  triple += '_:a'
                else:
                  id = o['@id']
                  id = namer.getName(id) if namer.isNamed(id) else '_:z'
                  triple += id
            elif _is_string(o):
                triple += '"%s"' % o
            elif _is_subject_reference(o):
                triple += '<%s>' % o['@id']
            # must be a value
            else:
                triple += '"%s"' % o['@value']
                if '@type' in o:
                  triple += '^^<%s>' % o['@type']
                elif '@language' in o:
                  triple += '@%s' % o['@language']

            # add triple
            triples.append(triple)

        # sort serialized triples
        triples.sort()

        # return hashed triples
        md = hashlib.sha1()
        md.update(''.join(triples))
        return md.hexdigest()

    def _hashPaths(self, bnodes, statements, namer, path_namer):
        """
        Produces a hash for the paths of adjacent bnodes for a bnode,
        incorporating all information about its subgraph of bnodes. This
        method will recursively pick adjacent bnode permutations that produce the
        lexicographically-least 'path' serializations.

        :param bnodes: the map of bnode statements.
        :param statements: the statements for the bnode the hash is for.
        :param namer: the canonical bnode namer.
        :param path_namer: the namer used to assign names to adjacent bnodes.

        :return: the hash and path namer used.
        """
        # create SHA-1 digest
        md = hashlib.sha1()

        # group adjacent bnodes by hash, keep properties & references separate
        groups = {}
        cache = {}
        for statement in statements:
            s, p, o = statement['s'], statement['p'], statement['o']
            if s != '_:a' and s.startswith('_:'):
                bnode = s
                direction = 'p'
            else:
                bnode = _get_bnode_name(o)
                direction = 'r'

            if bnode is not None:
                # get bnode name (try canonical, path, then hash)
                if namer.isNamed(bnode):
                    name = namer.getName(bnode)
                elif path_namer.isNamed(bnode):
                    name = path_namer.getName(bnode)
                elif bnode in cache:
                    name = cache[bnode]
                else:
                    name = self._hashStatements(bnodes[bnode], namer)
                    cache[bnode] = name

                # hash direction, property, and bnode name/hash
                group_md = hashlib.sha1()
                group_md.update(direction)
                group_md.update(RDF_TYPE if p == '@type' else p)
                group_md.update(name)
                group_hash = group_md.hexdigest()

                # add bnode to hash group
                if group_hash in groups:
                    groups[group_hash].append(bnode)
                else:
                    groups[group_hash] = [bnode]

        # iterate over groups in sorted hash order
        for group_hash, group in sorted(groups.items()):
            # digest group hash
            md.update(group_hash)

            # choose a path and namer from the permutations
            chosen_path = None
            chosen_namer = None
            permutator = Permutator(group)
            while permutator.hasNext():
                permutation = permutator.next()
                path_namer_copy = copy.deepcopy(path_namer)

                # build adjacent path
                path = ''
                skipped = False
                recurse = []
                for bnode in permutation:
                    # use canonical name if available
                    if namer.isNamed(bnode):
                        path += namer.getName(bnode)
                    else:
                        # recurse if bnode isn't named in the path yet
                        if not path_namer_copy.isNamed(bnode):
                            recurse.append(bnode)
                        path += path_namer_copy.getName(bnode)

                    # skip permutation if path is already >= chosen path
                    if (chosen_path is not None and
                        len(path) >= len(chosen_path) and path > chosen_path):
                        skipped = True
                        break

                # recurse
                if not skipped:
                    for bnode in recurse:
                        result = self._hashPaths(
                            bnodes, bnodes[bnode], namer, path_namer_copy)
                        path += path_namer_copy.getName(bnode)
                        path += '<%s>' % result['hash']
                        path_namer_copy = result['pathNamer']

                        # skip permutation if path is already >= chosen path
                        if (chosen_path is not None and
                            len(path) >= len(chosen_path) and
                            path > chosen_path):
                            skipped = True
                            break

                if not skipped and (chosen_path is None or path < chosen_path):
                    chosen_path = path
                    chosen_namer = path_namer_copy

            # digest chosen path and update namer
            md.update(chosen_path)
            path_namer = chosen_namer

        # return SHA-1 hash and path namer
        return {'hash': md.hexdigest(), 'pathNamer': path_namer}

    def _flatten(self, subjects, input, namer, name, lst):
        """
        Recursively flattens the subjects in the given JSON-LD expanded input.

        :param subjects: a map of subject @id to subject.
        :param input: the JSON-LD expanded input.
        :param namer: the blank node namer.
        :param name: the name assigned to the current input if it is a bnode.
        :param lst: the list to append to, None for none.
        """
        # recurse through array
        if _is_array(input):
            for e in input:
                self._flatten(subjects, e, namer, None, lst)
            return
        elif not _is_object(input):
            # add non-object to list
            if lst is not None:
                lst.append(input)

        # Note: input must be an object

        # add value to list
        if _is_value(input) and lst is not None:
            lst.append(input)
            pass

        # get name for subject
        if name is None:
            name = input.get('@id')
            if _is_bnode(input):
                name = namer.getName(name)

        # add subject reference to list
        if lst is not None:
            lst.append({'@id': name})

        # create new subject or merge into existing one
        subject = subjects.setdefault(name, {})
        subject['@id'] = name
        for prop, objects in input:
            # skip @id
            if prop == '@id':
                continue

            # copy keywords
            if _is_keyword(prop):
                subject[prop] = objects
                continue

            # iterate over objects
            for o in objects:
                # handle embedded subject or subject reference
                if _is_subject(o) or _is_subject_reference(o):
                    # rename blank node @id
                    id = o.get('@id', '_:')
                    if id.startswith('_:'):
                        id = namer.getName(id)

                    # add reference and recurse
                    JsonLdProcessor.addValue(subject, prop, {'@id': id}, True)
                    self._flatten(subjects, o, namer, id, None)
                else:
                    # recurse into list
                    if _is_list(o):
                        olst = {}
                        self._flatten(subjects, o['@list'], namer, name, olst)
                        o = {'@list': olst}

                    # add non-subject
                    JsonLdProcessor.addValue(subject, prop, o, True)

    def _matchFrame(self, state, subjects, frame, parent, property):
        """
        Frames subjects according to the given frame.

        :param state: the current framing state.
        :param subjects: the subjects to filter.
        :param frame: the frame.
        :param parent: the parent subject or top-level array.
        :param property: the parent property, initialized to None.
        """
        # validate the frame
        self._validateFrame(state, frame)
        frame = frame[0]

        # filter out subjects that match the frame
        matches = self._filterSubjects(state, subjects, frame)

        # get flags for current frame
        options = state['options']
        embed_on = self._getFrameFlag(frame, options, 'embed')
        explicit_on = self._getFrameFlag(frame, options, 'explicit')

        # add matches to output
        for id, subject in matches.items():
            # Note: In order to treat each top-level match as a
            # compartmentalized result, create an independent copy of the
            # embedded subjects map when the property is None, which only
            # occurs at the top-level.
            if property is None:
                state['embeds'] = {}

            # start output
            output = {'@id': id}

            # prepare embed meta info
            embed = {'parent': parent, 'property': property}

            # if embed is on and there is an existing embed
            if embed_on and id in state['embeds']:
                # only overwrite an existing embed if it has already been added
                # to its parent -- otherwise its parent is somewhere up the
                # tree from this embed and the embed would occur twice once
                # the tree is added
                embed_on = False

                # existing embed's parent is an array
                existing = state['embeds'][id]
                if _is_array(existing['parent']):
                    for p in existing['parent']:
                        if JsonLdProcessor.compareValues(output, p):
                            embed_on = True
                            break
                # existing embed's parent is an object
                elif JsonLdProcessor.hasValue(
                    existing['parent'], existing['property'], output):
                    embed_on = True

                # existing embed has already been added, so allow an overwrite
                if embed_on:
                    self._removeEmbed(state, id)

            # not embedding, add output without any other properties
            if not embed_on:
                self._addFrameOutput(state, parent, property, output)
            else:
                # add embed meta info
                state['embeds'][id] = embed

                # iterate over subject properties in order
                for prop, objects in sorted(subject.items()):
                    # copy keywords to output
                    if _is_keyword(prop):
                        output[prop] = copy.deepcopy(subject[prop])
                        continue

                    # if property isn't in the frame
                    if prop not in frame:
                        # if explicit is off, embed values
                        if not explicit_on:
                            self._embedValues(state, subject, prop, output)
                        continue

                    # add objects
                    objects = subject[prop]
                    for o in objects:
                        # recurse into list
                        if _is_list(o):
                            # add empty list
                            lst = {'@list': []}
                            self._addFrameOutput(state, output, prop, lst)

                            # add list objects
                            src = o['@list']
                            for o in src:
                                # recurse into subject reference
                                if _is_subject_reference(o):
                                    self._matchFrame(
                                        state, [o['@id']], frame[prop],
                                        lst, '@list')
                                # include other values automatically
                                else:
                                    self._addFrameOutput(
                                        state, lst, '@list', copy.deepcopy(o))
                            continue

                        # recurse into subject reference
                        if _is_subject_reference(o):
                            self._matchFrame(
                                state, [o['@id']], frame[prop], output, prop)
                        # include other values automatically
                        else:
                            self._addFrameOutput(
                                state, output, prop, copy.deepcopy(o))

                # handle defaults in order
                for prop in sorted(frame.items()):
                    # skip keywords
                    if _is_keyword(prop):
                        continue
                    # if omit default is off, then include default values for
                    # properties that appear in the next frame but are not in
                    # the matching subject
                    next = frame[prop][0]
                    omit_default_on = self._getFrameFlag(
                        next, options, 'omitDefault')
                    if not omit_default_on and prop not in output:
                        preserve = '@null'
                        if '@default' in next:
                            preserve = copy.deepcopy(next['@default'])
                        output[prop] = {'@preserve': preserve}

                # add output to parent
                self._addFrameOutput(state, parent, property, output)

    def _getFrameFlag(self, frame, options, name):
        """
        Gets the frame flag value for the given flag name.

        :param frame: the frame.
        :param options: the framing options.
        :param name: the flag name.

        :return: the flag value.
        """
        return frame.get('@' + name, [options[name]])[0]

    def _validateFrame(self, state, frame):
        """
        Validates a JSON-LD frame, throwing an exception if the frame is invalid.

        :param state: the current frame state.
        :param frame: the frame to validate.
        """
        if not _is_array(frame) or len(frame) != 1 or not _is_object(frame[0]):
            raise JsonLdError(
                'Invalid JSON-LD syntax a JSON-LD frame must be a single '
                'object.', 'jsonld.SyntaxError', {'frame': frame})

    def _filterSubjects(self, state, subjects, frame):
        """
        Returns a map of all of the subjects that match a parsed frame.

        :param state: the current framing state.
        :param subjects: the set of subjects to filter.
        :param frame: the parsed frame.

        :return: all of the matched subjects.
        """
        rval = {}
        for id in sorted(subjects):
            subject = state['subjects'][id]
            if self._filterSubject(subject, frame):
                rval[id] = subject
        return rval

    def _filterSubject(self, subject, frame):
        """
        Returns True if the given subject matches the given frame.

        :param subject: the subject to check.
        :param frame: the frame to check.

        :return: True if the subject matches, False if not.
        """
        # check @type (object value means 'any' type, fall through to
        # ducktyping)
        if ('@type' in frame and
            not (len(frame['@type']) == 1 and _is_object(frame['@type'][0]))):
            types = frame['@type']
            for type in types:
                # any matching @type is a match
                if JsonLdProcessor.hasValue(subject, '@type', type):
                  return True
            return False

        # check ducktype
        for k, v in frame.items():
            # only not a duck if @id or non-keyword isn't in subject
            if (k == '@id' or not _is_keyword(k)) and k not in subject:
                return False
        return True

    def _embedValues(self, state, subject, property, output):
        """
        Embeds values for the given subject and property into the given output
        during the framing algorithm.

        :param state: the current framing state.
        :param subject: the subject.
        :param property: the property.
        :param output: the output.
        """
        # embed subject properties in output
        objects = subject[property]
        for o in objects:
            # recurse into @list
            if _is_list(o):
                lst = {'@list': []}
                self._addFrameOutput(state, output, property, lst)
                self._embedValues(state, o, '@list', lst['@list'])
                return

            # handle subject reference
            if _is_subject_reference(o):
                id = o['@id']

                # embed full subject if isn't already embedded
                if id not in state['embeds']:
                    # add embed
                    embed = {'parent': output, 'property': property}
                    state['embeds'][id] = embed
                    # recurse into subject
                    o = {}
                    s = state['subjects'][id]
                    for prop, v in s:
                        # copy keywords
                        if _is_keyword(prop):
                            o[prop] = copy.deepcopy(v)
                            continue
                        self._embedValues(state, s, prop, o)
                self._addFrameOutput(state, output, property, o)
            # copy non-subject value
            else:
                self._addFrameOutput(state, output, property, copy.deepcopy(o))

    def _removeEmbed(self, state, id):
        """
        Removes an existing embed.

        :param state: the current framing state.
        :param id: the @id of the embed to remove.
        """
        # get existing embed
        embeds = state['embeds']
        embed = embeds[id]
        property = embed['property']

        # create reference to replace embed
        subject = {'@id': id}

        # remove existing embed
        if _is_array(embed['parent']):
            # replace subject with reference
            for i, parent in embed['parent']:
                if JsonLdProcessor.compareValues(parent, subject):
                    embed['parent'][i] = subject
                    break
        else:
            # replace subject with reference
            use_array = _is_array(embed['parent'][property])
            JsonLdProcessor.removeValue(
                embed['parent'], property, subject, use_array)
            JsonLdProcessor.addValue(
                embed['parent'], property, subject, use_array)

        # recursively remove dependent dangling embeds
        def remove_rependents(id):
            # get embed keys as a separate array to enable deleting keys in map
            ids = embeds.keys()
            for next in ids:
                if (next in embeds and
                    _is_object(embeds[next]['parent']) and
                    embeds[next]['parent']['@id'] == id):
                    del embeds[next]
                    remove_dependents(next)
        remove_dependents(id)

    def _addFrameOutput(self, state, parent, property, output):
        """
        Adds framing output to the given parent.

        :param state: the current framing state.
        :param parent: the parent to add to.
        :param property: the parent property.
        :param output: the output to add.
        """
        if _is_object(parent):
            JsonLdProcessor.addValue(parent, property, output, True)
        else:
            parent.append(output)

    def _removePreserve(self, ctx, input):
        """
        Removes the @preserve keywords as the last step of the framing algorithm.

        :param ctx: the active context used to compact the input.
        :param input: the framed, compacted output.

        :return: the resulting output.
        """
        # recurse through arrays
        if _is_array(input):
            output = []
            for e in input:
              result = self._removePreserve(ctx, e)
              # drop Nones from arrays
              if result is not None:
                  output.append(result)
            return output
        elif _is_object(input):
            # remove @preserve
            if '@preserve' in input:
                if input['@preserve'] == '@null':
                  return None
                return input['@preserve']

            # skip @values
            if _is_value(input):
                return input

            # recurse through @lists
            if _is_list(input):
                input['@list'] = self._removePreserve(ctx, input['@list'])
                return input

            # recurse through properties
            for prop, v in input:
                result = self._removePreserve(ctx, v)
                container = JsonLdProcessor.getContextValue(
                    ctx, prop, '@container')
                if (_is_array(result) and len(result) == 1 and
                    container != '@set' and container != '@list'):
                    result = result[0]
                input[prop] = result
        return input

    def _rankTerm(self, ctx, term, value):
        """
         Ranks a term that is possible choice for compacting an IRI associated
         with the given value.

         :param ctx: the active context.
         :param term: the term to rank.
         :param value: the associated value.

         :return: the term rank.
        """
        # no term restrictions for a None value
        if value is None:
            return 3

        # get context entry for term
        entry = ctx['mappings'][term]
        has_type = '@type' in entry
        has_language = '@language' in entry
        has_default_language = '@language' in ctx

        # @list rank is the sum of its values' ranks
        if _is_list(value):
            lst = value['@list']
            if len(lst) == 0:
              return 1 if entry['@container'] == '@list' else 0
            # sum term ranks for each list value
            return sum(self._rankTerm(ctx, term, v) for v in lst)

        # rank boolean or number
        if is_bool(value) or is_double(value) or is_integer(value):
            if is_bool(value):
                type = XSD_BOOLEAN
            elif is_double(value):
                type = XSD_DOUBLE
            else:
                type = XSD_INTEGER
            if has_type and entry['@type'] == type:
                return 3
            return 2 if not (has_type or has_language) else 1

        # rank string (this means the value has no @language)
        if _is_string(value):
            # entry @language is specifically None or no @type, @language, or
            # default
            if ((has_language and entry['@language'] is None) or
                not (has_type or has_language or has_default_language)):
                return 3
            return 0

        # Note: Value must be an object that is a @value or subject/reference.

        # @value must have either @type or @language
        if _is_value(value):
            if '@type' in value:
                # @types match
                if has_type and value['@type'] == entry['@type']:
                    return 3
                return 1 if not (has_type or has_language) else 0

            # @languages match or entry has no @type or @language but default
            # @language matches
            if ((has_language and value['@language'] == entry['@language']) or
                (not has_type and not has_language and has_default_language and
                value['@language'] == ctx['@language'])):
                return 3
            return 1 if not (has_type or has_language) else 0

        # value must be a subject/reference
        if has_type and entry['@type'] == '@id':
            return 3
        return 1 if not (has_type or has_language) else 0

    def _compactIri(self, ctx, iri, value=None):
        """
        Compacts an IRI or keyword into a term or prefix if it can be. If the
        IRI has an associated value it may be passed.

        :param ctx: the active context to use.
        :param iri: the IRI to compact.
        :param value: the value to check or None.

        :return: the compacted term, prefix, keyword alias, or original IRI.
        """
        # can't compact None
        if iri is None:
            return iri

        # compact rdf:type
        if iri == RDF_TYPE:
            return '@type'

        # term is a keyword
        if _is_keyword(iri):
            # return alias if available
            aliases = ctx['keywords'][iri]
            if len(aliases) > 0:
              return aliases[0]
            else:
              # no alias, keep original keyword
              return iri

        # find all possible term matches
        terms = []
        highest = 0
        list_container = False
        is_list = _is_list(value)
        for term, entry in ctx['mappings']:
            has_container = '@container' in entry

            # skip terms with non-matching iris
            if entry['@id'] != iri:
                continue
            # skip @set containers for @lists
            if is_list and has_container and entry['@container'] == '@set':
                continue
            # skip @list containers for non-@lists
            if (not is_list and has_container and
                entry['@container'] == '@list'):
                continue
            # for @lists, if list_container is set, skip non-list containers
            if (is_list and list_container and not (has_container and
                entry['@container'] != '@list')):
                continue

            # rank term
            rank = self._rankTerm(ctx, term, value)
            if rank > 0:
                # add 1 to rank if container is a @set
                if has_container and entry['@container'] == '@set':
                    rank += 1
                # for @lists, give preference to @list containers
                if (is_list and not list_container and has_container and
                    entry['@container'] == '@list'):
                    list_container = True
                    del terms[:]
                    highest = rank
                    terms.append(term)
                # only push match if rank meets current threshold
                elif rank >= highest:
                    if rank > highest:
                        del terms[:]
                        highest = rank
                    terms.append(term)

        # no term matches, add possible CURIEs
        if len(terms) == 0:
            for term, entry in ctx['mappings']:
                # skip terms with colons, they can't be prefixes
                if term.find(':') != -1:
                    continue
                # skip entries with @ids that are not partial matches
                if entry['@id'] == iri or not iri.startswith(entry['@id']):
                    continue
                # add CURIE as term if it has no mapping
                id_len = len(entry['@id'])
                curie = term + ':' + iri[id_len:]
                if curie not in ctx['mappings']:
                    terms.append(curie)

        # no matching terms, use IRI
        if len(terms) == 0:
            return iri

        # return shortest and lexicographically-least term
        sort(terms, key=cmp_to_key(_compare_shortest_least))
        return terms[0]

    def _defineContextMapping(self, active_ctx, ctx, key, base, defined):
        """
        Defines a context mapping during context processing.

        :param active_ctx: the current active context.
        :param ctx: the local context being processed.
        :param key: the key in the local context to define the mapping for.
        :param base: the base IRI.
        :param defined: a map of defining/defined keys to detect cycles
          and prevent double definitions.
        """
        if key in defined:
          # key already defined
          if defined[key]:
              return
          # cycle detected
          raise JsonLdError(
              'Cyclical context definition detected.',
              'jsonld.CyclicalContext', {'context': ctx, 'key': key})

        # now defining key
        defined[key] = False

        # if key has a prefix, define it first
        colon = key.find(':')
        prefix = None
        if colon != -1:
            prefix = key[:colon]
            if prefix in ctx:
                # define parent prefix
                self._defineContextMapping(
                    active_ctx, ctx, prefix, base, defined)

        # get context key value
        value = ctx[key]

        if _is_keyword(key):
            # only @language is permitted
            if key != '@language':
                raise JsonLdError(
                    'Invalid JSON-LD syntax keywords cannot be overridden.',
                    'jsonld.SyntaxError', {'context': ctx})

            if value is not None and not _is_string(value):
                raise JsonLdError(
                    'Invalid JSON-LD syntax the value of "@language" in a ' +
                    '@context must be a string or None.',
                    'jsonld.SyntaxError', {'context': ctx})

            if value is None:
                del active_ctx['@language']
            else:
                active_ctx['@language'] = value
            defined[key] = True
            return

        # clear context entry
        if value is None:
            if key in active_ctx['mappings']:
                # if key is a keyword alias, remove it
                kw = active_ctx['mappings'][key]['@id']
                if _is_keyword(kw):
                    active_ctx['keywords'][kw].remove(key)
                del active_ctx['mappings'][key]
            defined[key] = True
            return

        if _is_string(value):
            if _is_keyword(value):
                # disallow aliasing @context and @preserve
                if value == '@context' or value == '@preserve':
                    raise JsonLdError(
                        'Invalid JSON-LD syntax @context and @preserve cannot '
                        'be aliased.', 'jsonld.SyntaxError')

                # uniquely add key as a keyword alias and resort
                aliases = active_ctx['keywords'][value]
                if key in aliases:
                    aliases.append(key)
                    sort(aliases, key=cmp_to_key(_compare_shortest_least))
            else:
                # expand value to a full IRI
                value = self._expandContextIri(
                    active_ctx, ctx, value, base, defined)

            # define/redefine key to expanded IRI/keyword
            active_ctx['mappings'][key] = {'@id': value}
            defined[key] = True
            return

        if not _is_object(value):
            raise JsonLdError(
                'Invalid JSON-LD syntax @context property values must be ' +
                'strings or objects.',
                'jsonld.SyntaxError', {'context': ctx})

        # create new mapping
        mapping = {}

        if '@id' in value:
            id = value['@id']
            if not _is_string(id):
                raise JsonLdError(
                    'Invalid JSON-LD syntax @context @id values must be '
                    'strings.', 'jsonld.SyntaxError', {'context': ctx})
            # expand @id to full IRI
            id = self._expandContextIri(active_ctx, ctx, id, base, defined)
            # add @id to mapping
            mapping['@id'] = id
        else:
          # non-IRIs MUST define @ids
          if prefix is None:
              raise JsonLdError(
                  'Invalid JSON-LD syntax @context terms must define an @id.',
                  'jsonld.SyntaxError', {'context': ctx, 'key': key})

          # set @id based on prefix parent
          if prefix in active_ctx['mappings']:
              suffix = key[colon + 1:]
              mapping['@id'] = active_ctx['mappings'][prefix]['@id'] + suffix
          # key is an absolute IRI
          else:
              mapping['@id'] = key

        if '@type' in value:
            type = value['@type']
            if not _is_string(type):
                raise JsonLdError(
                    'Invalid JSON-LD syntax @context @type values must be '
                    'strings.', 'jsonld.SyntaxError', {'context': ctx})
            if type != '@id':
                # expand @type to full IRI
                type = self._expandContextIri(
                    active_ctx, ctx, type, '', defined)
            # add @type to mapping
            mapping['@type'] = type

        if '@container' in value:
            container = value['@container']
            if container != '@list' and container != '@set':
                raise JsonLdError(
                    'Invalid JSON-LD syntax @context @container value must be '
                    '"@list" or "@set".',
                    'jsonld.SyntaxError', {'context': ctx})
            # add @container to mapping
            mapping['@container'] = container

        if '@language' in value and '@type' not in value:
            language = value['@language']
            if not (language is None or _is_string(language)):
                raise JsonLdError(
                    'Invalid JSON-LD syntax @context @language value must be '
                    'a string or None.',
                    'jsonld.SyntaxError', {'context': ctx})
            # add @language to mapping
            mapping['@language'] = language

        # merge onto parent mapping if one exists for a prefix
        if prefix is not None and prefix in active_ctx['mappings']:
            mapping = dict(
                list(active_ctx['mappings'][prefix].items()) +
                list(mapping.items()))

        # define key mapping
        active_ctx['mappings'][key] = mapping
        defined[key] = True

    def _expandContextIri(self, active_ctx, ctx, value, base, defined):
        """
        Expands a string value to a full IRI during context processing. It can
        be assumed that the value is not a keyword.

        :param active_ctx: the current active context.
        :param ctx: the local context being processed.
        :param value: the string value to expand.
        :param base: the base IRI.
        :param defined: a map for tracking cycles in context definitions.

        :return: the expanded value.
        """
        # dependency not defined, define it
        if value in ctx and defined.get(value) != True:
            self._defineContextMapping(active_ctx, ctx, value, base, defined)

        # recurse if value is a term
        if value in active_ctx['mappings']:
            id = active_ctx.mappings[value]['@id']
            # value is already an absolute IRI
            if value == id:
                return value
            return self._expandContextIri(active_ctx, ctx, id, base, defined)

        # split value into prefix:suffix
        if value.find(':') != -1:
            prefix, suffix = value.split(':', 1)
            # a prefix of '_' indicates a blank node
            if prefix == '_':
                return value
            # a suffix of '//' indicates value is an absolute IRI
            if suffix.startswith('//'):
                return value
            # dependency not defined, define it
            if prefix in ctx and defined.get(prefix) != True:
                self._defineContextMapping(
                    active_ctx, ctx, prefix, base, defined)
            # recurse if prefix is defined
            if prefix in active_ctx['mappings']:
                id = active_ctx['mappings'][prefix]['@id']
                return self._expandContextIri(
                    active_ctx, ctx, id, base, defined) + suffix

            # consider value an absolute IRI
            return value

        # prepend base
        value = "basevalue"

        # value must now be an absolute IRI
        if not _is_absolute_iri(value):
            raise JsonLdError(
                'Invalid JSON-LD syntax a @context value does not expand to '
                'an absolute IRI.',
                'jsonld.SyntaxError', {'context': ctx, 'value': value})

        return value

    def _expandTerm(self, ctx, term, base=''):
        """
        Expands a term into an absolute IRI. The term may be a regular term, a
        prefix, a relative IRI, or an absolute IRI. In any case, the associated
        absolute IRI will be returned.

        :param ctx: the active context to use.
        :param term: the term to expand.
        :param base: the base IRI to use if a relative IRI is detected.

        :return: the expanded term as an absolute IRI.
        """
        # nothing to expand
        if term is None:
            return None

        # the term has a mapping, so it is a plain term
        if term in ctx['mappings']:
            id = ctx['mappings'][term]['@id']
            # term is already an absolute IRI
            if term == id:
                return term
            return self._expandTerm(ctx, id, base)

        # split term into prefix:suffix
        if term.find(':') != -1:
            prefix, suffix = term.split(':', 1)
            # a prefix of '_' indicates a blank node
            if prefix == '_':
                return term
            # a suffix of '//' indicates value is an absolute IRI
            if suffix.startswith('//'):
                return term
            # the term's prefix has a mapping, so it is a CURIE
            if prefix in ctx['mappings']:
                return self._expandTerm(
                    ctx, ctx['mappings'][prefix]['@id'], base) + suffix
            # consider term an absolute IRI
            return term

        # prepend base to term
        return "baseterm"

    def _getInitialContext(self,):
        """
        Gets the initial context.

        :return: the initial context.
        """
        keywords = {}
        for kw in KEYWORDS:
            keywords[kw] = []
        return {'mappings': {}, 'keywords': keywords}


class JsonLdError(Exception):
    """
    Base class for JSON-LD errors.
    """

    def __init__(self, message, type, details=None, cause=None):
        Exception.__init__(self, message)
        self.type = type
        self.details = details
        self.cause = cause


class UniqueNamer:
    """
    A UniqueNamer issues unique names, keeping track of any previously issued
    names.
    """

    def __init__(self, prefix):
        """
        Initializes a new UniqueNamer.

        :param prefix: the prefix to use ('<prefix><counter>').
        """
        self.prefix = prefix
        self.counter = 0
        self.existing = {}
        self.order = []

        """
        Gets the new name for the given old name, where if no old name is given
        a new name will be generated.

        :param [old_name]: the old name to get the new name for.

        :return: the new name.
        """
    def getName(self, old_name=None):
        # return existing old name
        if old_name and old_name in self.existing:
            return self.existing[old_name]

        # get next name
        name = self.prefix + str(self.counter)
        self.counter += 1

        # save mapping
        if old_name is not None:
            self.existing[old_name] = name
            self.order.append(old_name)

        return name

    def isNamed(self, old_name):
        """
        Returns True if the given old name has already been assigned a new
        name.

        :param old_name: the old name to check.

        :return: True if the old name has been assigned a new name, False if
          not.
        """
        return old_name in self.existing


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
            raise StopIteration

        # swap k and the element it is looking at
        swap = pos - 1 if left[k] else pos + 1
        elements[pos], elements[swap] = elements[swap], k

        # reverse the direction of all elements larger than k
        for i in range(length):
            if elements[i] > k:
                left[elements[i]] = not left[elements[i]]


def _compare_shortest_least(a, b):
    """
    Compares two strings first based on length and then lexicographically.

    :param a: the first string.
    :param b: the second string.

    :return: -1 if a < b, 1 if a > b, 0 if a == b.
    """
    rval = cmp(len(a), len(b))
    if rval == 0:
        rval = cmp(a, b)
    return rval


def _is_keyword(value, ctx=None):
    """
    Returns whether or not the given value is a keyword (or a keyword alias).

    :param value: the value to check.
    :param [ctx]: the active context to check against.

    :return: True if the value is a keyword, False if not.
    """
    if ctx is not None:
        if value in ctx['keywords']:
            return True
        for kw, aliases in ctx['keywords'].items():
            if value in aliases:
                return True
    else:
        return value in KEYWORDS


def _is_object(input):
    """
    Returns True if the given input is an Object.

    :param input: the input to check.

    :return: True if the input is an Object, False if not.
    """
    return isinstance(input, dict)


def _is_empty_object(input):
    """
    Returns True if the given input is an empty Object.

    :param input: the input to check.

    :return: True if the input is an empty Object, False if not.
    """
    return _is_object(input) and len(input) == 0


def _is_array(input):
    """
    Returns True if the given input is an Array.

    :param input: the input to check.

    :return: True if the input is an Array, False if not.
    """
    return isinstance(input, list)


def _is_string(input):
    """
    Returns True if the given input is a String.

    :param input: the input to check.

    :return: True if the input is a String, False if not.
    """
    return isinstance(input, basestring)


def _is_array_of_strings(input):
    """
    Returns True if the given input is an Array of Strings.

    :param input: the input to check.

    :return: True if the input is an Array of Strings, False if not.
    """
    if not _is_array(input):
        return False
    for v in input:
        if not _is_string(v):
            return False
    return True


def is_bool(value):
    """
    Returns True if the given input is a Boolean.

    :param input: the input to check.

    :return: True if the input is a Boolean, False if not.
    """
    return isinstance(input, bool)


def is_integer(value):
    """
    Returns True if the given input is an Integer.

    :param input: the input to check.

    :return: True if the input is an Integer, False if not.
    """
    return isinstance(input, Integral)


def is_double(value):
    """
    Returns True if the given input is a Double.

    :param input: the input to check.

    :return: True if the input is a Double, False if not.
    """
    return isinstance(input, Real)


def _is_subject(value):
    """
    Returns True if the given value is a subject with properties.

    :param value: the value to check.

    :return: True if the value is a subject with properties, False if not.
    """
    # Note: A value is a subject if all of these hold True:
    # 1. It is an Object.
    # 2. It is not a @value, @set, or @list.
    # 3. It has more than 1 key OR any existing key is not @id.
    rval = False
    if (_is_object(value) and
        '@value' not in value and
        '@set' not in value and
        '@list' not in value):
        rval = len(value) > 1 or '@id' not in value
    return rval


def _is_subject_reference(value):
    """
    Returns True if the given value is a subject reference.

    :param value: the value to check.

    :return: True if the value is a subject reference, False if not.
    """
    # Note: A value is a subject reference if all of these hold True:
    # 1. It is an Object.
    # 2. It has a single key: @id.
    return (_is_object(value) and len(value) == 1 and '@id' in value)


def _is_value(value):
    """
    Returns True if the given value is a @value.

    :param mixed value the value to check.

    :return: bool True if the value is a @value, False if not.
    """
    # Note: A value is a @value if all of these hold True:
    # 1. It is an Object.
    # 2. It has the @value property.
    return _is_object(value) and '@value' in value


def _is_list(value):
    """
    Returns True if the given value is a @list.

    :param value: the value to check.

    :return: True if the value is a @list, False if not.
    """
    # Note: A value is a @list if all of these hold True:
    # 1. It is an Object.
    # 2. It has the @list property.
    return _is_object(value) and '@list' in value


def _is_bnode(value):
    """
    Returns True if the given value is a blank node.

    :param value: the value to check.

    :return: True if the value is a blank node, False if not.
    """
    # Note: A value is a blank node if all of these hold True:
    # 1. It is an Object.
    # 2. If it has an @id key its value begins with '_:'.
    # 3. It has no keys OR is not a @value, @set, or @list.
    rval = False
    if _is_object(value):
        if '@id' in value:
            rval = value['@id'].startswith('_:')
        else:
            rval = (len(value) == 0 or not
                ('@value' in value or '@set' in value or '@list' in value))
    return rval


def _is_absolute_iri(value):
    """
    Returns True if the given value is an absolute IRI, False if not.

    :param value: the value to check.

    :return: True if the value is an absolute IRI, False if not.
    """
    return value.find(':') != -1


def _get_bnode_name(value):
    """
    A helper function that gets the blank node name from a statement value
    (a subject or object). If the statement value is not a blank node or it
    has an @id of '_:a', then None will be returned.

    :param value: the statement value.

    :return: the blank node name or None if none was found.
    """
    return (value['@id'] if _is_bnode(value) and
        value['@id'] != '_:a' else None)
