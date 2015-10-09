#!/usr/bin/env python
"""
Test runner for JSON-LD.

.. module:: runtests
  :synopsis: Test harness for pyld

.. moduleauthor:: Dave Longley
"""

from __future__ import print_function

import datetime
import json
import os
import sys
import traceback
import unittest
from optparse import OptionParser

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
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
        self.parser.add_option('-v', '--verbose', dest='verbose',
            action='store_true', default=False,
            help='Print verbose test data')

        # parse command line options
        (self.options, args) = self.parser.parse_args()

        # ensure a manifest or a directory was specified
        if self.options.manifest is None and self.options.directory is None:
            raise Exception('No test manifest or directory specified.')

        # config runner
        self.failfast = self.options.bail

        # get root manifest filename
        if self.options.manifest:
            filename = os.path.abspath(self.options.manifest)
        else:
            filename = os.path.abspath(
                os.path.join(self.options.directory, 'manifest.jsonld'))

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
            # assume entry is a test
            else:
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

    def setUp(self):
        data = self.data
        manifest = self.manifest

        # skip unknown and explicitly skipped test types
        global SKIP_TESTS
        types = []
        types.extend(get_jsonld_values(data, '@type'))
        types.extend(get_jsonld_values(data, 'type'))
        if self.test_type is None or self.test_type in SKIP_TESTS:
            # FIXME
            skipTest('Test type of %s' % types)

        # expand @id and input base
        if 'baseIri' in manifest.data:
            data['@id'] = (
                manifest.data['baseIri'] +
                os.path.basename(manifest.filename) + data['@id'])
            self.base = self.manifest.data['baseIri'] + data['input']

    def runTest(self):
        data = self.data
        global TEST_TYPES
        test_info = TEST_TYPES[self.test_type]
        fn = test_info['fn']
        params = test_info['params']
        params = [param(self) for param in params]
        result = None
        if self.is_negative:
            expect = data[self._get_expect_property()]
        else:
            expect = read_test_property(self._get_expect_property())(self)

        try:
            result = getattr(jsonld, fn)(*params)
            if self.is_negative:
                raise AssertionError('Expected an error; one was not raised')
            self.assertEqual(result, expect)
        except Exception as e:
            if not self.is_negative:
                if not isinstance(e, AssertionError):
                    print('\n')
                    traceback.print_exc(file=sys.stdout)
                else:
                    print('\nEXPECTED: ', json.dumps(expect, indent=2))
                    print('ACTUAL: ', json.dumps(result, indent=2))
                raise e
            result = get_jsonld_error_code(e)
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
    base = 'http://json-ld.org/test-suite'
    loader = jsonld.get_document_loader()

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
            filename = ROOT_MANIFEST_DIR + doc['documentUrl'][len(base):]
        try:
            doc['document'] = read_json(filename)
        except:
            raise Exception('loading document failed')
        return doc

    def local_loader(url):
        # always load remote-doc and non-base tests remotely
        if ((not url.startswith(base) and url.find(':') != -1) or
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
        'fn': 'compact',
        'params': [
            read_test_url('input'),
            read_test_property('context'),
            create_test_options()
            ]
        },
    'jld:ExpandTest': {
        'fn': 'expand',
        'params': [
            read_test_url('input'),
            create_test_options()
        ]
    },
    'jld:FlattenTest': {
        'fn': 'flatten',
        'params': [
            read_test_url('input'),
            read_test_property('context'),
            create_test_options()
        ]
    },
    'jld:FrameTest': {
        'fn': 'frame',
        'params': [
            read_test_url('input'),
            read_test_property('frame'),
            create_test_options()
        ]
    },
    'jld:FromRDFTest': {
        'fn': 'from_rdf',
        'params': [
            read_test_property('input'),
            create_test_options({'format': 'application/nquads'})
        ]
    },
    'jld:NormalizeTest': {
        'fn': 'normalize',
        'params': [
            read_test_property('input'),
            create_test_options({'format': 'application/nquads'})
        ]
    },
    'jld:ToRDFTest': {
        'fn': 'to_rdf',
        'params': [
            read_test_url('input'),
            create_test_options({'format': 'application/nquads'})
        ]
    },
    'rdfn:Urgna2012EvalTest': {
        'fn': 'normalize',
        'params': [
            read_test_property('action'),
            create_test_options({
                'algorithm': 'URGNA2012',
                'inputFormat': 'application/nquads',
                'format': 'application/nquads'
            })
        ]
    },
    'rdfn:Urdna2015EvalTest': {
        'fn': 'normalize',
        'params': [
            read_test_property('action'),
            create_test_options({
                'algorithm': 'URDNA2015',
                'inputFormat': 'application/nquads',
                'format': 'application/nquads'
            })
        ]
    }
}


if __name__ == '__main__':
    TestRunner(verbosity=2).main()
