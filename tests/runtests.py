#!/usr/bin/env python
"""
Test runner for JSON-LD.

.. module:: runtests
  :synopsis: Test harness for pyld

.. moduleauthor:: Dave Longley
.. moduleauthor:: Olaf Conradi <olaf@conradi.org>
"""

import datetime
import json
import os
import re
import sys
import traceback
import unittest
from argparse import ArgumentParser
from unittest import TextTestResult

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from pyld import jsonld

__copyright__ = 'Copyright (c) 2011-2013 Digital Bazaar, Inc.'
__license__ = 'New BSD license'

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

        # command line args
        self.options = {}
        self.parser = ArgumentParser()

    def _makeResult(self):
        return EarlTestResult(self.stream, self.descriptions, self.verbosity)

    def main(self):
        print('PyLD Tests')
        print('Use -h or --help to view options.\n')

        # add program options
        self.parser.add_argument('tests', metavar='TEST', nargs='*',
            help='A manifest or directory to test')
        self.parser.add_argument('-e', '--earl', dest='earl',
            help='The filename to write an EARL report to')
        self.parser.add_argument('-b', '--bail', dest='bail',
            action='store_true', default=False,
            help='Bail out as soon as any test fails')
        self.parser.add_argument('-l', '--loader', dest='loader',
            default='requests',
            help='The remote URL document loader: requests, aiohttp '
                 '[default: %(default)s]')
        self.parser.add_argument('-n', '--number', dest='number',
            help='Limit tests to those containing the specified test identifier')
        self.parser.add_argument('-v', '--verbose', dest='verbose',
            action='store_true', default=False,
            help='Print verbose test data')

        # parse command line args
        self.options = self.parser.parse_args()

        # Set a default JSON-LD document loader
        if self.options.loader == 'requests':
            jsonld._default_document_loader = jsonld.requests_document_loader()
        elif self.options.loader == 'aiohttp':
            jsonld._default_document_loader = jsonld.aiohttp_document_loader()

        # config runner
        self.failfast = self.options.bail

        # Global for saving test numbers to focus on
        global ONLY_IDENTIFIER
        if self.options.number:
          ONLY_IDENTIFIER = self.options.number

        if len(self.options.tests):
            # tests given on command line
            test_targets = self.options.tests
        else:
            # default to find known sibling test dirs
            test_targets = []
            sibling_dirs = [
                '../json-ld-api/tests/',
                '../json-ld-framing/tests/',
                '../normalization/tests/',
            ]
            for dir in sibling_dirs:
                if os.path.exists(dir):
                    print('Test dir found', dir)
                    test_targets.append(dir)
                else:
                    print('Test dir not found', dir)

        # ensure a manifest or a directory was specified
        if len(test_targets) == 0:
            raise Exception('No test manifest or directory specified.')

        # make root manifest with target files and dirs
        root_manifest = {
            '@context': 'https://w3c.github.io/tests/context.jsonld',
            '@id': '',
            '@type': 'mf:Manifest',
            'description': 'Top level PyLD test manifest',
            'name': 'PyLD',
            'sequence': [],
            'filename': '/'
        }
        for test in test_targets:
            if os.path.isfile(test):
                root, ext = os.path.splitext(test)
                if ext in ['.json', '.jsonld']:
                    root_manifest['sequence'].append(os.path.abspath(test))
                    #root_manifest['sequence'].append(test)
                else:
                    raise Exception('Unknown test file ext', root, ext)
            elif os.path.isdir(test):
                filename = os.path.join(test, 'manifest.jsonld')
                if os.path.exists(filename):
                    root_manifest['sequence'].append(os.path.abspath(filename))
                else:
                    raise Exception('Manifest not found', filename)
            else:
                raise Exception('Unknown test target.', test)

        # load root manifest
        global ROOT_MANIFEST_DIR
        #ROOT_MANIFEST_DIR = os.path.dirname(root_manifest['filename'])
        ROOT_MANIFEST_DIR = root_manifest['filename']
        suite = Manifest(root_manifest, root_manifest['filename']).load()

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
            if isinstance(entry, str):
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
        self.is_syntax = is_jsonld_type(data, 'jld:PositiveSyntaxTest')
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
                os.path.basename(str.replace(manifest.filename, '.jsonld', '')) + data['@id'])
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

        # mark tests to run with local loader
        run_remote_re = test_info.get('runLocal', [])
        for regex in run_remote_re:
            if re.match(regex, data.get('@id', data.get('id', ''))):
                data['runLocal'] = True

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
        elif self.is_syntax:
            expect = None
        else:
            expect = read_test_property(self._get_expect_property())(self)

        try:
            result = getattr(jsonld, fn)(*params)
            if self.is_negative and not self.pending:
                raise AssertionError('Expected an error; one was not raised')
            if self.is_syntax and not self.pending:
                self.assertTrue(True)
            elif self.test_type == 'jld:ToRDFTest':
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
                if result == expect:
                    self.assertTrue(True)
                else:
                    print('\nEXPECTED: ', expect)
                    print('ACTUAL: ', result)
                    raise AssertionError('results differ')
            elif not self.is_negative:
                # Perform order-independent equivalence test
                if equalUnordered(result, expect):
                    self.assertTrue(True)
                else:
                    print('\nEXPECTED: ', json.dumps(expect, indent=2))
                    print('ACTUAL: ', json.dumps(result, indent=2))
                    raise AssertionError('results differ')
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
                #import pdb; pdb.set_trace()
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

    def strip_fragment(url):
        if '#' in url:
            return url[:url.index('#')]
        else:
            return url

    def load_locally(url):
        options = test.data.get('option', {})
        content_type = options.get('contentType')

        url_no_frag = strip_fragment(url)
        if not content_type and url_no_frag.endswith('.jsonld'):
            content_type = 'application/ld+json'
        if not content_type and url_no_frag.endswith('.json'):
            content_type = 'application/json'
        if not content_type and url_no_frag.endswith('.html'):
            content_type = 'text/html'
        if not content_type:
            content_type = 'application/octet-stream'
        doc = {
            'contentType': content_type,
            'contextUrl': None,
            'documentUrl': url,
            'document': None
        }
        if options and url == test.base:
            if ('redirectTo' in options and options.get('httpStatus') >= 300):
                doc['documentUrl'] = (
                    test.manifest.data['baseIri'] + options['redirectTo'])
            elif 'httpLink' in options:
                link_header = options.get('httpLink', '')
                if isinstance(link_header, list):
                    link_header = ','.join(link_header)
                linked_context = jsonld.parse_link_header(
                    link_header).get('http://www.w3.org/ns/json-ld#context')
                if linked_context and content_type != 'application/ld+json':
                    if isinstance(linked_context, list):
                        raise Exception('multiple context link headers')
                    doc['contextUrl'] = linked_context['target']
                linked_alternate = jsonld.parse_link_header(
                    link_header).get('alternate')
                # if not JSON-LD, alternate may point there
                if (linked_alternate and
                        linked_alternate.get('type') == 'application/ld+json' and
                        not re.match(r'^application\/(\w*\+)?json$', content_type)):
                    doc['contentType'] = 'application/ld+json'
                    doc['documentUrl'] = jsonld.prepend_base(url, linked_alternate['target'])
        global ROOT_MANIFEST_DIR
        if doc['documentUrl'].find(':') == -1:
            filename = os.path.join(ROOT_MANIFEST_DIR, doc['documentUrl'])
            doc['documentUrl'] = 'file://' + filename
        else:
            filename = test.dirname + strip_fragment(strip_base(doc['documentUrl']))
        try:
            doc['document'] = read_file(filename)
        except:
            raise Exception('loading document failed')
        return doc

    def local_loader(url, headers):
        # always load remote-doc tests remotely
        # (some skipped due to lack of reasonable HTTP header support)
        if (test.manifest.data.get('name') == 'Remote document' and
            not test.data.get('runLocal')):
            return loader(url)

        # always load non-base tests remotely
        if not is_test_suite_url(url) and url.find(':') != -1:
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
        about = {}
        with open(os.path.join(
                os.path.dirname(__file__), '..', 'lib', 'pyld', '__about__.py')) as fp:
            exec(fp.read(), about)
        self.now = datetime.datetime.utcnow().replace(microsecond=0)
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
                'dc:date': {'@type': 'xsd:date'},
                'doap:created': {'@type': 'xsd:date'}
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
            'doap:release': {
                'doap:name': 'PyLD ' + about['__version__'],
                'doap:revision': about['__version__'],
                'doap:created': self.now.strftime('%Y-%m-%d')
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
                'dc:date': self.now.isoformat() + 'Z',
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
            ]
        },
        'runLocal': [
            '.*remote-doc-manifest#t0003$',
            '.*remote-doc-manifest#t0004$',
            '.*remote-doc-manifest#t0005$',
            '.*remote-doc-manifest#t0006$',
            '.*remote-doc-manifest#t0007$',
            '.*remote-doc-manifest#t0009$',
            '.*remote-doc-manifest#t0010$',
            '.*remote-doc-manifest#t0011$',
            '.*remote-doc-manifest#t0012$',
            '.*remote-doc-manifest#t0013$',
            '.*remote-doc-manifest#tla01$',
            '.*remote-doc-manifest#tla02$',
            '.*remote-doc-manifest#tla03$',
            '.*remote-doc-manifest#tla04$',
            '.*remote-doc-manifest#tla05$',
        ],
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
                '.*fromRdf-manifest#tdi11$',
                '.*fromRdf-manifest#tdi12$',
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
                # blank node property
                '.*toRdf-manifest#te075$',
                '.*toRdf-manifest#te122$',
                # rel vocab
                '.*toRdf-manifest#te111$',
                '.*toRdf-manifest#te112$',
                # number fixes
                '.*toRdf-manifest#trt01$',
                # type:none
                '.*toRdf-manifest#ttn02$',
                # well formed
                '.*toRdf-manifest#twf05$',
                '.*toRdf-manifest#twf06$',
            ]
        },
        'skip': {
            # skip tests where behavior changed for a 1.1 processor
            # see JSON-LD 1.0 Errata
            'specVersion': ['json-ld-1.0'],
            'idRegex': [
                # node object direction
                '.*toRdf-manifest#tdi11$',
                '.*toRdf-manifest#tdi12$',
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
