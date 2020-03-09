#!/usr/bin/env python
"""
Test runner for JSON-LD.

.. module:: runtests
  :synopsis: Test harness for pyld

.. moduleauthor:: Dave Longley
.. moduleauthor:: Olaf Conradi <olaf@conradi.org>
"""

from __future__ import print_function

import datetime
import json
import os
import sys
import traceback
import unittest
import re
from optparse import OptionParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from pyld import jsonld

try:
    from unittest import TextTestResult
except ImportError:
    from unittest import _TextTestResult as TextTestResult

__copyright__ = 'Copyright (c) 2011-2013 Digital Bazaar, Inc.'
__license__ = 'New BSD license'

# support python 2
if sys.version_info[0] >= 3:
    basestring = str

ROOT_MANIFEST_DIR = None
SKIP_TESTS = []
ONLY_IDENTIFIER = None

LOCAL_BASES = [
    'https://w3c.github.io/json-ld-api/tests',
    'https://w3c.github.io/json-ld-framing/tests',
    'https://github.com/json-ld/normalization/tests'
]

class TestRunner(unittest.TextTestRunner):
    """
    Loads test manifests and runs tests.
    """

    def __init__(self, stream=sys.stderr, descriptions=True, verbosity=1):
        unittest.TextTestRunner.__init__(
            self, stream, descriptions, verbosity)

        # command line options
        self.options = {}
        self.parser = OptionParser()

    def _makeResult(self):
        return EarlTestResult(self.stream, self.descriptions, self.verbosity)

    def main(self):
        print('PyLD Tests')
        print('Use -h or --help to view options.\n')

        # add program options
        self.parser.add_option('-m', '--manifest', dest='manifest',
            help='The single test manifest to run', metavar='FILE')
        self.parser.add_option('-d', '--directory', dest='directory',
            help='The directory with the root manifest to run', metavar='DIR')
        self.parser.add_option('-e', '--earl', dest='earl',
            help='The filename to write an EARL report to')
        self.parser.add_option('-b', '--bail', dest='bail',
            action='store_true', default=False,
            help='Bail out as soon as any test fails')
        self.parser.add_option('-l', '--loader', dest='loader',
            default='requests',
            help='The remote URL document loader: requests, aiohttp '
                 '[default: %default]')
        self.parser.add_option('-n', '--number', dest='number',
            help='Limit tests to those containing the specified test identifier')
        self.parser.add_option('-v', '--verbose', dest='verbose',
            action='store_true', default=False,
            help='Print verbose test data')

        # parse command line options
        (self.options, args) = self.parser.parse_args()

        # ensure a manifest or a directory was specified
        if self.options.manifest is None and self.options.directory is None:
            raise Exception('No test manifest or directory specified.')

        # Set a default JSON-LD document loader
        if self.options.loader == 'requests':
            jsonld._default_document_loader = jsonld.requests_document_loader()
        elif self.options.loader == 'aiohttp':
            jsonld._default_document_loader = jsonld.aiohttp_document_loader()

        # config runner
        self.failfast = self.options.bail

        # get root manifest filename
        if self.options.manifest:
            filename = os.path.abspath(self.options.manifest)
        else:
            filename = os.path.abspath(
                os.path.join(self.options.directory, 'manifest.jsonld'))

        # Global for saving test numbers to focus on
        global ONLY_IDENTIFIER
        if self.options.number:
          ONLY_IDENTIFIER = self.options.number

        # load root manifest
        global ROOT_MANIFEST_DIR
        ROOT_MANIFEST_DIR = os.path.dirname(filename)
        root_manifest = read_json(filename)
        suite = Manifest(root_manifest, filename).load()

        # run tests
        result = self.run(suite)

        # output earl report if specified
        if self.options.earl:
            filename = os.path.abspath(self.options.earl)
            print('Writing EARL report to: %s' % filename)
            result.writeReport(filename)

        if not result.wasSuccessful():
            exit(1)


class Manifest:
    def __init__(self, data, filename):
        self.data = data
        self.suite = unittest.TestSuite()
        self.filename = filename
        self.dirname = os.path.dirname(self.filename)

    def load(self):
        entries = []
        # get entries and sequence (alias for entries)
        entries.extend(get_jsonld_values(self.data, 'entries'))
        entries.extend(get_jsonld_values(self.data, 'sequence'))

        # add includes to entries as jsonld files
        includes = get_jsonld_values(self.data, 'include')
        for filename in includes:
            entries.append(filename + '.jsonld')

        global ONLY_IDENTIFIER

        for entry in entries:
            if isinstance(entry, basestring):
                filename = os.path.join(self.dirname, entry)
                entry = read_json(filename)
            else:
                filename = self.filename

            # entry is another manifest
            if is_jsonld_type(entry, 'mf:Manifest'):
                self.suite = unittest.TestSuite(
                    [self.suite, Manifest(entry, filename).load()])
            # don't add tests that are not focused

            # assume entry is a test
            elif not ONLY_IDENTIFIER or ONLY_IDENTIFIER in entry['@id']:
                self.suite.addTest(Test(self, entry, filename))

        return self.suite


