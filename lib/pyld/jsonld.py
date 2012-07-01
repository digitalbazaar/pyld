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

__all__ = ['compact', 'expand', 'frame', 'normalize', 'from_rdf', 'to_rdf',
    'set_url_resolver', 'resolve_url',
    'register_rdf_parser', 'unregister_rdf_parser',
    'JsonLdProcessor', 'ContextCache']

import copy, hashlib, json, os, re, string, sys, time, traceback
import urllib2, urlparse
from contextlib import closing
from functools import cmp_to_key
from numbers import Integral, Real
from httplib import HTTPSConnection

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

# Restraints
MAX_CONTEXT_URLS = 10


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


def from_rdf(input, options=None):
    """
    Converts RDF statements into JSON-LD.

    :param statements: a serialized string of RDF statements in a format
      specified by the format option or an array of the RDF statements
      to convert.
    :param [options]: the options to use:
      [format] the format if input is not an array:
        'application/nquads' for N-Quads (default).
      [notType] true to use rdf:type, false to use @type (default).

    :return: the JSON-LD output.
    """
    return JsonLdProcessor().from_rdf(input, options)

def to_rdf(input, options=None):
    """
    Outputs the RDF statements found in the given JSON-LD object.

    :param input: the JSON-LD object.
    :param [options]: the options to use.
      [base] the base IRI to use.
      [format] the format to use to output a string:
        'application/nquads' for N-Quads (default).

    :return: all RDF statements in the JSON-LD object.
    """
    return JsonLdProcessor().to_rdf(input, options)


def set_url_resolver(resolver):
    """
    Sets the default JSON-LD URL resolver.

    :param resolver(url): the URL resolver to use.
    """
    _default_url_resolver = resolver


def resolve_url(url):
    """
    Retrieves JSON-LD as the given URL.

    :param url: the URL to resolve.

    :return: the JSON-LD.
    """
    global _default_url_resolver
    global _context_cache
    if (_default_url_resolver is None or
        _default_url_resolver == resolve_url):
        # create context cache as needed
        if _context_cache is None:
            _context_cache = ContextCache()

        # default JSON-LD GET implementation
        ctx = _context_cache.get(url)
        if ctx is None:
            https_handler = VerifiedHTTPSHandler()
            url_opener = urllib2.build_opener(https_handler)
            with closing(url_opener.open(url)) as handle:
                ctx = handle.read()
                _context_cache.set(url, ctx)
        return ctx
    return _default_url_resolver(url)


# The default JSON-LD URL resolver and cache.
_default_url_resolver = resolve_url
_context_cache = None


# Registered global RDF Statement parsers hashed by content-type.
_rdf_parsers = {}


def register_rdf_parser(content_type, parser):
    """
    Registers a global RDF Statement parser by content-type, for use with
    jsonld_from_rdf. Global parsers will be used by JsonLdProcessors that
    do not register their own parsers.

    :param content_type: the content-type for the parser.
    :param parser(input): the parser function (takes a string as
             a parameter and returns an array of RDF statements).
    """
    global _rdf_parsers
    _rdf_parsers[content_type] = parser


def unregister_rdf_parser(content_type):
    """
    Unregisters a global RDF Statement parser by content-type.

    :param content_type: the content-type for the parser.
    """
    global _rdf_parsers
    if content_type in _rdf_parsers:
        del _rdf_parsers[content_type]


