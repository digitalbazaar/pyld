#!/usr/bin/env python
##
# TestRunner is a basic unit testing framework, adapted from PyForge.
# 
# @author Mike Johnson
# @author Dave Longley
# 
# Copyright 2011-2012 Digital Bazaar, Inc. All Rights Reserved.
import os, sys, json
from os.path import join
from optparse import OptionParser

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
from pyld import jsonld

##
# jsonld.triples callback to create ntriples lines
def _ntriple(s, p, o):
    if isinstance(o, basestring):
        # simple literal
        return "<%s> <%s> \"%s\" ." % (s, p, o)
    elif "@id" in o:
        # object is an IRI
        return "<%s> <%s> <%s> ." % (s, p, o["@id"])
    else:
        # object is a literal
        return "<%s> <%s> \"%s\"^^<%s> ." % \
            (s, p, o["@value"], o["@type"])

##
# TestRunner unit testing class.
# Loads test files and runs groups of tests.
class TestRunner:
    def __init__(self):
        ##
        # The program options.
        self.options = {}

        ##
        # The parser for program options.
        self.parser = OptionParser()

        ##
        # The test directory.
        self.testdir = None

        ##
        # The list of manifest files to run.
        self.manifestfiles = []

    ##
    # The main function for parsing options and running tests.
    def main(self):
        print "PyLD TestRunner"
        print "Use -h or --help to view options."

        # add program options
        self.parser.add_option("-f", "--file", dest="file",
            help="The single test file to run", metavar="FILE")
        self.parser.add_option("-d", "--directory", dest="directory",
            help="The directory full of test files", metavar="DIR")
        self.parser.add_option("-v", "--verbose", dest="verbose",
         action="store_true", default=False, help="Prints verbose test data")

        # parse options
        (self.options, args) = self.parser.parse_args()

        # check if file or directory were specified
        if self.options.file == None and self.options.directory == None:
            print "No test file or directory specified."
            return

        # check if file was specified, exists and is file
        if self.options.file != None:
            if (os.path.exists(self.options.file) and
                os.path.isfile(self.options.file)):
                # add manifest file to the file list
                self.manifestfiles.append(os.path.abspath(self.options.file))
                self.testdir = os.path.dirname(self.options.file)
            else:
                print "Invalid test file."
                return

        # check if directory was specified, exists and is dir
        if self.options.directory != None:
            if (os.path.exists(self.options.directory) and
                os.path.isdir(self.options.directory)):
                # load manifest files from test directory
                for self.testdir, dirs, files in os.walk(self.options.directory):
                    for manifest in files:
                        # add all .jsonld manifest files to the file list
                        if (manifest.find('manifest') != -1 and
                            manifest.endswith(".jsonld")):
                            self.manifestfiles.append(join(self.testdir, manifest))
            else:
                print "Invalid test directory."
                return

        # see if any manifests have been specified
        if len(self.manifestfiles) == 0:
            print "No manifest files found."
            return

        # FIXME: 
        #self.manifestfiles.sort()

        run = 0
        passed = 0
        failed = 0

        # run the tests from each manifest file
        for manifestfile in self.manifestfiles:
            manifest = json.load(open(manifestfile, 'r'))
            count = 1

            for test in manifest['sequence']:
                # skip unsupported types
                testType = test['@type']
                if ('jld:NormalizeTest' not in testType and
                    'jld:ExpandTest' not in testType and
                    'jld:CompactTest' not in testType and
                    'jld:FrameTest' not in testType and
                    'jld:TriplesTest' not in testType):
                    print 'Skipping test: %s...' % test['name']
                    continue

                print 'Test: %s %04d/%s...' % (
                    manifest['name'], count, test['name']),

                run += 1
                count += 1

                # open the input and expected result json files
                inputFile = open(join(self.testdir, test['input']))
                expectFile = open(join(self.testdir, test['expect']))
                inputJson = json.load(inputFile)
                expectType = os.path.splitext(test['expect'])[1][1:]
                if expectType == 'jsonld':
                    expect = json.load(expectFile)
                elif expectType == 'nt':
                    # read, strip non-data lines, stripe front/back whitespace, and sort
                    # FIXME: only handling strict nt format here
                    expectLines = []
                    for line in expectFile.readlines():
                        line = line.strip()
                        if len(line) == 0 or line[0] == '#':
                            continue
                        expectLines.append(line)
                    expect = '\n'.join(sorted(expectLines))

                result = None

                if 'jld:NormalizeTest' in testType:
                    result = jsonld.normalize(inputJson)
                elif 'jld:ExpandTest' in testType:
                    result = jsonld.expand(inputJson)
                elif 'jld:CompactTest' in testType:
                    contextFile = open(join(self.testdir, test['context']))
                    contextJson = json.load(contextFile)
                    result = jsonld.compact(contextJson['@context'], inputJson)
                elif 'jld:FrameTest' in testType:
                    frameFile = open(join(self.testdir, test['frame']))
                    frameJson = json.load(frameFile)
                    result = jsonld.frame(inputJson, frameJson)
                elif 'jld:TriplesTest' in testType:
                    result = '\n'.join(
                        sorted(jsonld.triples(inputJson, callback=_ntriple)))

                # check the expected value against the test result
                if expect == result:
                    passed += 1
                    print 'PASS'
                    if self.options.verbose:
                        print 'Expect:', json.dumps(expect, indent=2)
                        print 'Result:',
                        if expectType == 'json':
                            print json.dumps(result, indent=2)
                        else:
                            print
                            print result
                else:
                    failed += 1
                    print 'FAIL'
                    print 'Expect:', json.dumps(expect, indent=2)
                    print 'Result:',
                    if expectType == 'json':
                        print json.dumps(result, indent=2)
                    else:
                        print
                        print result

        print "Tests run: %d, Tests passed: %d, Tests Failed: %d" % (run, passed, failed)

if __name__ == "__main__":
   tr = TestRunner()
   tr.main()
