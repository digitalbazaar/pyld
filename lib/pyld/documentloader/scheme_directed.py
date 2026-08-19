"""
Scheme-dispatching JSON-LD document loader.

.. module:: jsonld.documentloader.scheme_directed
  :synopsis: SchemeDirectedDocumentLoader for multi-scheme document loading
"""

from urllib.parse import urlparse

from pyld.documentloader.base import DocumentLoader, RemoteDocument
from pyld.jsonld import JsonLdError


class SchemeDirectedDocumentLoader(DocumentLoader):
    """Document loader that dispatches to per-scheme loaders.

    Constructed as keyword arguments mapping each URL scheme name to a
    `DocumentLoader` instance. Non-identifier scheme names can be passed via
    ``SchemeDirectedDocumentLoader(**{'view-source': loader})``.

    An unregistered scheme raises `JsonLdError` with code
    `loading document failed` and details naming the registered schemes.

    :param loaders: keyword mapping of scheme name to document loader.
    """

    def __init__(self, **loaders: DocumentLoader) -> None:
        self.loaders = {scheme.lower(): loader for scheme, loader in loaders.items()}

    def __call__(self, url: str, options: dict | None = None) -> RemoteDocument:
        """Retrieve the JSON-LD document at `url` via the matching scheme loader.

        :param url: the URL string to retrieve.
        :param options: loader options forwarded to the chosen loader.
        :return: a `RemoteDocument`.
        """
        if options is None:
            options = {}

        scheme = urlparse(url).scheme

        try:
            loader = self.loaders[scheme]
        except KeyError:
            raise JsonLdError(
                'URL could not be dereferenced; no loader is registered for '
                f'the "{scheme}" scheme.',
                'jsonld.InvalidUrl',
                {'url': url, 'schemes': sorted(self.loaders)},
                code='loading document failed',
            ) from None

        return loader(url, options)