class JsonLdProcessor:
    """
    A JSON-LD processor.
    """

    def __init__(self):
        """
        Initialize the JSON-LD processor.
        """
        # processor-specific RDF statement parsers
        self.rdf_parsers = None

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
        options.setdefault('resolver', _default_url_resolver)

        # expand input
        try:
            expanded = self.expand(input, options)
        except JsonLdError as cause:
            raise JsonLdError('Could not expand input before compaction.',
                'jsonld.CompactError', None, cause)

        # process context
        active_ctx = self._get_initial_context()
        try:
            active_ctx = self.process_context(active_ctx, ctx, options)
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
                kwgraph = self._compact_iri(active_ctx, '@graph')
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
                for k, v in graph.items():
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
        options.setdefault('resolver', _default_url_resolver)

        # resolve all @context URLs in the input
        input = copy.deepcopy(input)
        try:
            self._resolve_context_urls(input, {}, options['resolver'])
        except Exception as cause:
            raise JsonLdError(
                'Could not perform JSON-LD expansion.',
                'jsonld.ExpandError', None, cause)

        # do expansion
        ctx = self._get_initial_context()
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
        options.setdefault('resolver', _default_url_resolver)

        # preserve frame context
        ctx = frame.get('@context', {})

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
        graph = self._compact_iri(ctx, '@graph')
        # remove @preserve from results
        compacted[graph] = self._remove_preserve(ctx, compacted[graph])
        return compacted

    def normalize(self, input, options):
        """
        Performs RDF normalization on the given JSON-LD input. The
        output is a sorted array of RDF statements unless the 'format'
        option is used.

        :param input: the JSON-LD object to normalize.
        :param options: the options to use.
          [base] the base IRI to use.
          [format] the format if output is a string:
            'application/nquads' for N-Quads.

        :return: the normalized output.
        """
        # set default options
        options = options or {}
        options.setdefault('base', '')
        options.setdefault('resolver', _default_url_resolver)

        try:
            # expand input then do normalization
            expanded = self.expand(input, options)
        except JsonLdError as cause:
            raise JsonLdError('Could not expand input before normalization.',
                'jsonld.NormalizeError', None, cause)

        # do normalization
        return self._normalize(expanded, options)

    def from_rdf(self, statements, options):
        """
        Converts RDF statements into JSON-LD.
        
        :param statements: a serialized string of RDF statements in a format
          specified by the format option or an array of the RDF statements
          to convert.
        :param options: the options to use.
        
        :return: the JSON-LD output.
        """
        global _rdf_parsers

        # set default options
        options = options or {}
        options.setdefault('format', 'application/nquads')
        options.setdefault('notType', False)

        if not _is_array(statements):
            # supported formats (processor-specific and global)
            if ((self.rdf_parsers is not None and
                not options['format'] in self.rdf_parsers) or
                (self.rdf_parsers is None and
                not options['format'] in _rdf_parsers)):
                raise JsonLdError('Unknown input format.',
                    'jsonld.UnknownFormat', {'format': options['format']})

            if self.rdf_parsers is not None:
                parser = self.rdf_parsers[options['format']]
            else:
                parser = _rdf_parsers[options['format']]
            statements = parser(statements)

        # convert from RDF
        return self._from_rdf(statements, options)

    def to_rdf(self, input, options):
        """
        Outputs the RDF statements found in the given JSON-LD object.

        :param input: the JSON-LD object.
        :param options: the options to use.

        :return: the RDF statements.
        """
        # set default options
        options = options or {}
        options.setdefault('base', '')
        options.setdefault('resolver', _default_url_resolver)

        try:
            # expand input
            expanded = self.expand(input, options)
        except JsonLdError as cause:
            raise JsonLdError('Could not expand input before conversion to '
                'RDF.', 'jsonld.RdfError', None, cause)

        # get RDF statements
        namer = UniqueNamer('_:t')
        statements = []
        self._to_rdf(expanded, namer, None, None, None, statements)

        # convert to output format
        if 'format' in options:
            if options['format'] == 'application/nquads':
                nquads = []
                for statement in statements:
                    nquads.append(JsonLdProcessor.to_nquad(statement))
                nquads.sort()
                statements = ''.join(nquads)
            else:
                raise JsonLdError('Unknown output format.',
                    'jsonld.UnknownFormat', {'format': options['format']})

        # output RDF statements
        return statements

    def process_context(self, active_ctx, local_ctx, options):
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
            return self._get_initial_context()

        # set default options
        options = options or {}
        options.setdefault('base', '')
        options.setdefault('resolver', _default_url_resolver)

        # resolve URLs in local_ctx
        ctx = copy.deepcopy(local_ctx)
        if _is_object(ctx) and '@context' not in ctx:
            ctx = {'@context': ctx}
        try:
            self._resolve_context_urls(ctx, {}, options['resolver'])
        except Exception as cause:
            raise JsonLdError(
                'Could not process JSON-LD context.',
                'jsonld.ContextError', None, cause)

        # process context
        return self._process_context(active_ctx, ctx, options)

    def register_rdf_parser(self, content_type, parser):
        """
        Registers a processor-specific RDF Statement parser by content-type.
        Global parsers will no longer be used by this processor.
    
        :param content_type: the content-type for the parser.
        :param parser(input): the parser function (takes a string as
                 a parameter and returns an array of RDF statements).
        """
        if self.rdf_parsers is None:
            self.rdf_parsers = {}
            self.rdf_parsers[content_type] = parser

    def unregister_rdf_parser(self, content_type):
        """
        Unregisters a process-specific RDF Statement parser by content-type.
        If there are no remaining processor-specific parsers, then the global
        parsers will be re-enabled.
    
        :param content_type: the content-type for the parser.
        """
        if (self.rdf_parsers is not None and
            content_type in self.rdf_parsers):
            del self.rdf_parsers[content_type]
            if len(self.rdf_parsers) == 0:
                self.rdf_parsers = None

    @staticmethod
    def has_property(subject, property):
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
    def has_value(subject, property, value):
        """
         Determines if the given value is a property of the given subject.

        :param subject: the subject to check.
        :param property: the property to check.
        :param value: the value to check.

        :return: True if the value exists, False if not.
        """
        rval = False
        if JsonLdProcessor.has_property(subject, property):
            val = subject[property]
            is_list = _is_list(val)
            if _is_array(val) or is_list:
                if is_list:
                    val = val['@list']
                for v in val:
                    if JsonLdProcessor.compare_values(value, v):
                        rval = True
                        break
            # avoid matching the set of values with an array value parameter
            elif not _is_array(value):
                rval = JsonLdProcessor.compare_values(value, val)
        return rval

    @staticmethod
    def add_value(subject, property, value, options={}):
        """
        Adds a value to a subject. If the value is an array, all values in the
        array will be added.

        :param subject: the subject to add the value to.
        :param property: the property that relates the value to the subject.
        :param value: the value to add.
        :param [options]: the options to use:
          [propertyIsArray] True if the property is always
            an array, False if not (default: False).
          [allowDuplicate] True to allow duplicates, False not to (uses
            a simple shallow comparison of subject ID or value)
            (default: True).
        """
        options.setdefault('propertyIsArray', False)
        options.setdefault('allowDuplicate', True)

        if _is_array(value):
            if (len(value) == 0 and options['propertyIsArray'] and
                property not in subject):
                subject[property] = []
            for v in value:
                JsonLdProcessor.add_value(subject, property, v, options)
        elif property in subject:
            # check if subject already has value if duplicates not allowed
            has_value = (not options['allowDuplicate'] and
                JsonLdProcessor.has_value(subject, property, value))

            # make property an array if value not present or always an array
            if (not _is_array(subject[property]) and
                (not has_value or options['propertyIsArray'])):
                subject[property] = [subject[property]]

            # add new value
            if not has_value:
                subject[property].append(value)
        else:
            # add new value as set or single value
            subject[property] = (
                [value] if options['propertyIsArray'] else value)

    @staticmethod
    def get_values(subject, property):
        """
        Gets all of the values for a subject's property as an array.

        :param subject: the subject.
        :param property: the property.

        :return: all of the values for a subject's property as an array.
        """
        return JsonLdProcessor.arrayify(subject[property] or [])

    @staticmethod
    def remove_property(subject, property):
        """
        Removes a property from a subject.

        :param subject: the subject.
        :param property: the property.
        """
        del subject[property]

    @staticmethod
    def remove_value(subject, property, value, options={}):
        """
        Removes a value from a subject.

        :param subject: the subject.
        :param property: the property that relates the value to the subject.
        :param value: the value to remove.
        :param [options]: the options to use:
          [propertyIsArray]: True if the property is always an array,
            False if not (default: False).
        """
        options.setdefault('propertyIsArray', False)

        # filter out value
        def filter_value(e):
            return not JsonLdProcessor.compare_values(e, value)
        values = JsonLdProcessor.get_values(subject, property)
        values = filter(filter_value, values)

        if len(values) == 0:
            JsonLdProcessor.remove_property(subject, property)
        elif len(values) == 1 and not options['propertyIsArray']:
            subject[property] = values[0]
        else:
            subject[property] = values

    @staticmethod
    def compare_values(v1, v2):
        """
        Compares two JSON-LD values for equality. Two JSON-LD values will be
        considered equal if:

        1. They are both primitives of the same type and value.
        2. They are both @values with the same @value, @type, @language, OR
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
    def get_context_value(ctx, key, type):
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
    def parse_nquads(input):
        """
        Parses statements in the form of N-Quads.

        :param input: the N-Quads input to parse.

        :return: an array of RDF statements.
        """
        # define partial regexes
        iri = '(?:<([^:]+:[^>]*)>)'
        bnode = '(_:(?:[A-Za-z][A-Za-z0-9]*))'
        plain = '"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)"'
        datatype = '(?:\\^\\^' + iri + ')'
        language = '(?:@([a-z]+(?:-[a-z0-9]+)*))'
        literal = '(?:' + plain + '(?:' + datatype + '|' + language + ')?)'
        ws = '[ \\t]+'
        wso = '[ \\t]*'
        eoln = r'(?:\r\n)|(?:\n)|(?:\r)/g'
        empty = r'^' + wso + '$'

        # define quad part regexes
        subject = '(?:' + iri + '|' + bnode + ')' + ws
        property = iri + ws
        object = '(?:' + iri + '|' + bnode + '|' + literal + ')' + wso
        graph = '(?:\\.|(?:(?:' + iri + '|' + bnode + ')' + wso + '\\.))'

        # full quad regex
        quad = r'^' + wso + subject + property + object + graph + wso + '$'

        # build RDF statements
        statements = []

        # split N-Quad input into lines
        lines = re.split(eoln, input)
        line_number = 0
        for line in lines:
            line_number += 1

            # skip empty lines
            if re.match(empty, line) is not None:
                continue

            # parse quad
            match = re.match(quad, line)
            if match is None:
                raise JsonLdError(
                    'Error while parsing N-Quads invalid quad.',
                    'jsonld.ParseError', {'line': lineNumber})
            match = match.groups()

            # create RDF statement
            s = {}

            # get subject
            if match[0] is not None:
                s['subject'] = {
                    'nominalValue': match[0], 'interfaceName': 'IRI'}
            else:
                s['subject'] = {
                    'nominalValue': match[1], 'interfaceName': 'BlankNode'}

            # get property
            s['property'] = {'nominalValue': match[2], 'interfaceName': 'IRI'}

            # get object
            if match[3] is not None:
                s['object'] = {
                    'nominalValue': match[3], 'interfaceName': 'IRI'}
            elif match[4] is not None:
                s['object'] = {
                    'nominalValue': match[4], 'interfaceName': 'BlankNode'}
            else:
                unescaped = (match[5]
                    .replace('\\"', '\"')
                    .replace('\\t', '\t')
                    .replace('\\n', '\n')
                    .replace('\\r', '\r')
                    .replace('\\\\', '\\'))
                s['object'] = {
                    'nominalValue': unescaped, 'interfaceName': 'LiteralNode'}
                if match[6] is not None:
                    s['object']['datatype'] = {
                        'nominalValue': match[6], 'interfaceName': 'IRI'}
                elif match[7] is not None:
                    s['object']['language'] = match[7]

            # get graph
            if match[8] is not None:
                s['name'] = {'nominalValue': match[8], 'interfaceName': 'IRI'}
            elif match[9] is not None:
                s['name'] = {
                    'nominalValue': match[9], 'interfaceName': 'BlankNode'}

            # add statement
            JsonLdProcessor._append_unique_rdf_statement(statements, s)

        return statements

    @staticmethod
    def to_nquad(statement, bnode=None):
        """
        Converts an RDF statement to an N-Quad string (a single quad).

        :param statement: the RDF statement to convert.
        :param bnode: the bnode the statement is mapped to (optional, for
          use during normalization only).

        :return: the N-Quad string.
        """
        s = statement['subject']
        p = statement['property']
        o = statement['object']
        g = statement.get('name')

        quad = ''

        # subject is an IRI or bnode
        if s['interfaceName'] == 'IRI':
            quad += '<' + s['nominalValue'] + '>'
        # normalization mode
        elif bnode is not None:
            quad += '_:a' if s['nominalValue'] == bnode else '_:z'
        # normal mode
        else:
            quad += s['nominalValue']

        # property is always an IRI
        quad += ' <' + p['nominalValue'] + '> '

        # object is IRI, bnode, or literal
        if o['interfaceName'] == 'IRI':
            quad += '<' + o['nominalValue'] + '>'
        elif(o['interfaceName'] == 'BlankNode'):
            # normalization mode
            if bnode is not None:
                quad += '_:a' if o['nominalValue'] == bnode else '_:z'
            # normal mode
            else:
                quad += o['nominalValue']
        else:
            escaped = (o['nominalValue']
                .replace('\\', '\\\\')
                .replace('\t', '\\t')
                .replace('\n', '\\n')
                .replace('\r', '\\r')
                .replace('\"', '\\"'))
            quad += '"' + o['nominalValue'] + '"'
            if 'datatype' in o:
                quad += '^^<' + o['datatype']['nominalValue'] + '>'
            elif 'language' in o:
                quad += '@' + o['language']

        # graph
        if g is not None:
            if g['interfaceName'] == 'IRI':
                quad += ' <' + g['nominalValue'] + '>'
            elif bnode is not None:
                quad += ' _:g'
            else:
                quad += ' ' + g['nominalValue']

        quad += ' .\n'
        return quad

    @staticmethod
    def arrayify(value):
        """
        If value is an array, returns value, otherwise returns an array
        containing value as the only element.

        :param value: the value.

        :return: an array.
        """
        return value if _is_array(value) else [value]

    @staticmethod
    def _compare_rdf_statements(s1, s2):
        """
        Compares two RDF statements for equality.
        
        :param s1: the first statement.
        :param s2: the second statement.
        
        :return: true if the statements are the same, false if not.
        """
        if _is_string(s1) or _is_string(s2):
            return s1 == s2

        for attr in ['subject', 'property', 'object']:
            if(s1[attr]['interfaceName'] != s2[attr]['interfaceName'] or
                s1[attr]['nominalValue'] != s2[attr]['nominalValue']):
                return False

        if s1['object'].get('language') != s2['object'].get('language'):
            return False
        if ('datatype' in s1['object']) != ('datatype' in s2['object']):
            return False
        if 'datatype' in s1['object']:
            if(s1['object']['datatype']['interfaceName'] !=
                s2['object']['datatype']['interfaceName'] or
                s1['object']['datatype']['nominalValue'] !=
                s2['object']['datatype']['nominalValue']):
                return False
        if 'name' in s1 != 'name' in s2:
            return False
        if 'name' in s1:
            if s1['name'] != s2['name']:
                return False
        return True

    @staticmethod
    def _append_unique_rdf_statement(statements, statement):
        """
        Appends an RDF statement to the given array of statements if it is
        unique.
        
        :param statements: the array to add to.
        :param statement: the statement to add.
        """
        for s in statements:
            if JsonLdProcessor._compare_rdf_statements(s, statement):
                return
        statements.append(statement)

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
                container = JsonLdProcessor.get_context_value(
                    ctx, property, '@container')
                if container != '@list' and container != '@set':
                    rval = rval[0]
            return rval

        # recursively compact object
        if _is_object(element):
            # element is a @value
            if _is_value(element):
                # if @value is the only key
                if len(element) == 1:
                    # if there is no default language or @value is not a
                    # string, return value of @value
                    if ('@language' not in ctx or
                        not _is_string(element['@value'])):
                        return element['@value']
                    # return full element, alias @value
                    rval = {}
                    rval[self._compact_iri(ctx, '@value')] = element['@value']
                    return rval

                # get type and language context rules
                type = JsonLdProcessor.get_context_value(
                    ctx, property, '@type')
                language = JsonLdProcessor.get_context_value(
                    ctx, property, '@language')

                # matching @type specified in context, compact element
                if (type != None and
                    '@type' in element and element['@type'] == type):
                    return element['@value']
                # matching @language specified in context, compact element
                elif(language is not None and
                     '@language' in element and
                     element['@language'] == language):
                    return element['@value']
                else:
                    rval = {}
                    # compact @type IRI
                    if '@type' in element:
                        rval[self._compact_iri(ctx, '@type')] = (
                            self._compact_iri(ctx, element['@type']))
                    elif '@language' in element:
                        rval[self._compact_iri(ctx, '@language')] = (
                            element['@language'])
                    rval[self._compact_iri(ctx, '@value')] = element['@value']
                    return rval

            # compact subject references
            if _is_subject_reference(element):
                type = JsonLdProcessor.get_context_value(
                    ctx, property, '@type')
                if type == '@id' or property == '@graph':
                    return self._compact_iri(ctx, element['@id'])

            # recursively process element keys
            rval = {}
            for key, value in element.items():
                # compact @id and @type(s)
                if key == '@id' or key == '@type':
                    # compact single @id
                    if _is_string(value):
                        value = self._compact_iri(ctx, value)
                    # value must be a @type array
                    else:
                        types = []
                        for v in value:
                            types.append(self._compact_iri(ctx, v))
                        value = types

                    # compact property and add value
                    prop = self._compact_iri(ctx, key)
                    is_array = (_is_array(value) and len(value) == 0)
                    JsonLdProcessor.add_value(
                        rval, prop, value, {'propertyIsArray': is_array})
                    continue

                # Note: value must be an array due to expansion algorithm.

                # preserve empty arrays
                if len(value) == 0:
                    prop = self._compact_iri(ctx, key)
                    JsonLdProcessor.add_value(
                        rval, prop, [], {'propertyIsArray': True})

                # recusively process array values
                for v in value:
                    is_list = _is_list(v)

                    # compact property
                    prop = self._compact_iri(ctx, key, v)

                    # remove @list for recursion (will re-add if necessary)
                    if is_list:
                        v = v['@list']

                    # recursively compact value
                    v = self._compact(ctx, prop, v, options)

                    # get container type for property
                    container = JsonLdProcessor.get_context_value(
                        ctx, prop, '@container')

                    # handle @list
                    if is_list and container != '@list':
                        # handle messy @list compaction
                        if prop in rval and options['strict']:
                            raise JsonLdError(
                                'JSON-LD compact error property has a '
                                '"@list" @container rule but there is more '
                                'than a single @list that matches the '
                                'compacted term in the document. Compaction '
                                'might mix unwanted items into the list.',
                                'jsonld.SyntaxError')
                        # reintroduce @list keyword
                        kwlist = self._compact_iri(ctx, '@list')
                        v = {kwlist: v}

                    # if @container is @set or @list or value is an empty
                    # array, use an array when adding value
                    is_array = (container == '@set' or container == '@list' or
                      (_is_array(v) and len(v) == 0))

                    # add compact value
                    JsonLdProcessor.add_value(
                        rval, prop, v, {'propertyIsArray': is_array})

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
            return self._expand_value(ctx, property, element, options['base'])

        # Note: element must be an object, recursively expand it

        # if element has a context, process it
        if '@context' in element:
            ctx = self._process_context(ctx, element['@context'], options)
            del element['@context']

        rval = {}
        for key, value in element.items():
            # expand property
            prop = self._expand_term(ctx, key)

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

            # validate @type value
            if prop == '@type':
                _validate_type_value(value)

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

            # recurse into @list or @set keeping active property
            is_list = (prop == '@list')
            if is_list or prop == '@set':
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
                    container = JsonLdProcessor.get_context_value(
                        ctx, property, '@container')
                    if container == '@list':
                        # ensure value is an array
                        value = {'@list': JsonLdProcessor.arrayify(value)}

                # optimize away @id for @type
                if prop == '@type':
                    if _is_subject_reference(value):
                        value = value['@id']
                    elif _is_array(value):
                        val = []
                        for v in value:
                          if _is_subject_reference(v):
                            val.append(v['@id'])
                          else:
                            val.append(v)
                        value = val

                # add value, use an array if not @id, @type, @value, or
                # @language
                use_array = not (prop == '@id' or prop == '@type' or
                    prop == '@value' or prop == '@language')
                JsonLdProcessor.add_value(
                    rval, prop, value, {'propertyIsArray': use_array})

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
        state = {
            'options': options,
            'graphs': {'@default': {}, '@merged': {}}
        }

        # produce a map of all graphs and name each bnode
        namer = UniqueNamer('_:t')
        self._flatten(input, state['graphs'], '@default', namer, None, None)
        namer = UniqueNamer('_:t')
        self._flatten(input, state['graphs'], '@merged', namer, None, None)
        # FIXME: currently uses subjects from @merged graph only
        state['subjects'] = state['graphs']['@merged']

        # frame the subjects
        framed = []
        self._match_frame(
            state, state['subjects'].keys(), frame, framed, None)
        return framed

    def _normalize(self, input, options):
        """
        Performs RDF normalization on the given JSON-LD input.

        :param input: the expanded JSON-LD object to normalize.
        :param options: the normalization options.

        :return: the normalized output.
        """
        # map bnodes to RDF statements
        statements = []
        bnodes = {}
        namer = UniqueNamer('_:t')
        self._to_rdf(input, namer, None, None, None, statements)
        for statement in statements:
            for node in ['subject', 'object']:
                id = statement[node]['nominalValue']
                if statement[node]['interfaceName'] == 'BlankNode':
                    if id in bnodes:
                        bnodes[id]['statements'].append(statement)
                    else:
                        bnodes[id] = {'statements': [statement]}

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
                hash = self._hash_statements(bnode, bnodes, namer)

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
                namer.get_name(bnode)

            # done when no more bnodes named
            if len(unnamed) == len(nextUnnamed):
                break

        # enumerate duplicate hash groups in sorted order
        for hash, group in sorted(duplicates.items()):
            # process group
            results = []
            for bnode in group:
                # skip already-named bnodes
                if namer.is_named(bnode):
                  continue

                # hash bnode paths
                path_namer = UniqueNamer('_:t')
                path_namer.get_name(bnode)
                results.append(self._hash_paths(
                  bnode, bnodes, namer, path_namer))

            # name bnodes in hash order
            cmp_hashes = cmp_to_key(lambda x, y: cmp(x['hash'], y['hash']))
            for result in sorted(results, key=cmp_hashes):
                # name all bnodes in path namer in key-entry order
                for bnode in result['pathNamer'].order:
                    namer.get_name(bnode)

        # create normalized array
        normalized = []

        # update bnode names in each statement and serialize
        for statement in statements:
            for node in ['subject', 'object']:
                if statement[node]['interfaceName'] == 'BlankNode':
                    statement[node]['nominalValue'] = namer.get_name(
                        statement[node]['nominalValue'])
            normalized.append(JsonLdProcessor.to_nquad(statement))

        # sort normalized output
        normalized.sort()

        # handle output format
        if 'format' in options:
            if options['format'] == 'application/nquads':
                return ''.join(normalized)
            else:
                raise JsonLdError('Unknown output format.',
                    'jsonld.UnknownFormat', {'format': options['format']})

        # return parsed RDF statements
        return JsonLdProcessor.parse_nquads(''.join(normalized))

    def _from_rdf(self, statements, options):
        """
        Converts RDF statements into JSON-LD.
        
        :param statements: the RDF statements.
        :param options: the RDF conversion options.
        
        :return: the JSON-LD output.
        """
        # prepare graph map (maps graph name => subjects, lists)
        default_graph = {'subjects': {}, 'listMap': {}}
        graphs = {'': default_graph}

        for statement in statements:
            # get subject, property, object, and graph name (default to '')
            s = statement['subject']['nominalValue']
            p = statement['property']['nominalValue']
            o = statement['object']
            name = statement.get('name', {'nominalValue': ''})['nominalValue']

            # create a graph entry as needed
            graph = graphs.setdefault(name, {'subjects': {}, 'listMap': {}})

            # handle element in @list
            if p == RDF_FIRST:
                # create list entry as needed
                list_map = graph['listMap']
                entry = list_map.setdefault(s, {})
                # set object value
                entry['first'] = self._rdf_to_object(o)
                continue

            # handle other element in @list
            if p == RDF_REST:
                # set next in list
                if o['interfaceName'] == 'BlankNode':
                    # create list entry as needed
                    list_map = graph['listMap']
                    entry = list_map.setdefault(s, {})
                    entry['rest'] = o['nominalValue']
                continue

            # if graph is not the default graph
            if name != '':
                # add graph subject to default graph as needed
                default_graph['subjects'].setdefault(name, {'@id': name})

            # add subject to graph as needed
            subjects = graph['subjects']
            value = subjects.setdefault(s, {'@id': s})

            # convert to @type unless options indicate to treat rdf:type as
            # property
            if p == RDF_TYPE and not options['notType']:
                # add value of object as @type
                JsonLdProcessor.add_value(
                    value, '@type', o['nominalValue'],
                    {'propertyIsArray': True})
            else:
                # add property to value as needed
                object = self._rdf_to_object(o)
                JsonLdProcessor.add_value(
                    value, p, object, {'propertyIsArray': True})

                # a bnode might be the start of a list, so add it to list map
                if o['interfaceName'] == 'BlankNode':
                    id = object['@id']
                    # create list entry as needed
                    list_map = graph['listMap']
                    entry = list_map.setdefault(id, {})
                    entry['head'] = object

        # build @lists
        for name, graph in graphs.items():
            # find list head
            list_map = graph['listMap']
            for subject, entry in list_map.items():
                # head found, build lists
                if 'head' in entry and 'first' in entry:
                    # replace bnode @id with @list
                    value = entry['head']
                    del value['@id']
                    list_ = value['@list'] = [entry['first']]
                    while 'rest' in entry:
                        rest = entry['rest']
                        entry = list_map[rest]
                        if 'first' not in entry:
                            raise JsonLdError(
                                'Invalid RDF list entry.',
                                'jsonld.RdfError', {'bnode': rest})
                        list_.append(entry['first'])

        # build default graph in subject @id order
        output = []
        for id, subject in sorted(default_graph['subjects'].items()):
            # add subject to default graph
            output.append(subject)

            # output named graph in subject @id order
            if id in graphs:
                graph = subject['@graph'] = []
                for id, subject in sorted(graphs[id]['subjects'].items()):
                    graph.append(subject)
        return output

    def _to_rdf(self, element, namer, subject, property, graph, statements):
        """
        Outputs the RDF statements found in the given JSON-LD object.

        :param element: the JSON-LD element.
        :param namer: the UniqueNamer for assigning bnode names.
        :param subject: the active subject.
        :param property: the active property.
        :param graph: the graph name.
        :param statements: the array to add statements to.
        """
        if _is_object(element):
            # convert @value to object
            if _is_value(element):
                value = element['@value']
                datatype = element.get('@type')
                if (_is_bool(value) or _is_double(value) or
                    _is_integer(value)):
                    # convert to XSD datatype
                    if _is_bool(value):
                        value = 'true' if value else 'false'
                        datatype = datatype or XSD_BOOLEAN
                    elif _is_double(value):
                        # printf('%1.15e') equivalent
                        value = '%1.15e' % value
                        datatype = datatype or XSD_DOUBLE
                    else:
                        value = str(value)
                        datatype = datatype or XSD_INTEGER

                object = {
                    'nominalValue': value,
                    'interfaceName': 'LiteralNode'
                }
                if datatype is not None:
                    object['datatype'] = {
                        'nominalValue': datatype,
                        'interfaceName': 'IRI'
                    }
                elif '@language' in element:
                    object['language'] = element['@language']
                # emit literal
                statement = {
                    'subject': copy.deepcopy(subject),
                    'property': copy.deepcopy(property),
                    'object': object
                }
                if graph is not None:
                    statement['name'] = graph
                JsonLdProcessor._append_unique_rdf_statement(
                    statements, statement)
                return

            # convert @list
            if _is_list(element):
                list_ = self._make_linked_list(element)
                self._to_rdf(
                    list_, namer, subject, property, graph, statements)
                return

            # Note: element must be a subject

            # get subject @id (generate one if it is a bnode)
            id = element['@id'] if '@id' in element else None
            is_bnode = _is_bnode(element)
            if is_bnode:
                id = namer.get_name(id)

            # create object
            object = {
                'nominalValue': id,
                'interfaceName': 'BlankNode' if is_bnode else 'IRI'
            }

            # emit statement if subject isn't None
            if subject is not None:
                statement = {
                    'subject': copy.deepcopy(subject),
                    'property': copy.deepcopy(property),
                    'object': copy.deepcopy(object)
                }
                if graph is not None:
                    statement['name'] = graph
                JsonLdProcessor._append_unique_rdf_statement(
                    statements, statement)

            # set new active subject to object
            subject = object

            # recurse over subject properties in order
            for prop, value in sorted(element.items()):
                # convert @type to rdf:type
                if prop == '@type':
                    prop = RDF_TYPE

                # recurse into @graph
                if prop == '@graph':
                    self._to_rdf(
                        value, namer, None, None, subject, statements)
                    continue

                # skip keywords
                if _is_keyword(prop):
                    continue

                # create new active property
                property = {'nominalValue': prop, 'interfaceName': 'IRI'}

                # recurse into value
                self._to_rdf(
                    value, namer, subject, property, graph, statements)

            return

        if _is_array(element):
            # recurse into arrays
            for e in element:
                self._to_rdf(e, namer, subject, property, graph, statements)
            return

        # element must be an rdf:type IRI (@values covered above)
        if _is_string(element):
            # emit IRI
            statement = {
                'subject': copy.deepcopy(subject),
                'property': copy.deepcopy(property),
                'object': {
                    'nominalValue': element,
                    'interfaceName': 'IRI'
                }
            }
            if graph is not None:
                statement['name'] = graph
            JsonLdProcessor._append_unique_rdf_statement(
                statements, statement)
            return

    def _process_context(self, active_ctx, local_ctx, options):
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
        if (_is_object(local_ctx) and '@context' in local_ctx and
            _is_array(local_ctx['@context'])):
            local_ctx = local_ctx['@context']
        ctxs = JsonLdProcessor.arrayify(local_ctx)

        # process each context in order
        for ctx in ctxs:
            # reset to initial context
            if ctx is None:
                rval = self._get_initial_context()
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
                self._define_context_mapping(
                    rval, ctx, k, options['base'], defined)

        return rval

    def _expand_value(self, ctx, property, value, base):
        """
        Expands the given value by using the coercion and keyword rules in the
        given context.

        :param ctx: the active context to use.
        :param property: the property the value is associated with.
        :param value: the value to expand.
        :param base: the base IRI to use.

        :return: the expanded value.
        """
        # nothing to expand
        if value is None:
            return None

        # default to simple string return value
        rval = value

        # special-case expand @id and @type (skips '@id' expansion)
        prop = self._expand_term(ctx, property)
        if prop == '@id':
            rval = self._expand_term(ctx, value, base)
        elif prop == '@type':
            rval = self._expand_term(ctx, value)
        else:
            # get type definition from context
            type = JsonLdProcessor.get_context_value(ctx, property, '@type')

            # do @id expansion (automatic for @graph)
            if type == '@id' or prop == '@graph':
                rval = {'@id': self._expand_term(ctx, value, base)}
            elif not _is_keyword(prop):
                rval = {'@value': value}

                # other type
                if type is not None:
                    rval['@type'] = type
                # check for language tagging
                else:
                    language = JsonLdProcessor.get_context_value(
                        ctx, property, '@language')
                    if language is not None:
                        rval['@language'] = language

        return rval

    def _rdf_to_object(self, o):
        """
        Converts an RDF statement object to a JSON-LD object.

        :param o: the RDF statement object to convert.

        :return: the JSON-LD object.
        """
        # convert empty list
        if o['interfaceName'] == 'IRI' and o['nominalValue'] == RDF_NIL:
            return {'@list': []}

        # convert IRI/BlankNode object to JSON-LD
        if o['interfaceName'] == 'IRI' or o['interfaceName'] == 'BlankNode':
            return {'@id': o['nominalValue']}

        # convert literal object to JSON-LD
        rval = {'@value': o['nominalValue']}
        # add datatype
        if 'datatype' in o:
            rval['@type'] = o['datatype']['nominalValue']
        # add language
        elif 'language' in o:
            rval['@language'] = o['language']
        return rval

    def _make_linked_list(self, value):
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
            tail = {RDF_FIRST: [e], RDF_REST: [tail]}
        return tail

    def _hash_statements(self, id, bnodes, namer):
        """
        Hashes all of the statements about a blank node.

        :param id: the ID of the bnode to hash statements for.
        :param bnodes: the mapping of bnodes to statements.
        :param namer: the canonical bnode namer.

        :return: the new hash.
        """
        # return cached hash
        if 'hash' in bnodes[id]:
            return bnodes[id]['hash']

        # serialize all of bnode's statements
        statements = bnodes[id]['statements']
        nquads = []
        for statement in statements:
            nquads.append(JsonLdProcessor.to_nquad(statement, id))
        # sort serialized quads
        nquads.sort()
        # return hashed quads
        md = hashlib.sha1()
        md.update(''.join(nquads))
        hash = bnodes[id]['hash'] = md.hexdigest()
        return hash

    def _hash_paths(self, id, bnodes, namer, path_namer):
        """
        Produces a hash for the paths of adjacent bnodes for a bnode,
        incorporating all information about its subgraph of bnodes. This
        method will recursively pick adjacent bnode permutations that produce the
        lexicographically-least 'path' serializations.

        :param id: the ID of the bnode to hash paths for.
        :param bnodes: the map of bnode statements.
        :param namer: the canonical bnode namer.
        :param path_namer: the namer used to assign names to adjacent bnodes.

        :return: the hash and path namer used.
        """
        # create SHA-1 digest
        md = hashlib.sha1()

        # group adjacent bnodes by hash, keep properties & references separate
        groups = {}
        statements = bnodes[id]['statements']
        for statement in statements:
            # get adjacent bnode
            bnode = _get_adjacent_bnode_name(statement['subject'], id)
            if bnode is not None:
                direction = 'p'
            else:
                bnode = _get_adjacent_bnode_name(statement['object'], id)
                if bnode is not None:
                    direction = 'r'

            if bnode is not None:
                # get bnode name (try canonical, path, then hash)
                if namer.is_named(bnode):
                    name = namer.get_name(bnode)
                elif path_namer.is_named(bnode):
                    name = path_namer.get_name(bnode)
                else:
                    name = self._hash_statements(bnode, bnodes, namer)

                # hash direction, property, and bnode name/hash
                group_md = hashlib.sha1()
                group_md.update(direction)
                group_md.update(statement['property']['nominalValue'])
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
            for permutation in permutations(group):
                path_namer_copy = copy.deepcopy(path_namer)

                # build adjacent path
                path = ''
                skipped = False
                recurse = []
                for bnode in permutation:
                    # use canonical name if available
                    if namer.is_named(bnode):
                        path += namer.get_name(bnode)
                    else:
                        # recurse if bnode isn't named in the path yet
                        if not path_namer_copy.is_named(bnode):
                            recurse.append(bnode)
                        path += path_namer_copy.get_name(bnode)

                    # skip permutation if path is already >= chosen path
                    if (chosen_path is not None and
                        len(path) >= len(chosen_path) and path > chosen_path):
                        skipped = True
                        break

                # recurse
                if not skipped:
                    for bnode in recurse:
                        result = self._hash_paths(
                            bnode, bnodes, namer, path_namer_copy)
                        path += path_namer_copy.get_name(bnode)
                        path += '<%s>' % result['hash']
                        path_namer_copy = result['pathNamer']

                        # skip permutation if path is already >= chosen path
                        if (chosen_path is not None and
                            len(path) >= len(chosen_path) and
                            path > chosen_path):
                            skipped = True
                            break

                if (not skipped and
                    (chosen_path is None or path < chosen_path)):
                    chosen_path = path
                    chosen_namer = path_namer_copy

            # digest chosen path and update namer
            md.update(chosen_path)
            path_namer = chosen_namer

        # return SHA-1 hash and path namer
        return {'hash': md.hexdigest(), 'pathNamer': path_namer}

    def _flatten(self, input, graphs, graph, namer, name, list_):
        """
        Recursively flattens the subjects in the given JSON-LD expanded input.

        :param input: the JSON-LD expanded input.
        :param graphs: a map of graph name to subject map.
        :param graph: the name of the current graph.
        :param namer: the blank node namer.
        :param name: the name assigned to the current input if it is a bnode.
        :param list_: the list to append to, None for none.
        """
        # recurse through array
        if _is_array(input):
            for e in input:
                self._flatten(e, graphs, graph, namer, None, list_)
            return

        # add non-object or value
        elif not _is_object(input) or _is_value(input):
            if list_ is not None:
                list_.append(input)
            return

        # Note: At this point, input must be a subject.

        # get name for subject
        if name is None:
            name = input.get('@id')
            if _is_bnode(input):
                name = namer.get_name(name)

        # add subject reference to list
        if list_ is not None:
            list_.append({'@id': name})

        # create new subject or merge into existing one
        subject = graphs.setdefault(graph, {}).setdefault(name, {})
        subject['@id'] = name
        for prop, objects in input.items():
            # skip @id
            if prop == '@id':
                continue

            # recurse into graph
            if prop == '@graph':
                # add graph subjects map entry
                graphs.setdefault(name, {})
                g = graph if graph == '@merged' else name
                self._flatten(objects, graphs, g, namer, None, None)
                continue

            # copy non-@type keywords
            if prop != '@type' and _is_keyword(prop):
                subject[prop] = objects
                continue

            # iterate over objects
            for o in objects:
                # handle embedded subject or subject reference
                if _is_subject(o) or _is_subject_reference(o):
                    id = o.get('@id')
                    # rename blank node @id
                    if _is_bnode(o):
                        id = namer.get_name(id)

                    # add reference and recurse
                    JsonLdProcessor.add_value(
                        subject, prop, {'@id': id}, {'propertyIsArray': True})
                    self._flatten(o, graphs, graph, namer, id, None)
                else:
                    # recurse into list
                    if _is_list(o):
                        olist = []
                        self._flatten(
                            o['@list'], graphs, graph, namer, name, olist)
                        o = {'@list': olist}
                    # special-handle @type IRIs
                    elif prop == '@type' and o.startswith('_:'):
                        o = namer.get_name(o)

                    # add non-subject
                    JsonLdProcessor.add_value(
                        subject, prop, o, {'propertyIsArray': True})

    def _match_frame(self, state, subjects, frame, parent, property):
        """
        Frames subjects according to the given frame.

        :param state: the current framing state.
        :param subjects: the subjects to filter.
        :param frame: the frame.
        :param parent: the parent subject or top-level array.
        :param property: the parent property, initialized to None.
        """
        # validate the frame
        self._validate_frame(state, frame)
        frame = frame[0]

        # filter out subjects that match the frame
        matches = self._filter_subjects(state, subjects, frame)

        # get flags for current frame
        options = state['options']
        embed_on = self._get_frame_flag(frame, options, 'embed')
        explicit_on = self._get_frame_flag(frame, options, 'explicit')

        # add matches to output
        for id, subject in sorted(matches.items()):
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
                # only overwrite an existing embed if it has already been
                # added to its parent -- otherwise its parent is somewhere up
                # the tree from this embed and the embed would occur twice
                # once the tree is added
                embed_on = False

                # existing embed's parent is an array
                existing = state['embeds'][id]
                if _is_array(existing['parent']):
                    for p in existing['parent']:
                        if JsonLdProcessor.compare_values(output, p):
                            embed_on = True
                            break
                # existing embed's parent is an object
                elif JsonLdProcessor.has_value(
                    existing['parent'], existing['property'], output):
                    embed_on = True

                # existing embed has already been added, so allow an overwrite
                if embed_on:
                    self._remove_embed(state, id)

            # not embedding, add output without any other properties
            if not embed_on:
                self._add_frame_output(state, parent, property, output)
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
                            self._embed_values(state, subject, prop, output)
                        continue

                    # add objects
                    objects = subject[prop]
                    for o in objects:
                        # recurse into list
                        if _is_list(o):
                            # add empty list
                            list_ = {'@list': []}
                            self._add_frame_output(state, output, prop, list_)

                            # add list objects
                            src = o['@list']
                            for o in src:
                                # recurse into subject reference
                                if _is_subject_reference(o):
                                    self._match_frame(
                                        state, [o['@id']], frame[prop],
                                        list_, '@list')
                                # include other values automatically
                                else:
                                    self._add_frame_output(
                                        state, list_, '@list', copy.deepcopy(o))
                            continue

                        # recurse into subject reference
                        if _is_subject_reference(o):
                            self._match_frame(
                                state, [o['@id']], frame[prop], output, prop)
                        # include other values automatically
                        else:
                            self._add_frame_output(
                                state, output, prop, copy.deepcopy(o))

                # handle defaults in order
                for prop in sorted(frame.keys()):
                    # skip keywords
                    if _is_keyword(prop):
                        continue
                    # if omit default is off, then include default values for
                    # properties that appear in the next frame but are not in
                    # the matching subject
                    next = frame[prop][0]
                    omit_default_on = self._get_frame_flag(
                        next, options, 'omitDefault')
                    if not omit_default_on and prop not in output:
                        preserve = '@null'
                        if '@default' in next:
                            preserve = copy.deepcopy(next['@default'])
                        output[prop] = {'@preserve': preserve}

                # add output to parent
                self._add_frame_output(state, parent, property, output)

    def _get_frame_flag(self, frame, options, name):
        """
        Gets the frame flag value for the given flag name.

        :param frame: the frame.
        :param options: the framing options.
        :param name: the flag name.

        :return: the flag value.
        """
        return frame.get('@' + name, [options[name]])[0]

    def _validate_frame(self, state, frame):
        """
        Validates a JSON-LD frame, throwing an exception if the frame is invalid.

        :param state: the current frame state.
        :param frame: the frame to validate.
        """
        if (not _is_array(frame) or len(frame) != 1 or
            not _is_object(frame[0])):
            raise JsonLdError(
                'Invalid JSON-LD syntax a JSON-LD frame must be a single '
                'object.', 'jsonld.SyntaxError', {'frame': frame})

    def _filter_subjects(self, state, subjects, frame):
        """
        Returns a map of all of the subjects that match a parsed frame.

        :param state: the current framing state.
        :param subjects: the set of subjects to filter.
        :param frame: the parsed frame.

        :return: all of the matched subjects.
        """
        rval = {}
        for id in subjects:
            subject = state['subjects'][id]
            if self._filter_subject(subject, frame):
                rval[id] = subject
        return rval

    def _filter_subject(self, subject, frame):
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
                if JsonLdProcessor.has_value(subject, '@type', type):
                  return True
            return False

        # check ducktype
        for k, v in frame.items():
            # only not a duck if @id or non-keyword isn't in subject
            if (k == '@id' or not _is_keyword(k)) and k not in subject:
                return False
        return True

    def _embed_values(self, state, subject, property, output):
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
                list_ = {'@list': []}
                self._add_frame_output(state, output, property, list_)
                self._embed_values(state, o, '@list', list_['@list'])
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
                    for prop, v in s.items():
                        # copy keywords
                        if _is_keyword(prop):
                            o[prop] = copy.deepcopy(v)
                            continue
                        self._embed_values(state, s, prop, o)
                self._add_frame_output(state, output, property, o)
            # copy non-subject value
            else:
                self._add_frame_output(
                    state, output, property, copy.deepcopy(o))

    def _remove_embed(self, state, id):
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
                if JsonLdProcessor.compare_values(parent, subject):
                    embed['parent'][i] = subject
                    break
        else:
            # replace subject with reference
            use_array = _is_array(embed['parent'][property])
            JsonLdProcessor.remove_value(
                embed['parent'], property, subject,
                {'propertyIsArray': use_array})
            JsonLdProcessor.add_value(
                embed['parent'], property, subject,
                {'propertyIsArray': use_array})

        # recursively remove dependent dangling embeds
        def remove_dependents(id):
            # get embed keys as a separate array to enable deleting keys
            # in map
            ids = embeds.keys()
            for next in ids:
                if (next in embeds and
                    _is_object(embeds[next]['parent']) and
                    embeds[next]['parent']['@id'] == id):
                    del embeds[next]
                    remove_dependents(next)
        remove_dependents(id)

    def _add_frame_output(self, state, parent, property, output):
        """
        Adds framing output to the given parent.

        :param state: the current framing state.
        :param parent: the parent to add to.
        :param property: the parent property.
        :param output: the output to add.
        """
        if _is_object(parent):
            JsonLdProcessor.add_value(
                parent, property, output, {'propertyIsArray': True})
        else:
            parent.append(output)

    def _remove_preserve(self, ctx, input):
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
              result = self._remove_preserve(ctx, e)
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
                input['@list'] = self._remove_preserve(ctx, input['@list'])
                return input

            # recurse through properties
            for prop, v in input.items():
                result = self._remove_preserve(ctx, v)
                container = JsonLdProcessor.get_context_value(
                    ctx, prop, '@container')
                if (_is_array(result) and len(result) == 1 and
                    container != '@set' and container != '@list'):
                    result = result[0]
                input[prop] = result
        return input

    def _rank_term(self, ctx, term, value):
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
            list_ = value['@list']
            if len(list_) == 0:
              return 1 if entry['@container'] == '@list' else 0
            # sum term ranks for each list value
            return sum(self._rank_term(ctx, term, v) for v in list_)

        # Note: Value must be an object that is a @value or subject/reference.

        if _is_value(value):
            # value has a @type
            if '@type' in value:
                # @types match
                if has_type and value['@type'] == entry['@type']:
                    return 3
                return 1 if not (has_type or has_language) else 0

            # rank non-string value
            if not _is_string(value['@value']):
                return 2 if not (has_type or has_language) else 1

            # value has no @type or @language
            if '@language' not in value:
                # entry @language is specifically None or no @type, @language, or
                # default
                if ((has_language and entry['@language'] is None) or
                    not (has_type or has_language or has_default_language)):
                    return 3
                return 0

            # @languages match or entry has no @type or @language but default
            # @language matches
            if ((has_language and value['@language'] == entry['@language']) or
                (not has_type and not has_language and has_default_language
                and value['@language'] == ctx['@language'])):
                return 3
            return 1 if not (has_type or has_language) else 0

        # value must be a subject/reference
        if has_type and entry['@type'] == '@id':
            return 3
        return 1 if not (has_type or has_language) else 0

    def _compact_iri(self, ctx, iri, value=None):
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
        for term, entry in ctx['mappings'].items():
            has_container = '@container' in entry

            # skip terms with non-matching iris
            if entry['@id'] != iri:
                continue
            # skip @set containers for @lists
            if is_list and has_container and entry['@container'] == '@set':
                continue
            # skip @list containers for non-@lists
            if (not is_list and has_container and
                entry['@container'] == '@list' and value is not None):
                continue
            # for @lists, if list_container is set, skip non-list containers
            if (is_list and list_container and not (has_container and
                entry['@container'] != '@list')):
                continue

            # rank term
            rank = self._rank_term(ctx, term, value)
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
            for term, entry in ctx['mappings'].items():
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

        # no matching terms
        if len(terms) == 0:
            # use iri
            return iri

        # return shortest and lexicographically-least term
        terms.sort(key=cmp_to_key(_compare_shortest_least))
        return terms[0]

    def _define_context_mapping(self, active_ctx, ctx, key, base, defined):
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
                self._define_context_mapping(
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
        if (value is None or
            (_is_object(value) and '@id' in value and
            value['@id'] is None)):
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
                        'Invalid JSON-LD syntax @context and @preserve '
                        'cannot be aliased.', 'jsonld.SyntaxError')

                # uniquely add key as a keyword alias and resort
                aliases = active_ctx['keywords'][value]
                if key not in aliases:
                    aliases.append(key)
                    aliases.sort(key=cmp_to_key(_compare_shortest_least))
            elif value:
                # expand value to a full IRI
                value = self._expand_context_iri(
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
            # expand @id if it is not @type
            if id != '@type':
                # expand @id to full IRI
                id = self._expand_context_iri(
                    active_ctx, ctx, id, base, defined)
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
                type = self._expand_context_iri(
                    active_ctx, ctx, type, '', defined)
            # add @type to mapping
            mapping['@type'] = type

        if '@container' in value:
            container = value['@container']
            if container != '@list' and container != '@set':
                raise JsonLdError(
                    'Invalid JSON-LD syntax @context @container value '
                    'must be "@list" or "@set".',
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

    def _expand_context_iri(self, active_ctx, ctx, value, base, defined):
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
            self._define_context_mapping(
                active_ctx, ctx, value, base, defined)

        # recurse if value is a term
        if value in active_ctx['mappings']:
            id = active_ctx['mappings'][value]['@id']
            # value is already an absolute IRI
            if value == id:
                return value
            return self._expand_context_iri(
                active_ctx, ctx, id, base, defined)

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
                self._define_context_mapping(
                    active_ctx, ctx, prefix, base, defined)
            # recurse if prefix is defined
            if prefix in active_ctx['mappings']:
                id = active_ctx['mappings'][prefix]['@id']
                return self._expand_context_iri(
                    active_ctx, ctx, id, base, defined) + suffix

            # consider value an absolute IRI
            return value

        # prepend base
        value = self._prepend_base(base, value)

        # value must now be an absolute IRI
        if not _is_absolute_iri(value):
            raise JsonLdError(
                'Invalid JSON-LD syntax a @context value does not expand to '
                'an absolute IRI.',
                'jsonld.SyntaxError', {'context': ctx, 'value': value})

        return value

    def _expand_term(self, ctx, term, base=''):
        """
        Expands a term into an absolute IRI. The term may be a regular term, a
        prefix, a relative IRI, or an absolute IRI. In any case, the
        associated absolute IRI will be returned.

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
            return self._expand_term(ctx, id, base)

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
                return self._expand_term(
                    ctx, ctx['mappings'][prefix]['@id'], base) + suffix
            # consider term an absolute IRI
            return term

        # prepend base to term
        return self._prepend_base(base, term)

    def _find_context_urls(self, input, urls, replace):
        """
        Finds all @context URLs in the given JSON-LD input.

        :param input: the JSON-LD input.
        :param urls: a map of URLs (url => false/@contexts).
        :param replace: true to replace the URLs in the given input with
                 the @contexts from the urls map, false not to.
        """
        count = len(urls)
        if _is_array(input):
            for e in input:
                self._find_context_urls(e, urls, replace)
        elif _is_object(input):
            for k, v in input.items():
                if k != '@context':
                    self._find_context_urls(v, urls, replace)
                    continue

                # array @context
                if _is_array(v):
                    length = len(v)
                    i = 0
                    while i < length:
                        if _is_string(v[i]):
                            url = v[i]
                            # replace w/@context if requested
                            if replace:
                                ctx = urls[url]
                                if _is_array(ctx):
                                    # add flattened context
                                    v.pop(i)
                                    for e in reversed(ctx):
                                        v.insert(i, e)
                                    i += len(ctx)
                                    length += len(ctx)
                                else:
                                    v[i] = ctx
                            # @context URL found
                            elif url not in urls:
                                urls[url] = False
                        i += 1
                # string @context
                elif _is_string(v):
                    # replace w/@context if requested
                    if replace:
                        input[k] = urls[v]
                    # @context URL found
                    elif v not in urls:
                        urls[v] = False

    def _resolve_context_urls(self, input, cycles, resolver):
        """
        Resolves external @context URLs using the given URL resolver. Each
        instance of @context in the input that refers to a URL will be
        replaced with the JSON @context found at that URL.

        :param input: the JSON-LD input with possible contexts.
        :param cycles: an object for tracking context cycles.
        :param resolver(url): the URL resolver.

        :return: the result.
        """
        if len(cycles) > MAX_CONTEXT_URLS:
            raise JsonLdError(
                'Maximum number of @context URLs exceeded.',
                'jsonld.ContextUrlError', {'max': MAX_CONTEXT_URLS})

        # for tracking URLs to resolve
        urls = {}

        # find all URLs in the given input
        self._find_context_urls(input, urls, False)

        # queue all unresolved URLs
        queue = []
        for url, ctx in urls.items():
            if ctx == False:
                # validate URL
                pieces = urlparse.urlparse(url)
                if (not all([pieces.scheme, pieces.netloc]) or
                    pieces.scheme not in ['http', 'https'] or
                    set(pieces.netloc) > set(
                        string.letters + string.digits + '-.:')):
                    raise JsonLdError(
                        'Malformed or unsupported URL.',
                        'jsonld.InvalidUrl', {'url': url})
                queue.append(url)

        # resolve URLs in queue
        for url in queue:
            # check for context URL cycle
            if url in cycles:
                raise JsonLdError(
                    'Cyclical @context URLs detected.',
                    'jsonld.ContextUrlError', {'url': url})
            _cycles = copy.deepcopy(cycles)
            _cycles[url] = True

            # resolve URL
            ctx = resolver(url)

            # parse string context as JSON
            if _is_string(ctx):
                try:
                    ctx = json.loads(ctx)
                except Exception as cause:
                    raise JsonLdError(
                        'Could not parse JSON from URL.',
                        'jsonld.ParseError', {'url': url}, cause)

            # ensure ctx is an object
            if not _is_object(ctx):
                raise JsonLdError(
                    'URL does not resolve to a valid JSON-LD context.',
                    'jsonld.InvalidUrl', {'url': url})

            # use empty context if no @context key is present
            if '@context' not in ctx:
                ctx = {'@context': {}}

            # recurse
            self._resolve_context_urls(ctx, cycles, resolver)
            urls[url] = ctx['@context']

        # replace all URLs in the input
        self._find_context_urls(input, urls, True)

    def _prepend_base(self, base, iri):
        """
        Prepends a base IRI to the given relative IRI.

        :param base: the base IRI.
        :param iri: the relative IRI.

        :return: the absolute IRI.
        """
        if iri == '' or iri.startswith('#'):
            return base + iri
        else:
            # prepend last directory for base
            return base[:base.rfind('/') + 1] + iri

    def _get_initial_context(self):
        """
        Gets the initial context.

        :return: the initial context.
        """
        keywords = {}
        for kw in KEYWORDS:
            keywords[kw] = []
        return {'mappings': {}, 'keywords': keywords}


