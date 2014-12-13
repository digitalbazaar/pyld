#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
"""
pyldcli - CLI script for PyLD
"""
import codecs
import json
import logging
import os
import sys

import pyld

log = logging.getLogger()


def rdf_to_jsonld(path, options):
    """
    Read an RDF dataset and generate a JSON-LD string

    :param path: path to an RDF file
    :param options: options dict
    :returns: JSON-LD string
    :rtype: str
    """
    # format=None, useRdfType=False, useNativeTypes=False
    # compact=None
    log.debug("rdf_to_jsonld: %r, %r" % (path, options))
    with codecs.open(path, 'r', encoding='utf8') as f:
        output = pyld.jsonld.from_rdf(f.read(), options)
        assert isinstance(output, list)

    compact = options.get('compact')
    frame = options.get('frame')
    if compact:
        if os.path.exists(compact):
            with codecs.open(compact, 'r', encoding='utf-8') as f:
                compact_str = f.read()
        else:
            compact_str = compact
        output = pyld.jsonld.compact(output, compact_str)

    elif options.get('expand'):
        output = pyld.jsonld.expand(output)

    elif options.get('flatten'):
        output = pyld.jsonld.flatten(output)

    elif frame:
        output = pyld.jsonld.frame(output, frame)  # TODO

    elif options.get('normalize'):
        output = pyld.jsonld.normalize(output, {'format': options.get('format')})

    json_str = json.dumps(output, indent=options.get('indent', 1))
    log.debug("rdf_to_jsonld: len(output): %d" % len(json_str))
    return json_str


import unittest
class Test_pyldcli(unittest.TestCase):
    def setUp(self):
        self.TEST_NQUADS = '../tb/schema.ttl.nquads'
        self.__exit = sys.exit
        sys.exit = lambda x: x

    def tearDown(self):
        sys.exit = self.__exit

    def test_00_pyldcli(self):
        #output = main('')
        #self.assertEqual(output, 0)
        output = main('-h')
        self.assertEqual(output, 0)
        output = main('--help')
        self.assertEqual(output, 0)

    def test_01_rdf_to_jsonld(self):
        output = main('--rdf-to-jsonld', self.TEST_NQUADS)
        self.assertEqual(output, 0)
        output = main('--rdf-to-jsonld', self.TEST_NQUADS,
                      '--format', 'application/nquads')
        self.assertEqual(output, 0)

    def test_01_rdf_to_jsonld_unknown_format_raises(self):
        with self.assertRaises(pyld.jsonld.JsonLdError):
            output = main('--rdf-to-jsonld', self.TEST_NQUADS,
                        '--format', 'application/xyz')
            self.assertNotEqual(output, 0)

    def test_02_rdf_to_jsonld_indent(self):
        output = main('--rdf-to-jsonld', self.TEST_NQUADS, '--indent', '0')
        self.assertEqual(output, 0)
        output = main('--rdf-to-jsonld', self.TEST_NQUADS, '--indent', '2')
        self.assertEqual(output, 0)

    def test_03_rdf_to_jsonld_useRdfType(self):
        output = main('--rdf-to-jsonld', self.TEST_NQUADS, '--rdf-type')
        self.assertEqual(output, 0)

    def test_04_rdf_to_jsonld_useNativeTypes(self):
        output = main('--rdf-to-jsonld', self.TEST_NQUADS, '--native-types')
        self.assertEqual(output, 0)

    def test_05_rdf_to_jsonld_compact(self):
        output = main('--rdf-to-jsonld', self.TEST_NQUADS,
                      '--compact', 'http://schema.org')
        self.assertEqual(output, 0)

    def test_06_rdf_to_jsonld_expand(self):
        output = main('--rdf-to-jsonld', self.TEST_NQUADS,
                      '--expand')
        self.assertEqual(output, 0)

    def test_06_rdf_to_jsonld_flatten(self):
        output = main('--rdf-to-jsonld', self.TEST_NQUADS,
                      '--flatten')
        self.assertEqual(output, 0)

    def test_06_rdf_to_jsonld_frame(self):
        output = main('--rdf-to-jsonld', self.TEST_NQUADS,
                      '--frame')
        self.assertEqual(output, 0)

    def test_06_rdf_to_jsonld_normalize(self):
        output = main('--rdf-to-jsonld', self.TEST_NQUADS,
                      '--normalize')
        self.assertEqual(output, 0)


