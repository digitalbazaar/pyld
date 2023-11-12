import unittest
from typing import Any

import pyld.jsonld as jsonld


def raise_this(value: Any):
    raise ValueError(value)


class TestOnKeyDropped(unittest.TestCase):
    """
    Tests for on_key_dropped argument and logic in JSON-LD expand algorithm.

    Original implementation is © pchampin.
    """

    CTX = {"foo": {"@id": "http://example.com/foo"}}
    DATA = {"fooo": "bar"}
    RESULT = []

    def test_silently_ignored(self):
        got = jsonld.expand(
            self.DATA,
            {'expandContext': self.CTX},
        )
        self.assertEqual(got, self.RESULT)

    def test_strict_fails(self):
        with self.assertRaises(ValueError):
            jsonld.expand(
                self.DATA,
                {'expandContext': self.CTX},
                on_key_dropped=raise_this,
            )

    def test_dropped_keys(self):
        dropped_keys = set()
        got = jsonld.expand(
            self.DATA,
            {'expandContext': self.CTX},
            on_key_dropped=dropped_keys.add,
        )
        self.assertEqual(got, self.RESULT)
        self.assertSetEqual(dropped_keys, {"fooo"})

    DATA2 = {
        "@id": "foo", "foo": "bar", "fooo": "baz",
        "http://example.com/other": "blah"}
    RESULT2 = [{
        "@id": u"foo",
        "http://example.com/foo": [{"@value": "bar"}],
        "http://example.com/other": [{"@value": "blah"}],
    }]

    def test_silently_ignored_2(self):
        got = jsonld.expand(
            self.DATA2,
            {'expandContext': self.CTX},
        )
        self.assertEqual(got, self.RESULT2)

    def test_strict_fails_2(self):
        with self.assertRaises(ValueError):
            jsonld.expand(
                self.DATA2,
                {'expandContext': self.CTX},
                on_key_dropped=raise_this,
            )

    def test_dropped_keys_2(self):
        dropped_keys = set()
        got = jsonld.expand(
            self.DATA2,
            {'expandContext': self.CTX},
            on_key_dropped=dropped_keys.add,
        )
        self.assertEqual(got, self.RESULT2)
        self.assertSetEqual(dropped_keys, {"fooo"})


if __name__ == "__main__":
    unittest.main()
