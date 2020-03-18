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
            if self.test_type == 'jld:ToRDFTest':
                # Test normalized results
                result = jsonld.normalize(result, {
                    'algorithm': 'URGNA2012',
                    'inputFormat': 'application/n-quads',
                    'format': 'application/n-quads'
                })
                expect = jsonld.normalize(expect, {
                    'algorithm': 'URGNA2012',
                    'inputFormat': 'application/n-quads',
                    'format': 'application/n-quads'
                })
                self.assertEqual(result, expect)
            elif not self.is_negative:
                # Perform order-independent equivalence test
                self.assertTrue(equalUnordered(result, expect))
            else:
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

# Compare values with order-insensitive array tests
def equalUnordered(result, expect):
    if isinstance(result, list) and isinstance(expect, list):
        return(len(result) == len(expect) and
            all(any(equalUnordered(v1, v2) for v2 in expect) for v1 in result))
    elif isinstance(result, dict) and isinstance(expect, dict):
        return(len(result) == len(expect) and
            all(k in expect and equalUnordered(v, expect[k]) for k, v in result.items()))
    else:
        return(result == expect)

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

    def local_loader(url, headers):
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
                # type set
                '.*compact-manifest.jsonld#t0104$',
                '.*compact-manifest.jsonld#t0105$',
                # @container: @graph with multiple objects
                '.*compact-manifest.jsonld#t0109$',
                '.*compact-manifest.jsonld#t0110$',
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
                '.*compact-manifest.jsonld#tdi02$',
                '.*compact-manifest.jsonld#tdi03$',
                '.*compact-manifest.jsonld#tdi07$',
                # IRI confusion
                '.*compact-manifest.jsonld#te002$',
                # included
                '.*compact-manifest.jsonld#tin01$',
                '.*compact-manifest.jsonld#tin02$',
                '.*compact-manifest.jsonld#tin03$',
                '.*compact-manifest.jsonld#tin04$',
                '.*compact-manifest.jsonld#tin05$',
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
                '.*frame-manifest.jsonld#t0016$',
                # graphs
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
                '.*frame-manifest.jsonld#t0068$',
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
        'skip': {
            'specVersion': ['json-ld-1.0'],
            'idRegex': [
                # direction (compound-literal)
                '.*fromRdf-manifest.jsonld#tdi11$',
                '.*fromRdf-manifest.jsonld#tdi12$',
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
                # direction
                '.*toRdf-manifest.jsonld#tdi09$',
                '.*toRdf-manifest.jsonld#tdi10$',
                '.*toRdf-manifest.jsonld#tdi11$',
                '.*toRdf-manifest.jsonld#tdi12$',
                # blank node property
                '.*toRdf-manifest.jsonld#te075$',
                '.*toRdf-manifest.jsonld#te122$',
                # rel vocab
                '.*toRdf-manifest.jsonld#te111$',
                '.*toRdf-manifest.jsonld#te112$',
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
                '.*toRdf-manifest.jsonld#tli03$',
                '.*toRdf-manifest.jsonld#tli04$',
                '.*toRdf-manifest.jsonld#tli05$',
                '.*toRdf-manifest.jsonld#tli06$',
                '.*toRdf-manifest.jsonld#tli07$',
                '.*toRdf-manifest.jsonld#tli08$',
                '.*toRdf-manifest.jsonld#tli09$',
                '.*toRdf-manifest.jsonld#tli10$',
                # number fixes
                '.*toRdf-manifest.jsonld#trt01$',
                # type:none
                '.*toRdf-manifest.jsonld#ttn02$',
                # well formed
                '.*toRdf-manifest.jsonld#twf05$',
                '.*toRdf-manifest.jsonld#twf06$',

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
