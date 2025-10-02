"""
Tests for to_rdf functionality, specifically focusing on double/float handling bugs.
"""

import json
import sys
import os
import unittest

# Add the lib directory to the path so we can import pyld
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import pyld.jsonld


class TestDoubleToRdf(unittest.TestCase):
    """Test cases for to_rdf functionality with double/float values."""

    def test_offline_pyld_bug_reproduction(self):
        """Test reproducing the PyLD bug with captured Wikidata data structure."""
        # This is the exact problematic data structure captured from Wikidata Q399
        # The bug occurs when PyLD tries to convert this to RDF
        data = {
            "@context": {
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "geoLongitude": "http://www.w3.org/2003/01/geo/wgs84_pos#longitude"
            },
            "@graph": [
                {
                    "@id": "http://www.wikidata.org/entity/Q399",
                    "geoLongitude": {
                        "@type": "xsd:double",
                        "@value": "45"  # This string number causes the PyLD bug
                    }
                }
            ]
        }
        
        # This should work now that the bug is fixed
        # The bug was in PyLD's _object_to_rdf method where string values
        # with @type: "xsd:double" were not being converted to float
        result = pyld.jsonld.to_rdf(data)
        
        # Expected result after bug fix
        expected = {
            "@default": [
                {
                    "subject": {
                        "type": "IRI",
                        "value": "http://www.wikidata.org/entity/Q399"
                    },
                    "predicate": {
                        "type": "IRI",
                        "value": "http://www.w3.org/2003/01/geo/wgs84_pos#longitude"
                    },
                    "object": {
                        "type": "literal",
                        "value": "4.5E1",
                        "datatype": "http://www.w3.org/2001/XMLSchema#double"
                    }
                }
            ]
        }
        
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
