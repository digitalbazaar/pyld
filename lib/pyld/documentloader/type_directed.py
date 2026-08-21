"""
Type-dispatching JSON-LD document loader.

.. module:: jsonld.documentloader.type_directed
  :synopsis: TypeDirectedDocumentLoader for type-based document loading
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pyld.documentloader.base import DocumentLoader, RemoteDocument
from pyld.jsonld import JsonLdError


@dataclass
class TypeDirectedDocumentLoader(DocumentLoader):
    """Document loader that dispatches to per-type loaders.

    Constructed with a mapping from Python types to `DocumentLoader` instances.
    Dispatch uses `isinstance`, so a `pathlib.Path` registration matches
    `pathlib.PosixPath` / `WindowsPath`. The first matching entry in insertion
    order wins.

    An unregistered input type raises `JsonLdError` with code
    `loading document failed` and details naming the registered types.

    :param loaders: mapping of type to document loader.
    """

    loaders: Mapping[type, DocumentLoader]

    def __call__(self, url: Any, options: dict | None = None) -> RemoteDocument:
        """Retrieve the JSON-LD document at `url` via the matching type loader.

        :param url: the URL, path, or other location to retrieve.
        :param options: loader options forwarded to the chosen loader.
        :return: a `RemoteDocument`.
        """
        if options is None:
            options = {}

        for typ, loader in self.loaders.items():
            if isinstance(url, typ):
                return loader(url, options)

        raise JsonLdError(
            'URL could not be dereferenced; no loader is registered for '
            f'type "{type(url).__name__}".',
            'jsonld.InvalidUrl',
            {
                'url': url,
                'types': [typ.__name__ for typ in self.loaders],
            },
            code='loading document failed',
        )