class Test(unittest.TestCase):
    def __init__(self, manifest, data, filename):
        unittest.TestCase.__init__(self)
        #self.maxDiff = None
        self.manifest = manifest
        self.data = data
        self.filename = filename
        self.dirname = os.path.dirname(filename)
        self.is_positive = is_jsonld_type(data, 'jld:PositiveEvaluationTest')
        self.is_negative = is_jsonld_type(data, 'jld:NegativeEvaluationTest')
        self.test_type = None
        self.pending = False
        global TEST_TYPES
        for t in TEST_TYPES.keys():
            if is_jsonld_type(data, t):
                self.test_type = t
                break

    def __str__(self):
        manifest = self.manifest.data.get(
                'name', self.manifest.data.get('label'))
        test_id = self.data.get('id', self.data.get('@id'))
        label = self.data.get(
                'purpose', self.data.get('name', self.data.get('label')))

        return ('%s: %s: %s' % (manifest, test_id, label))

    def _get_expect_property(self):
        '''Find the expected output property or raise error.'''
        if 'expect' in self.data:
            return 'expect'
        elif 'result' in self.data:
            return 'result'
        else:
            raise Exception('No expected output property found')

    def _get_expect_error_code_property(self):
        '''Find the expectErrorCode property.'''
        if 'expectErrorCode' in self.data:
            return 'expectErrorCode'
        else:
            raise Exception('No expectErrorCode property found')

    def setUp(self):
        data = self.data
        manifest = self.manifest
        # skip unknown and explicitly skipped test types
        global SKIP_TESTS
        types = []
        types.extend(get_jsonld_values(data, '@type'))
        types.extend(get_jsonld_values(data, 'type'))
        if self.test_type is None or self.test_type in SKIP_TESTS:
            self.skipTest('Test type of %s' % types)

        global TEST_TYPES
        test_info = TEST_TYPES[self.test_type]

        # expand @id and input base
        if 'baseIri' in manifest.data:
            data['@id'] = (
                manifest.data['baseIri'] +
                os.path.basename(manifest.filename) + data['@id'])
            self.base = self.manifest.data['baseIri'] + data['input']

        # skip based on id regular expression
        skip_id_re = test_info.get('skip', {}).get('idRegex', [])
        for regex in skip_id_re:
            if re.match(regex, data.get('@id', data.get('id', ''))):
                self.skipTest('Test with id regex %s' % regex)

        # mark tests as pending, meaning that they are expected to fail
        pending_id_re = test_info.get('pending', {}).get('idRegex', [])
        for regex in pending_id_re:
            if re.match(regex, data.get('@id', data.get('id', ''))):
                self.pending = 'Test with id regex %s' % regex

        # skip based on description regular expression
        skip_description_re = test_info.get('skip', {}).get(
            'descriptionRegex', [])
        for regex in skip_description_re:
            if re.match(regex, data.get('description', '')):
                self.skipTest('Test with description regex %s' % regex)

        # skip based on processingMode
        skip_pm = test_info.get('skip', {}).get('processingMode', [])
        data_pm = data.get('option', {}).get('processingMode', None)
        if data_pm in skip_pm:
            self.skipTest('Test with processingMode %s' % data_pm)

        # skip based on specVersion
        skip_sv = test_info.get('skip', {}).get('specVersion', [])
        data_sv = data.get('option', {}).get('specVersion', None)
        if data_sv in skip_sv:
            self.skipTest('Test with specVersion %s' % data_sv)

    def runTest(self):
        data = self.data
        global TEST_TYPES
        test_info = TEST_TYPES[self.test_type]
        fn = test_info['fn']
        params = test_info['params']
        params = [param(self) for param in params]
        result = None
        if self.is_negative:
            expect = data[self._get_expect_error_code_property()]
        else:
            expect = read_test_property(self._get_expect_property())(self)

        try:
            result = getattr(jsonld, fn)(*params)
            if self.is_negative and not self.pending:
                raise AssertionError('Expected an error; one was not raised')
            self.assertEqual(result, expect)
            if self.pending and not self.is_negative:
                raise AssertionError('pending positive test passed')
        except AssertionError as e:
            if e.args[0] == 'pending positive test passed':
              print(e)
              raise e
            elif not self.is_negative and not self.pending:
                print('\nEXPECTED: ', json.dumps(expect, indent=2))
                print('ACTUAL: ', json.dumps(result, indent=2))
                raise e
            elif not self.is_negative:
                print('pending')
            elif self.is_negative and self.pending:
                print('pending')
            else:
                raise e
        except Exception as e:
            if not self.is_negative and not self.pending:
                print('\n')
                traceback.print_exc(file=sys.stdout)
                raise e
            result = get_jsonld_error_code(e)
            if self.pending and result == expect:
                print('pending negative test passed')
                raise AssertionError('pending negative test passed')
            elif self.pending:
                print('pending')
            else:
                self.assertEqual(result, expect)


def is_jsonld_type(node, type_):
    node_types = []
    node_types.extend(get_jsonld_values(node, '@type'))
    node_types.extend(get_jsonld_values(node, 'type'))
    types = type_ if isinstance(type_, list) else [type_]
    return len(set(node_types).intersection(set(types))) > 0


def get_jsonld_values(node, property):
    rval = []
    if property in node:
        rval = node[property]
        if not isinstance(rval, list):
            rval = [rval]
    return rval


def get_jsonld_error_code(err):
    if isinstance(err, jsonld.JsonLdError):
        if err.code:
            return err.code
        elif err.cause:
            return get_jsonld_error_code(err.cause)
    return str(err)


def read_json(filename):
    with open(filename) as f:
        return json.load(f)


def read_file(filename):
    with open(filename) as f:
        if sys.version_info[0] >= 3:
            return f.read()
        else:
            return f.read().decode('utf8')


def read_test_url(property):
    def read(test):
        if property not in test.data:
            return None
        if 'baseIri' in test.manifest.data:
            return test.manifest.data['baseIri'] + test.data[property]
        else:
            return test.data[property]
    return read


def read_test_property(property):
    def read(test):
        if property not in test.data:
            return None
        filename = os.path.join(test.dirname, test.data[property])
        if filename.endswith('.jsonld'):
            return read_json(filename)
        else:
            return read_file(filename)
    return read


def create_test_options(opts=None):
    def create(test):
        http_options = ['contentType', 'httpLink', 'httpStatus', 'redirectTo']
        test_options = test.data.get('option', {})
        options = {}
        for k, v in test_options.items():
            if k not in http_options:
                options[k] = v
        options['documentLoader'] = create_document_loader(test)
        options.update(opts or {})
        if 'expandContext' in options:
            filename = os.path.join(test.dirname, options['expandContext'])
            options['expandContext'] = read_json(filename)
        return options
    return create


