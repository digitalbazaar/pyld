"""
Python implementation of JSON-LD processor

This implementation is ported from the JavaScript implementation of
JSON-LD.

.. module:: jsonld
  :synopsis: Python implementation of JSON-LD

.. moduleauthor:: Dave Longley
.. moduleauthor:: Mike Johnson
.. moduleauthor:: Tim McNamara <tim.mcnamara@okfn.org>
.. moduleauthor:: Olaf Conradi <olaf@conradi.org>
"""

import copy
import hashlib
import json
import re
import sys
import traceback
from collections import deque, namedtuple
from numbers import Integral, Real
from pyld.__about__ import (__copyright__, __license__, __version__)

try:
    from functools import cmp_to_key
except ImportError:
    def cmp_to_key(mycmp):
        """
        Convert a cmp= function into a key= function

        Source: http://hg.python.org/cpython/file/default/Lib/functools.py
        """
        class K(object):
            __slots__ = ['obj']

            def __init__(self, obj):
                self.obj = obj

            def __lt__(self, other):
                return mycmp(self.obj, other.obj) < 0

            def __gt__(self, other):
                return mycmp(self.obj, other.obj) > 0

            def __eq__(self, other):
                return mycmp(self.obj, other.obj) == 0

            def __le__(self, other):
                return mycmp(self.obj, other.obj) <= 0

            def __ge__(self, other):
                return mycmp(self.obj, other.obj) >= 0

            def __ne__(self, other):
                return mycmp(self.obj, other.obj) != 0
            __hash__ = None
        return K

# support python 2 and 3
if sys.version_info[0] >= 3:
    import urllib.parse as urllib_parse
    basestring = str

    def cmp(a, b):
        return (a > b) - (a < b)
else:
    import urlparse as urllib_parse

__all__ = [
    '__copyright__', '__license__', '__version__',
    'compact', 'expand', 'flatten', 'frame', 'link', 'from_rdf', 'to_rdf',
    'normalize', 'set_document_loader', 'get_document_loader',
    'parse_link_header', 'load_document',
    'requests_document_loader', 'aiohttp_document_loader',
    'register_rdf_parser', 'unregister_rdf_parser',
    'JsonLdProcessor', 'JsonLdError', 'ActiveContextCache'
]

# XSD constants
XSD_BOOLEAN = 'http://www.w3.org/2001/XMLSchema#boolean'
XSD_DOUBLE = 'http://www.w3.org/2001/XMLSchema#double'
XSD_INTEGER = 'http://www.w3.org/2001/XMLSchema#integer'
XSD_STRING = 'http://www.w3.org/2001/XMLSchema#string'

# RDF constants
RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
RDF_LIST = RDF + 'List'
RDF_FIRST = RDF + 'first'
RDF_REST = RDF + 'rest'
RDF_NIL = RDF + 'nil'
RDF_TYPE = RDF + 'type'
RDF_LANGSTRING = RDF + 'langString'

# JSON-LD keywords
KEYWORDS = [
    '@base',
    '@context',
    '@container',
    '@default',
    '@embed',
    '@explicit',
    '@graph',
    '@id',
    '@index',
    '@language',
    '@list',
    '@nest',
    '@none',
    '@omitDefault',
    '@preserve',
    '@requireAll',
    '@reverse',
    '@set',
    '@type',
    '@value',
    '@version',
    '@vocab']

# JSON-LD link header rel
LINK_HEADER_REL = 'http://www.w3.org/ns/json-ld#context'

# Restraints
MAX_CONTEXT_URLS = 10


def compact(input_, ctx, options=None):
    """
    Performs JSON-LD compaction.

    :param input_: the JSON-LD input to compact.
    :param ctx: the JSON-LD context to compact with.
    :param [options]: the options to use.
      [base] the base IRI to use.
      [compactArrays] True to compact arrays to single values when
        appropriate, False not to (default: True).
      [graph] True to always output a top-level graph (default: False).
      [expandContext] a context to expand with.
      [documentLoader(url)] the document loader
        (default: _default_document_loader).

    :return: the compacted JSON-LD output.
    """
    return JsonLdProcessor().compact(input_, ctx, options)


def expand(input_, options=None):
    """
    Performs JSON-LD expansion.

    :param input_: the JSON-LD input to expand.
    :param [options]: the options to use.
      [base] the base IRI to use.
      [expandContext] a context to expand with.
      [documentLoader(url)] the document loader
        (default: _default_document_loader).

    :return: the expanded JSON-LD output.
    """
    return JsonLdProcessor().expand(input_, options)


def flatten(input_, ctx=None, options=None):
    """
    Performs JSON-LD flattening.

    :param input_: the JSON-LD input to flatten.
    :param ctx: the JSON-LD context to compact with (default: None).
    :param [options]: the options to use.
      [base] the base IRI to use.
      [expandContext] a context to expand with.
      [documentLoader(url)] the document loader
        (default: _default_document_loader).

    :return: the flattened JSON-LD output.
    """
    return JsonLdProcessor().flatten(input_, ctx, options)


def frame(input_, frame, options=None):
    """
    Performs JSON-LD framing.

    :param input_: the JSON-LD input to frame.
    :param frame: the JSON-LD frame to use.
    :param [options]: the options to use.
      [base] the base IRI to use.
      [expandContext] a context to expand with.
      [embed] default @embed flag (default: True).
      [explicit] default @explicit flag (default: False).
      [requireAll] default @requireAll flag (default: True).
      [omitDefault] default @omitDefault flag (default: False).
      [pruneBlankNodeIdentifiers] remove unnecessary blank node identifiers (default: True)
      [documentLoader(url)] the document loader
        (default: _default_document_loader).

    :return: the framed JSON-LD output.
    """
    return JsonLdProcessor().frame(input_, frame, options)


def link(input_, ctx, options=None):
    """
    **Experimental**

    Links a JSON-LD document's nodes in memory.

    :param input_: the JSON-LD document to link.
    :param ctx: the JSON-LD context to apply or None.
    :param [options]: the options to use.
      [base] the base IRI to use.
      [expandContext] a context to expand with.
      [documentLoader(url)] the document loader
        (default: _default_document_loader).

    :return: the linked JSON-LD output.
    """
    # API matches running frame with a wildcard frame and embed: '@link'
    # get arguments
    frame_ = {'@embed': '@link'}
    if ctx:
        frame_['@context'] = ctx
    frame_['@embed'] = '@link'
    return frame(input_, frame_, options)


def normalize(input_, options=None):
    """
    Performs RDF dataset normalization on the given input. The input is
    JSON-LD unless the 'inputFormat' option is used. The output is an RDF
    dataset unless the 'format' option is used'.

    :param input_: the JSON-LD input to normalize.
    :param [options]: the options to use.
      [algorithm] the algorithm to use: `URDNA2015` or `URGNA2012`
        (default: `URGNA2012`).
      [base] the base IRI to use.
      [inputFormat] the format if input is not JSON-LD:
        'application/n-quads' for N-Quads.
      [format] the format if output is a string:
        'application/n-quads' for N-Quads.
      [documentLoader(url)] the document loader
        (default: _default_document_loader).

    :return: the normalized output.
    """
    return JsonLdProcessor().normalize(input_, options)


def from_rdf(input_, options=None):
    """
    Converts an RDF dataset to JSON-LD.

    :param input_: a serialized string of RDF in a format specified
      by the format option or an RDF dataset to convert.
    :param [options]: the options to use:
      [format] the format if input is a string:
        'application/n-quads' for N-Quads (default: 'application/n-quads').
      [useRdfType] True to use rdf:type, False to use @type (default: False).
      [useNativeTypes] True to convert XSD types into native types
        (boolean, integer, double), False not to (default: True).

    :return: the JSON-LD output.
    """
    return JsonLdProcessor().from_rdf(input_, options)


def to_rdf(input_, options=None):
    """
    Outputs the RDF dataset found in the given JSON-LD object.

    :param input_: the JSON-LD input.
    :param [options]: the options to use.
      [base] the base IRI to use.
      [format] the format to use to output a string:
        'application/n-quads' for N-Quads.
      [produceGeneralizedRdf] true to output generalized RDF, false
        to produce only standard RDF (default: false).
      [documentLoader(url)] the document loader
        (default: _default_document_loader).

    :return: the resulting RDF dataset (or a serialization of it).
    """
    return JsonLdProcessor().to_rdf(input_, options)


def set_document_loader(load_document):
    """
    Sets the default JSON-LD document loader.

    :param load_document(url): the document loader to use.
    """
    global _default_document_loader
    _default_document_loader = load_document


def get_document_loader():
    """
    Gets the default JSON-LD document loader.

    :return: the default document loader.
    """
    return _default_document_loader


def parse_link_header(header):
    """
    Parses a link header. The results will be key'd by the value of "rel".

    Link: <http://json-ld.org/contexts/person.jsonld>; \
      rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"

    Parses as: {
      'http://www.w3.org/ns/json-ld#context': {
        target: http://json-ld.org/contexts/person.jsonld,
        type: 'application/ld+json'
      }
    }

    If there is more than one "rel" with the same IRI, then entries in the
    resulting map for that "rel" will be lists.

    :param header: the link header to parse.

    :return: the parsed result.
    """
    rval = {}
    # split on unbracketed/unquoted commas
    entries = re.findall(r'(?:<[^>]*?>|"[^"]*?"|[^,])+', header)
    if not entries:
        return rval
    r_link_header = r'\s*<([^>]*?)>\s*(?:;\s*(.*))?'
    for entry in entries:
        match = re.search(r_link_header, entry)
        if not match:
            continue
        match = match.groups()
        result = {'target': match[0]}
        params = match[1]
        r_params = r'(.*?)=(?:(?:"([^"]*?)")|([^"]*?))\s*(?:(?:;\s*)|$)'
        matches = re.findall(r_params, params)
        for match in matches:
            result[match[0]] = match[2] if match[1] is None else match[1]
        rel = result.get('rel', '')
        if isinstance(rval.get(rel), list):
            rval[rel].append(result)
        elif rel in rval:
            rval[rel] = [rval[rel], result]
        else:
            rval[rel] = result
    return rval


def dummy_document_loader(**kwargs):
    """
    Create a dummy document loader that will raise an exception on use.

    :param **kwargs: extra keyword args

    :return: the RemoteDocument loader function.
    """

    def loader(url):
        """
        Raises an exception on every call.

        :param url: the URL to retrieve.

        :return: the RemoteDocument.
        """
        raise JsonLdError('No default document loader configured',
                          {'url': url}, code='no default document loader')

    return loader


def requests_document_loader(**kwargs):
    import pyld.documentloader.requests

    return pyld.documentloader.requests.requests_document_loader(**kwargs)


def aiohttp_document_loader(**kwargs):
    import pyld.documentloader.aiohttp

    return pyld.documentloader.aiohttp.aiohttp_document_loader(**kwargs)


def register_rdf_parser(content_type, parser):
    """
    Registers a global RDF parser by content-type, for use with
    from_rdf. Global parsers will be used by JsonLdProcessors that
    do not register their own parsers.

    :param content_type: the content-type for the parser.
    :param parser(input): the parser function (takes a string as
             a parameter and returns an RDF dataset).
    """
    global _rdf_parsers
    _rdf_parsers[content_type] = parser


def unregister_rdf_parser(content_type):
    """
    Unregisters a global RDF parser by content-type.

    :param content_type: the content-type for the parser.
    """
    global _rdf_parsers
    if content_type in _rdf_parsers:
        del _rdf_parsers[content_type]


def prepend_base(base, iri):
    """
    Prepends a base IRI to the given relative IRI.

    :param base: the base IRI.
    :param iri: the relative IRI.

    :return: the absolute IRI.
    """
    # skip IRI processing
    if base is None:
        return iri

    # already an absolute iri
    if _is_absolute_iri(iri):
        return iri

    # parse IRIs
    base = parse_url(base)
    rel = parse_url(iri)

    # per RFC3986 5.2.2
    transform = {
        'scheme': base.scheme
    }

    if rel.authority is not None:
        transform['authority'] = rel.authority
        transform['path'] = rel.path
        transform['query'] = rel.query
    else:
        transform['authority'] = base.authority

        if rel.path == '':
            transform['path'] = base.path
            if rel.query is not None:
                transform['query'] = rel.query
            else:
                transform['query'] = base.query
        else:
            if rel.path.startswith('/'):
                # IRI represents an absolute path
                transform['path'] = rel.path
            else:
                # merge paths
                path = base.path

                # append relative path to the end of the last directory from
                # base
                path = path[0:path.rfind('/') + 1]
                if len(path) > 0 and not path.endswith('/'):
                    path += '/'
                path += rel.path

                transform['path'] = path

            transform['query'] = rel.query

    if rel.path != '':
        # normalize path
        transform['path'] = remove_dot_segments(transform['path'])

    transform['fragment'] = rel.fragment

    # construct URL
    rval = unparse_url(transform)

    # handle empty base case
    if rval == '':
        rval = './'

    return rval


def remove_base(base, iri):
    """
    Removes a base IRI from the given absolute IRI.

    :param base: the base IRI.
    :param iri: the absolute IRI.

    :return: the relative IRI if relative to base, otherwise the absolute IRI.
    """
    # TODO: better sync with jsonld.js version
    # skip IRI processing
    if base is None:
        return iri

    base = parse_url(base)
    rel = parse_url(iri)

    # schemes and network locations (authorities) don't match, don't alter IRI
    if not (base.scheme == rel.scheme and base.authority == rel.authority):
        return iri

    # remove path segments that match (do not remove last segment unless there
    # is a hash or query
    base_segments = remove_dot_segments(base.path).split('/')
    iri_segments = remove_dot_segments(rel.path).split('/')
    last = 0 if (rel.fragment or rel.query) else 1
    while (len(base_segments) and len(iri_segments) > last and
            base_segments[0] == iri_segments[0]):
        base_segments.pop(0)
        iri_segments.pop(0)

    # use '../' for each non-matching base segment
    rval = ''
    if len(base_segments):
        # don't count the last segment (if it ends with '/' last path doesn't
        # count and if it doesn't end with '/' it isn't a path)
        base_segments.pop()
        rval += '../' * len(base_segments)

    # prepend remaining segments
    rval += '/'.join(iri_segments)

    return unparse_url((None, None, rval, rel.query, rel.fragment)) or './'


def remove_dot_segments(path):
    """
    Removes dot segments from a URL path.

    :param path: the path to remove dot segments from.

    :return: a path with normalized dot segments.
    """

    # RFC 3984 5.2.4 (reworked)

    # empty path shortcut
    if len(path) == 0:
        return ''

    input = path.split('/')
    output = []

    while len(input) > 0:
        next = input.pop(0)
        done = len(input) == 0

        if next == '.':
            if done:
                # ensure output has trailing /
                output.append('')
            continue

        if next == '..':
            if len(output) > 0:
                output.pop()
            if done:
                # ensure output has trailing /
                output.append('')
            continue

        output.append(next)

    # ensure output has leading /
    if len(output) > 0 and output[0] != '':
        output.insert(0, '')
    if len(output) is 1 and output[0] == '':
        return '/'

    return '/'.join(output)


ParsedUrl = namedtuple(
    'ParsedUrl', ['scheme', 'authority', 'path', 'query', 'fragment'])


def parse_url(url):
    # regex from RFC 3986
    p = r'^(?:([^:/?#]+):)?(?://([^/?#]*))?([^?#]*)(?:\?([^#]*))?(?:#(.*))?'
    m = re.match(p, url)
    # remove default http and https ports
    g = list(m.groups())
    if ((g[0] == 'https' and g[1].endswith(':443')) or
            (g[0] == 'http' and g[1].endswith(':80'))):
        g[1] = g[1][:g[1].rfind(':')]
    return ParsedUrl(*g)


def unparse_url(parsed):
    if isinstance(parsed, dict):
        parsed = ParsedUrl(**parsed)
    elif isinstance(parsed, list) or isinstance(parsed, tuple):
        parsed = ParsedUrl(*parsed)
    rval = ''
    if parsed.scheme:
        rval += parsed.scheme + ':'
    if parsed.authority is not None:
        rval += '//' + parsed.authority
    rval += parsed.path
    if parsed.query is not None:
        rval += '?' + parsed.query
    if parsed.fragment is not None:
        rval += '#' + parsed.fragment
    return rval


# The default JSON-LD document loader.
try:
    _default_document_loader = requests_document_loader()
except ImportError:
    try:
        _default_document_loader = aiohttp_document_loader()
    except (ImportError, SyntaxError):
        _default_document_loader = dummy_document_loader()

# Use default document loader for older exposed load_document API
load_document = _default_document_loader

# Registered global RDF parsers hashed by content-type.
_rdf_parsers = {}


