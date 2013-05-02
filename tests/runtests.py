#!/usr/bin/env python
"""
Runs json-ld.org unit tests for JSON-LD.
 
.. module:: runtests
  :synopsis: Test harness for pyld

.. moduleauthor:: Dave Longley
.. moduleauthor:: Mike Johnson
"""

__copyright__ = 'Copyright (c) 2011-2013 Digital Bazaar, Inc.'
__license__ = 'New BSD license'

import os, sys, json, datetime
from os.path import join
from optparse import OptionParser

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
from pyld import jsonld

# supported test types
TEST_TYPES = [
    'jld:ExpandTest',
    'jld:CompactTest',
    'jld:FlattenTest',
    'jld:FrameTest',
    'jld:FromRDFTest',
    'jld:ToRDFTest',
    'jld:NormalizeTest']

SKIP_TEST_TYPES = ['jld:ApiErrorTest']

# EARL report
EARL = {
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
    'doap:name': 'PyLd',
    'dc:title': 'PyLd',
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

class TestRunner:
    """
    Loads test files and runs groups of tests.
    """

    def __init__(self):
        # command line options
        self.options = {}
        self.parser = OptionParser()
        self.manifest_files = []

    def main(self):
        print 'PyLD Unit Tests'
        print 'Use -h or --help to view options.'

        # add program options
        self.parser.add_option('-f', '--file', dest='file',
            help='The single test file to run', metavar='FILE')
        self.parser.add_option('-d', '--directory', dest='directory',
            help='The directory full of test files', metavar='DIR')
        self.parser.add_option('-e', '--earl', dest='earl',
            help='The filename to write the EARL report to', metavar='EARL')
        self.parser.add_option('-v', '--verbose', dest='verbose',
            action='store_true', default=False,
            help='Prints verbose test data')

        # parse options
        (self.options, args) = self.parser.parse_args()

        # check if file or directory were specified
        if self.options.file == None and self.options.directory == None:
            raise Exception('No test file or directory specified.')

        # check if file was specified, exists, and is file
        if self.options.file is not None:
            if (os.path.exists(self.options.file) and
                os.path.isfile(self.options.file)):
                # add manifest file to the file list
                self.manifest_files.append(os.path.abspath(self.options.file))
            else:
                raise Exception('Invalid test file: "%s"' % self.options.file)

        # check if directory was specified, exists and is dir
        if self.options.directory is not None:
            if (os.path.exists(self.options.directory) and
                os.path.isdir(self.options.directory)):
                # load manifest files from test directory
                for test_dir, dirs, files in os.walk(self.options.directory):
                    for manifest in files:
                        # add all .jsonld manifest files to the file list
                        if (manifest.find('manifest') != -1 and
                            manifest.endswith('.jsonld')):
                            self.manifest_files.append(
                                join(test_dir, manifest))
            else:
                raise Exception('Invalid test directory: "%s"' %
                    self.options.directory)

        # see if any manifests have been specified
        if len(self.manifest_files) == 0:
            raise Exception('No manifest files found.')

        passed = 0
        failed = 0
        total = 0

        # run the tests from each manifest file
        for manifest_file in self.manifest_files:
            test_dir = os.path.dirname(manifest_file)
            manifest = json.load(open(manifest_file, 'r'))
            count = 1

            for test in manifest['sequence']:
                # skip unsupported types
                skip = True
                test_type = test['@type']
                for tt in test_type:
                    if tt in SKIP_TEST_TYPES:
                        skip = True
                        break
                    if tt in TEST_TYPES:
                        skip = False
                if skip:
                    # print 'Skipping test: "%s" ...' % test['name']
                    continue

                print 'JSON-LD/%s %04d/%s...' % (
                    manifest['name'], count, test['name']),

                total += 1
                count += 1

                # read input file
                with open(join(test_dir, test['input'])) as f:
                    if test['input'].endswith('.jsonld'):
                        input = json.load(f)
                    else:
                        input = f.read().decode('utf8')
                # read expect file
                with open(join(test_dir, test['expect'])) as f:
                    if test['expect'].endswith('.jsonld'):
                        expect = json.load(f)
                    else:
                        expect = f.read().decode('utf8')
                result = None

                # JSON-LD options
                options = {
                    'base': 'http://json-ld.org/test-suite/tests/' +
                        test['input']}

                success = False
                try:
                    if 'jld:ExpandTest' in test_type:
                        result = jsonld.expand(input, options)
                    elif 'jld:CompactTest' in test_type:
                        ctx = json.load(open(join(test_dir, test['context'])))
                        result = jsonld.compact(input, ctx, options)
                    elif 'jld:FlattenTest' in test_type:
                        result = jsonld.flatten(input, None, options)
                    elif 'jld:FrameTest' in test_type:
                        frame = json.load(open(join(test_dir, test['frame'])))
                        result = jsonld.frame(input, frame, options)
                    elif 'jld:FromRDFTest' in test_type:
                        result = jsonld.from_rdf(input, options)
                    elif 'jld:ToRDFTest' in test_type:
                        options['format'] = 'application/nquads'
                        result = jsonld.to_rdf(input, options)
                    elif 'jld:NormalizeTest' in test_type:
                        options['format'] = 'application/nquads'
                        result = jsonld.normalize(input, options)

                    # check the expected value against the test result
                    success = deep_compare(expect, result)

                    if success:
                        passed += 1
                        print 'PASS'
                    else:
                        failed += 1
                        print 'FAIL'

                    if not success or self.options.verbose:
                        print 'Expect:', json.dumps(expect, indent=2)
                        print 'Result:', json.dumps(result, indent=2)
                except jsonld.JsonLdError as e:
                    print '\nError: ', e
                    failed += 1
                    print 'FAIL'

                # add EARL report assertion
                EARL['subjectOf'].append({
                    '@type': 'earl:Assertion',
                    'earl:assertedBy': EARL['doap:developer']['@id'],
                    'earl:mode': 'earl:automatic',
                    'earl:test': ('http://json-ld.org/test-suite/tests/' +
                        os.path.basename(manifest_file) + test['@id']),
                    'earl:result': {
                        '@type': 'earl:TestResult',
                        'dc:date': datetime.datetime.utcnow().isoformat(),
                        'earl:outcome': ('earl:' + 'passed' if success else
                            'failed')
                    }
                })

        if self.options.earl:
            f = open(self.options.earl, 'w')
            f.write(json.dumps(EARL, indent=2))
            f.close()

        print 'Done. Total:%d Passed:%d Failed:%d' % (total, passed, failed)

def deep_compare(expect, result):
    if isinstance(expect, list):
        if not isinstance(result, list):
            return False
        if len(expect) != len(result):
            return False
        for a, b in zip(expect, result):
            if not deep_compare(a, b):
                return False
        return True

    if isinstance(expect, dict):
        if not isinstance(result, dict):
            return False
        if len(expect) != len(result):
            return False
        for k, v in expect.items():
            if k not in result:
                return False
            if not deep_compare(v, result[k]):
                return False
        return True

    return expect == result


if __name__ == '__main__':
   tr = TestRunner()
   tr.main()