def create_document_loader(test):
    loader = jsonld.get_document_loader()

    def is_test_suite_url(url):
        return any(url.startswith(base) for base in LOCAL_BASES)

    def strip_base(url):
        for base in LOCAL_BASES:
            if url.startswith(base):
                return url[len(base):]
        raise Exception('unkonwn base')

    def load_locally(url):
        doc = {'contextUrl': None, 'documentUrl': url, 'document': None}
        options = test.data.get('option')
        if options and url == test.base:
            if ('redirectTo' in options and options.get('httpStatus') >= 300):
                doc['documentUrl'] = (
                        test.manifest.data['baseIri'] + options['redirectTo'])
            elif 'httpLink' in options:
                content_type = options.get('contentType')
                if not content_type and url.endswith('.jsonld'):
                    content_type = 'application/ld+json'
                link_header = options.get('httpLink', '')
                if isinstance(link_header, list):
                    link_header = ','.join(link_header)
                link_header = jsonld.parse_link_header(
                    link_header).get('http://www.w3.org/ns/json-ld#context')
                if link_header and content_type != 'application/ld+json':
                    if isinstance(link_header, list):
                        raise Exception('multiple context link headers')
                    doc['contextUrl'] = link_header['target']
        global ROOT_MANIFEST_DIR
        if doc['documentUrl'].find(':') == -1:
            filename = os.path.join(ROOT_MANIFEST_DIR, doc['documentUrl'])
            doc['documentUrl'] = 'file://' + filename
        else:
            #filename = os.path.join(
            #    ROOT_MANIFEST_DIR, doc['documentUrl'][len(base):])
            filename = ROOT_MANIFEST_DIR + strip_base(doc['documentUrl'])
        try:
            doc['document'] = read_json(filename)
        except:
            raise Exception('loading document failed')
        return doc

    def local_loader(url):
        # always load remote-doc and non-base tests remotely
        if ((not is_test_suite_url(url) and url.find(':') != -1) or
                test.manifest.data.get('name') == 'Remote document'):
            return loader(url)

        # attempt to load locally
        return load_locally(url)

    return local_loader


