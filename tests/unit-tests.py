import json
import unittest

from pyld import jsonld

# Inputs and outputs used here are essentially modified documents
# of JSON-LD frame-0001 test.

FRAME_0001_IN = '''{
  "@context": {
    "dc": "http://purl.org/dc/elements/1.1/",
    "ex": "http://example.org/vocab#",
    "ex:contains": {"@type": "@id"}
  },
  "@graph": [
    {
      "@id": "http://example.org/test/#library",
      "@type": "ex:Library",
      "ex:contains": "http://example.org/test#book"
    },
    {
      "@id": "http://example.org/test#book",
      "@type": "ex:Book",
      "dc:contributor": "Writer",
      "dc:title": "My Book",
      "ex:contains": "http://example.org/test#chapter"
    },
    {
      "@id": "http://example.org/test#chapter",
      "@type": "ex:Chapter",
      "dc:description": "Fun",
      "dc:title": "Chapter One"
    }
  ]
}'''


FRAME_0001_FRAME = '''{
  "@context": {
    "dc": "http://purl.org/dc/elements/1.1/",
    "ex": "http://example.org/vocab#"
  },
  "@type": "ex:Library",
  "ex:contains": {
    "@type": "ex:Book",
    "ex:contains": {
      "@type": "ex:Chapter"
    }
  }
}'''

FRAME_0001_FRAME_WITHOUT_CONTEXT = '''{
  "@type": "ex:Library",
  "ex:contains": {
    "@type": "ex:Book",
    "ex:contains": {
      "@type": "ex:Chapter"
    }
  }
}'''

FRAME_0001_FRAME_WITH_PARTIAL_CONTEXT = '''{
  "@context": {
    "dc": "http://purl.org/dc/elements/1.1/"
  },
  "@type": "ex:Library",
  "ex:contains": {
    "@type": "ex:Book",
    "ex:contains": {
      "@type": "ex:Chapter"
    }
  }
}'''

FRAME_0001_FRAME_CONTEXT = '''{
  "@context": {
    "dc": "http://purl.org/dc/elements/1.1/",
    "ex": "http://example.org/vocab#"
  }
}'''

FRAME_0001_FRAME_PARTIAL_CONTEXT = '''{
  "@context": {
    "ex": "http://example.org/vocab#"
  }
}'''

FRAME_0001_OUT_WITH_REMOTE_CONTEXT = '''{
  "@context": "http://example.com/frame-context.json",
  "@graph": [{
    "@id": "http://example.org/test/#library",
    "@type": "ex:Library",
    "ex:contains": {
      "@id": "http://example.org/test#book",
      "@type": "ex:Book",
      "dc:contributor": "Writer",
      "dc:title": "My Book",
      "ex:contains": {
        "@id": "http://example.org/test#chapter",
        "@type": "ex:Chapter",
        "dc:description": "Fun",
        "dc:title": "Chapter One"
      }
    }
  }]
}'''

FRAME_0001_OUT_WITH_LOCAL_AND_REMOTE_CONTEXT = '''{
  "@context": [{
    "dc": "http://purl.org/dc/elements/1.1/",
    "ex": "http://example.org/vocab#"
  }, "http://example.com/frame-context.json"],
  "@graph": [{
    "@id": "http://example.org/test/#library",
    "@type": "ex:Library",
    "ex:contains": {
      "@id": "http://example.org/test#book",
      "@type": "ex:Book",
      "dc:contributor": "Writer",
      "dc:title": "My Book",
      "ex:contains": {
        "@id": "http://example.org/test#chapter",
        "@type": "ex:Chapter",
        "dc:description": "Fun",
        "dc:title": "Chapter One"
      }
    }
  }]
}'''

FRAME_0001_OUT_WITH_HALF_LOCAL_AND_HALF_REMOTE_CONTEXT = '''{
  "@context": [{
    "dc": "http://purl.org/dc/elements/1.1/"
  }, "http://example.com/frame-context.json"],
  "@graph": [{
    "@id": "http://example.org/test/#library",
    "@type": "ex:Library",
    "ex:contains": {
      "@id": "http://example.org/test#book",
      "@type": "ex:Book",
      "dc:contributor": "Writer",
      "dc:title": "My Book",
      "ex:contains": {
        "@id": "http://example.org/test#chapter",
        "@type": "ex:Chapter",
        "dc:description": "Fun",
        "dc:title": "Chapter One"
      }
    }
  }]
}'''


class TestCaseForFrame(unittest.TestCase):

    def _test_remote_context_with(
            self, frame_doc, frame_context_doc, out_doc):
        input_ = json.loads(FRAME_0001_IN)

        def fake_loader(url):
            if url == 'http://example.com/frame.json':
                return {
                    'contextUrl': 'http://example.com/frame-context.json',
                    'document': frame_doc,
                    'documentUrl': url
                }
            elif url == 'http://example.com/frame-context.json':
                return {
                    'contextUrl': None,
                    'document': frame_context_doc,
                    'documentUrl': url
                }
            else:
                raise Exception("Unknown URL: {}".format(url))

        options = {
            'documentLoader': fake_loader
        }
        framed = jsonld.frame(
            input_, 'http://example.com/frame.json', options=options)

        self.assertEqual(framed, json.loads(out_doc))

    def test_remote_context_local_and_remote_context_equal(self):
        self._test_remote_context_with(
            FRAME_0001_FRAME, FRAME_0001_FRAME_CONTEXT,
            FRAME_0001_OUT_WITH_LOCAL_AND_REMOTE_CONTEXT)

    def test_remote_context_remote_context_only(self):
        self._test_remote_context_with(
            FRAME_0001_FRAME_WITHOUT_CONTEXT, FRAME_0001_FRAME_CONTEXT,
            FRAME_0001_OUT_WITH_REMOTE_CONTEXT)

    def test_remote_context_half_context_local_and_half_remote(self):
        self._test_remote_context_with(
            FRAME_0001_FRAME_WITH_PARTIAL_CONTEXT,
            FRAME_0001_FRAME_PARTIAL_CONTEXT,
            FRAME_0001_OUT_WITH_HALF_LOCAL_AND_HALF_REMOTE_CONTEXT)


if __name__ == '__main__':
    unittest.main()