class JsonLdProcessor(object):
    """
    A JSON-LD processor.
    """

    def __init__(self):
        """
        Initialize the JSON-LD processor.
        """
        # processor-specific RDF parsers
        self.rdf_parsers = None

    def compact(self, input_, ctx, options):
        """
        Performs JSON-LD compaction.

        :param input_: the JSON-LD input to compact.
        :param ctx: the context to compact with.
        :param options: the options to use.
          [base] the base IRI to use.
          [compactArrays] True to compact arrays to single values when
            appropriate, False not to (default: True).
          [graph] True to always output a top-level graph (default: False).
          [expandContext] a context to expand with.
          [skipExpansion] True to assume the input is expanded and skip
            expansion, False not to, (default: False).
          [activeCtx] True to also return the active context used.
          [documentLoader(url)] the document loader
            (default: _default_document_loader).

        :return: the compacted JSON-LD output.
        """
        if ctx is None:
            raise JsonLdError(
                'The compaction context must not be null.',
                'jsonld.CompactError', code='invalid local context')

        # nothing to compact
        if input_ is None:
            return None

        # set default options
        options = options.copy() if options else {}
        options.setdefault('base', input_ if _is_string(input_) else '')
        options.setdefault('compactArrays', True)
        options.setdefault('graph', False)
        options.setdefault('skipExpansion', False)
        options.setdefault('activeCtx', False)
        options.setdefault('documentLoader', _default_document_loader)
        options.setdefault('link', False)
        if options['link']:
            # force skip expansion when linking, "link" is not part of the
            # public API, it should only be called from framing
            options['skipExpansion'] = True

        if options['skipExpansion']:
            expanded = input_
        else:
            # expand input
            try:
                expanded = self.expand(input_, options)
            except JsonLdError as cause:
                raise JsonLdError(
                    'Could not expand input before compaction.',
                    'jsonld.CompactError', cause=cause)

        # process context
        active_ctx = self._get_initial_context(options)
        try:
            active_ctx = self.process_context(active_ctx, ctx, options)
        except JsonLdError as cause:
            raise JsonLdError(
                'Could not process context before compaction.',
                'jsonld.CompactError', cause=cause)

        # do compaction
        compacted = self._compact(active_ctx, None, expanded, options)

        if (options['compactArrays'] and not options['graph'] and
                _is_array(compacted)):
            # simplify to a single item
            if len(compacted) == 1:
                compacted = compacted[0]
            # simplify to an empty object
            elif len(compacted) == 0:
                compacted = {}
        # always use an array if graph options is on
        elif options['graph']:
            compacted = JsonLdProcessor.arrayify(compacted)

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

        # add context and/or @graph
        if _is_array(compacted):
            # use '@graph' keyword
            kwgraph = self._compact_iri(active_ctx, '@graph')
            graph = compacted
            compacted = {}
            if has_context:
                compacted['@context'] = ctx
            compacted[kwgraph] = graph
        elif _is_object(compacted) and has_context:
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

    def expand(self, input_, options):
        """
        Performs JSON-LD expansion.

        :param input_: the JSON-LD input to expand.
        :param options: the options to use.
          [base] the base IRI to use.
          [expandContext] a context to expand with.
          [isFrame] True to allow framing keywords and interpretation,
            False not to (default: false).
          [keepFreeFloatingNodes] True to keep free-floating nodes,
            False not to (default: False).
          [documentLoader(url)] the document loader
            (default: _default_document_loader).

        :return: the expanded JSON-LD output.
        """
        # set default options
        options = options.copy() if options else {}
        options.setdefault('isFrame', False)
        options.setdefault('keepFreeFloatingNodes', False)
        options.setdefault('documentLoader', _default_document_loader)

        # if input is a string, attempt to dereference remote document
        if _is_string(input_):
            remote_doc = options['documentLoader'](input_)
        else:
            remote_doc = {
                'contextUrl': None,
                'documentUrl': None,
                'document': input_
            }

        try:
            if remote_doc['document'] is None:
                raise JsonLdError(
                    'No remote document found at the given URL.',
                    'jsonld.NullRemoteDocument')
            if _is_string(remote_doc['document']):
                remote_doc['document'] = json.loads(remote_doc['document'])
        except Exception as cause:
            raise JsonLdError(
                'Could not retrieve a JSON-LD document from the URL.',
                'jsonld.LoadDocumentError',
                {'remoteDoc': remote_doc}, code='loading document failed',
                cause=cause)

        # set default base
        options.setdefault('base', remote_doc['documentUrl'] or '')

        # build meta-object and retrieve all @context urls
        input_ = {
            'document': copy.deepcopy(remote_doc['document']),
            'remoteContext': {'@context': remote_doc['contextUrl']}
        }
        if 'expandContext' in options:
            expand_context = copy.deepcopy(options['expandContext'])
            if _is_object(expand_context) and '@context' in expand_context:
                input_['expandContext'] = expand_context
            else:
                input_['expandContext'] = {'@context': expand_context}

        try:
            self._retrieve_context_urls(
                input_, {}, options['documentLoader'], options['base'])
        except Exception as cause:
            raise JsonLdError(
                'Could not perform JSON-LD expansion.',
                'jsonld.ExpandError', cause=cause)

        active_ctx = self._get_initial_context(options)
        document = input_['document']
        remote_context = input_['remoteContext']['@context']

        # process optional expandContext
        if 'expandContext' in input_:
            active_ctx = self.process_context(
                active_ctx, input_['expandContext']['@context'], options)

        # process remote context from HTTP Link Header
        if remote_context is not None:
            active_ctx = self.process_context(
                active_ctx, remote_context, options)

        # do expansion
        expanded = self._expand(active_ctx, None, document, options, False)

        # optimize away @graph with no other properties
        if (_is_object(expanded) and '@graph' in expanded and
                len(expanded) == 1):
            expanded = expanded['@graph']
        elif expanded is None:
            expanded = []

        # normalize to an array
        return JsonLdProcessor.arrayify(expanded)

    def flatten(self, input_, ctx, options):
        """
        Performs JSON-LD flattening.

        :param input_: the JSON-LD input to flatten.
        :param ctx: the JSON-LD context to compact with (default: None).
        :param options: the options to use.
          [base] the base IRI to use.
          [expandContext] a context to expand with.
          [documentLoader(url)] the document loader
            (default: _default_document_loader).

        :return: the flattened JSON-LD output.
        """
        options = options.copy() if options else {}
        options.setdefault('base', input_ if _is_string(input_) else '')
        options.setdefault('documentLoader', _default_document_loader)

        try:
            # expand input
            expanded = self.expand(input_, options)
        except Exception as cause:
            raise JsonLdError(
                'Could not expand input before flattening.',
                'jsonld.FlattenError', cause=cause)

        # do flattening
        flattened = self._flatten(expanded)

        if ctx is None:
            return flattened

        # compact result (force @graph option to true, skip expansion)
        options['graph'] = True
        options['skipExpansion'] = True
        try:
            compacted = self.compact(flattened, ctx, options)
        except Exception as cause:
            raise JsonLdError(
                'Could not compact flattened output.',
                'jsonld.FlattenError', cause=cause)

        return compacted

    def frame(self, input_, frame, options):
        """
        Performs JSON-LD framing.

        :param input_: the JSON-LD object to frame.
        :param frame: the JSON-LD frame to use.
        :param options: the options to use.
          [base] the base IRI to use.
          [expandContext] a context to expand with.
          [embed] default @embed flag: '@last', '@always', '@never', '@link'
            (default: '@last').
          [explicit] default @explicit flag (default: False).
          [requireAll] default @requireAll flag (default: True).
          [omitDefault] default @omitDefault flag (default: False).
          [pruneBlankNodeIdentifiers] remove unnecessary blank node identifiers (default: True)
          [documentLoader(url)] the document loader
            (default: _default_document_loader).

        :return: the framed JSON-LD output.
        """
        # set default options
        options = options.copy() if options else {}
        options.setdefault('base', input_ if _is_string(input_) else '')
        options.setdefault('compactArrays', True)
        options.setdefault('embed', '@last')
        options.setdefault('explicit', False)
        options.setdefault('requireAll', True)
        options.setdefault('omitDefault', False)
        options.setdefault('pruneBlankNodeIdentifiers', True)
        options.setdefault('bnodesToClear', [])
        options.setdefault('documentLoader', _default_document_loader)

        # if frame is a string, attempt to dereference remote document
        if _is_string(frame):
            remote_frame = options['documentLoader'](frame)
        else:
            remote_frame = {
                'contextUrl': None,
                'documentUrl': None,
                'document': frame
            }

        try:
            if remote_frame['document'] is None:
                raise JsonLdError(
                    'No remote document found at the given URL.',
                    'jsonld.NullRemoteDocument')
            if _is_string(remote_frame['document']):
                remote_frame['document'] = json.loads(remote_frame['document'])
        except Exception as cause:
            raise JsonLdError(
                'Could not retrieve a JSON-LD document from the URL.',
                'jsonld.LoadDocumentError',
                {'remoteDoc': remote_frame}, code='loading document failed',
                cause=cause)

        # preserve frame context
        frame = remote_frame['document']
        if frame is not None:
            ctx = frame.get('@context', {})
            if remote_frame['contextUrl'] is not None:
                if ctx is not None:
                    ctx = remote_frame['contextUrl']
                else:
                    ctx = JsonLdProcessor.arrayify(ctx)
                    ctx.append(remote_frame['contextUrl'])
                frame['@context'] = ctx

        try:
            # expand input
            expanded = self.expand(input_, options)
        except JsonLdError as cause:
            raise JsonLdError(
                'Could not expand input before framing.',
                'jsonld.FrameError', cause=cause)

        try:
            # expand frame
            opts = copy.deepcopy(options)
            opts['isFrame'] = True
            opts['keepFreeFloatingNodes'] = True
            expanded_frame = self.expand(frame, opts)
        except JsonLdError as cause:
            raise JsonLdError(
                'Could not expand frame before framing.',
                'jsonld.FrameError', cause=cause)

        # do framing
        # FIXME should look for aliases of @graph
        options['merged'] = '@graph' not in frame
        framed = self._frame(expanded, expanded_frame, options)

        try:
            # compact result (force @graph option to True, skip expansion,
            # check for linked embeds)
            options['graph'] = True
            options['skipExpansion'] = True
            options['link'] = {}
            options['activeCtx'] = True
            result = self.compact(framed, ctx, options)
        except JsonLdError as cause:
            raise JsonLdError(
                'Could not compact framed output.',
                'jsonld.FrameError', cause=cause)

        compacted = result['compacted']
        active_ctx = result['activeCtx']

        # get graph alias
        graph = self._compact_iri(active_ctx, '@graph')
        # remove @preserve from results
        compacted[graph] = self._remove_preserve(
            active_ctx, compacted[graph], options)
        return compacted

    def normalize(self, input_, options):
        """
        Performs RDF dataset normalization on the given input. The input is
        JSON-LD unless the 'inputFormat' option is used. The output is an RDF
        dataset unless the 'format' option is used'.

        :param input_: the JSON-LD input to normalize.
        :param options: the options to use.
          [algorithm] the algorithm to use: `URDNA2015` or `URGNA2012`
            (default: `URGNA2012`).
          [base] the base IRI to use.
          [inputFormat] the format if input is not JSON-LD:
            'application/n-quads' for N-Quads.
          [format] the format if output is a string:
            'application/n-quads' for N-Quads.
          [documentLoader(url)] the document loader
            (default: _default_document_loader).

        :return: the normalized output.
        """
        # set default options
        options = options.copy() if options else {}
        options.setdefault('algorithm', 'URGNA2012')
        options.setdefault('base', input_ if _is_string(input_) else '')
        options.setdefault('documentLoader', _default_document_loader)

        if not options['algorithm'] in ['URDNA2015', 'URGNA2012']:
            raise JsonLdError(
                'Unsupported normalization algorithm.',
                'jsonld.NormalizeError')

        try:
            if 'inputFormat' in options:
                if (options['inputFormat'] != 'application/n-quads' and
                        options['inputFormat'] != 'application/nquads'):
                    raise JsonLdError(
                        'Unknown normalization input format.',
                        'jsonld.NormalizeError')
                dataset = JsonLdProcessor.parse_nquads(input_)
            else:
                # convert to RDF dataset then do normalization
                opts = copy.deepcopy(options)
                if 'format' in opts:
                    del opts['format']
                opts['produceGeneralizedRdf'] = False
                dataset = self.to_rdf(input_, opts)
        except JsonLdError as cause:
            raise JsonLdError(
                'Could not convert input to RDF dataset before normalization.',
                'jsonld.NormalizeError', cause=cause)

        # do normalization
        if options['algorithm'] == 'URDNA2015':
            return URDNA2015().main(dataset, options)
        # assume URGNA2012
        return URGNA2012().main(dataset, options)

    def from_rdf(self, dataset, options):
        """
        Converts an RDF dataset to JSON-LD.

        :param dataset: a serialized string of RDF in a format specified by
          the format option or an RDF dataset to convert.
        :param options: the options to use.
          [format] the format if input is a string:
            'application/n-quads' for N-Quads (default: 'application/n-quads').
          [useRdfType] True to use rdf:type, False to use @type
            (default: False).
          [useNativeTypes] True to convert XSD types into native types
            (boolean, integer, double), False not to (default: False).

        :return: the JSON-LD output.
        """
        global _rdf_parsers

        # set default options
        options = options.copy() if options else {}
        options.setdefault('useRdfType', False)
        options.setdefault('useNativeTypes', False)

        if ('format' not in options) and _is_string(dataset):
            options['format'] = 'application/n-quads'

        # handle special format
        if 'format' in options:
            # supported formats (processor-specific and global)
            if ((self.rdf_parsers is not None and
                not options['format'] in self.rdf_parsers) or
                (self.rdf_parsers is None and
                    not options['format'] in _rdf_parsers)):
                raise JsonLdError(
                    'Unknown input format.',
                    'jsonld.UnknownFormat', {'format': options['format']})

            if self.rdf_parsers is not None:
                parser = self.rdf_parsers[options['format']]
            else:
                parser = _rdf_parsers[options['format']]
            dataset = parser(dataset)

        # convert from RDF
        return self._from_rdf(dataset, options)

    def to_rdf(self, input_, options):
        """
        Outputs the RDF dataset found in the given JSON-LD object.

        :param input_: the JSON-LD input.
        :param options: the options to use.
          [base] the base IRI to use.
          [format] the format if input is a string:
            'application/n-quads' for N-Quads.
          [produceGeneralizedRdf] true to output generalized RDF, false
            to produce only standard RDF (default: false).
          [documentLoader(url)] the document loader
            (default: _default_document_loader).

        :return: the resulting RDF dataset (or a serialization of it).
        """
        # set default options
        options = options.copy() if options else {}
        options.setdefault('base', input_ if _is_string(input_) else '')
        options.setdefault('produceGeneralizedRdf', False)
        options.setdefault('documentLoader', _default_document_loader)

        try:
            # expand input
            expanded = self.expand(input_, options)
        except JsonLdError as cause:
            raise JsonLdError(
                'Could not expand input before serialization to '
                'RDF.', 'jsonld.RdfError', cause=cause)

        # create node map for default graph (and any named graphs)
        issuer = IdentifierIssuer('_:b')
        node_map = {'@default': {}}
        self._create_node_map(expanded, node_map, '@default', issuer)

        # output RDF dataset
        dataset = {}
        for graph_name, graph in sorted(node_map.items()):
            # skip relative IRIs
            if graph_name == '@default' or _is_absolute_iri(graph_name):
                dataset[graph_name] = self._graph_to_rdf(
                    graph, issuer, options)

        # convert to output format
        if 'format' in options:
            if (options['format'] == 'application/n-quads' or
                    options['format'] == 'application/nquads'):
                return self.to_nquads(dataset)
            raise JsonLdError(
                'Unknown output format.',
                'jsonld.UnknownFormat', {'format': options['format']})
        return dataset

    def process_context(self, active_ctx, local_ctx, options):
        """
        Processes a local context, retrieving any URLs as necessary, and
        returns a new active context in its callback.

        :param active_ctx: the current active context.
        :param local_ctx: the local context to process.
        :param options: the options to use.
          [documentLoader(url)] the document loader
            (default: _default_document_loader).

        :return: the new active context.
        """
        # return initial context early for None context
        if local_ctx is None:
            return self._get_initial_context(options)

        # set default options
        options = options.copy() if options else {}
        options.setdefault('base', '')
        options.setdefault('documentLoader', _default_document_loader)

        # retrieve URLs in local_ctx
        local_ctx = copy.deepcopy(local_ctx)
        if (_is_string(local_ctx) or (
                _is_object(local_ctx) and '@context' not in local_ctx)):
            local_ctx = {'@context': local_ctx}
        try:
            self._retrieve_context_urls(
                local_ctx, {}, options['documentLoader'], options['base'])
        except Exception as cause:
            raise JsonLdError(
                'Could not process JSON-LD context.',
                'jsonld.ContextError', cause=cause)

        # process context
        return self._process_context(active_ctx, local_ctx, options)

    def register_rdf_parser(self, content_type, parser):
        """
        Registers a processor-specific RDF parser by content-type.
        Global parsers will no longer be used by this processor.

        :param content_type: the content-type for the parser.
        :param parser(input): the parser function (takes a string as
                 a parameter and returns an RDF dataset).
        """
        if self.rdf_parsers is None:
            self.rdf_parsers = {}
            self.rdf_parsers[content_type] = parser

    def unregister_rdf_parser(self, content_type):
        """
        Unregisters a process-specific RDF parser by content-type.
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
        if JsonLdProcessor.has_property(subject, property):
            val = subject[property]
            is_list = _is_list(val)
            if _is_array(val) or is_list:
                if is_list:
                    val = val['@list']
                for v in val:
                    if JsonLdProcessor.compare_values(value, v):
                        return True
            # avoid matching the set of values with an array value parameter
            elif not _is_array(value):
                return JsonLdProcessor.compare_values(value, val)
        return False

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
            has_value = (
                    not options['allowDuplicate'] and
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
        return JsonLdProcessor.arrayify(subject.get(property) or [])

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
        values = list(filter(filter_value, values))

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
        2. They are both @values with the same @value, @type, @language,
          and @index, OR
        3. They both have @ids that are the same.

        :param v1: the first value.
        :param v2: the second value.

        :return: True if v1 and v2 are considered equal, False if not.
        """
        # 1. equal primitives
        if not _is_object(v1) and not _is_object(v2) and v1 == v2:
            type1 = type(v1)
            type2 = type(v2)
            if type1 == bool or type2 == bool:
                return type1 == type2
            return True

        # 2. equal @values
        if (_is_value(v1) and _is_value(v2) and
                v1['@value'] == v2['@value'] and
                v1.get('@type') == v2.get('@type') and
                v1.get('@language') == v2.get('@language') and
                v1.get('@index') == v2.get('@index')):
            type1 = type(v1['@value'])
            type2 = type(v2['@value'])
            if type1 == bool or type2 == bool:
                return type1 == type2
            return True

        # 3. equal @ids
        if (_is_object(v1) and '@id' in v1 and
                _is_object(v2) and '@id' in v2):
            return v1['@id'] == v2['@id']

        return False

    @staticmethod
    def get_context_value(ctx, key, type_):
        """
        Gets the value for the given active context key and type, None if none
        is set.

        :param ctx: the active context.
        :param key: the context key.
        :param [type_]: the type of value to get (eg: '@id', '@type'), if not
          specified gets the entire entry for a key, None if not found.

        :return: mixed the value.
        """
        rval = None

        # return None for invalid key
        if key is None:
            return rval

        # get default language
        if type_ == '@language' and type_ in ctx:
            rval = ctx[type_]

        # get specific entry information
        if key in ctx['mappings']:
            entry = ctx['mappings'][key]
            if entry is None:
                return None

            # return whole entry
            if type_ is None:
                rval = entry
            # return entry value for type
            elif type_ in entry:
                rval = entry[type_]

        return rval

    @staticmethod
    def parse_nquads(input_):
        """
        Parses RDF in the form of N-Quads.

        :param input_: the N-Quads input to parse.

        :return: an RDF dataset.
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
        eoln = r'(?:\r\n)|(?:\n)|(?:\r)'
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
        lines = re.split(eoln, input_)
        line_number = 0
        for line in lines:
            line_number += 1

            # skip empty lines
            if re.search(empty, line) is not None:
                continue

            # parse quad
            match = re.search(quad, line)
            if match is None:
                raise JsonLdError(
                    'Error while parsing N-Quads invalid quad.',
                    'jsonld.ParseError', {'line': line_number})
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
                unescaped = (
                    match[5]
                    .replace('\\"', '\"')
                    .replace('\\t', '\t')
                    .replace('\\n', '\n')
                    .replace('\\r', '\r')
                    .replace('\\\\', '\\'))
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
                    if JsonLdProcessor._compare_rdf_triples(t, triple):
                        unique = False
                        break
                if unique:
                    triples.append(triple)

        return dataset

    @staticmethod
    def to_nquads(dataset):
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
                quads.append(JsonLdProcessor.to_nquad(triple, graph_name))
        quads.sort()
        return ''.join(quads)

    @staticmethod
    def to_nquad(triple, graph_name=None):
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
            escaped = (
                o['value']
                .replace('\\', '\\\\')
                .replace('\t', '\\t')
                .replace('\n', '\\n')
                .replace('\r', '\\r')
                .replace('\"', '\\"'))
            quad += '"' + escaped + '"'
            if o['datatype'] == RDF_LANGSTRING:
                if o['language']:
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

    def _compact(self, active_ctx, active_property, element, options):
        """
        Recursively compacts an element using the given active context. All
        values must be in expanded form before this method is called.

        :param active_ctx: the active context to use.
        :param active_property: the compacted property with the element to
          compact, None for none.
        :param element: the element to compact.
        :param options: the compaction options.

        :return: the compacted value.
        """
        # recursively compact array
        if _is_array(element):
            rval = []
            for e in element:
                # compact, dropping any None values
                e = self._compact(active_ctx, active_property, e, options)
                if e is not None:
                    rval.append(e)
            if options['compactArrays'] and len(rval) == 1:
                # use single element if no container is specified
                container = JsonLdProcessor.arrayify(
                    JsonLdProcessor.get_context_value(
                        active_ctx, active_property, '@container'))
                if not container:
                    rval = rval[0]
            return rval

        # use any scoped context on active_property
        ctx = JsonLdProcessor.get_context_value(active_ctx, active_property, '@context')
        if ctx:
            active_ctx = self._process_context(
                active_ctx, ctx, options)

        # recursively compact object
        if _is_object(element):
            if(options['link'] and '@id' in element and
                    element['@id'] in options['link']):
                # check for a linked element to reuse
                linked = options['link'][element['@id']]
                for link in linked:
                    if link['expanded'] == element:
                        return link['compacted']

            # do value compaction on @values and subject references
            if _is_value(element) or _is_subject_reference(element):
                rval = self._compact_value(
                    active_ctx, active_property, element)
                if options['link'] and _is_subject_reference(element):
                    # store linked element
                    options['link'].setdefault(element['@id'], []).append(
                        {'expanded': element, 'compacted': rval})
                return rval

            # FIXME: avoid misuse of active property as an expanded property?
            inside_reverse = (active_property == '@reverse')

            rval = {}

            if options['link'] and '@id' in element:
                # store linked element
                options['link'].setdefault(element['@id'], []).append(
                    {'expanded': element, 'compacted': rval})

            # apply any context defined on an alias of @type
            # if key is @type and any compacted value is a term having a local
            # context, overlay that context
            for type in element.get('@type', []):
                compacted_type = self._compact_iri(active_ctx, type, vocab=True)

                # use any scoped context defined on this value
                ctx = JsonLdProcessor.get_context_value(
                        active_ctx, compacted_type, '@context')
                if ctx:
                    active_ctx = self._process_context(active_ctx, ctx, options)

            # recursively process element keys in order
            for expanded_property, expanded_value in sorted(element.items()):
                # compact @id and @type(s)
                if expanded_property == '@id' or expanded_property == '@type':

                    compacted_value = [
                            self._compact_iri(
                                active_ctx, expanded_iri,
                                vocab=(expanded_property == '@type'))
                            for expanded_iri in
                            JsonLdProcessor.arrayify(expanded_value)]
                    if len(compacted_value) == 1:
                        compacted_value = compacted_value[0]

                    # use keyword alias and add value
                    alias = self._compact_iri(active_ctx, expanded_property)
                    is_array = (
                            _is_array(compacted_value) and
                            len(compacted_value) == 0)
                    JsonLdProcessor.add_value(
                        rval, alias, compacted_value,
                        {'propertyIsArray': is_array})
                    continue

                # handle @reverse
                if expanded_property == '@reverse':
                    # recursively compact expanded value
                    compacted_value = self._compact(
                        active_ctx, '@reverse', expanded_value, options)

                    # handle double-reversed properties
                    for compacted_property, value in \
                            list(compacted_value.items()):
                        mapping = active_ctx['mappings'].get(
                            compacted_property)
                        if mapping and mapping['reverse']:
                            container = JsonLdProcessor.arrayify(
                                JsonLdProcessor.get_context_value(
                                    active_ctx, compacted_property, '@container'))
                            use_array = (
                                    '@set' in container or
                                    not options['compactArrays'])
                            JsonLdProcessor.add_value(
                                rval, compacted_property, value,
                                {'propertyIsArray': use_array})
                            del compacted_value[compacted_property]

                    if len(compacted_value.keys()) > 0:
                        # use keyword alias and add value
                        alias = self._compact_iri(
                            active_ctx, expanded_property)
                        JsonLdProcessor.add_value(rval, alias, compacted_value)

                    continue

                if expanded_property == '@preserve':
                    # compact using active_property
                    compacted_value = self._compact(
                        active_ctx, active_property, expanded_value, options)
                    if not (_is_array(compacted_value) and len(compacted_value) == 0):
                        JsonLdProcessor.add_value(rval, expanded_property, compacted_value)
                    continue

                # handle @index
                if expanded_property == '@index':
                    # drop @index if inside an @index container
                    container = JsonLdProcessor.arrayify(
                        JsonLdProcessor.get_context_value(
                            active_ctx, active_property, '@container'))
                    if '@index' in container:
                        continue

                    # use keyword alias and add value
                    alias = self._compact_iri(active_ctx, expanded_property)
                    JsonLdProcessor.add_value(rval, alias, expanded_value)
                    continue

                # skip array processing for keywords that aren't @graph or
                # @list
                if(expanded_property != '@graph' and
                        expanded_property != '@list' and
                        _is_keyword(expanded_property)):
                    # use keyword alias and add value as is
                    alias = self._compact_iri(active_ctx, expanded_property)
                    JsonLdProcessor.add_value(rval, alias, expanded_value)
                    continue

                # Note: expanded value must be an array due to expansion
                # algorithm.

                # preserve empty arrays
                if len(expanded_value) == 0:
                    item_active_property = self._compact_iri(
                        active_ctx, expanded_property, expanded_value,
                        vocab=True, reverse=inside_reverse)
                    nest_result = rval
                    nest_property = active_ctx['mappings'].get(item_active_property, {}).get('@nest')
                    if nest_property:
                        self._check_nest_property(active_ctx, nest_property)
                        if not _is_object(rval.get(nest_property)):
                            rval[nest_property] = {}
                        nest_result = rval[nest_property]
                    JsonLdProcessor.add_value(
                        nest_result, item_active_property, [],
                        {'propertyIsArray': True})

                # recusively process array values
                for expanded_item in expanded_value:
                    # compact property and get container type
                    item_active_property = self._compact_iri(
                        active_ctx, expanded_property, expanded_item,
                        vocab=True, reverse=inside_reverse)

                    # if item_active_property is a @nest property, add values to nestResult, otherwise rval
                    nest_result = rval
                    nest_property = active_ctx['mappings'].get(item_active_property, {}).get('@nest')
                    if nest_property:
                        self._check_nest_property(active_ctx, nest_property)
                        if not _is_object(rval.get(nest_property)):
                            rval[nest_property] = {}
                        nest_result = rval[nest_property]

                    container = JsonLdProcessor.arrayify(
                        JsonLdProcessor.get_context_value(
                            active_ctx, item_active_property, '@container'))

                    # get simple @graph or @list value if appropriate
                    is_graph = _is_graph(expanded_item)
                    is_list = _is_list(expanded_item)
                    inner_ = None
                    if is_list:
                        inner_ = expanded_item['@list']
                    elif is_graph:
                        inner_ = expanded_item['@graph']

                    # recursively compact expanded item
                    compacted_item = self._compact(
                        active_ctx, item_active_property,
                        inner_ if (is_list or is_graph) else expanded_item, options)

                    # handle @list
                    if is_list:
                        # ensure @list is an array
                        compacted_item = JsonLdProcessor.arrayify(
                            compacted_item)

                        if '@list' not in container:
                            # wrap using @list alias
                            wrapper = {}
                            wrapper[self._compact_iri(
                                active_ctx, '@list')] = compacted_item
                            compacted_item = wrapper

                            # include @index from expanded @list, if any
                            if '@index' in expanded_item:
                                alias = self._compact_iri(active_ctx, '@index')
                                compacted_item[alias] = (
                                    expanded_item['@index'])
                        # can't use @list container for more than 1 list
                        elif item_active_property in nest_result:
                            raise JsonLdError(
                                'JSON-LD compact error; property has a '
                                '"@list" @container rule but there is more '
                                'than a single @list that matches the '
                                'compacted term in the document. Compaction '
                                'might mix unwanted items into the list.',
                                'jsonld.SyntaxError',
                                code='compaction to list of lists')

                    # graph object compaction
                    if is_graph:
                        as_array = not options['compactArrays'] or '@set' in container
                        if ('@graph' in container and
                            ('@id' in container or '@index' in container and _is_simple_graph(expanded_item))):
                            map_object = {}
                            if item_active_property in nest_result:
                                map_object = nest_result[item_active_property]
                            else:
                                nest_result[item_active_property] = map_object

                            # index on @id or @index or alias of @none
                            key = expanded_item.get(
                                ('@id' if '@id' in container else '@index'),
                                self._compact_iri(active_ctx, '@none'))
                            # add compactedItem to map, using value of `@id`
                            # or a new blank node identifier
                            JsonLdProcessor.add_value(
                                map_object, key, compacted_item,
                                {'propertyIsArray': as_array})
                        elif '@graph' in container and _is_simple_graph(expanded_item):
                            JsonLdProcessor.add_value(
                                nest_result, item_active_property, compacted_item,
                                {'propertyIsArray': as_array})
                        else:
                            # wrap using @graph alias, remove array if only one
                            # item and compactArrays not set
                            if (_is_array(compacted_item) and
                                    len(compacted_item) == 1 and
                                    options['compactArrays']):
                                compacted_item = compacted_item[0];
                            compacted_item = {
                                self._compact_iri(active_ctx, '@graph'): compacted_item
                            }

                            # include @id from expanded graph, if any
                            if '@id' in expanded_item:
                                compacted_item[self._compact_iri(active_ctx, '@id')] = expanded_item['@id']

                            # include @index from expanded graph, if any
                            if '@index' in expanded_item:
                                compacted_item[self._compact_iri(active_ctx, '@index')] = expanded_item['@index']

                            JsonLdProcessor.add_value(
                                nest_result, item_active_property, compacted_item,
                                {'propertyIsArray': as_array})

                    # handle language index, id and type maps
                    elif ('@language' in container or '@index' in container or
                            '@id' in container or '@type' in container):
                        # get or create the map object
                        map_object = nest_result.setdefault(item_active_property, {})
                        key = None

                        if '@language' in container:
                            if _is_value(compacted_item):
                                compacted_item = compacted_item['@value']
                            key = expanded_item.get('@language')
                        elif '@index' in container:
                            key = expanded_item.get('@index')
                        elif '@id' in container:
                            id_key = self._compact_iri(active_ctx, '@id')
                            key = compacted_item.pop(id_key, None)
                        elif '@type' in container:
                            type_key = self._compact_iri(active_ctx, '@type')
                            types = JsonLdProcessor.arrayify(compacted_item.pop(type_key, []))
                            key = types.pop(0) if types else None
                            if types:
                                JsonLdProcessor.add_value(compacted_item, type_key, types)

                        key = key or self._compact_iri(active_ctx, '@none')

                        # add compact value to map object using key from
                        # expanded value based on the container type
                        JsonLdProcessor.add_value(
                            map_object, key, compacted_item,
                            {'propertyIsArray': '@set' in container})
                    else:
                        # use an array if compactArrays flag is false,
                        # @container is @set or @list, value is an empty
                        # array, or key is @graph
                        is_array = (
                                not options['compactArrays'] or
                                '@set' in container or
                                '@list' in container or
                                (_is_array(compacted_item) and
                                    len(compacted_item) == 0) or
                                expanded_property == '@list' or
                                expanded_property == '@graph')

                        # add compact value
                        JsonLdProcessor.add_value(
                            nest_result, item_active_property, compacted_item,
                            {'propertyIsArray': is_array})

            return rval

        # only primitives remain which are already compact
        return element

    def _expand(
            self, active_ctx, active_property, element, options, inside_list):
        """
        Recursively expands an element using the given context. Any context in
        the element will be removed. All context URLs must have been retrieved
        before calling this method.

        :param active_ctx: the context to use.
        :param active_property: the property for the element, None for none.
        :param element: the element to expand.
        :param options: the expansion options.
        :param inside_list: True if the property is a list, False if not.

        :return: the expanded value.
        """
        # nothing to expand
        if element is None:
            return element

        # disable framing if active_property is @default
        if active_property == '@default':
            options = options.copy()
            options['isFrame'] = False

        # recursively expand array
        if _is_array(element):
            rval = []
            container = JsonLdProcessor.arrayify(
                JsonLdProcessor.get_context_value(
                    active_ctx, active_property, '@container'))
            inside_list = inside_list or '@list' in container
            for e in element:
                # expand element
                e = self._expand(
                    active_ctx, active_property, e, options, inside_list)
                if inside_list and (_is_array(e) or _is_list(e)):
                    # lists of lists are illegal
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; lists of lists are not '
                        'permitted.', 'jsonld.SyntaxError',
                        code='list of lists')
                # drop None values
                if e is not None:
                    if _is_array(e):
                        rval.extend(e)
                    else:
                        rval.append(e)
            return rval

        # handle scalars
        if not _is_object(element):
            # drop free-floating scalars that are not in lists
            if (not inside_list and (active_property is None or
                self._expand_iri(
                    active_ctx, active_property, vocab=True) == '@graph')):
                return None

            # expand element according to value expansion rules
            return self._expand_value(active_ctx, active_property, element)

        # recursively expand object
        # if element has a context, process it
        if '@context' in element:
            active_ctx = self._process_context(
                active_ctx, element['@context'], options)

        # look for scoped context on @type
        for key, value in sorted(element.items()):
            expanded_property = self._expand_iri(
                active_ctx, key, vocab=True)
            if expanded_property == '@type':
                # set scoped contexts from @type
                types = [t for t in JsonLdProcessor.arrayify(element[key]) if _is_string(t)]
                for type_ in types:
                    ctx = JsonLdProcessor.get_context_value(
                        active_ctx, type_, '@context')
                    if ctx:
                        active_ctx = self._process_context(
                            active_ctx, ctx, options)

        # expand the active property
        expanded_active_property = self._expand_iri(
            active_ctx, active_property, vocab=True)

        # process each key and value in element, ignoring @nest content
        rval = {}
        self._expand_object(
            active_ctx, active_property, expanded_active_property,
            element, rval, options, inside_list)

        # get property count on expanded output
        count = len(rval)

        if '@value' in rval:
            # @value must only have @language or @type
            if '@type' in rval and '@language' in rval:
                raise JsonLdError(
                    'Invalid JSON-LD syntax; an element containing '
                    '"@value" may not contain both "@type" and "@language".',
                    'jsonld.SyntaxError', {'element': rval},
                    code='invalid value object')
            valid_count = count - 1
            if '@type' in rval:
                valid_count -= 1
            if '@index' in rval:
                valid_count -= 1
            if '@language' in rval:
                valid_count -= 1
            if valid_count != 0:
                raise JsonLdError(
                    'Invalid JSON-LD syntax; an element containing "@value" '
                    'may only have an "@index" property and at most one other '
                    'property which can be "@type" or "@language".',
                    'jsonld.SyntaxError', {'element': rval},
                    code='invalid value object')

            values = JsonLdProcessor.get_values(rval, '@value')
            types = JsonLdProcessor.get_values(rval, '@type')

            # drop None @values
            if rval['@value'] is None:
                rval = None
            # if @language is present, @value must be a string
            elif '@language' in rval and not all(_is_string(val) or _is_empty_object(val) for val in values):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; only strings may be '
                    'language-tagged.', 'jsonld.SyntaxError',
                    {'element': rval}, code='invalid language-tagged value')
            elif not all(
                    _is_empty_object(type) or
                    _is_string(type) and
                    _is_absolute_iri(type) and
                    not type.startswith('_:') for type in types):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; an element containing "@value" '
                    'and "@type" must have an absolute IRI for the value '
                    'of "@type".', 'jsonld.SyntaxError', {'element': rval},
                    code='invalid typed value')
        # convert @type to an array
        elif '@type' in rval and not _is_array(rval['@type']):
            rval['@type'] = [rval['@type']]
        # handle @set and @list
        elif '@set' in rval or '@list' in rval:
            if count > 1 and not (count == 2 and '@index' in rval):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; if an element has the '
                    'property "@set" or "@list", then it can have at most '
                    'one other property, which is "@index".',
                    'jsonld.SyntaxError', {'element': rval},
                    code='invalid set or list object')
            # optimize away @set
            if '@set' in rval:
                rval = rval['@set']
                count = len(rval)
        # drop objects with only @language
        elif count == 1 and '@language' in rval:
            rval = None

        # drop certain top-level objects that do not occur in lists
        if (_is_object(rval) and not options.get('keepFreeFloatingNodes') and
                not inside_list and
                (active_property is None or
                    expanded_active_property == '@graph')):
            # drop empty object or top-level @value/@list,
            # or object with only @id
            if (count == 0 or '@value' in rval or '@list' in rval or
                    (count == 1 and '@id' in rval)):
                rval = None

        return rval


    def _expand_object(
            self, active_ctx, active_property, expanded_active_property,
            element, expanded_parent, options, inside_list):
        """
        Expand each key and value of element adding to result.

        :param active_ctx: the context to use.
        :param active_property: the property for the element, None for none.
        :param expanded_active_property: the expansion of active_property
        :param element: the element to expand.
        :param expanded_parent: the expanded result into which to add values.
        :param options: the expansion options.
        :param inside_list: True if the property is a list, False if not.

        :return: the expanded value.
        """

        nests = []
        for key, value in sorted(element.items()):
            if key == '@context':
                continue

            # expand key to IRI
            expanded_property = self._expand_iri(
                active_ctx, key, vocab=True)

            # drop non-absolute IRI keys that aren't keywords
            if (expanded_property is None or
                not (
                    _is_absolute_iri(expanded_property) or
                    _is_keyword(expanded_property))):
                continue

            if _is_keyword(expanded_property):
                if expanded_active_property == '@reverse':
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; a keyword cannot be used as '
                        'a @reverse property.',
                        'jsonld.SyntaxError', {'value': value},
                        code='invalid reverse property map')
                if expanded_property in expanded_parent:
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; colliding keywords detected.',
                        'jsonld.SyntaxError', {'keyword': expanded_property},
                        code='colliding keywords')

            # syntax error if @id is not a string
            if expanded_property == '@id':
                if not _is_string(value):
                    if not options.get('isFrame'):
                        raise JsonLdError(
                            'Invalid JSON-LD syntax; "@id" value must be a '
                            'string.', 'jsonld.SyntaxError',
                            {'value': value}, code='invalid @id value')
                    if _is_object(value):
                        if not _is_empty_object(value):
                            raise JsonLdError(
                                'Invalid JSON-LD syntax; "@id" value must be a '
                                'string or an empty object or array of strings.',
                                'jsonld.SyntaxError',
                                {'value': value}, code='invalid @id value')
                    elif _is_array(value):
                        if not all(_is_string(v) for v in value):
                           raise JsonLdError(
                              'Invalid JSON-LD syntax; "@id" value an empty object or array of strings, if framing',
                              'jsonld.SyntaxError',
                              {'value': value}, code='invalid @id value')
                    else:
                        raise JsonLdError(
                          'Invalid JSON-LD syntax; "@id" value an empty object or array of strings, if framing',
                          'jsonld.SyntaxError',
                          {'value': value}, code='invalid @id value')

                expanded_values = []
                for v in JsonLdProcessor.arrayify(value):
                    expanded_values.append(v if _is_object(v) else self._expand_iri(active_ctx, v, base=True))

                JsonLdProcessor.add_value(
                    expanded_parent, '@id', expanded_values,
                    {'propertyIsArray': options['isFrame']})
                continue

            if expanded_property == '@type':
                _validate_type_value(value)
                expanded_values = []
                for v in JsonLdProcessor.arrayify(value):
                    expanded_values.append(self._expand_iri(active_ctx, v, vocab=True, base=True) if _is_string(v) else v)
                JsonLdProcessor.add_value(
                    expanded_parent, '@type', expanded_values,
                    {'propertyIsArray': options['isFrame']})
                continue

            # @graph must be an array or an object
            if (expanded_property == '@graph' and
                    not (_is_object(value) or _is_array(value))):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; "@graph" must not be an '
                    'object or an array.', 'jsonld.SyntaxError',
                    {'value': value}, code='invalid @graph value')

            # @value must not be an object or an array
            if expanded_property == '@value':
                if (_is_object(value) or _is_array(value)) and not options['isFrame']:
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; "@value" value must not be an '
                        'object or an array.', 'jsonld.SyntaxError',
                        {'value': value}, code='invalid value object value')
                JsonLdProcessor.add_value(
                    expanded_parent, '@value', value,
                    {'propertyIsArray': options['isFrame']})
                continue

            # @language must be a string
            if expanded_property == '@language':
                if value is None:
                    # drop null @language values, they expand as if they
                    # didn't exist
                    continue
                if not _is_string(value) and not options['isFrame']:
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; "@language" value must be '
                        'a string.', 'jsonld.SyntaxError', {'value': value},
                        code='invalid language-tagged string')
                # ensure language value is lowercase
                expanded_values = []
                for v in JsonLdProcessor.arrayify(value):
                    expanded_values.append(v.lower() if _is_string(v) else v)
                JsonLdProcessor.add_value(
                    expanded_parent, '@language', expanded_values,
                    {'propertyIsArray': options['isFrame']})
                continue

            # @index must be a string
            if expanded_property == '@index':
                if not _is_string(value):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; "@index" value must be '
                        'a string.', 'jsonld.SyntaxError', {'value': value},
                        code='invalid @index value')
                JsonLdProcessor.add_value(expanded_parent, '@index', value)
                continue

            # reverse must be an object
            if expanded_property == '@reverse':
                if not _is_object(value):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; "@reverse" value must be '
                        'an object.', 'jsonld.SyntaxError', {'value': value},
                        code='invalid @reverse value')

                expanded_value = self._expand(
                    active_ctx, '@reverse', value, options, inside_list)

                # properties double-reversed
                if '@reverse' in expanded_value:
                    for rproperty, rvalue in (
                            expanded_value['@reverse'].items()):
                        JsonLdProcessor.add_value(
                            expanded_parent, rproperty, rvalue,
                            {'propertyIsArray': True})

                # merge in all reversed properties
                reverse_map = expanded_parent.get('@reverse')
                for property, items in expanded_value.items():
                    if property == '@reverse':
                        continue
                    if reverse_map is None:
                        reverse_map = expanded_parent['@reverse'] = {}
                    JsonLdProcessor.add_value(
                        reverse_map, property, [],
                        {'propertyIsArray': True})
                    for item in items:
                        if _is_value(item) or _is_list(item):
                            raise JsonLdError(
                                'Invalid JSON-LD syntax; "@reverse" '
                                'value must not be an @value or an @list',
                                'jsonld.SyntaxError',
                                {'value': expanded_value},
                                code='invalid reverse property value')
                        JsonLdProcessor.add_value(
                            reverse_map, property, item,
                            {'propertyIsArray': True})

                continue

            # nested keys
            if expanded_property == '@nest':
                nests.append(key)
                continue

            # use potential scoped context for key
            term_ctx = active_ctx
            ctx = JsonLdProcessor.get_context_value(active_ctx, key, '@context')
            if ctx:
                term_ctx = self._process_context(active_ctx, ctx, options)

            container = JsonLdProcessor.arrayify(
                JsonLdProcessor.get_context_value(
                    active_ctx, key, '@container'))

            # handle language map container (skip if value is not an object)
            if '@language' in container and _is_object(value):
                expanded_value = self._expand_language_map(term_ctx, value)
            # handle index container (skip if value is not an object)
            elif '@index' in container and _is_object(value):
                expanded_value = self._expand_index_map(term_ctx, key, value, '@index', '@graph' in container, options)
            elif '@id' in container and _is_object(value):
                expanded_value = self._expand_index_map(term_ctx, key, value, '@id', '@graph' in container, options)
            elif '@type' in container and _is_object(value):
                expanded_value = self._expand_index_map(term_ctx, key, value, '@type', False, options)
            else:
                # recurse into @list or @set
                is_list = (expanded_property == '@list')
                if is_list or expanded_property == '@set':
                    next_active_property = active_property
                    if is_list and expanded_active_property == '@graph':
                        next_active_property = None
                    expanded_value = self._expand(
                        term_ctx, next_active_property, value, options,
                        is_list)
                    if is_list and _is_list(expanded_value):
                        raise JsonLdError(
                            'Invalid JSON-LD syntax; lists of lists are '
                            'not permitted.', 'jsonld.SyntaxError',
                            code='list of lists')
                else:
                    # recursively expand value w/key as new active property
                    expanded_value = self._expand(
                        term_ctx, key, value, options, inside_list=False)

            # drop None values if property is not @value (dropped below)
            if expanded_value is None and expanded_property != '@value':
                continue

            # convert expanded value to @list if container specifies it
            if (expanded_property != '@list' and
                    not _is_list(expanded_value) and
                    '@list' in container):
                # ensure expanded value is an array
                expanded_value = {
                    '@list': JsonLdProcessor.arrayify(expanded_value)
                }

            # convert expanded value to @graph
            if ('@graph' in container and
                    '@id' not in container and
                    '@index' not in container and
                    not _is_graph(expanded_value)):
                expanded_value = {'@graph': JsonLdProcessor.arrayify(expanded_value)}

            # merge in reverse properties
            mapping = term_ctx['mappings'].get(key)
            if mapping and mapping['reverse']:
                reverse_map = expanded_parent.setdefault('@reverse', {})
                expanded_value = JsonLdProcessor.arrayify(expanded_value)
                for item in expanded_value:
                    if _is_value(item) or _is_list(item):
                        raise JsonLdError(
                            'Invalid JSON-LD syntax; "@reverse" value must '
                            'not be an @value or an @list.',
                            'jsonld.SyntaxError', {'value': expanded_value},
                            code='invalid reverse property value')
                    JsonLdProcessor.add_value(
                        reverse_map, expanded_property, item,
                        {'propertyIsArray': True})
                continue

            # add value for property, use an array exception for certain
            # key words
            use_array = (expanded_property not in [
                '@index', '@id', '@type', '@value', '@language'])
            JsonLdProcessor.add_value(
                expanded_parent, expanded_property, expanded_value,
                {'propertyIsArray': use_array})

        # expand each nested key
        for key in nests:
            for nv in JsonLdProcessor.arrayify(element[key]):
                if (not _is_object(nv) or
                    [k for k, v in nv.items() if self._expand_iri(active_ctx, k, vocab=True) == '@value']):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; nested value must be a node object.',
                        'jsonld.SyntaxError', {'value': nv},
                        code='invalid @nest value')
                self._expand_object(
                    active_ctx, active_property, expanded_active_property,
                    nv, expanded_parent, options, inside_list)

    def _flatten(self, input):
        """
        Performs JSON-LD flattening.

        :param input_: the expanded JSON-LD to flatten.

        :return: the flattened JSON-LD output.
        """
        # produce a map of all subjects and label each bnode
        issuer = IdentifierIssuer('_:b')
        graphs = {'@default': {}}
        self._create_node_map(input, graphs, '@default', issuer)

        # add all non-default graphs to default graph
        default_graph = graphs['@default']
        for graph_name, node_map in graphs.items():
            if graph_name == '@default':
                continue
            graph_subject = default_graph.setdefault(
                graph_name, {'@id': graph_name, '@graph': []})
            graph_subject.setdefault('@graph', []).extend(
                [v for k, v in sorted(node_map.items())
                    if not _is_subject_reference(v)])

        # produce flattened output
        return [value for key, value in sorted(default_graph.items())
                if not _is_subject_reference(value)]

    def _frame(self, input_, frame, options):
        """
        Performs JSON-LD framing.

        :param input_: the expanded JSON-LD to frame.
        :param frame: the expanded JSON-LD frame to use.
        :param options: the framing options.

        :return: the framed output.
        """
        # create framing state
        state = {
            'options': options,
            'graph': '@default',
            'graphMap': {'@default': {}},
            'graphStack': [],
            'subjectStack': [],
            'link': {},
            'bnodeMap': {}
        }

        # produce a map of all graphs and name each bnode
        issuer = IdentifierIssuer('_:b')
        self._create_node_map(input_, state['graphMap'], '@default', issuer)
        if options['merged']:
            state['graphMap']['@merged'] = self._merge_node_map_graphs(state['graphMap'])
            state['graph'] = '@merged'
        state['subjects'] = state['graphMap'][state['graph']]

        # frame the subjects
        framed = []
        self._match_frame(
            state, sorted(state['subjects'].keys()), frame, framed, None)

        # if pruning blank nodes, find those to prune
        if options['pruneBlankNodeIdentifiers']:
            options['bnodesToClear'].extend(
                [id_ for id_ in state['bnodeMap'].keys() if len(state['bnodeMap'][id_]) == 1])
        return framed

    def _from_rdf(self, dataset, options):
        """
        Converts an RDF dataset to JSON-LD.

        :param dataset: the RDF dataset.
        :param options: the RDF serialization options.

        :return: the JSON-LD output.
        """
        default_graph = {}
        graph_map = {'@default': default_graph}
        referenced_once = {}

        for name, graph in dataset.items():
            graph_map.setdefault(name, {})
            if name != '@default' and name not in default_graph:
                default_graph[name] = {'@id': name}
            node_map = graph_map[name]
            for triple in graph:
                # get subject, predicate, object
                s = triple['subject']['value']
                p = triple['predicate']['value']
                o = triple['object']

                node = node_map.setdefault(s, {'@id': s})

                object_is_id = (
                    o['type'] == 'IRI' or
                    o['type'] == 'blank node')
                if object_is_id and o['value'] not in node_map:
                    node_map[o['value']] = {'@id': o['value']}

                if (p == RDF_TYPE and not options.get('useRdfType', False) and
                        object_is_id):
                    JsonLdProcessor.add_value(
                        node, '@type', o['value'], {'propertyIsArray': True})
                    continue

                value = self._rdf_to_object(o, options['useNativeTypes'])
                JsonLdProcessor.add_value(
                    node, p, value, {'propertyIsArray': True})

                # object may be an RDF list/partial list node but we
                # can't know easily until all triples are read
                if object_is_id:
                    # track rdf:nil uniquely per graph
                    if o['value'] == RDF_NIL:
                        object = node_map[o['value']]
                        if 'usages' not in object:
                            object['usages'] = []
                        object['usages'].append({
                            'node': node,
                            'property': p,
                            'value': value
                        })
                    # object referenced more than once
                    elif o['value'] in referenced_once:
                        referenced_once[o['value']] = False
                    # track single reference
                    else:
                        referenced_once[o['value']] = {
                            'node': node,
                            'property': p,
                            'value': value
                        }

        # convert linked lists to @list arrays
        for name, graph_object in graph_map.items():
            # no @lists to be converted, continue
            if RDF_NIL not in graph_object:
                continue

            # iterate backwards through each RDF list
            nil = graph_object[RDF_NIL]
            for usage in nil['usages']:
                node = usage['node']
                property = usage['property']
                head = usage['value']
                list_ = []
                list_nodes = []

                # ensure node is a well-formed list node; it must:
                # 1. Be referenced only once.
                # 2. Have an array for rdf:first that has 1 item.
                # 3. Have an array for rdf:rest that has 1 item
                # 4. Have no keys other than: @id, rdf:first, rdf:rest
                #   and, optionally, @type where the value is rdf:List.
                node_key_count = len(node.keys())
                while(property == RDF_REST and
                        _is_object(referenced_once.get(node['@id'])) and
                        _is_array(node[RDF_FIRST]) and
                        len(node[RDF_FIRST]) == 1 and
                        _is_array(node[RDF_REST]) and
                        len(node[RDF_REST]) == 1 and
                        (node_key_count == 3 or (node_key_count == 4 and
                         _is_array(node.get('@type')) and
                         len(node['@type']) == 1 and
                         node['@type'][0] == RDF_LIST))):
                    list_.append(node[RDF_FIRST][0])
                    list_nodes.append(node['@id'])

                    # get next node, moving backwards through list
                    usage = referenced_once[node['@id']]
                    node = usage['node']
                    property = usage['property']
                    head = usage['value']
                    node_key_count = len(node.keys())

                    # if node is not a blank node, then list head found
                    if not node['@id'].startswith('_:'):
                        break

                # the list is nested in another list
                if property == RDF_FIRST:
                    # empty list
                    if node['@id'] == RDF_NIL:
                        # can't convert rdf:nil to a @list object because it
                        # would result in a list of lists which isn't supported
                        continue

                    # preserve list head
                    head = graph_object[head['@id']][RDF_REST][0]
                    list_.pop()
                    list_nodes.pop()

                # transform list into @list object
                del head['@id']
                list_.reverse()
                head['@list'] = list_
                for node in list_nodes:
                    graph_object.pop(node, None)

            nil.pop('usages', None)

        result = []
        for subject, node in sorted(default_graph.items()):
            if subject in graph_map:
                graph = node['@graph'] = []
                for s, n in sorted(graph_map[subject].items()):
                    # only add full subjects to top-level
                    if not _is_subject_reference(n):
                        graph.append(n)
            # only add full subjects to top-level
            if not _is_subject_reference(node):
                result.append(node)

        return result

    def _process_context(self, active_ctx, local_ctx, options):
        """
        Processes a local context and returns a new active context.

        :param active_ctx: the current active context.
        :param local_ctx: the local context to process.
        :param options: the context processing options.

        :return: the new active context.
        """
        global _cache

        # normalize local context to an array
        if _is_object(local_ctx) and _is_array(local_ctx.get('@context')):
            local_ctx = local_ctx['@context']
        ctxs = JsonLdProcessor.arrayify(local_ctx)

        # no contexts in array, clone existing context
        if len(ctxs) == 0:
            return self._clone_active_context(active_ctx)

        # process each context in order, update active context on each
        # iteration to ensure proper caching
        rval = active_ctx
        for ctx in ctxs:
            # reset to initial context
            if ctx is None:
                rval = active_ctx = self._get_initial_context(options)
                continue

            # dereference @context key if present
            if _is_object(ctx) and '@context' in ctx:
                ctx = ctx['@context']

            # context must be an object now, all URLs retrieved prior to call
            if not _is_object(ctx):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; @context must be an object.',
                    'jsonld.SyntaxError', {'context': ctx},
                    code='invalid local context')

            # get context from cache if available
            if _cache.get('activeCtx') is not None:
                cached = _cache['activeCtx'].get(active_ctx, ctx)
                if cached:
                    rval = active_ctx = cached
                    continue

            # update active context and clone new one before updating
            active_ctx = rval
            rval = self._clone_active_context(active_ctx)

            # define context mappings for keys in local context
            defined = {}

            # handle @version
            if '@version' in ctx:
                if ctx['@version'] != 1.1:
                    raise JsonLdError(
                        'Unsupported JSON-LD version: ' + str(ctx['@version']),
                        'jsonld.UnsupportedVersion', {'context': ctx},
                        code='invalid @version value')
                if active_ctx.get('processingMode') == 'json-ld-1.0':
                    raise JsonLdError(
                        '@version: ' + str(ctx['@version']) +
                        ' not compatible with ' + active_ctx['processingMode'],
                        'jsonld.ProcessingModeConflict', {'context': ctx},
                        code='processing mode conflict')
                rval['processingMode'] = 'json-ld-1.1'
                rval['@version'] = ctx['@version']
                defined['@version'] = True

            # if not set explicitly, set processingMode to "json-ld-1.0"
            rval['processingMode'] = rval.get(
                'processingMode', active_ctx.get('processingMode', 'json-ld-1.0'))

            # handle @base
            if '@base' in ctx:
                base = ctx['@base']
                if base is None:
                    base = None
                elif _is_absolute_iri(base):
                    base = base
                elif _is_relative_iri(base):
                    base = prepend_base(active_ctx['@base'], base)
                else:
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; the value of "@base" in a '
                        '@context must be a string or null.',
                        'jsonld.SyntaxError', {'context': ctx},
                        code='invalid base IRI')
                rval['@base'] = base
                defined['@base'] = True

            # handle @vocab
            if '@vocab' in ctx:
                value = ctx['@vocab']
                if value is None:
                    del rval['@vocab']
                elif not _is_string(value):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; the value of "@vocab" in a '
                        '@context must be a string or null.',
                        'jsonld.SyntaxError', {'context': ctx},
                        code='invalid vocab mapping')
                elif not _is_absolute_iri(value):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; the value of "@vocab" in a '
                        '@context must be an absolute IRI.',
                        'jsonld.SyntaxError', {'context': ctx},
                        code='invalid vocab mapping')
                else:
                    rval['@vocab'] = value
                defined['@vocab'] = True

            # handle @language
            if '@language' in ctx:
                value = ctx['@language']
                if value is None:
                    del rval['@language']
                elif not _is_string(value):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; the value of "@language" in '
                        'a @context must be a string or null.',
                        'jsonld.SyntaxError', {'context': ctx},
                        code='invalid default language')
                else:
                    rval['@language'] = value.lower()
                defined['@language'] = True

            # process all other keys
            for k, v in ctx.items():
                self._create_term_definition(rval, ctx, k, defined)

            # cache result
            if _cache.get('activeCtx') is not None:
                _cache.get('activeCtx').set(active_ctx, ctx, rval)

        return rval

    def _processing_mode(self, active_ctx, version):
        """
        Processing Mode check.

        :param active_ctx: the current active context.
        :param version: the string or numeric version to check.

        :return: True if the check matches.
        """
        if str(version) >= '1.1':
            return str(active_ctx.get('processingMode')) >= ('json-ld-' + str(version))
        else:
            return active_ctx.get('processingMode', 'json-ld-1.0') == 'json-ld-1.0'


    def _check_nest_property(self, active_ctx, nest_property):
        """
        The value of `@nest` in the term definition must either be `@nest`, or a term
        which resolves to `@nest`.

        :param active_ctx: the current active context
        :param nest_property: a term in the active context or `@nest`
        """
        if self._expand_iri(active_ctx, nest_property, vocab=True) != '@nest':
            raise JsonLdError(
                'JSON-LD compact error; nested property must have an @nest value resolving to @nest.',
                'jsonld.SyntaxError', {'context': active_ctx},
                code='invalid @nest value')
    
    def _expand_language_map(self, active_ctx, language_map):
        """
        Expands a language map.

        :param active_ctx: the current active context.
        :param language_map: the language map to expand.

        :return: the expanded language map.
        """
        rval = []
        for key, values in sorted(language_map.items()):
            expanded_key = self._expand_iri(active_ctx, key, vocab=True)
            values = JsonLdProcessor.arrayify(values)
            for item in values:
                if item is None:
                    continue
                if not _is_string(item):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; language map values must be '
                        'strings.', 'jsonld.SyntaxError',
                        {'languageMap': language_map},
                        code='invalid language map value')
                val = {'@value': item}
                if expanded_key != '@none':
                    val['@language'] = key.lower()
                rval.append(val)
        return rval


    def _expand_index_map(self, active_ctx, active_property, value, index_key, as_graph, options):
        """
        Expands in index, id or type map.

        :param active_ctx: the current active context.
        :param active_property: the property for the element, None for none.
        :param value: the object containing indexed values
        :param index_key: the key value used to index
        :param as_graph: contents should form a named graph
        """
        rval = []
        for k, v in sorted(value.items()):
            ctx = JsonLdProcessor.get_context_value(
                active_ctx, k, '@context')
            if ctx:
                active_ctx = self._process_context(active_ctx, ctx, options)

            expanded_key = self._expand_iri(active_ctx, k, vocab=True)
            if index_key == '@id':
                # expand document relative
                k = self._expand_iri(active_ctx, k, base=True)
            elif index_key == '@type':
                k = expanded_key

            v = self._expand(
                active_ctx, active_property,
                JsonLdProcessor.arrayify(v),
                options, inside_list=False)
            for item in v:
                if as_graph and not _is_graph(item):
                    item = {'@graph': [item]}
                if index_key == '@type':
                    if expanded_key == '@none':
                        # ignore @none
                        item
                    elif item.get('@type'):
                        types = [k]
                        types.extend(item['@type'])
                        item['@type'] = types
                    else:
                        item['@type'] = [k]
                elif expanded_key != '@none' and index_key not in item:
                    item[index_key] = k

                rval.append(item)
        return rval

    def _expand_value(self, active_ctx, active_property, value):
        """
        Expands the given value by using the coercion and keyword rules in the
        given context.

        :param active_ctx: the active context to use.
        :param active_property: the property the value is associated with.
        :param value: the value to expand.

        :return: the expanded value.
        """
        # nothing to expand
        if value is None:
            return None

        # special-case expand @id and @type (skips '@id' expansion)
        expanded_property = self._expand_iri(
            active_ctx, active_property, vocab=True)
        if expanded_property == '@id':
            return self._expand_iri(active_ctx, value, base=True)
        elif expanded_property == '@type':
            return self._expand_iri(active_ctx, value, vocab=True, base=True)

        # get type definition from context
        type_ = JsonLdProcessor.get_context_value(
            active_ctx, active_property, '@type')

        # do @id expansion (automatic for @graph)
        if (type_ == '@id' or expanded_property == '@graph') and _is_string(value):
            return {'@id': self._expand_iri(active_ctx, value, base=True)}
        # do @id expansion w/vocab
        if type_ == '@vocab' and _is_string(value):
            return {'@id': self._expand_iri(
                active_ctx, value, vocab=True, base=True)}

        # do not expand keyword values
        if _is_keyword(expanded_property):
            return value

        rval = {}

        # other type
        if type_ is not None and type_ != '@id' and type_ != '@vocab':
            rval['@type'] = type_
        # check for language tagging
        elif _is_string(value):
            language = JsonLdProcessor.get_context_value(
                active_ctx, active_property, '@language')
            if language is not None:
                rval['@language'] = language

        # do conversion of values that aren't basic JSON types to strings
        if not (_is_bool(value) or _is_numeric(value) or _is_string(value)):
            value = str(value)

        rval['@value'] = value
        return rval

    def _graph_to_rdf(self, graph, issuer, options):
        """
        Creates an array of RDF triples for the given graph.

        :param graph: the graph to create RDF triples for.
        :param issuer: the IdentifierIssuer for issuing blank node identifiers.
        :param options: the RDF serialization options.

        :return: the array of RDF triples for the given graph.
        """
        rval = []
        for id_, node in sorted(graph.items()):
            for property, items in sorted(node.items()):
                if property == '@type':
                    property = RDF_TYPE
                elif _is_keyword(property):
                    continue

                for item in items:
                    # skip relative IRI subjects and predicates
                    if not (_is_absolute_iri(id_) and
                            _is_absolute_iri(property)):
                        continue

                    # RDF subject
                    subject = {}
                    if id_.startswith('_:'):
                        subject['type'] = 'blank node'
                    else:
                        subject['type'] = 'IRI'
                    subject['value'] = id_

                    # RDF predicate
                    predicate = {}
                    if property.startswith('_:'):
                        # skip bnode predicates unless producing
                        # generalized RDF
                        if not options['produceGeneralizedRdf']:
                            continue
                        predicate['type'] = 'blank node'
                    else:
                        predicate['type'] = 'IRI'
                    predicate['value'] = property

                    # convert @list to triples
                    if _is_list(item):
                        self._list_to_rdf(
                            item['@list'], issuer, subject, predicate, rval)
                    # convert value or node object to triple
                    else:
                        object = self._object_to_rdf(item)
                        # skip None objects (they are relative IRIs)
                        if object is not None:
                            rval.append({
                                'subject': subject,
                                'predicate': predicate,
                                'object': object
                            })
        return rval

    def _list_to_rdf(self, list, issuer, subject, predicate, triples):
        """
        Converts a @list value into a linked list of blank node RDF triples
        (and RDF collection).

        :param list: the @list value.
        :param issuer: the IdentifierIssuer for issuing blank node identifiers.
        :param subject: the subject for the head of the list.
        :param predicate: the predicate for the head of the list.
        :param triples: the array of triples to append to.
        """
        first = {'type': 'IRI', 'value': RDF_FIRST}
        rest = {'type': 'IRI', 'value': RDF_REST}
        nil = {'type': 'IRI', 'value': RDF_NIL}

        for item in list:
            blank_node = {'type': 'blank node', 'value': issuer.get_id()}
            triples.append({
                'subject': subject,
                'predicate': predicate,
                'object': blank_node
            })

            subject = blank_node
            predicate = first
            object = self._object_to_rdf(item)
            # skip None objects (they are relative IRIs)
            if object is not None:
                triples.append({
                    'subject': subject,
                    'predicate': predicate,
                    'object': object
                })

            predicate = rest

        triples.append({
            'subject': subject,
            'predicate': predicate,
            'object': nil
        })

    def _object_to_rdf(self, item):
        """
        Converts a JSON-LD value object to an RDF literal or a JSON-LD string
        or node object to an RDF resource.

        :param item: the JSON-LD value or node object.

        :return: the RDF literal or RDF resource.
        """
        object = {}

        if _is_value(item):
            object['type'] = 'literal'
            value = item['@value']
            datatype = item.get('@type')

            # convert to XSD datatypes as appropriate
            if _is_bool(value):
                object['value'] = 'true' if value else 'false'
                object['datatype'] = datatype or XSD_BOOLEAN
            elif _is_double(value) or datatype == XSD_DOUBLE:
                # canonical double representation
                object['value'] = re.sub(
                    r'(\d)0*E\+?0*(\d)', r'\1E\2',
                    ('%1.15E' % value))
                object['datatype'] = datatype or XSD_DOUBLE
            elif _is_integer(value):
                object['value'] = str(value)
                object['datatype'] = datatype or XSD_INTEGER
            elif '@language' in item:
                object['value'] = value
                object['datatype'] = datatype or RDF_LANGSTRING
                object['language'] = item['@language']
            else:
                object['value'] = value
                object['datatype'] = datatype or XSD_STRING
        # convert string/node object to RDF
        else:
            id_ = item['@id'] if _is_object(item) else item
            if id_.startswith('_:'):
                object['type'] = 'blank node'
            else:
                object['type'] = 'IRI'
            object['value'] = id_

        # skip relative IRIs
        if object['type'] == 'IRI' and not _is_absolute_iri(object['value']):
            return None

        return object

    def _rdf_to_object(self, o, use_native_types):
        """
        Converts an RDF triple object to a JSON-LD object.

        :param o: the RDF triple object to convert.
        :param use_native_types: True to output native types, False not to.

        :return: the JSON-LD object.
        """
        # convert IRI/BlankNode object to JSON-LD
        if o['type'] == 'IRI' or o['type'] == 'blank node':
            return {'@id': o['value']}

        # convert literal object to JSON-LD
        rval = {'@value': o['value']}

        # add language
        if 'language' in o:
            rval['@language'] = o['language']
        # add datatype
        else:
            type_ = o['datatype']
            # use native types for certain xsd types
            if use_native_types:
                if type_ == XSD_BOOLEAN:
                    if rval['@value'] == 'true':
                        rval['@value'] = True
                    elif rval['@value'] == 'false':
                        rval['@value'] = False
                elif _is_numeric(rval['@value']):
                    if type_ == XSD_INTEGER:
                        if rval['@value'].isdigit():
                            rval['@value'] = int(rval['@value'])
                    elif type_ == XSD_DOUBLE:
                        rval['@value'] = float(rval['@value'])
                # do not add native type
                if type_ not in [
                        XSD_BOOLEAN, XSD_INTEGER, XSD_DOUBLE, XSD_STRING]:
                    rval['@type'] = type_
            elif type_ != XSD_STRING:
                rval['@type'] = type_
        return rval

    def _create_node_map(
            self, input_, graphs, graph, issuer, name=None, list_=None):
        """
        Recursively flattens the subjects in the given JSON-LD expanded
        input into a node map.

        :param input_: the JSON-LD expanded input.
        :param graphs: a map of graph name to subject map.
        :param graph: the name of the current graph.
        :param issuer: the IdentifierIssuer for issuing blank node identifiers.
        :param name: the name assigned to the current input if it is a bnode.
        :param list_: the list to append to, None for none.
        """
        # recurse through array
        if _is_array(input_):
            for e in input_:
                self._create_node_map(e, graphs, graph, issuer, None, list_)
            return

        # add non-object to list
        if not _is_object(input_):
            if list_ is not None:
                list_.append(input_)
            return

        # add values to list
        if _is_value(input_):
            if '@type' in input_:
                type_ = input_['@type']
                # relabel @type blank node
                if type_.startswith('_:'):
                    type_ = input_['@type'] = issuer.get_id(type_)
            if list_ is not None:
                list_.append(input_)
            return

        # Note: At this point, input must be a subject.

        # spec requires @type to be labeled first, so assign identifiers early
        if '@type' in input_:
            for type_ in input_['@type']:
                if type_.startswith('_:'):
                    issuer.get_id(type_)

        # get identifier for subject
        if name is None:
            name = input_.get('@id')
            if _is_bnode(input_):
                name = issuer.get_id(name)

        # add subject reference to list
        if list_ is not None:
            list_.append({'@id': name})

        # create new subject or merge into existing one
        subject = graphs.setdefault(graph, {}).setdefault(name, {'@id': name})
        for property, objects in sorted(input_.items()):
            # skip @id
            if property == '@id':
                continue

            # handle reverse properties
            if property == '@reverse':
                referenced_node = {'@id': name}
                reverse_map = input_['@reverse']
                for reverse_property, items in reverse_map.items():
                    for item in items:
                        item_name = item.get('@id')
                        if _is_bnode(item):
                            item_name = issuer.get_id(item_name)
                        self._create_node_map(
                            item, graphs, graph, issuer, item_name)
                        JsonLdProcessor.add_value(
                            graphs[graph][item_name], reverse_property,
                            referenced_node,
                            {'propertyIsArray': True, 'allowDuplicate': False})
                continue

            # recurse into graph
            if property == '@graph':
                # add graph subjects map entry
                graphs.setdefault(name, {})
                g = graph if graph == '@merged' else name
                self._create_node_map(objects, graphs, g, issuer)
                continue

            # copy non-@type keywords
            if property != '@type' and _is_keyword(property):
                if property == '@index' and '@index' in subject \
                    and (input_['@index'] != subject['@index'] or
                         input_['@index']['@id'] != subject['@index']['@id']):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; conflicting @index property '
                        ' detected.', 'jsonld.SyntaxError',
                        {'subject': subject}, code='conflicting indexes')
                subject[property] = input_[property]
                continue

            # if property is a bnode, assign it a new id
            if property.startswith('_:'):
                property = issuer.get_id(property)

            # ensure property is added for empty arrays
            if len(objects) == 0:
                JsonLdProcessor.add_value(
                    subject, property, [], {'propertyIsArray': True})
                continue

            for o in objects:
                if property == '@type':
                    # rename @type blank nodes
                    o = issuer.get_id(o) if o.startswith('_:') else o

                # handle embedded subject or subject reference
                if _is_subject(o) or _is_subject_reference(o):
                    # rename blank node @id
                    id_ = o.get('@id')
                    if _is_bnode(o):
                        id_ = issuer.get_id(id_)

                    # add reference and recurse
                    JsonLdProcessor.add_value(
                        subject, property, {'@id': id_},
                        {'propertyIsArray': True, 'allowDuplicate': False})
                    self._create_node_map(o, graphs, graph, issuer, id_)
                # handle @list
                elif _is_list(o):
                    olist = []
                    self._create_node_map(
                        o['@list'], graphs, graph, issuer, name, olist)
                    o = {'@list': olist}
                    JsonLdProcessor.add_value(
                        subject, property, o,
                        {'propertyIsArray': True, 'allowDuplicate': False})
                # handle @value
                else:
                    self._create_node_map(o, graphs, graph, issuer, name)
                    JsonLdProcessor.add_value(
                        subject, property, o,
                        {'propertyIsArray': True, 'allowDuplicate': False})

    def _merge_node_map_graphs(self, graphs):
        """
        Merge separate named graphs into a single merged graph including
        all nodes from the default graph and named graphs.

        :param graphs: a map of graph name to subject map.

        :return: merged graph map.
        """
        merged = {}
        for name, graph in sorted(graphs.items()):
            for id_, node in sorted(graph.items()):
                if id_ not in merged:
                    merged[id_] = {'@id': id}
                merged_node = merged[id_]
                for property, values in sorted(node.items()):
                    if _is_keyword(property):
                        # copy keywords
                        merged_node[property] = copy.deepcopy(values)
                    else:
                        # merge objects
                        for value in values:
                            JsonLdProcessor.add_value(
                                merged_node, property, copy.deepcopy(value),
                                {'propertyIsArray': True, 'allowDuplicate': False})
        return merged

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
        self._validate_frame(frame)
        frame = frame[0]

        # get flags for current frame
        options = state['options']
        flags = {
            'embed': self._get_frame_flag(frame, options, 'embed'),
            'explicit': self._get_frame_flag(frame, options, 'explicit'),
            'requireAll': self._get_frame_flag(frame, options, 'requireAll')
        }

        # filter out subjects that match the frame
        matches = self._filter_subjects(state, subjects, frame, flags)

        # add matches to output
        for id_, subject in sorted(matches.items()):
            if flags['embed'] == '@link' and id_ in state['link']:
                # TODO: may want to also match an existing linked subject
                # against the current frame ... so different frames could
                # produce different subjects that are only shared in-memory
                # when the frames are the same

                # add existing linked subject
                self._add_frame_output(parent, property, state['link'][id_])
                continue

            # Note: In order to treat each top-level match as a
            # compartmentalized result, clear the unique embedded subjects map
            # when the property is None, which only occurs at the top-level.
            if property is None:
                state['uniqueEmbeds'] = {state['graph']: {}}
            elif not state['graph'] in state['uniqueEmbeds']:
                state['uniqueEmbeds'][state['graph']] = {}

            # start output for subject
            output = {'@id': id_}
            # keep track of objects having blank nodes
            if id_.startswith('_:'):
                JsonLdProcessor.add_value(
                    state['bnodeMap'], id_, output,
                    {'propertyIsArray': True})
            state['link'][id_] = output

            # if embed is @never or if a circular reference would be created
            # by an embed, the subject cannot be embedded, just add the
            # reference; note that a circular reference won't occur when the
            # embed flag is `@link` as the above check will short-circuit
            # before reaching this point
            if(flags['embed'] == '@never' or self._creates_circular_reference(
                    subject, state['graph'], state['subjectStack'])):
                self._add_frame_output(parent, property, output)
                continue

            # if only the last match should be embedded
            if flags['embed'] == '@last':
                # remove any existing embed
                if id_ in state['uniqueEmbeds'][state['graph']]:
                    self._remove_embed(state, id_)
                state['uniqueEmbeds'][state['graph']][id_] = {
                    'parent': parent,
                    'property': property
                }

            # push matching subject onto stack to enable circular embed checks
            state['subjectStack'].append({'subject': subject, 'graph': state['graph']})

            # subject is also the name of a graph
            if id_ in state['graphMap']:
                recurse, subframe = False, None
                if '@graph' not in frame:
                    recurse = state['graph'] != '@merged'
                    subframe = {}
                else:
                    subframe = frame['@graph'][0]
                    if not _is_object(subframe):
                        subFrame = {}
                    recurse = not (id_ == '@merged' or id_ == '@default')

                if recurse:
                    state['graphStack'].append(state['graph'])
                    state['graph'] = id_
                    # recurse into graph
                    self._match_frame(
                        state, sorted(state['graphMap'][id_].keys()), [subframe], output, '@graph')

            # iterate over subject properties in order
            for prop, objects in sorted(subject.items()):
                # copy keywords to output
                if _is_keyword(prop):
                    output[prop] = copy.deepcopy(subject[prop])

                    if prop == '@type':
                        # count bnode values of @type
                        for type_ in subject['@type']:
                            if type_.startswith('_:'):
                                JsonLdProcessor.add_value(
                                    state['bnodeMap'], type_, output,
                                    {'propertyIsArray': True})
                    continue

                # explicit is on and property isn't in frame, skip processing
                if flags['explicit'] and prop not in frame:
                    continue

                # add objects
                for o in objects:
                    if prop in frame:
                        subframe = frame[prop]
                    else:
                        subframe = self._create_implicit_frame(flags)

                    # recurse into list
                    if _is_list(o):
                        # add empty list
                        list_ = {'@list': []}
                        self._add_frame_output(output, prop, list_)

                        # add list objects
                        src = o['@list']
                        for o in src:
                            if _is_subject_reference(o):
                                # recurse into subject reference
                                if prop in frame:
                                    subframe = frame[prop][0]['@list']
                                else:
                                    subframe = self._create_implicit_frame(
                                        flags)
                                self._match_frame(
                                    state, [o['@id']],
                                    subframe, list_, '@list')
                            else:
                                # include other values automatically
                                self._add_frame_output(
                                    list_, '@list', copy.deepcopy(o))
                        continue

                    if _is_subject_reference(o):
                        # recurse into subject reference
                        self._match_frame(
                            state, [o['@id']], subframe, output, prop)
                    elif self._value_match(subframe[0], o):
                        # include other values automatically, if they match
                        self._add_frame_output(output, prop, copy.deepcopy(o))

            # handle defaults in order
            for prop in sorted(frame.keys()):
                # skip keywords
                if _is_keyword(prop):
                    continue
                # if omit default is off, then include default values for
                # properties that appear in the next frame but are not in
                # the matching subject
                next = frame[prop][0] if frame[prop] else {}
                omit_default_on = self._get_frame_flag(
                    next, options, 'omitDefault')
                if not omit_default_on and prop not in output:
                    preserve = '@null'
                    if '@default' in next:
                        preserve = copy.deepcopy(next['@default'])
                    preserve = JsonLdProcessor.arrayify(preserve)
                    output[prop] = [{'@preserve': preserve}]

            # embed reverse values by finding nodes having this subject as a value of the associated property
            if '@reverse' in frame:
                for reverse_prop, subframe in sorted(frame['@reverse'].items()):
                    for subject, subject_value in state['subjects'].items():
                        node_values = JsonLdProcessor.get_values(subject_value, reverse_prop)
                        if [v for v in node_values if v['@id'] == id_]:
                            # node has property referencing this subject, recurse
                            output['@reverse'] = output['@reverse'] if '@reverse' in output else {}
                            JsonLdProcessor.add_value(
                                output['@reverse'], reverse_prop, [],
                                {'propertyIsArray': True})
                            self._match_frame(
                                state, [subject], subframe, output['@reverse'][reverse_prop], property)

            # add output to parent
            self._add_frame_output(parent, property, output)

            # pop matching subject from circular ref-checking stack
            state['subjectStack'].pop()

    def _create_implicit_frame(self, flags):
        """
        Creates an implicit frame when recursing through subject matches. If
        a frame doesn't have an explicit frame for a particular property, then
        a wildcard child frame will be created that uses the same flags that
        the parent frame used.

        :param flags: the current framing flags.

        :return: the implicit frame.
        """
        frame = {}
        for key in flags:
            frame['@' + key] = [flags[key]]
        return [frame]

    def _creates_circular_reference(self, subject_to_embed, graph, subject_stack):
        """
        Checks the current subject stack to see if embedding the given subject
        would cause a circular reference.

        :param subject_to_embed: the subject to embed.
        :param graph: the graph the subject to embed is in.
        :param subject_stack: the current stack of subjects.

        :return: true if a circular reference would be created, false if not.
        """
        for subject in reversed(subject_stack[:-1]):
            if subject['graph'] == graph and subject['subject']['@id'] == subject_to_embed['@id']:
                return True
        return False

    def _get_frame_flag(self, frame, options, name):
        """
        Gets the frame flag value for the given flag name.

        :param frame: the frame.
        :param options: the framing options.
        :param name: the flag name.

        :return: the flag value.
        """
        rval = frame.get('@' + name, [options[name]])[0]
        if name == 'embed':
            # default is "@last"
            # backwards-compatibility support for "embed" maps:
            # true => "@last"
            # false => "@never"
            if rval is True:
                rval = '@last'
            elif rval is False:
                rval = '@never'
            elif rval != '@always' and rval != '@never' and rval != '@link':
                rval = '@last'
        return rval

    def _validate_frame(self, frame):
        """
        Validates a JSON-LD frame, throwing an exception if the frame is
        invalid.

        :param frame: the frame to validate.
        """
        if (not _is_array(frame) or len(frame) != 1 or
                not _is_object(frame[0])):
            raise JsonLdError(
                'Invalid JSON-LD syntax; a JSON-LD frame must be a single '
                'object.', 'jsonld.SyntaxError', {'frame': frame})

    def _filter_subjects(self, state, subjects, frame, flags):
        """
        Returns a map of all of the subjects that match a parsed frame.

        :param state: the current framing state.
        :param subjects: the set of subjects to filter.
        :param frame: the parsed frame.
        :param flags: the frame flags.

        :return: all of the matched subjects.
        """
        rval = {}
        for id_ in subjects:
            subject = state['graphMap'][state['graph']][id_]
            if self._filter_subject(state, subject, frame, flags):
                rval[id_] = subject
        return rval

    def _filter_subject(self, state, subject, frame, flags):
        """
        Returns True if the given subject matches the given frame.

        Matches either based on explicit type inclusion where the node has any
        type listed in the frame. If the frame has empty types defined matches
        nodes not having a @type. If the frame has a type of {} defined matches
        nodes having any type defined.

        Otherwise, does duck typing, where the node must have all of the
        properties defined in the frame.

        :param state: the current framing state.
        :param subject: the subject to check.
        :param frame: the frame to check.
        :param flags: the frame flags.

        :return: True if the subject matches, False if not.
        """
        # check ducktype
        wildcard = True
        matches_some = False
        for k, v in sorted(frame.items()):
            match_this = False
            node_values = JsonLdProcessor.get_values(subject, k)
            is_empty = len(v) == 0

            if _is_keyword(k):
                # skip non-@id and non-@type
                if k != '@id' and k != '@type':
                    continue
                wildcard = True

                # check @id for a specific @id value
                if k == '@id':
                    # if @id is not a wildcard and is not empty, then match or not on specific value
                    if len(frame['@id']) >= 0 and not _is_empty_object(frame['@id'][0]):
                        return node_values[0] in frame['@id']
                    match_this = True
                    continue

                # check @type (object value means 'any' type, fall through to ducktyping)
                if k == '@type':
                    if is_empty:
                        if len(node_values) > 0:
                            # don't match on no @type
                            return False
                        match_this = True
                    elif _is_empty_object(frame['@type'][0]):
                        match_this = len(node_values) > 0
                    else:
                        # match on a specific @type
                        return len([tv for tv in node_values if [tf for tf in frame['@type'] if tv == tf]]) > 0

            # force a copy of this frame entry so it can be manipulated
            this_frame = JsonLdProcessor.get_values(frame, k)
            this_frame = this_frame[0] if this_frame else None
            has_default = False
            if this_frame:
                self._validate_frame([this_frame])
                has_default = '@default' in this_frame

            # no longer a wildcard pattern if frame has any non-keyword properties
            wildcard = False

            # skip, but allow match if node has no value for property, and frame has a default value
            if not node_values and has_default:
                continue

            # if frame value is empty, don't match if subject has any value
            if node_values and is_empty:
                return False

            if this_frame == None:
                # node does not match if values is not empty and the value of property in frame is match none.
                if node_values:
                    return False
                match_this = True
            elif _is_object(this_frame):
                # node matches if values is not empty and the value of property in frame is wildcard
                match_this = len(node_values) > 0
            else:
                if _is_value(this_frame):
                    # match on any matching value
                    match_this = any(self._value_match(this_frame, nv) for nv in node_values)
                elif _is_list(this_frame):
                    list_value = this_frame['@list'][0] if this_frame['@list'] else None
                    if _is_list(node_values[0] if node_values else None):
                        node_list_values = node_values[0]['@list']

                        if _is_value(list_value):
                            match_this = any(
                                self._value_match(list_value, lv) for lv in node_list_values)
                        elif _is_subject(list_value) or _is_subject_reference(list_value):
                            match_this = any(
                                self._node_match(state, list_value, lv, flags) for lv in node_list_values)
                    else:
                        match_this = False

            if not match_this and flags['requireAll']:
                return False

            matches_some = matches_some or match_this

        # return true if wildcard or subject matches some properties
        return wildcard or matches_some

    def _remove_embed(self, state, id_):
        """
        Removes an existing embed.

        :param state: the current framing state.
        :param id_: the @id of the embed to remove.
        """
        # get existing embed
        embeds = state['uniqueEmbeds'][state['graph']]
        embed = embeds[id_]
        property = embed['property']

        # create reference to replace embed
        subject = {'@id': id_}

        # remove existing embed
        if _is_array(embed['parent']):
            # replace subject with reference
            for i, parent in enumerate(embed['parent']):
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
        def remove_dependents(id_):
            # get embed keys as a separate array to enable deleting keys
            # in map
            try:
                ids = list(embeds.iterkeys())
            except AttributeError:
                ids = list(embeds.keys())
            for next in ids:
                if (next in embeds and
                        _is_object(embeds[next]['parent']) and
                        '@id' in embeds[next]['parent'] and # could be @list
                        embeds[next]['parent']['@id'] == id_):
                    del embeds[next]
                    remove_dependents(next)
        remove_dependents(id_)

    def _add_frame_output(self, parent, property, output):
        """
        Adds framing output to the given parent.

        :param parent: the parent to add to.
        :param property: the parent property.
        :param output: the output to add.
        """
        if _is_object(parent):
            JsonLdProcessor.add_value(
                parent, property, output, {'propertyIsArray': True})
        else:
            parent.append(output)

    def _node_match(self, state, pattern, value, flags):
        """
        Node matches if it is a node, and matches the pattern as a frame.

        :param state: the current framing state.
        :param pattern: used to match value.
        :param value: to check.
        :param flags: the frame flags.
        """
        if '@id' not in value:
            return False
        node_object = state['subjects'][value['@id']]
        return node_object and self._filter_subject(state, node_object, pattern, flags)

    def _value_match(self, pattern, value):
        """
        Value matches if it is a value and matches the value pattern

        - `pattern` is empty
        - @values are the same, or `pattern[@value]` is a wildcard,
        - @types are the same or `value[@type]` is not None
          and `pattern[@type]` is `{}` or `value[@type]` is None
          and `pattern[@type]` is None or `[]`, and
        - @languages are the same or `value[@language]` is not None
          and `pattern[@language]` is `{}`, or `value[@language]` is None
          and `pattern[@language]` is None or `[]`

        :param pattern: used to match value.
        :param value: to check.
        """
        v1, t1, l1 = value.get('@value'), value.get('@type'), value.get('@language')
        v2 = JsonLdProcessor.get_values(pattern, '@value')
        t2 = JsonLdProcessor.get_values(pattern, '@type')
        l2 = JsonLdProcessor.get_values(pattern, '@language')

        if not v2 and not t2 and not l2:
            return True
        if not (v1 in v2 or _is_empty_object(v2[0])):
            return False
        if not ((not t1 and not t2) or (t1 in t2) or (t1 and t2 and _is_empty_object(t2[0]))):
            return False
        if not ((not l1 and not l2) or (l1 in l2) or (l1 and l2 and _is_empty_object(l2[0]))):
            return False
        return True

    def _remove_preserve(self, ctx, input_, options):
        """
        Removes the @preserve keywords as the last step of the framing
        algorithm.

        :param ctx: the active context used to compact the input.
        :param input_: the framed, compacted output.
        :param options: the compaction options used.

        :return: the resulting output.
        """
        # recurse through arrays
        if _is_array(input_):
            output = []
            for e in input_:
                result = self._remove_preserve(ctx, e, options)
                # drop Nones from arrays
                if result is not None:
                    output.append(result)
            return output
        elif _is_object(input_):
            # remove @preserve
            if '@preserve' in input_:
                if input_['@preserve'] == '@null':
                    return None
                return input_['@preserve']

            # skip @values
            if _is_value(input_):
                return input_

            # recurse through @lists
            if _is_list(input_):
                input_['@list'] = self._remove_preserve(
                    ctx, input_['@list'], options)
                return input_

            # handle in-memory linked nodes
            id_alias = self._compact_iri(ctx, '@id')
            if id_alias in input_:
                id_ = input_[id_alias]
                if id_ in options['link']:
                    try:
                        idx = options['link'][id_].index(input_)
                        # already visited
                        return options['link'][id_][idx]
                    except:
                        # prevent circular visitation
                        options['link'][id_].append(input_)
                else:
                    # prevent circular visitation
                    options['link'][id_] = [input_]

            # potentially remove the id, if it is an unreference bnode
            if input_.get(id_alias) in options['bnodesToClear']:
                input_.pop(id_alias)

            # recurse through properties
            graph_alias = self._compact_iri(ctx, '@graph')
            for prop, v in input_.items():
                result = self._remove_preserve(ctx, v, options)
                container = JsonLdProcessor.arrayify(
                    JsonLdProcessor.get_context_value(
                        ctx, prop, '@container'))
                if (options['compactArrays'] and
                        _is_array(result) and len(result) == 1 and
                        '@set' not in container and '@list' not in container and
                        prop != graph_alias):
                    result = result[0]
                input_[prop] = result
        return input_

    def _select_term(
            self, active_ctx, iri, value, containers,
            type_or_language, type_or_language_value):
        """
        Picks the preferred compaction term from the inverse context entry.

        :param active_ctx: the active context.
        :param iri: the IRI to pick the term for.
        :param value: the value to pick the term for.
        :param containers: the preferred containers.
        :param type_or_language: either '@type' or '@language'.
        :param type_or_language_value: the preferred value for '@type' or
          '@language'

        :return: the preferred term.
        """
        if type_or_language_value is None:
            type_or_language_value = '@null'

        # preferred options for the value of @type or language
        prefs = []

        # determine prefs for @id based on whether value compacts to term
        if ((type_or_language_value == '@id' or
                type_or_language_value == '@reverse') and
                _is_subject_reference(value)):
            # prefer @reverse first
            if type_or_language_value == '@reverse':
                prefs.append('@reverse')
            # try to compact value to a term
            term = self._compact_iri(
                active_ctx, value['@id'], None, vocab=True)
            mapping = active_ctx['mappings'].get(term)
            if term is not None and mapping and mapping['@id'] == value['@id']:
                # prefer @vocab
                prefs.extend(['@vocab', '@id'])
            else:
                # prefer @id
                prefs.extend(['@id', '@vocab'])
        else:
            prefs.append(type_or_language_value)
        prefs.append('@none')

        container_map = active_ctx['inverse'][iri]
        for container in containers:
            # skip container if not in map
            if container not in container_map:
                continue
            type_or_language_value_map = (
                container_map[container][type_or_language])
            for pref in prefs:
                # skip type/language preference if not in map
                if pref not in type_or_language_value_map:
                    continue
                return type_or_language_value_map[pref]
        return None

    def _compact_iri(
            self, active_ctx, iri, value=None, vocab=False, reverse=False):
        """
        Compacts an IRI or keyword into a term or CURIE if it can be. If the
        IRI has an associated value it may be passed.

        :param active_ctx: the active context to use.
        :param iri: the IRI to compact.
        :param value: the value to check or None.
        :param vocab: True to compact using @vocab if available, False not to.
        :param reverse: True if a reverse property is being compacted, False if
          not.

        :return: the compacted term, prefix, keyword alias, or original IRI.
        """
        # can't compact None
        if iri is None:
            return iri

        inverse_context = self._get_inverse_context(active_ctx)

        # term is a keyword, force vocab to True
        if _is_keyword(iri):
            alias = inverse_context.get(iri, {}).get('@none', {}).get('@type', {}).get('@none')
            if alias:
                return alias
            vocab = True

        # use inverse context to pick a term if iri is relative to vocab
        if vocab and iri in inverse_context:
            default_language = active_ctx.get('@language', '@none')

            # prefer @index if available in value
            containers = []
            if _is_object(value) and '@index' in value and '@graph' not in value:
                containers.extend(['@index', '@index@set'])

            # if value is a preserve object, use its value
            if _is_object(value) and '@preserve' in value:
                value = value['@preserve'][0]

            # prefer most specific container including @graph
            if _is_graph(value):
                if '@index' in value:
                    containers.extend(['@graph@index', '@graph@index@set', '@index', '@index@set'])
                if '@id' in value:
                    containers.extend(['@graph@id', '@graph@id@set'])
                containers.extend(['@graph', '@graph@set', '@set'])
                if '@index' not in value:
                    containers.extend(['@graph@index', '@graph@index@set', '@index', '@index@set'])
                if '@id' not in value:
                    containers.extend(['@graph@id', '@graph@id@set'])
            elif _is_object(value) and not _is_value(value):
                containers.extend(['@id', '@id@set', '@type','@set@type'])

            # defaults for term selection based on type/language
            type_or_language = '@language'
            type_or_language_value = '@null'

            if reverse:
                type_or_language = '@type'
                type_or_language_value = '@reverse'
                containers.append('@set')
            # choose most specific term that works for all elements in @list
            elif _is_list(value):
                # only select @list containers if @index is NOT in value
                if '@index' not in value:
                    containers.append('@list')
                list_ = value['@list']
                if len(list_) == 0:
                    # any empty list can be matched against any term that uses
                    # the @list container regardless of @type or @language
                    type_or_language = '@any'
                    type_or_language_value = '@none'
                else:
                    common_language = (
                            default_language if len(list_) == 0 else None)
                    common_type = None
                    for item in list_:
                        item_language = '@none'
                        item_type = '@none'
                        if _is_value(item):
                            if '@language' in item:
                                item_language = item['@language']
                            elif '@type' in item:
                                item_type = item['@type']
                            # plain literal
                            else:
                                item_language = '@null'
                        else:
                            item_type = '@id'
                        if common_language is None:
                            common_language = item_language
                        elif item_language != common_language and \
                                _is_value(item):
                            common_language = '@none'
                        if common_type is None:
                            common_type = item_type
                        elif item_type != common_type:
                            common_type = '@none'
                        # there are different languages and types in the list,
                        # so choose the most generic term, no need to keep
                        # iterating
                        if common_language == '@none' and \
                                common_type == '@none':
                            break
                    if common_language is None:
                        common_language = '@none'
                    if common_type is None:
                        common_type = '@none'
                    if common_type != '@none':
                        type_or_language = '@type'
                        type_or_language_value = common_type
                    else:
                        type_or_language_value = common_language
            # non-@list
            else:
                if _is_value(value):
                    if '@language' in value and '@index' not in value:
                        containers.extend(['@language', '@language@set'])
                        type_or_language_value = value['@language']
                    elif '@type' in value:
                        type_or_language = '@type'
                        type_or_language_value = value['@type']
                else:
                    type_or_language = '@type'
                    type_or_language_value = '@id'
                containers.append('@set')

            # do term selection
            containers.append('@none')

            # an index map can be used to index values using @none, so add as a low priority
            if _is_object(value) and '@index' not in value:
                containers.extend(['@index', '@index@set'])

            # values without type or language can use @language map
            if _is_value(value) and len(value) == 1:
                containers.extend(['@language', '@language@set'])

            term = self._select_term(
                active_ctx, iri, value, containers,
                type_or_language, type_or_language_value)
            if term is not None:
                return term

        # no term match, use @vocab if available
        if vocab:
            if '@vocab' in active_ctx:
                vocab_ = active_ctx['@vocab']
                if iri.startswith(vocab_) and iri != vocab_:
                    # use suffix as relative iri if it is not a term in the
                    # active context
                    suffix = iri[len(vocab_):]
                    if suffix not in active_ctx['mappings']:
                        return suffix

        # no term or @vocab match, check for possible CURIEs
        candidate = None
        for term, definition in active_ctx['mappings'].items():
            # skip terms with colons, they can't be prefixes
            if ':' in term:
                continue
            # skip entries with @ids that are not partial matches
            if (definition is None or definition['@id'] == iri or
                    not iri.startswith(definition['@id'])):
                continue

            # a CURIE is usable if:
            # 1. it has no mapping, OR
            # 2. value is None, which means we're not compacting an @value, AND
            #  the mapping matches the IRI
            curie = term + ':' + iri[len(definition['@id']):]
            is_usable_curie = (
                active_ctx['mappings'][term].get('_prefix') and
                curie not in active_ctx['mappings'] or
                (value is None and
                 active_ctx['mappings'].get(curie, {}).get('@id') == iri))

            # select curie if it is shorter or the same length but
            # lexicographically less than the current choice
            if (is_usable_curie and (
                    candidate is None or
                    _compare_shortest_least(curie, candidate) < 0)):
                candidate = curie

        # return curie candidate
        if candidate is not None:
            return candidate

        # compact IRI relative to base
        if not vocab:
            return remove_base(active_ctx['@base'], iri)

        # return IRI as is
        return iri

    def _compact_value(self, active_ctx, active_property, value):
        """
        Performs value compaction on an object with @value or @id as the only
        property.

        :param active_ctx: the active context.
        :param active_property: the active property that points to the value.
        :param value: the value to compact.
        """
        if _is_value(value):
            # get context rules
            type_ = JsonLdProcessor.get_context_value(
                active_ctx, active_property, '@type')
            language = JsonLdProcessor.get_context_value(
                active_ctx, active_property, '@language')
            container = JsonLdProcessor.arrayify(
                JsonLdProcessor.get_context_value(
                    active_ctx, active_property, '@container'))

            # whether or not the value has an @index that must be preserved
            preserve_index = '@index' in value and '@index' not in container

            # if there's no @index to preserve
            if not preserve_index:
                # matching @type or @language specified in context, compact
                if (('@type' in value and value['@type'] == type_) or
                        ('@language' in value and
                            value['@language'] == language)):
                    return value['@value']

            # return just the value of @value if all are true:
            # 1. @value is the only key or @index isn't being preserved
            # 2. there is no default language or @value is not a string or
            #  the key has a mapping with a null @language
            key_count = len(value)
            is_value_only_key = (
                key_count == 1 or (
                    key_count == 2 and '@index' in value and
                    not preserve_index))
            has_default_language = '@language' in active_ctx
            is_value_string = _is_string(value['@value'])
            has_null_mapping = (
                active_ctx['mappings'].get(active_property) is not None and
                '@language' in active_ctx['mappings'][active_property] and
                active_ctx['mappings'][active_property]['@language'] is None)
            if (is_value_only_key and (
                    not has_default_language or not is_value_string or
                    has_null_mapping)):
                return value['@value']

            rval = {}

            # preserve @index
            if preserve_index:
                rval[self._compact_iri(active_ctx, '@index')] = value['@index']

            # compact @type IRI
            if '@type' in value:
                rval[self._compact_iri(active_ctx, '@type')] = (
                    self._compact_iri(active_ctx, value['@type'], vocab=True))
            # alias @language
            elif '@language' in value:
                rval[self._compact_iri(active_ctx, '@language')] = (
                    value['@language'])

            # alias @value
            rval[self._compact_iri(active_ctx, '@value')] = value['@value']

            return rval

        # value is a subject reference
        expanded_property = self._expand_iri(
            active_ctx, active_property, vocab=True)
        type_ = JsonLdProcessor.get_context_value(
            active_ctx, active_property, '@type')
        compacted = self._compact_iri(
            active_ctx, value['@id'], vocab=(type_ == '@vocab'))

        # compact to scalar
        if type_ in ['@id', '@vocab'] or expanded_property == '@graph':
            return compacted

        rval = {}
        rval[self._compact_iri(active_ctx, '@id')] = compacted
        return rval

    def _create_term_definition(self, active_ctx, local_ctx, term, defined):
        """
        Creates a term definition during context processing.

        :param active_ctx: the current active context.
        :param local_ctx: the local context being processed.
        :param term: the key in the local context to define the mapping for.
        :param defined: a map of defining/defined keys to detect cycles
          and prevent double definitions.
        """
        if term in defined:
            # term already defined
            if defined[term]:
                return
            # cycle detected
            raise JsonLdError(
                'Cyclical context definition detected.',
                'jsonld.CyclicalContext', {
                    'context': local_ctx,
                    'term': term
                }, code='cyclic IRI mapping')

        # now defining term
        defined[term] = False

        if _is_keyword(term):
            raise JsonLdError(
                'Invalid JSON-LD syntax; keywords cannot be overridden.',
                'jsonld.SyntaxError', {'context': local_ctx, 'term': term},
                code='keyword redefinition')

        if term == '':
            raise JsonLdError(
                'Invalid JSON-LD syntax; a term cannot be an empty string.',
                'jsonld.SyntaxError', {'context': local_ctx},
                code='invalid term definition')

        # remove old mapping
        if term in active_ctx['mappings']:
            del active_ctx['mappings'][term]

        # get context term value
        value = local_ctx[term]

        # clear context entry
        if (value is None or (
                _is_object(value) and '@id' in value and
                value['@id'] is None)):
            active_ctx['mappings'][term] = None
            defined[term] = True
            return

        # convert short-hand value to object w/@id
        _simple_term = False
        if _is_string(value):
            _simple_term = True
            value = {'@id': value}

        if not _is_object(value):
            raise JsonLdError(
                'Invalid JSON-LD syntax; @context property values must be '
                'strings or objects.', 'jsonld.SyntaxError',
                {'context': local_ctx}, code='invalid term definition')

        # create new mapping
        mapping = active_ctx['mappings'][term] = {'reverse': False}

        # make sure term definition only has expected keywords
        valid_keys = ['@container', '@id', '@language', '@reverse', '@type']
        if self._processing_mode(active_ctx, 1.1):
            valid_keys.extend(['@context', '@nest', '@prefix'])
        for kw in value:
            if kw not in valid_keys:
                raise JsonLdError(
                    'Invalid JSON-LD syntax; a term definition must not contain ' + kw,
                    'jsonld.SyntaxError',
                    {'context': local_ctx}, code='invalid term definition')

        # always compute whether term has a colon as an optimization for _compact_iri
        _term_has_colon = ':' in term

        if '@reverse' in value:
            if '@id' in value:
                raise JsonLdError(
                    'Invalid JSON-LD syntax; an @reverse term definition must '
                    'not contain @id.', 'jsonld.SyntaxError',
                    {'context': local_ctx}, code='invalid reverse property')
            if '@nest' in value:
                raise JsonLdError(
                    'Invalid JSON-LD syntax; an @reverse term definition must '
                    'not contain @nest.', 'jsonld.SyntaxError',
                    {'context': local_ctx}, code='invalid reverse property')
            reverse = value['@reverse']
            if not _is_string(reverse):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; @context @reverse value must be '
                    'a string.', 'jsonld.SyntaxError', {'context': local_ctx},
                    code='invalid IRI mapping')

            # expand and add @id mapping
            id_ = self._expand_iri(
                active_ctx, reverse, vocab=True, base=False,
                local_ctx=local_ctx, defined=defined)
            if not _is_absolute_iri(id_):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; @context @reverse value must be '
                    'an absolute IRI or a blank node identifier.',
                    'jsonld.SyntaxError', {'context': local_ctx},
                    code='invalid IRI mapping')
            mapping['@id'] = id_
            mapping['reverse'] = True
        elif '@id' in value:
            id_ = value['@id']
            if not _is_string(id_):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; @context @id value must be a '
                    'string.', 'jsonld.SyntaxError',
                    {'context': local_ctx}, code='invalid IRI mapping')
            if id_ != term:
                # add @id to mapping
                id_ = self._expand_iri(
                    active_ctx, id_, vocab=True, base=False,
                    local_ctx=local_ctx, defined=defined)
                if not _is_absolute_iri(id_) and not _is_keyword(id_):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; @context @id value must be '
                        'an absolute IRI, a blank node identifier, or a '
                        'keyword.', 'jsonld.SyntaxError',
                        {'context': local_ctx}, code='invalid IRI mapping')
                mapping['@id'] = id_
                mapping['_prefix'] = (
                    not _term_has_colon
                    and re.match('.*[:/\?#\[\]@]$', id_)
                    and (_simple_term or self._processing_mode(active_ctx, 1.0)))
        if '@id' not in mapping:
            # see if the term has a prefix
            colon = term.find(':')
            if colon != -1:
                prefix = term[0:colon]
                if prefix in local_ctx:
                    # define parent prefix
                    self._create_term_definition(
                        active_ctx, local_ctx, prefix, defined)

                # set @id based on prefix parent
                if active_ctx['mappings'].get(prefix) is not None:
                    suffix = term[colon + 1:]
                    mapping['@id'] = (
                            active_ctx['mappings'][prefix]['@id'] + suffix)
                # term is an absolute IRI
                else:
                    mapping['@id'] = term
            else:
                # non-IRIs MUST define @ids if @vocab not available
                if '@vocab' not in active_ctx:
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; @context terms must define '
                        'an @id.', 'jsonld.SyntaxError', {
                            'context': local_ctx,
                            'term': term
                        }, code='invalid IRI mapping')
                # prepend vocab to term
                mapping['@id'] = active_ctx['@vocab'] + term

        # IRI mapping now defined
        defined[term] = True

        if '@type' in value:
            type_ = value['@type']
            if not _is_string(type_):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; @context @type value must be '
                    'a string.', 'jsonld.SyntaxError',
                    {'context': local_ctx}, code='invalid type mapping')
            if type_ != '@id' and type_ != '@vocab':
                # expand @type to full IRI
                type_ = self._expand_iri(
                    active_ctx, type_, vocab=True,
                    local_ctx=local_ctx, defined=defined)
                if not _is_absolute_iri(type_):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; an @context @type value must '
                        'be an absolute IRI.', 'jsonld.SyntaxError',
                        {'context': local_ctx}, code='invalid type mapping')
                if type_.startswith('_:'):
                    raise JsonLdError(
                        'Invalid JSON-LD syntax; an @context @type values '
                        'must be an IRI, not a blank node identifier.',
                        'jsonld.SyntaxError', {'context': local_ctx},
                        code='invalid type mapping')
            # add @type to mapping
            mapping['@type'] = type_

        if '@container' in value:
            container = JsonLdProcessor.arrayify(value['@container'])
            valid_containers = ['@list', '@set', '@index', '@language']
            is_valid = True
            has_set = '@set' in container

            if self._processing_mode(active_ctx, 1.1):
                valid_containers.extend(['@graph', '@id', '@type'])
                
                # check container length
                if '@list' in container:
                    if len(container) != 1:
                        raise JsonLdError(
                            'Invalid JSON-LD syntax; @context @container with @list must have no other values.',
                            'jsonld.SyntaxError',
                            {'context': local_ctx}, code='invalid container mapping')
                elif '@graph' in container:
                    _extra_keys = [kw for kw in container if kw not in ['@graph', '@id', '@index', '@set']]
                    if _extra_keys:
                        raise JsonLdError(
                            'Invalid JSON-LD syntax; @context @container with @graph must have no other values ' +
                            'other than @id, @index, and @set',
                            'jsonld.SyntaxError',
                            {'context': local_ctx}, code='invalid container mapping')
                else:
                    is_valid = is_valid and (len(container) <= (2 if has_set else 1))
            else: # json-ld-1.0
                is_valid = is_valid and _is_string(value['@container'])

            # check against valid containers
            is_valid = is_valid and not [kw for kw in container if kw not in valid_containers]

            # @set not allowed with @list
            is_valid = is_valid and not (has_set and '@list' in container)

            if not is_valid:
                raise JsonLdError(
                    'Invalid JSON-LD syntax; @context @container value '
                    'must be one of the following: ' + ', '.join(valid_containers) + '.',
                    'jsonld.SyntaxError',
                    {'context': local_ctx}, code='invalid container mapping')
            _extra_reverse_keys = [kw for kw in container if kw not in ['@index', '@set']]
            if (mapping['reverse'] and _extra_reverse_keys):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; @context @container value for '
                    'an @reverse type definition must be @index or @set.',
                    'jsonld.SyntaxError', {'context': local_ctx},
                    code='invalid reverse property')

            # add @container to mapping
            mapping['@container'] = container

        # scoped contexts
        if '@context' in value:
            mapping['@context'] = value['@context']

        if '@language' in value and '@type' not in value:
            language = value['@language']
            if not (language is None or _is_string(language)):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; @context @language value must be '
                    'a string or null.', 'jsonld.SyntaxError',
                    {'context': local_ctx}, code='invalid language mapping')
            # add @language to mapping
            if language is not None:
                language = language.lower()
            mapping['@language'] = language

        # term may be used as prefix
        if '@prefix' in value:
            if _term_has_colon:
                raise JsonLdError(
                    'Invalid JSON-LD syntax; @context @prefix used on a compact IRI term.',
                    'jsonld.SyntaxError',
                    {'context': local_ctx}, code='invalid term definition')
            if not _is_bool(value['@prefix']):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; @context value for @prefix must be boolean.',
                    'jsonld.SyntaxError',
                    {'context': local_ctx}, code='invalid @prefix value')
            mapping['_prefix'] = value['@prefix']

        # nesting
        if '@nest' in value:
            nest = value['@nest']
            if not _is_string(nest) or (nest != '@nest' and nest[0] == '@'):
                raise JsonLdError(
                    'Invalid JSON-LD syntax; @context @nest value must be ' +
                    'a string which is not a keyword other than @nest.',
                    'jsonld.SyntaxError',
                    {'context': local_ctx}, code='invalid @nest value')
            mapping['@nest'] = nest

        # disallow aliasing @context and @preserve
        id_ = mapping['@id']
        if id_ == '@context' or id_ == '@preserve':
            raise JsonLdError(
                'Invalid JSON-LD syntax; @context and @preserve '
                'cannot be aliased.', 'jsonld.SyntaxError',
                {'context': local_ctx}, code='invalid keyword alias')

    def _expand_iri(
            self, active_ctx, value, base=False, vocab=False,
            local_ctx=None, defined=None):
        """
        Expands a string value to a full IRI. The string may be a term, a
        prefix, a relative IRI, or an absolute IRI. The associated absolute
        IRI will be returned.

        :param active_ctx: the current active context.
        :param value: the string value to expand.
        :param base: True to resolve IRIs against the base IRI, False not to.
        :param vocab: True to concatenate after @vocab, False not to.
        :param local_ctx: the local context being processed (only given if
          called during context processing).
        :param defined: a map for tracking cycles in context definitions (only
          given if called during context processing).

        :return: the expanded value.
        """
        # already expanded
        if value is None or _is_keyword(value) or not _is_string(value):
            return value

        # define dependency not if defined
        if (local_ctx and value in local_ctx and
                defined.get(value) is not True):
            self._create_term_definition(active_ctx, local_ctx, value, defined)

        if vocab and value in active_ctx['mappings']:
            mapping = active_ctx['mappings'].get(value)
            # value is explicitly ignored with None mapping
            if mapping is None:
                return None
            # value is a term
            return mapping['@id']

        # split value into prefix:suffix
        if ':' in str(value):
            prefix, suffix = value.split(':', 1)

            # do not expand blank nodes (prefix of '_') or already-absolute
            # IRIs (suffix of '//')
            if prefix == '_' or suffix.startswith('//'):
                return value

            # prefix dependency not defined, define it
            if local_ctx and prefix in local_ctx:
                self._create_term_definition(
                    active_ctx, local_ctx, prefix, defined)

            # use mapping if prefix is defined
            mapping = active_ctx['mappings'].get(prefix)
            if mapping:
                return mapping['@id'] + suffix

            # already absolute IRI
            return value

        # prepend vocab
        if vocab and '@vocab' in active_ctx:
            return active_ctx['@vocab'] + value

        # resolve against base
        rval = value
        if base:
            rval = prepend_base(active_ctx['@base'], rval)

        return rval

    def _find_context_urls(self, input_, urls, replace, base):
        """
        Finds all @context URLs in the given JSON-LD input.

        :param input_: the JSON-LD input.
        :param urls: a map of URLs (url => False/@contexts).
        :param replace: True to replace the URLs in the given input with
                 the @contexts from the urls map, False not to.
        :param base: the base URL to resolve relative URLs against.
        """
        if _is_array(input_):
            for e in input_:
                self._find_context_urls(e, urls, replace, base)
        elif _is_object(input_):
            for k, v in input_.items():
                if k != '@context':
                    self._find_context_urls(v, urls, replace, base)
                    continue

                # array @context
                if _is_array(v):
                    length = len(v)
                    for i in range(length):
                        if _is_string(v[i]):
                            url = prepend_base(base, v[i])
                            # replace w/@context if requested
                            if replace:
                                ctx = urls[url]
                                if _is_array(ctx):
                                    # add flattened context
                                    v.pop(i)
                                    for e in reversed(ctx):
                                        v.insert(i, e)
                                    i += len(ctx) - 1
                                    length = len(v)
                                else:
                                    v[i] = ctx
                            # @context URL found
                            elif url not in urls:
                                urls[url] = False
                        elif _is_object(v[i]):
                          # look for scoped context
                          for kk, vv in v[i].items():
                              if _is_object(vv):
                                  self._find_context_urls(vv, urls, replace, base)
                # string @context
                elif _is_string(v):
                    v = prepend_base(base, v)
                    # replace w/@context if requested
                    if replace:
                        input_[k] = urls[v]
                    # @context URL found
                    elif v not in urls:
                        urls[v] = False
                elif _is_object(v):
                  # look for soped context
                  for kk, vv in v.items():
                      if _is_object(vv):
                          self._find_context_urls(vv, urls, replace, base)

    def _retrieve_context_urls(self, input_, cycles, load_document, base=''):
        """
        Retrieves external @context URLs using the given document loader. Each
        instance of @context in the input that refers to a URL will be
        replaced with the JSON @context found at that URL.

        :param input_: the JSON-LD input with possible contexts.
        :param cycles: an object for tracking context cycles.
        :param load_document(url): the document loader.
        :param base: the base URL to resolve relative URLs against.

        :return: the result.
        """
        if len(cycles) > MAX_CONTEXT_URLS:
            raise JsonLdError(
                'Maximum number of @context URLs exceeded.',
                'jsonld.ContextUrlError', {'max': MAX_CONTEXT_URLS},
                code='loading remote context failed')

        # for tracking URLs to retrieve
        urls = {}

        # find all URLs in the given input
        self._find_context_urls(input_, urls, replace=False, base=base)

        # queue all unretrieved URLs
        queue = []
        for url, ctx in urls.items():
            if ctx is False:
                queue.append(url)

        # retrieve URLs in queue
        for url in queue:
            # check for context URL cycle
            if url in cycles:
                raise JsonLdError(
                    'Cyclical @context URLs detected.',
                    'jsonld.ContextUrlError', {'url': url},
                    code='recursive context inclusion')
            cycles_ = copy.deepcopy(cycles)
            cycles_[url] = True

            # retrieve URL
            try:
                remote_doc = load_document(url)
                ctx = remote_doc['document']
            except Exception as cause:
                raise JsonLdError(
                    'Dereferencing a URL did not result in a valid JSON-LD '
                    'context.',
                    'jsonld.ContextUrlError',  {'url': url},
                    code='loading remote context failed', cause=cause)

            # parse string context as JSON
            if _is_string(ctx):
                try:
                    ctx = json.loads(ctx)
                except Exception as cause:
                    raise JsonLdError(
                        'Could not parse JSON from URL.',
                        'jsonld.ParseError', {'url': url},
                        code='loading remote context failed', cause=cause)

            # ensure ctx is an object
            if not _is_object(ctx):
                raise JsonLdError(
                    'Dereferencing a URL did not result in a valid JSON-LD '
                    'object.',
                    'jsonld.InvalidUrl', {'url': url},
                    code='invalid remote context')

            # use empty context if no @context key is present
            if '@context' not in ctx:
                ctx = {'@context': {}}
            else:
                ctx = {'@context': ctx['@context']}

            # append context URL to context if given
            if remote_doc['contextUrl'] is not None:
                ctx['@context'] = JsonLdProcessor.arrayify(ctx['@context'])
                ctx['@context'].append(remote_doc['contextUrl'])

            # recurse
            self._retrieve_context_urls(ctx, cycles_, load_document, url)
            urls[url] = ctx['@context']

        # replace all URLs in the input
        self._find_context_urls(input_, urls, replace=True, base=base)

    def _get_initial_context(self, options):
        """
        Gets the initial context.

        :param options: the options to use.
          [base] the document base IRI.

        :return: the initial context.
        """
        return {
            '@base': options['base'],
            'processingMode': options.get('processingMode', None),
            'mappings': {},
            'inverse': None
        }

    def _get_inverse_context(self, active_ctx):
        """
        Generates an inverse context for use in the compaction algorithm, if
        not already generated for the given active context.

        :param active_ctx: the active context to use.

        :return: the inverse context.
        """
        # inverse context already generated
        if active_ctx['inverse']:
            return active_ctx['inverse']

        inverse = active_ctx['inverse'] = {}

        # handle default language
        default_language = active_ctx.get('@language', '@none')

        # create term selections for each mapping in the context, ordered by
        # shortest and then lexicographically least
        for term, mapping in sorted(
                active_ctx['mappings'].items(),
                key=cmp_to_key(_compare_shortest_least)):
            if mapping is None:
                continue

            # add term selection where it applies
            container = ''.join(sorted(mapping.get('@container', ['@none'])))

            # iterate over every IRI in the mapping
            iris = JsonLdProcessor.arrayify(mapping['@id'])
            for iri in iris:
                container_map = inverse.setdefault(iri, {})
                entry = container_map.setdefault(
                    container, {
                        '@language': {},
                        '@type': {},
                        '@any': {}})
                entry['@any'].setdefault('@none', term)

                # term is preferred for values using @reverse
                if mapping['reverse']:
                    entry['@type'].setdefault('@reverse', term)
                # term is preferred for values using specific type
                elif '@type' in mapping:
                    entry['@type'].setdefault(mapping['@type'], term)
                # term is preferred for values using specific language
                elif '@language' in mapping:
                    language = mapping['@language']
                    if language is None:
                        language = '@null'
                    entry['@language'].setdefault(language, term)
                # term is preferred for values w/default language or not type
                # and no language
                else:
                    # add an entry for the default language
                    entry['@language'].setdefault(default_language, term)
                    # add entries for no type and no language
                    entry['@type'].setdefault('@none', term)
                    entry['@language'].setdefault('@none', term)

        return inverse

    def _clone_active_context(self, active_ctx):
        """
        Clones an active context, creating a child active context.

        :param active_ctx: the active context to clone.

        :return: a clone (child) of the active context.
        """
        child = {
            '@base': active_ctx['@base'],
            'mappings': copy.deepcopy(active_ctx['mappings']),
            'inverse': None
        }
        if '@language' in active_ctx:
            child['@language'] = active_ctx['@language']
        if '@vocab' in active_ctx:
            child['@vocab'] = active_ctx['@vocab']
        return child


# register the N-Quads RDF parser
register_rdf_parser('application/n-quads', JsonLdProcessor.parse_nquads)
register_rdf_parser('application/nquads', JsonLdProcessor.parse_nquads)


class JsonLdError(Exception):
    """
    Base class for JSON-LD errors.
    """

    def __init__(self, message, type_, details=None, code=None, cause=None):
        Exception.__init__(self, message)
        self.type = type_
        self.details = details
        self.code = code
        self.cause = cause
        self.causeTrace = traceback.extract_tb(*sys.exc_info()[2:])

    def __str__(self):
        rval = str(self.args)
        rval += '\nType: ' + self.type
        if self.code:
            rval += '\nCode: ' + self.code
        if self.details:
            rval += '\nDetails: ' + repr(self.details)
        if self.cause:
            rval += '\nCause: ' + str(self.cause)
            rval += ''.join(traceback.format_list(self.causeTrace))
        return rval


class IdentifierIssuer(object):
    """
    An IdentifierIssuer issues unique identifiers, keeping track of any
    previously issued identifiers.
    """

    def __init__(self, prefix):
        """
        Initializes a new IdentifierIssuer.

        :param prefix: the prefix to use ('<prefix><counter>').
        """
        self.prefix = prefix
        self.counter = 0
        self.existing = {}
        self.order = []

        """
        Gets the new identifier for the given old identifier, where if no old
        identifier is given a new identifier will be generated.

        :param [old]: the old identifier to get the new identifier for.

        :return: the new identifier.
        """
    def get_id(self, old=None):
        # return existing old identifier
        if old and old in self.existing:
            return self.existing[old]

        # get next identifier
        id_ = self.prefix + str(self.counter)
        self.counter += 1

        # save mapping
        if old is not None:
            self.existing[old] = id_
            self.order.append(old)

        return id_

    def has_id(self, old):
        """
        Returns True if the given old identifier has already been assigned a
        new identifier.

        :param old: the old identifier to check.

        :return: True if the old identifier has been assigned a new identifier,
          False if not.
        """
        return old in self.existing


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
                raise JsonLdError(
                    'Unknown output format.',
                    'jsonld.UnknownFormat', {'format': options['format']})

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
            cmp_hashes = cmp_to_key(lambda x, y: cmp(x['hash'], y['hash']))
            for result in sorted(hash_path_list, key=cmp_hashes):
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
            normalized.append(JsonLdProcessor.to_nquad(quad))

        # sort normalized output
        normalized.sort()

        # 8) Return the normalized dataset.
        if (options.get('format') == 'application/n-quads' or
                options.get('format') == 'application/nquads'):
            return ''.join(normalized)
        return JsonLdProcessor.parse_nquads(''.join(normalized))

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
            nquads.append(JsonLdProcessor.to_nquad(copy))

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


def _is_keyword(v):
    """
    Returns whether or not the given value is a keyword.

    :param v: the value to check.

    :return: True if the value is a keyword, False if not.
    """
    if not _is_string(v):
        return False
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
    # must be a string or empty object
    if (_is_string(v) or _is_empty_object(v)):
        return

    # must be an array
    is_valid = False
    if _is_array(v):
        # must contain only strings
        is_valid = True
        for e in v:
            if not _is_string(e):
                is_valid = False
                break

    if not is_valid:
        raise JsonLdError(
            'Invalid JSON-LD syntax; "@type" value must be a string, an array '
            'of strings, or an empty object.',
            'jsonld.SyntaxError', {'value': v}, code='invalid type value')


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


def _is_numeric(v):
    """
    Returns True if the given value is numeric.

    :param v: the value to check.

    :return: True if the value is numeric, False if not.
    """
    try:
        float(v)
        return True
    except ValueError:
        return False


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


def _is_graph(v):
    """
    Note: A value is a graph if all of these hold true:
    1. It is an object.
    2. It has an `@graph` key.
    3. It may have '@id' or '@index'

    :param v: the value to check.

    :return: True if the value is a graph object
    """
    return (_is_object(v) and '@graph' in v and
        len([k for k, vv in v.items() if (k != '@id' and k != '@index')]) == 1)


def _is_simple_graph(v):
    """
    Returns true if the given value is a simple @graph

    :param v: the value to check.

    :return: True if the value is a simple graph object
    """
    return _is_graph(v) and '@id' not in v


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
            rval = (
                len(v) == 0 or
                not ('@value' in v or '@set' in v or '@list' in v))
    return rval


def _is_absolute_iri(v):
    """
    Returns True if the given value is an absolute IRI, False if not.

    :param v: the value to check.

    :return: True if the value is an absolute IRI, False if not.
    """
    return _is_string(v) and ':' in v

def _is_relative_iri(v):
    """
    Returns true if the given value is a relative IRI, false if not.
    Note: this is a weak check.

    :param v: the value to check.

    :return: True if the value is an absolute IRI, False if not.
    """
    return _is_string(v)


class ActiveContextCache(object):
    """
    An ActiveContextCache caches active contexts so they can be reused without
    the overhead of recomputing them.
    """

    def __init__(self, size=100):
        self.order = deque()
        self.cache = {}
        self.size = size

    def get(self, active_ctx, local_ctx):
        key1 = json.dumps(active_ctx)
        key2 = json.dumps(local_ctx)
        return self.cache.get(key1, {}).get(key2)

    def set(self, active_ctx, local_ctx, result):
        if len(self.order) == self.size:
            entry = self.order.popleft()
            del self.cache[entry['activeCtx']][entry['localCtx']]
        key1 = json.dumps(active_ctx)
        key2 = json.dumps(local_ctx)
        self.order.append({'activeCtx': key1, 'localCtx': key2})
        self.cache.setdefault(key1, {})[key2] = json.loads(json.dumps(result))


# Shared in-memory caches.
_cache = {
    'activeCtx': ActiveContextCache()
}
