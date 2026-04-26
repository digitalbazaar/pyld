"""
Frozen JSON-LD document loader.

A document loader that serves *only* the URLs in its ``documents`` allowlist
and refuses everything else with :class:`pyld.jsonld.JsonLdError`. Suitable for
secure / air-gapped / privacy-sensitive deployments and for honoring the
guidance in the W3C *JSON-LD Best Practices* note that clients SHOULD attempt
to use a locally cached version of contexts (§ Cache JSON-LD Contexts,
https://w3c.github.io/json-ld-bp/#cache-json-ld-contexts).

This module also defines :data:`BUNDLED_CONTEXTS`, a curated mapping of
high-traffic public W3C / W3ID JSON-LD context URLs to vendored on-disk copies
shipped with the package. See ``scripts/download_contexts.py`` for how the
files in ``bundled/`` are refreshed.

.. module:: jsonld.documentloader.frozen
  :synopsis: FrozenDocumentLoader and BUNDLED_CONTEXTS
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pyld.documentloader.base import DocumentLoader, RemoteDocument
from pyld.jsonld import JsonLdError

_BUNDLED_DIR = Path(__file__).parent / 'bundled'


BUNDLED_CONTEXTS: Mapping[str, Path] = {
    'https://www.w3.org/ns/activitystreams': _BUNDLED_DIR / 'activitystreams.jsonld',
    'https://www.w3.org/ns/did/v1': _BUNDLED_DIR / 'did-v1.jsonld',
    'https://www.w3.org/2018/credentials/v1': _BUNDLED_DIR / 'credentials-v1.jsonld',
    'https://www.w3.org/ns/credentials/v2': _BUNDLED_DIR / 'credentials-v2.jsonld',
    'https://w3id.org/security/v1': _BUNDLED_DIR / 'security-v1.jsonld',
    'https://w3id.org/security/v2': _BUNDLED_DIR / 'security-v2.jsonld',
    'https://w3id.org/security/suites/ed25519-2020/v1': _BUNDLED_DIR
    / 'security-ed25519-2020-v1.jsonld',
    'https://w3id.org/security/suites/jws-2020/v1': _BUNDLED_DIR
    / 'security-jws-2020-v1.jsonld',
}


@dataclass
class FrozenDocumentLoader(DocumentLoader):
    """Document loader that serves only a sealed allowlist of URLs.

    ``documents`` maps each allowed URL to either a parsed JSON-LD ``dict`` or
    a :class:`pathlib.Path` pointing to a JSON file on disk. Path entries are
    read and parsed lazily on first request, then cached in place so subsequent
    calls skip the file read. Any URL not present in the mapping raises
    :class:`pyld.jsonld.JsonLdError` with code ``'loading document failed'``.

    With no arguments, a ``FrozenDocumentLoader`` serves the curated
    :data:`BUNDLED_CONTEXTS` set. To extend rather than replace the bundle::

        FrozenDocumentLoader(documents=dict(BUNDLED_CONTEXTS, **extras))
    """

    documents: dict = field(default_factory=lambda: dict(BUNDLED_CONTEXTS))

    def __post_init__(self) -> None:
        # Take ownership of the mapping so we can cache parsed Paths in place
        # without mutating the caller's dict.
        self.documents = dict(self.documents)

    def __call__(self, url: str, options: dict) -> RemoteDocument:
        if url not in self.documents:
            raise JsonLdError(
                'Refusing to load document outside the allowed set.',
                'jsonld.LoadDocumentError',
                {'url': url},
                code='loading document failed',
            )
        value: dict | Path = self.documents[url]
        if isinstance(value, Path):
            value = json.loads(value.read_text(encoding='utf-8'))
            self.documents[url] = value
        return {
            'contentType': 'application/ld+json',
            'contextUrl': None,
            'documentUrl': url,
            'document': value,
        }