def main(*argv):
    import argparse

    prs = argparse.ArgumentParser() # usage="%prog [args] filename")

    # from_rdf
    prs.add_argument('--rdf-to-jsonld',
                     help='TASK: Convert an RDF dataset to JSON-LD',
                     dest='rdf_to_jsonld',
                     action='store')

    prs.add_argument('--format',
                     help='Input file format [default: application/nquads]',
                     dest='format',
                     action='store')

    prs.add_argument('--rdf-type',
                     help='Use rdf:type instead of @type',
                     dest='useRdfType',
                     action='store_true')
    prs.add_argument('--native-types',
                     help='Convert XSD types into native types',
                     dest='useNativeTypes',
                     action='store_true')

    prs.add_argument('--indent',
                     help='Indent json with n spaces [default: 1]',
                     dest='indent',
                     action='store',
                     type=int,
                     default=1)

    prs.add_argument('--compact',
                     help=('ACTION: Compact the document with the given '
                           '@context file or URI'),
                     dest='compact',
                     action='store')
    prs.add_argument('--expand',
                     help='ACTION: Perform JSON-LD expansion',
                     dest='expand',
                     action='store_true')
    prs.add_argument('--flatten',
                     help='ACTION: Perform JSON-LD flattening',
                     dest='flatten',
                     action='store_true')
    prs.add_argument('--frame',
                     help='ACTION: Perform JSON-LD framing',
                     dest='frame',
                     action='store_true')
    prs.add_argument('--normalize',
                     help='ACTION: Perform JSON-LD normalization',
                     dest='normalize',
                     action='store_true',
                     default=False)



    prs.add_argument('--base',
                     help='Base IRI to use',
                     dest='base',
                     action='store')
    prs.add_argument('--dont-compact-arrays',
                     help='Don\'t compact arrays to single values',
                     dest='dont_compact_arrays',
                     action='store_true',
                     default=False)
    prs.add_argument('--top-level-graph',
                     help='Always output a top level graph (default: False)',
                     dest='top_level_graph',
                     action='store_true',
                     default=False)
    prs.add_argument('--expand-context',
                     help='@context file or URI to expand with',
                     dest='expandContext',
                     action='store',
                     default=None)

    prs.add_argument('--no-embed',
                     help='default @embed flag (default: True)',
                     dest='embed',
                     action='store_false',
                     default=True)
    prs.add_argument('--explicit',
                     help='default @explicit flag (default: False)',
                     dest='explicit',
                     action='store_true',
                     default=False)
    prs.add_argument('--no-require-all',
                     help='default @requireAll flag (default: True)',
                     dest='requireAll',
                     action='store_false',
                     default=True)
    prs.add_argument('--omit-default',
                     help='default @omitDefault flag (default: False)',
                     dest='omitDefault',
                     action='store_true',
                     default=False)


    prs.add_argument('-v', '--verbose',
                     dest='verbose',
                     action='store_true',)
    prs.add_argument('-q', '--quiet',
                     dest='quiet',
                     action='store_true',)
    prs.add_argument('-t', '--test',
                     dest='run_tests',
                     action='store_true',)
    if not argv:
        _argv = sys.argv[1:]
    else:
        _argv = list(argv)
    opts = prs.parse_args(args=_argv)

    if not opts.quiet:
        logging.basicConfig()

        if opts.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    if opts.run_tests:
        _args = _argv[:]
        _args.remove('-t')
        sys.argv = [sys.argv[0]] + _args
        sys.exit(unittest.main())

    if opts.rdf_to_jsonld:
        options = {
            # read_rdf
            'useRdfType': opts.useRdfType,
            'useNativeTypes': opts.useNativeTypes,
            # rdf_to_jsonld
            'compact': opts.compact,
            'base': opts.base,
            'compactArrays': not opts.dont_compact_arrays,
            'graph': opts.top_level_graph,
            'expandContext': opts.expandContext,

            'expand': opts.expand,
             # base
             # expandContext

            'flatten': opts.flatten,
             # base
             # expandContext

            'frame': opts.frame,
             # base
             # expandContext
            'embed': opts.embed,
            'explicit': opts.explicit,
            'requireAll': opts.requireAll,
            'omitDefault': opts.omitDefault,

            'normalize': opts.normalize,

            # json.dumps
            'indent': opts.indent,
        }
        if opts.format is not None:
            options['format'] = opts.format  # read_rdf

        json_str = rdf_to_jsonld(opts.rdf_to_jsonld, options)
        #print(json_str)

    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