class EarlTestResult(TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        TextTestResult.__init__(self, stream, descriptions, verbosity)
        self.report = EarlReport()

    def addError(self, test, err):
        TextTestResult.addError(self, test, err)
        self.report.add_assertion(test, False)

    def addFailure(self, test, err):
        TextTestResult.addFailure(self, test, err)
        self.report.add_assertion(test, False)

    def addSuccess(self, test):
        TextTestResult.addSuccess(self, test)
        self.report.add_assertion(test, True)

    def writeReport(self, filename):
        self.report.write(filename)


class EarlReport():
    """
    Generates an EARL report.
    """

    def __init__(self):
        self.report = {
            '@context': {
                'doap': 'http://usefulinc.com/ns/doap#',
                'foaf': 'http://xmlns.com/foaf/0.1/',
                'dc': 'http://purl.org/dc/terms/',
                'earl': 'http://www.w3.org/ns/earl#',
                'xsd': 'http://www.w3.org/2001/XMLSchema#',
                'doap:homepage': {'@type': '@id'},
                'doap:license': {'@type': '@id'},
                'dc:creator': {'@type': '@id'},
                'foaf:homepage': {'@type': '@id'},
                'subjectOf': {'@reverse': 'earl:subject'},
                'earl:assertedBy': {'@type': '@id'},
                'earl:mode': {'@type': '@id'},
                'earl:test': {'@type': '@id'},
                'earl:outcome': {'@type': '@id'},
                'dc:date': {'@type': 'xsd:date'}
            },
            '@id': 'https://github.com/digitalbazaar/pyld',
            '@type': [
                'doap:Project',
                'earl:TestSubject',
                'earl:Software'
            ],
            'doap:name': 'PyLD',
            'dc:title': 'PyLD',
            'doap:homepage': 'https://github.com/digitalbazaar/pyld',
            'doap:license': 'https://github.com/digitalbazaar/pyld/blob/master/LICENSE',
            'doap:description': 'A JSON-LD processor for Python',
            'doap:programming-language': 'Python',
            'dc:creator': 'https://github.com/dlongley',
            'doap:developer': {
                '@id': 'https://github.com/dlongley',
                '@type': [
                    'foaf:Person',
                    'earl:Assertor'
                ],
                'foaf:name': 'Dave Longley',
                'foaf:homepage': 'https://github.com/dlongley'
            },
            'dc:date': {
                '@value': datetime.datetime.utcnow().strftime('%Y-%m-%d'),
                '@type': 'xsd:date'
            },
            'subjectOf': []
        }

    def add_assertion(self, test, success):
        self.report['subjectOf'].append({
            '@type': 'earl:Assertion',
            'earl:assertedBy': self.report['doap:developer']['@id'],
            'earl:mode': 'earl:automatic',
            'earl:test': test.data.get('id', test.data.get('@id')),
            'earl:result': {
                '@type': 'earl:TestResult',
                'dc:date': datetime.datetime.utcnow().isoformat(),
                'earl:outcome': 'earl:passed' if success else 'earl:failed'
            }
        })
        return self

    def write(self, filename):
        with open(filename, 'w') as f:
            f.write(json.dumps(self.report, indent=2))
            f.close()


# supported test types
TEST_TYPES = {
    'jld:CompactTest': {
        'pending': {
            'idRegex': [
                # @graph
                '.*compact-manifest.jsonld#t0092$',
                '.*compact-manifest.jsonld#t0093$',
                # rel iri
                '.*compact-manifest.jsonld#t0095$',
                # type set
                '.*compact-manifest.jsonld#t0104$',
                '.*compact-manifest.jsonld#t0105$',
                # rel vocab
                '.*compact-manifest.jsonld#t0107$',
                # scoped context on @type
                '.*compact-manifest.jsonld#tc009$',
                '.*compact-manifest.jsonld#tc012$',
                #'.*compact-manifest.jsonld#tc013$',
                '.*compact-manifest.jsonld#tc014$',
                '.*compact-manifest.jsonld#tc015$',
                '.*compact-manifest.jsonld#tc016$',
                '.*compact-manifest.jsonld#tc017$',
                '.*compact-manifest.jsonld#tc018$',
                '.*compact-manifest.jsonld#tc021$',
                # @propogate
                '.*compact-manifest.jsonld#tc027$',
                # @direction
                '.*compact-manifest.jsonld#tdi01$',
                '.*compact-manifest.jsonld#tdi02$',
                '.*compact-manifest.jsonld#tdi03$',
                '.*compact-manifest.jsonld#tdi04$',
                '.*compact-manifest.jsonld#tdi05$',
                '.*compact-manifest.jsonld#tdi06$',
                '.*compact-manifest.jsonld#tdi07$',
                # IRI confusion
                '.*compact-manifest.jsonld#te002$',
                # @container: @graph with multiple objects
                '.*compact-manifest.jsonld#t0109$',
                '.*compact-manifest.jsonld#t0110$',
                # included
                '.*compact-manifest.jsonld#tin01$',
                '.*compact-manifest.jsonld#tin02$',
                '.*compact-manifest.jsonld#tin03$',
                '.*compact-manifest.jsonld#tin04$',
                '.*compact-manifest.jsonld#tin05$',
                # JSON literals
                '.*compact-manifest.jsonld#tjs01$',
                '.*compact-manifest.jsonld#tjs02$',
                '.*compact-manifest.jsonld#tjs03$',
                '.*compact-manifest.jsonld#tjs04$',
                '.*compact-manifest.jsonld#tjs05$',
                '.*compact-manifest.jsonld#tjs06$',
                '.*compact-manifest.jsonld#tjs07$',
                '.*compact-manifest.jsonld#tjs08$',
                '.*compact-manifest.jsonld#tjs09$',
                '.*compact-manifest.jsonld#tjs10$',
                '.*compact-manifest.jsonld#tjs11$',
                # list of lists
                '.*compact-manifest.jsonld#tli01$',
                '.*compact-manifest.jsonld#tli02$',
                '.*compact-manifest.jsonld#tli03$',
                '.*compact-manifest.jsonld#tli04$',
                '.*compact-manifest.jsonld#tli05$',
                # index on @type
                '.*compact-manifest.jsonld#tm020$',
                '.*compact-manifest.jsonld#tm021$',
                '.*compact-manifest.jsonld#tm022$',
                # property-valued indexes
                '.*compact-manifest.jsonld#tpi01$',
                '.*compact-manifest.jsonld#tpi02$',
                '.*compact-manifest.jsonld#tpi03$',
                '.*compact-manifest.jsonld#tpi04$',
                # protected
                '.*compact-manifest.jsonld#tpr04$',
                # context values
                '.*compact-manifest.jsonld#ts001$',
                '.*compact-manifest.jsonld#ts002$',
                # @type: @none
                '.*compact-manifest.jsonld#ttn01$',
                '.*compact-manifest.jsonld#ttn02$',
                '.*compact-manifest.jsonld#ttn03$',

                # html
                '.*html-manifest.jsonld#tc001$',
                '.*html-manifest.jsonld#tc002$',
                '.*html-manifest.jsonld#tc003$',
                '.*html-manifest.jsonld#tc004$',
            ]
        },
        'skip': {
            # skip tests where behavior changed for a 1.1 processor
            # see JSON-LD 1.0 Errata
            'specVersion': ['json-ld-1.0'],
            'idRegex': [
            ]
        },
        'fn': 'compact',
        'params': [
            read_test_url('input'),
            read_test_property('context'),
            create_test_options()
        ]
    },
    'jld:ExpandTest': {
        'pending': {
            'idRegex': [
                # Don't double-expand an already expanded graph
                '.*expand-manifest.jsonld#t0081$',
                ## rel iri
                '.*expand-manifest.jsonld#t0092$',
                # @graph container
                '.*expand-manifest.jsonld#t0093$',
                '.*expand-manifest.jsonld#t0094$',
                # Double-expand an already expanded graph
                '.*expand-manifest.jsonld#t0095$',
                # indexed graph objects
                '.*expand-manifest.jsonld#t0102$',
                # multiple graphs
                '.*expand-manifest.jsonld#t0103$',
                '.*expand-manifest.jsonld#t0104$',
                ## iris
                '.*expand-manifest.jsonld#t0109$',
                # rel vocab
                '.*expand-manifest.jsonld#t0110$',
                '.*expand-manifest.jsonld#t0111$',
                '.*expand-manifest.jsonld#t0112$',
                # invalid iris
                '.*expand-manifest.jsonld#t0123$',
                # colliding keywords
                '.*expand-manifest.jsonld#t0114$',
                # scoped context
                '.*expand-manifest.jsonld#tc009$',
                '.*expand-manifest.jsonld#tc011$',
                '.*expand-manifest.jsonld#tc013$',
                '.*expand-manifest.jsonld#tc014$',
                '.*expand-manifest.jsonld#tc015$',
                '.*expand-manifest.jsonld#tc016$',
                '.*expand-manifest.jsonld#tc017$',
                '.*expand-manifest.jsonld#tc018$',
                '.*expand-manifest.jsonld#tc021$',
                # @propogate
                '.*expand-manifest.jsonld#tc027$',
                '.*expand-manifest.jsonld#tc028$',
                # text direction
                '.*expand-manifest.jsonld#tdi01$',
                '.*expand-manifest.jsonld#tdi02$',
                '.*expand-manifest.jsonld#tdi04$',
                '.*expand-manifest.jsonld#tdi05$',
                '.*expand-manifest.jsonld#tdi06$',
                '.*expand-manifest.jsonld#tdi07$',
                '.*expand-manifest.jsonld#tdi08$',
                # misc
                '.*expand-manifest.jsonld#te043$',
                '.*expand-manifest.jsonld#te044$',
                # vocab iri/term
                '.*expand-manifest.jsonld#te046$',
                '.*expand-manifest.jsonld#te047$',
                '.*expand-manifest.jsonld#te048$',
                # included
                '.*expand-manifest.jsonld#tin03$',
                '.*expand-manifest.jsonld#tin06$',
                '.*expand-manifest.jsonld#tin07$',
                '.*expand-manifest.jsonld#tin08$',
                '.*expand-manifest.jsonld#tin09$',
                # @json
                '.*expand-manifest.jsonld#tjs01$',
                '.*expand-manifest.jsonld#tjs02$',
                '.*expand-manifest.jsonld#tjs03$',
                '.*expand-manifest.jsonld#tjs04$',
                '.*expand-manifest.jsonld#tjs05$',
                '.*expand-manifest.jsonld#tjs06$',
                '.*expand-manifest.jsonld#tjs07$',
                '.*expand-manifest.jsonld#tjs08$',
                '.*expand-manifest.jsonld#tjs09$',
                '.*expand-manifest.jsonld#tjs10$',
                '.*expand-manifest.jsonld#tjs11$',
                '.*expand-manifest.jsonld#tjs12$',
                '.*expand-manifest.jsonld#tjs13$',
                '.*expand-manifest.jsonld#tjs14$',
                '.*expand-manifest.jsonld#tjs15$',
                '.*expand-manifest.jsonld#tjs16$',
                '.*expand-manifest.jsonld#tjs17$',
                '.*expand-manifest.jsonld#tjs18$',
                '.*expand-manifest.jsonld#tjs19$',
                '.*expand-manifest.jsonld#tjs20$',
                '.*expand-manifest.jsonld#tjs21$',
                '.*expand-manifest.jsonld#tjs22$',
                '.*expand-manifest.jsonld#tjs23$',
                # list of lists
                '.*expand-manifest.jsonld#tli01$',
                '.*expand-manifest.jsonld#tli02$',
                '.*expand-manifest.jsonld#tli03$',
                '.*expand-manifest.jsonld#tli04$',
                '.*expand-manifest.jsonld#tli05$',
                '.*expand-manifest.jsonld#tli06$',
                '.*expand-manifest.jsonld#tli07$',
                '.*expand-manifest.jsonld#tli08$',
                '.*expand-manifest.jsonld#tli09$',
                '.*expand-manifest.jsonld#tli10$',
                # @container: @id/@type
                '.*expand-manifest.jsonld#tm000$',
                # @nest
                '.*expand-manifest.jsonld#tn008$',
                ## property index maps
                '.*expand-manifest.jsonld#tpi05$',
                '.*expand-manifest.jsonld#tpi06$',
                '.*expand-manifest.jsonld#tpi07$',
                '.*expand-manifest.jsonld#tpi08$',
                '.*expand-manifest.jsonld#tpi09$',
                '.*expand-manifest.jsonld#tpi10$',
                '.*expand-manifest.jsonld#tpi11$',
                # protected
                '.*expand-manifest.jsonld#tpr06$',
                '.*expand-manifest.jsonld#tpr07$',
                '.*expand-manifest.jsonld#tpr14$',
                '.*expand-manifest.jsonld#tpr15$',
                '.*expand-manifest.jsonld#tpr16$',
                '.*expand-manifest.jsonld#tpr19$',
                '.*expand-manifest.jsonld#tpr28$',
                '.*expand-manifest.jsonld#tpr30$',
                '.*expand-manifest.jsonld#tpr31$',
                '.*expand-manifest.jsonld#tpr32$',
                # @import should be "invalid context entry" not "recursive context inclusion"
                '.*expand-manifest.jsonld#tso01$',
                '.*expand-manifest.jsonld#tso03$',
                # context propagation
                '.*expand-manifest.jsonld#tso06$',
                # @import should be "invalid context entry" not "recursive context inclusion"
                '.*expand-manifest.jsonld#tso12$',
                # context merging
                '.*expand-manifest.jsonld#tso13$',
                # @type: @none
                '.*expand-manifest.jsonld#ttn02$',

                ## html
                '.*html-manifest.jsonld#te001$',
                '.*html-manifest.jsonld#te002$',
                '.*html-manifest.jsonld#te003$',
                '.*html-manifest.jsonld#te004$',
                '.*html-manifest.jsonld#te005$',
                '.*html-manifest.jsonld#te007$',
                '.*html-manifest.jsonld#te010$',
                '.*html-manifest.jsonld#te014$',
                '.*html-manifest.jsonld#te015$',
                '.*html-manifest.jsonld#te016$',
                '.*html-manifest.jsonld#te017$',
                '.*html-manifest.jsonld#te018$',
                '.*html-manifest.jsonld#te019$',
                '.*html-manifest.jsonld#te020$',
                '.*html-manifest.jsonld#te021$',
                '.*html-manifest.jsonld#te022$',
                '.*html-manifest.jsonld#tex01$',

                ## remote
                '.*remote-doc-manifest.jsonld#t0005$',
                '.*remote-doc-manifest.jsonld#t0006$',
                '.*remote-doc-manifest.jsonld#t0007$',
                '.*remote-doc-manifest.jsonld#t0010$',
                '.*remote-doc-manifest.jsonld#t0011$',
                '.*remote-doc-manifest.jsonld#t0012$',
                '.*remote-doc-manifest.jsonld#t0013$',
                '.*remote-doc-manifest.jsonld#tla01$',
                '.*remote-doc-manifest.jsonld#tla05$',
            ]
        },
        'skip': {
            # skip tests where behavior changed for a 1.1 processor
            # see JSON-LD 1.0 Errata
            'specVersion': ['json-ld-1.0'],
            'idRegex': [
            ]
        },
        'fn': 'expand',
        'params': [
            read_test_url('input'),
            create_test_options()
        ]
    },
    'jld:FlattenTest': {
        'pending': {
            'idRegex': [
                ## html
                '.*html-manifest.jsonld#tf001$',
                '.*html-manifest.jsonld#tf002$',
                '.*html-manifest.jsonld#tf003$',
                '.*html-manifest.jsonld#tf004$',
                # included
                '.*flatten-manifest.jsonld#tin01$',
                '.*flatten-manifest.jsonld#tin02$',
                '.*flatten-manifest.jsonld#tin03$',
                '.*flatten-manifest.jsonld#tin04$',
                '.*flatten-manifest.jsonld#tin05$',
                '.*flatten-manifest.jsonld#tin06$',
                # list of lists
                '.*flatten-manifest.jsonld#tli01$',
                '.*flatten-manifest.jsonld#tli02$',
                '.*flatten-manifest.jsonld#tli03$',
            ]
        },
        'skip': {
            # skip tests where behavior changed for a 1.1 processor
            # see JSON-LD 1.0 Errata
            'specVersion': ['json-ld-1.0'],
            'idRegex': [
            ]
        },
        'fn': 'flatten',
        'params': [
            read_test_url('input'),
            read_test_property('context'),
            create_test_options()
        ]
    },
    'jld:FrameTest': {
        'pending': {
            'idRegex': [
                # misc
                '.*frame-manifest.jsonld#t0011$',
                # graphs
                #'.*frame-manifest.jsonld#t0010$',
                '.*frame-manifest.jsonld#t0020$',
                '.*frame-manifest.jsonld#t0023$',
                '.*frame-manifest.jsonld#t0026$',
                '.*frame-manifest.jsonld#t0027$',
                '.*frame-manifest.jsonld#t0028$',
                '.*frame-manifest.jsonld#t0029$',
                '.*frame-manifest.jsonld#t0030$',
                '.*frame-manifest.jsonld#t0031$',
                '.*frame-manifest.jsonld#t0032$',
                #'.*frame-manifest.jsonld#t0033$',
                '.*frame-manifest.jsonld#t0034$',
                '.*frame-manifest.jsonld#t0035$',
                '.*frame-manifest.jsonld#t0036$',
                '.*frame-manifest.jsonld#t0037$',
                '.*frame-manifest.jsonld#t0038$',
                '.*frame-manifest.jsonld#t0039$',
                '.*frame-manifest.jsonld#t0046$',
                '.*frame-manifest.jsonld#t0040$',
                '.*frame-manifest.jsonld#t0041$',
                '.*frame-manifest.jsonld#t0042$',
                '.*frame-manifest.jsonld#t0043$',
                '.*frame-manifest.jsonld#t0044$',
                '.*frame-manifest.jsonld#t0045$',
                '.*frame-manifest.jsonld#t0047$',
                '.*frame-manifest.jsonld#t0048$',
                '.*frame-manifest.jsonld#t0049$',
                '.*frame-manifest.jsonld#t0050$',
                '.*frame-manifest.jsonld#t0051$',
                # blank nodes
                '.*frame-manifest.jsonld#t0052$',
                '.*frame-manifest.jsonld#t0053$',
                # embed
                '.*frame-manifest.jsonld#t0054$',
                # lists
                '.*frame-manifest.jsonld#t0055$',
                '.*frame-manifest.jsonld#t0058$',
                # @embed:@first
                '.*frame-manifest.jsonld#t0060$',
                # wildcard
                '.*frame-manifest.jsonld#t0061$',
                '.*frame-manifest.jsonld#t0062$',
                '.*frame-manifest.jsonld#t0063$',
                '.*frame-manifest.jsonld#t0064$',
                '.*frame-manifest.jsonld#t0065$',
                '.*frame-manifest.jsonld#t0066$',
                '.*frame-manifest.jsonld#t0067$',
                # misc
                #'.*frame-manifest.jsonld#tp010$',
                '.*frame-manifest.jsonld#teo01$',
                '.*frame-manifest.jsonld#tp050$',
                # ex
                '.*frame-manifest.jsonld#tg001$',
                '.*frame-manifest.jsonld#tg002$',
                '.*frame-manifest.jsonld#tg003$',
                '.*frame-manifest.jsonld#tg004$',
                '.*frame-manifest.jsonld#tg006$',
                '.*frame-manifest.jsonld#tg007$',
                '.*frame-manifest.jsonld#tg008$',
                '.*frame-manifest.jsonld#tg009$',
                '.*frame-manifest.jsonld#tg010$',
                '.*frame-manifest.jsonld#tp046$',
                '.*frame-manifest.jsonld#tp049$',
                # included
                '.*frame-manifest.jsonld#tin01$',
                '.*frame-manifest.jsonld#tin02$',
                '.*frame-manifest.jsonld#tin03$',
                # requireAll
                '.*frame-manifest.jsonld#tra01$',
                '.*frame-manifest.jsonld#tra02$',
                '.*frame-manifest.jsonld#tra03$',
            ]
        },
        'skip': {
            # skip tests where behavior changed for a 1.1 processor
            # see JSON-LD 1.0 Errata
            'specVersion': ['json-ld-1.0'],
            'idRegex': [
            ]
        },
        'fn': 'frame',
        'params': [
            read_test_url('input'),
            read_test_property('frame'),
            create_test_options()
        ]
    },
    'jld:FromRDFTest': {
        'pending': {
            'idRegex': [
                '.*fromRdf-manifest.jsonld#t0023$',
                '.*fromRdf-manifest.jsonld#t0026$',
                # list of lists
                '.*fromRdf-manifest.jsonld#tli01$',
                '.*fromRdf-manifest.jsonld#tli02$',
                '.*fromRdf-manifest.jsonld#tli03$',
                # @json
                '.*fromRdf-manifest.jsonld#tjs01$',
                '.*fromRdf-manifest.jsonld#tjs02$',
                '.*fromRdf-manifest.jsonld#tjs03$',
                '.*fromRdf-manifest.jsonld#tjs04$',
                '.*fromRdf-manifest.jsonld#tjs05$',
                '.*fromRdf-manifest.jsonld#tjs06$',
                '.*fromRdf-manifest.jsonld#tjs07$',
                '.*fromRdf-manifest.jsonld#tjs08$',
                '.*fromRdf-manifest.jsonld#tjs09$',
                '.*fromRdf-manifest.jsonld#tjs10$',
                '.*fromRdf-manifest.jsonld#tjs11$',
                # misc
                '.*fromRdf-manifest.jsonld#tdi06$',
                '.*fromRdf-manifest.jsonld#tdi05$',
                '.*fromRdf-manifest.jsonld#tdi11$',
                '.*fromRdf-manifest.jsonld#tdi12$',
            ]
        },
        'skip': {
            # skip tests where behavior changed for a 1.1 processor
            # see JSON-LD 1.0 Errata
            'specVersion': ['json-ld-1.0'],
            'idRegex': [
            ]
        },
        'fn': 'from_rdf',
        'params': [
            read_test_property('input'),
            create_test_options({'format': 'application/n-quads'})
        ]
    },
    'jld:NormalizeTest': {
        'skip': {},
        'fn': 'normalize',
        'params': [
            read_test_property('input'),
            create_test_options({'format': 'application/n-quads'})
        ]
    },
    'jld:ToRDFTest': {
        'pending': {
            'idRegex': [
                # IRI resolution
                '.*toRdf-manifest.jsonld#t0130$',
                '.*toRdf-manifest.jsonld#t0131$',
                '.*toRdf-manifest.jsonld#t0132$',
                # misc
                '.*toRdf-manifest.jsonld#tc009$',
                '.*toRdf-manifest.jsonld#tc010$',
                '.*toRdf-manifest.jsonld#tc011$',
                '.*toRdf-manifest.jsonld#tc013$',
                '.*toRdf-manifest.jsonld#tc014$',
                '.*toRdf-manifest.jsonld#tc015$',
                '.*toRdf-manifest.jsonld#tc016$',
                '.*toRdf-manifest.jsonld#tc017$',
                '.*toRdf-manifest.jsonld#tc018$',
                '.*toRdf-manifest.jsonld#tc019$',
                '.*toRdf-manifest.jsonld#tc020$',
                '.*toRdf-manifest.jsonld#tc021$',
                '.*toRdf-manifest.jsonld#tc024$',
                '.*toRdf-manifest.jsonld#tc027$',
                '.*toRdf-manifest.jsonld#tc028$',
                # direction
                '.*toRdf-manifest.jsonld#tdi01$',
                '.*toRdf-manifest.jsonld#tdi02$',
                '.*toRdf-manifest.jsonld#tdi03$',
                '.*toRdf-manifest.jsonld#tdi04$',
                '.*toRdf-manifest.jsonld#tdi05$',
                '.*toRdf-manifest.jsonld#tdi06$',
                '.*toRdf-manifest.jsonld#tdi07$',
                '.*toRdf-manifest.jsonld#tdi08$',
                '.*toRdf-manifest.jsonld#tdi09$',
                '.*toRdf-manifest.jsonld#tdi10$',
                '.*toRdf-manifest.jsonld#tdi11$',
                '.*toRdf-manifest.jsonld#tdi12$',
                ## errors
                '.*toRdf-manifest.jsonld#te029$',
                '.*toRdf-manifest.jsonld#te060$',
                '.*toRdf-manifest.jsonld#te066$',
                '.*toRdf-manifest.jsonld#te073$',
                # @vocab mapping
                '.*toRdf-manifest.jsonld#te075$',
                # expandContext option
                '.*toRdf-manifest.jsonld#te077$',
                '.*toRdf-manifest.jsonld#te078$',
                # graph containers
                '.*toRdf-manifest.jsonld#te079$',
                '.*toRdf-manifest.jsonld#te081$',
                '.*toRdf-manifest.jsonld#te085$',
                '.*toRdf-manifest.jsonld#te086$',
                '.*toRdf-manifest.jsonld#te087$',
                '.*toRdf-manifest.jsonld#te088$',
                '.*toRdf-manifest.jsonld#te105$',
                '.*toRdf-manifest.jsonld#te106$',
                '.*toRdf-manifest.jsonld#te118$',
                '.*toRdf-manifest.jsonld#te121$',
                '.*toRdf-manifest.jsonld#te122$',
                '.*toRdf-manifest.jsonld#te123$',
                '.*toRdf-manifest.jsonld#te093$',
                '.*toRdf-manifest.jsonld#te094$',
                '.*toRdf-manifest.jsonld#te095$',
                '.*toRdf-manifest.jsonld#te096$',
                '.*toRdf-manifest.jsonld#te097$',
                '.*toRdf-manifest.jsonld#te098$',
                '.*toRdf-manifest.jsonld#te099$',
                '.*toRdf-manifest.jsonld#te100$',
                '.*toRdf-manifest.jsonld#te101$',
                '.*toRdf-manifest.jsonld#te107$',
                '.*toRdf-manifest.jsonld#te108$',
                ## rel IRI
                '.*toRdf-manifest.jsonld#te092$',
                # Does not create a new graph object
                '.*toRdf-manifest.jsonld#te102$',
                '.*toRdf-manifest.jsonld#te103$',
                '.*toRdf-manifest.jsonld#te104$',
                '.*toRdf-manifest.jsonld#te109$',
                '.*toRdf-manifest.jsonld#te110$',
                '.*toRdf-manifest.jsonld#te111$',
                '.*toRdf-manifest.jsonld#te112$',
                # colliding keyword
                '.*toRdf-manifest.jsonld#te114$',
                # included
                '.*toRdf-manifest.jsonld#tin01$',
                '.*toRdf-manifest.jsonld#tin02$',
                '.*toRdf-manifest.jsonld#tin03$',
                '.*toRdf-manifest.jsonld#tin04$',
                '.*toRdf-manifest.jsonld#tin05$',
                '.*toRdf-manifest.jsonld#tin06$',
                # @json
                '.*toRdf-manifest.jsonld#tjs01$',
                '.*toRdf-manifest.jsonld#tjs02$',
                '.*toRdf-manifest.jsonld#tjs03$',
                '.*toRdf-manifest.jsonld#tjs04$',
                '.*toRdf-manifest.jsonld#tjs05$',
                '.*toRdf-manifest.jsonld#tjs06$',
                '.*toRdf-manifest.jsonld#tjs07$',
                '.*toRdf-manifest.jsonld#tjs08$',
                '.*toRdf-manifest.jsonld#tjs09$',
                '.*toRdf-manifest.jsonld#tjs10$',
                '.*toRdf-manifest.jsonld#tjs11$',
                '.*toRdf-manifest.jsonld#tjs12$',
                '.*toRdf-manifest.jsonld#tjs13$',
                '.*toRdf-manifest.jsonld#tjs14$',
                '.*toRdf-manifest.jsonld#tjs15$',
                '.*toRdf-manifest.jsonld#tjs16$',
                '.*toRdf-manifest.jsonld#tjs17$',
                '.*toRdf-manifest.jsonld#tjs18$',
                '.*toRdf-manifest.jsonld#tjs19$',
                '.*toRdf-manifest.jsonld#tjs20$',
                '.*toRdf-manifest.jsonld#tjs21$',
                '.*toRdf-manifest.jsonld#tjs22$',
                '.*toRdf-manifest.jsonld#tjs23$',
                # list of lists
                '.*toRdf-manifest.jsonld#tli01$',
                '.*toRdf-manifest.jsonld#tli02$',
                # index on @type
                '.*toRdf-manifest.jsonld#tm001$',
                '.*toRdf-manifest.jsonld#tm002$',
                '.*toRdf-manifest.jsonld#tm003$',
                '.*toRdf-manifest.jsonld#tm004$',
                #'.*toRdf-manifest.jsonld#tm005$',
                '.*toRdf-manifest.jsonld#tm006$',
                '.*toRdf-manifest.jsonld#tm007$',
                '.*toRdf-manifest.jsonld#tm008$',
                '.*toRdf-manifest.jsonld#tm009$',
                '.*toRdf-manifest.jsonld#tm010$',
                '.*toRdf-manifest.jsonld#tm011$',
                '.*toRdf-manifest.jsonld#tm012$',
                # @nest
                '.*toRdf-manifest.jsonld#tn001$',
                '.*toRdf-manifest.jsonld#tn002$',
                '.*toRdf-manifest.jsonld#tn003$',
                '.*toRdf-manifest.jsonld#tn004$',
                '.*toRdf-manifest.jsonld#tn005$',
                '.*toRdf-manifest.jsonld#tn006$',
                '.*toRdf-manifest.jsonld#tn007$',
                '.*toRdf-manifest.jsonld#tn008$',
                # processing
                '.*toRdf-manifest.jsonld#tp002$',
                '.*toRdf-manifest.jsonld#tp003$',
                '.*toRdf-manifest.jsonld#tp004$',
                ## index maps
                '.*toRdf-manifest.jsonld#tpi05$',
                '.*toRdf-manifest.jsonld#tpi06$',
                '.*toRdf-manifest.jsonld#tpi07$',
                '.*toRdf-manifest.jsonld#tpi08$',
                '.*toRdf-manifest.jsonld#tpi09$',
                '.*toRdf-manifest.jsonld#tpi10$',
                '.*toRdf-manifest.jsonld#tpi11$',
                # prefix
                '.*toRdf-manifest.jsonld#tpr02$',
                '.*toRdf-manifest.jsonld#tpr06$',
                '.*toRdf-manifest.jsonld#tpr10$',
                '.*toRdf-manifest.jsonld#tpr13$',
                '.*toRdf-manifest.jsonld#tpr14$',
                '.*toRdf-manifest.jsonld#tpr15$',
                '.*toRdf-manifest.jsonld#tpr16$',
                '.*toRdf-manifest.jsonld#tpr19$',
                '.*toRdf-manifest.jsonld#tpr22$',
                '.*toRdf-manifest.jsonld#tpr25$',
                '.*toRdf-manifest.jsonld#tpr28$',
                '.*toRdf-manifest.jsonld#tpr30$',
                '.*toRdf-manifest.jsonld#tpr31$',
                '.*toRdf-manifest.jsonld#tpr32$',
                '.*toRdf-manifest.jsonld#tpr39$',
                # number fixes
                '.*toRdf-manifest.jsonld#trt01$',
                # @import
                '.*toRdf-manifest.jsonld#tso01$',
                '.*toRdf-manifest.jsonld#tso03$',
                # @propogate
                '.*toRdf-manifest.jsonld#tso05$',
                '.*toRdf-manifest.jsonld#tso06$',
                # context merging
                '.*toRdf-manifest.jsonld#tso12$',
                '.*toRdf-manifest.jsonld#tso13$',
                # type:none
                '.*toRdf-manifest.jsonld#ttn02$',
                # well formed
                '.*toRdf-manifest.jsonld#twf01$',
                '.*toRdf-manifest.jsonld#twf02$',
                '.*toRdf-manifest.jsonld#twf03$',
                '.*toRdf-manifest.jsonld#twf04$',
                '.*toRdf-manifest.jsonld#twf05$',
                '.*toRdf-manifest.jsonld#twf06$',
                '.*toRdf-manifest.jsonld#twf07$',

                ## html
                '.*html-manifest.jsonld#tr001$',
                '.*html-manifest.jsonld#tr002$',
                '.*html-manifest.jsonld#tr003$',
                '.*html-manifest.jsonld#tr004$',
                '.*html-manifest.jsonld#tr005$',
                '.*html-manifest.jsonld#tr006$',
                '.*html-manifest.jsonld#tr007$',
                '.*html-manifest.jsonld#tr010$',
                '.*html-manifest.jsonld#tr014$',
                '.*html-manifest.jsonld#tr015$',
                '.*html-manifest.jsonld#tr016$',
                '.*html-manifest.jsonld#tr017$',
                '.*html-manifest.jsonld#tr018$',
                '.*html-manifest.jsonld#tr019$',
                '.*html-manifest.jsonld#tr020$',
                '.*html-manifest.jsonld#tr021$',
                '.*html-manifest.jsonld#tr022$',
            ]
        },
        'skip': {
            # skip tests where behavior changed for a 1.1 processor
            # see JSON-LD 1.0 Errata
            'specVersion': ['json-ld-1.0'],
            'idRegex': [
                # nt
                '.*toRdf-manifest.jsonld#tnt01$',
                '.*toRdf-manifest.jsonld#tnt02$',
                '.*toRdf-manifest.jsonld#tnt03$',
                '.*toRdf-manifest.jsonld#tnt04$',
                '.*toRdf-manifest.jsonld#tnt05$',
                '.*toRdf-manifest.jsonld#tnt06$',
                '.*toRdf-manifest.jsonld#tnt07$',
                '.*toRdf-manifest.jsonld#tnt08$',
                '.*toRdf-manifest.jsonld#tnt09$',
                '.*toRdf-manifest.jsonld#tnt10$',
                '.*toRdf-manifest.jsonld#tnt11$',
                '.*toRdf-manifest.jsonld#tnt12$',
                '.*toRdf-manifest.jsonld#tnt13$',
                '.*toRdf-manifest.jsonld#tnt14$',
                '.*toRdf-manifest.jsonld#tnt15$',
                '.*toRdf-manifest.jsonld#tnt16$',
            ]
        },
        'fn': 'to_rdf',
        'params': [
            read_test_url('input'),
            create_test_options({'format': 'application/n-quads'})
        ]
    },
    'rdfn:Urgna2012EvalTest': {
        'pending': {
            'idRegex': [
            ]
        },
        'skip': {
            'idRegex': [
                '.*manifest-urgna2012#test060$',
            ]
        },
        'fn': 'normalize',
        'params': [
            read_test_property('action'),
            create_test_options({
                'algorithm': 'URGNA2012',
                'inputFormat': 'application/n-quads',
                'format': 'application/n-quads'
            })
        ]
    },
    'rdfn:Urdna2015EvalTest': {
        'pending': {
            'idRegex': [
            ]
        },
        'skip': {
            'idRegex': [
                '.*manifest-urdna2015#test059$',
                '.*manifest-urdna2015#test060$',
            ]
        },
        'fn': 'normalize',
        'params': [
            read_test_property('action'),
            create_test_options({
                'algorithm': 'URDNA2015',
                'inputFormat': 'application/n-quads',
                'format': 'application/n-quads'
            })
        ]
    }
}


if __name__ == '__main__':
    TestRunner(verbosity=2).main()
