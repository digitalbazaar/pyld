#!/usr/bin/env python
##
# TestRunner is a basic unit testing framework, adapted from PyForge.
# 
# @author Mike Johnson
# @author Dave Longley
# 
# Copyright 2011 Digital Bazaar, Inc. All Rights Reserved.
import os, sys, json
from os.path import join
from optparse import OptionParser

sys.path += ('../lib',)
from pyld import jsonld

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
        # The list of test files to run.
        self.testfiles = []

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
                # add test file to the file list
                self.testfiles.append(os.path.abspath(self.options.file))
                self.testdir = os.path.dirname(self.options.file)
            else:
                print "Invalid test file."
                return
        
        # check if directory was specified, exists and is dir
        if self.options.directory != None:
            if (os.path.exists(self.options.directory) and
                os.path.isdir(self.options.directory)):
                # load test files from test directory
                for self.testdir, dirs, files in os.walk(self.options.directory):
                    for testfile in files:
                        # add all .test files to the file list
                        if testfile.endswith(".test"):
                            self.testfiles.append(join(self.testdir, testfile))
            else:
                print "Invalid test directory."
                return
        
        # see if any tests have been specified
        if len(self.testfiles) == 0:
            print "No tests found."
            return
        
        # FIXME: 
        #self.testFiles.sort()
        
        # run the tests from each test file
        for testfile in self.testfiles:
            # test group in test file
            testgroup = json.load(open(testfile, 'r'))
            
            for test in testgroup['tests']:
                print 'Test: ', testgroup['group'], ' / ', test['name'], '...'
                
                # open the input and expected result json files
                inputFd = open(join(self.testdir, test['input']))
                expectFd = open(join(self.testdir, test['expect']))
                inputJson = json.load(inputFd)
                expectJson = json.load(expectFd)
                
                resultJson = None

                testType = test['type']
                if testType == 'normalize':
                    resultJson = jsonld.normalize(inputJson)
                elif testType == 'expand':
                    resultJson = jsonld.removeContext(inputJson)
                elif testType == 'compact':
                    contextFd = open(join(self.testdir, test['context']))
                    contextJson = json.load(contextFd)
                    resultJson = jsonld.addContext(contextJson, inputJson)
                elif testType == 'frame':
                    frameFd = open(join(self.testdir, test['frame']))
                    frameJson = json.load(frameFd)
                    resultJson = jsonld.frame(inputJson, frameJson)
                else:
                    print "Unknown test type."
                
                # check the expected value against the test result
                if expectJson == resultJson:
                    print 'PASS'
                    if self.options.verbose:
                        print 'Expect:', json.dumps(expectJson, indent=4)
                        print 'Result:', json.dumps(resultJson, indent=4)
                else:
                    print 'FAIL'
                    print 'Expect:', json.dumps(expectJson, indent=4)
                    print 'Result:', json.dumps(resultJson, indent=4)

if __name__ == "__main__":
   tr = TestRunner()
   tr.main()
