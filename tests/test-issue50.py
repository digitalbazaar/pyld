import unittest

import pyld.jsonld as jsonld

class TestIssue50(unittest.TestCase):

    CTX = { "foo": { "@id": "http://example.com/foo" } }
    DATA = { "fooo": "bar" }
    RESULT = []

    def test_silently_ignored(self):
        got = jsonld.expand(self.DATA,
                            {'expandContext': self.CTX})
        self.assertEqual(got, self.RESULT)

    def test_strict_fails(self):
        with self.assertRaises(ValueError):
            got = jsonld.expand(self.DATA,
                                {'expandContext': self.CTX, 'strict': True})

    def test_dropped_keys(self):
        dk = set()
        got = jsonld.expand(self.DATA,
                            {'expandContext': self.CTX, 'droppedKeys': dk})
        self.assertEqual(got, self.RESULT)
        self.assertSetEqual(dk, {"fooo"})


    DATA2 = { "@id": "foo", "foo": "bar", "fooo": "baz", "http://example.com/other": "blah" }
    RESULT2 = [{ "@id": u"foo",
                 "http://example.com/foo": [{"@value": "bar"}],
                 "http://example.com/other": [{"@value": "blah"}],
    }]

    def test_silently_ignored_2(self):
        got = jsonld.expand(self.DATA2,
                            {'expandContext': self.CTX})
        self.assertEqual(got, self.RESULT2)

    def test_strict_fails_2(self):
        with self.assertRaises(ValueError):
            got = jsonld.expand(self.DATA2,
                                {'expandContext': self.CTX, 'strict': True})

    def test_dropped_keys_2(self):
        dk = set()
        got = jsonld.expand(self.DATA2,
                            {'expandContext': self.CTX, 'droppedKeys': dk})
        self.assertEqual(got, self.RESULT2)
        self.assertSetEqual(dk, {"fooo"})


if __name__ == "__main__":
    unittest.main()