# register the N-Quads RDF parser
register_rdf_parser('application/nquads', JsonLdProcessor.parse_nquads)


class JsonLdError(Exception):
    """
    Base class for JSON-LD errors.
    """

    def __init__(self, message, type, details=None, cause=None):
        Exception.__init__(self, message)
        self.type = type
        self.details = details
        self.cause = cause
        self.causeTrace = traceback.extract_tb(*sys.exc_info()[2:])

    def __str__(self):
        rval = repr(self.message)
        rval += '\nType: ' + self.type
        if self.details:
            rval += '\nDetails: ' + repr(self.details)
        if self.cause:
            rval += '\nCause: ' + str(self.cause)
            rval += ''.join(traceback.format_list(self.causeTrace))
        return rval


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
        Gets the new name for the given old name, where if no old name is
        given a new name will be generated.

        :param [old_name]: the old name to get the new name for.

        :return: the new name.
        """
    def get_name(self, old_name=None):
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

    def is_named(self, old_name):
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


def _is_keyword(v, ctx=None):
    """
    Returns whether or not the given value is a keyword (or a keyword alias).

    :param v: the value to check.
    :param [ctx]: the active context to check against.

    :return: True if the value is a keyword, False if not.
    """
    if ctx is not None:
        if v in ctx['keywords']:
            return True
        for kw, aliases in ctx['keywords'].items():
            if v in aliases:
                return True
    else:
        return v in KEYWORDS


def _is_object(v):
    """
    Returns True if the given value is an Object.

    :param v: the value to check.

    :return: True if the value is an Object, False if not.
    """
    return isinstance(v, dict)


def _is_empty_object(v):
    """
    Returns True if the given value is an empty Object.

    :param v: the value to check.

    :return: True if the value is an empty Object, False if not.
    """
    return _is_object(v) and len(v) == 0


def _is_array(v):
    """
    Returns True if the given value is an Array.

    :param v: the value to check.

    :return: True if the value is an Array, False if not.
    """
    return isinstance(v, list)


def _is_string(v):
    """
    Returns True if the given value is a String.

    :param v: the value to check.

    :return: True if the value is a String, False if not.
    """
    return isinstance(v, basestring)


def _validate_type_value(v):
    """
    Raises an exception if the given value is not a valid @type value.

    :param v: the value to check.
    """
    # must be a string, subject reference, or empty object
    if (_is_string(v) or _is_subject_reference(v) or
        _is_empty_object(v)):
        return

    # must be an array
    is_valid = False
    if _is_array(v):
        # must contain only strings or subject references
        is_valid = True
        for e in v:
            if not (_is_string(e) or _is_subject_reference(e)):
                is_valid = False
                break

    if not is_valid:
        raise JsonLdError(
            'Invalid JSON-LD syntax "@type" value must a string, '
            'an array of strings, or an empty object.',
            'jsonld.SyntaxError', {'value': v})


def _is_bool(v):
    """
    Returns True if the given value is a Boolean.

    :param v: the value to check.

    :return: True if the value is a Boolean, False if not.
    """
    return isinstance(v, bool)


def _is_integer(v):
    """
    Returns True if the given value is an Integer.

    :param v: the value to check.

    :return: True if the value is an Integer, False if not.
    """
    return isinstance(v, Integral)


def _is_double(v):
    """
    Returns True if the given value is a Double.

    :param v: the value to check.

    :return: True if the value is a Double, False if not.
    """
    return not isinstance(v, Integral) and isinstance(v, Real)


def _is_subject(v):
    """
    Returns True if the given value is a subject with properties.

    :param v: the value to check.

    :return: True if the value is a subject with properties, False if not.
    """
    # Note: A value is a subject if all of these hold True:
    # 1. It is an Object.
    # 2. It is not a @value, @set, or @list.
    # 3. It has more than 1 key OR any existing key is not @id.
    rval = False
    if (_is_object(v) and
        '@value' not in v and '@set' not in v and '@list' not in v):
        rval = len(v) > 1 or '@id' not in v
    return rval


def _is_subject_reference(v):
    """
    Returns True if the given value is a subject reference.

    :param v: the value to check.

    :return: True if the value is a subject reference, False if not.
    """
    # Note: A value is a subject reference if all of these hold True:
    # 1. It is an Object.
    # 2. It has a single key: @id.
    return (_is_object(v) and len(v) == 1 and '@id' in v)


def _is_value(v):
    """
    Returns True if the given value is a @value.

    :param v: the value to check.

    :return: True if the value is a @value, False if not.
    """
    # Note: A value is a @value if all of these hold True:
    # 1. It is an Object.
    # 2. It has the @value property.
    return _is_object(v) and '@value' in v


def _is_list(v):
    """
    Returns True if the given value is a @list.

    :param v: the value to check.

    :return: True if the value is a @list, False if not.
    """
    # Note: A value is a @list if all of these hold True:
    # 1. It is an Object.
    # 2. It has the @list property.
    return _is_object(v) and '@list' in v


def _is_bnode(v):
    """
    Returns True if the given value is a blank node.

    :param v: the value to check.

    :return: True if the value is a blank node, False if not.
    """
    # Note: A value is a blank node if all of these hold True:
    # 1. It is an Object.
    # 2. If it has an @id key its value begins with '_:'.
    # 3. It has no keys OR is not a @value, @set, or @list.
    rval = False
    if _is_object(v):
        if '@id' in v:
            rval = v['@id'].startswith('_:')
        else:
            rval = (len(v) == 0 or not
                ('@value' in v or '@set' in v or '@list' in v))
    return rval


def _is_absolute_iri(v):
    """
    Returns True if the given value is an absolute IRI, False if not.

    :param v: the value to check.

    :return: True if the value is an absolute IRI, False if not.
    """
    return v.find(':') != -1


def _get_adjacent_bnode_name(node, id):
    """
    A helper function that gets the blank node name from an RDF statement
    node (subject or object). If the node is not a blank node or its
    nominal value does not match the given blank node ID, it will be
    returned.

    :param node: the RDF statement node.
    :param id: the ID of the blank node to look next to.

    :return: the adjacent blank node name or None if none was found.
    """
    if node['interfaceName'] == 'BlankNode' and node['nominalValue'] != id:
        return node['nominalValue']
    return None


class ContextCache:
    """
    A simple JSON-LD context cache.
    """

    def __init__(self, size=50):
        self.order = []
        self.cache = {}
        self.size = size
        self.expires = 30 * 60 * 1000

    def get(self, url):
        if url in self.cache:
            entry = self.cache[url]
            if entry['expires'] >= time.time():
                return entry['ctx']
            del self.cache[url]
            self.order.remove(url)
        return None

    def set(self, url, ctx):
        if(len(self.order) == self.size):
            del self.cache[self.order.pop(0)]
        self.order.append(url)
        self.cache[url] = {
            'ctx': ctx, 'expires': (time.time() + self.expires)}


class VerifiedHTTPSConnection(HTTPSConnection):
    """
    Used to verify SSL certificates when resolving URLs.
    Taken from: http://thejosephturner.com/blog/2011/03/19/https-certificate-verification-in-python-with-urllib2/
    """

    def connect(self):
        global _trust_root_certificates
        # overrides the version in httplib to do certificate verification
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        # wrap the socket using verification with trusted_root_certs
        self.sock = ssl.wrap_socket(sock,
            self.key_file,
            self.cert_file,
            cert_reqs=ssl.CERT_REQUIRED,
            ca_certs=_trust_root_certificates)


class VerifiedHTTPSHandler(urllib2.HTTPSHandler):
    """
    Wraps urllib2 HTTPS connections enabling SSL certificate verification.
    """

    def __init__(self, connection_class=VerifiedHTTPSConnection):
        self.specialized_conn_class = connection_class
        urllib2.HTTPSHandler.__init__(self)

    def https_open(self, req):
        return self.do_open(self.specialized_conn_class, req)


# the path to the system's default trusted root SSL certificates
_trust_root_certificates = None
if os.path.exists('/etc/ssl/certs'):
    _trust_root_certificates = '/etc/ssl/certs'
