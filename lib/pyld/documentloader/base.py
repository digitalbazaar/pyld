"""
Abstract base class for class-based JSON-LD document loaders.

.. module:: jsonld.documentloader.base
  :synopsis: DocumentLoader abstract base class
"""

from abc import ABC, abstractmethod
from typing import Any, TypedDict


class RemoteDocument(TypedDict):
    """Shape returned by a JSON-LD document loader.

    Mirrors the *RemoteDocument* structure defined in the W3C JSON-LD 1.1 API
    (https://www.w3.org/TR/json-ld11-api/#remotedocument).
    """

    contentType: str
    contextUrl: str | None
    documentUrl: str
    document: Any


class DocumentLoader(ABC):
    """Abstract base class for class-based JSON-LD document loaders.

    Concrete subclasses implement :meth:`__call__` to fetch a document for a
    given URL and return a :class:`RemoteDocument`.

    Existing function-based loaders (:func:`pyld.jsonld.requests_document_loader`,
    :func:`pyld.jsonld.aiohttp_document_loader`) remain valid: pyld's loader
    contract is "any callable with the right signature". This ABC is for new
    class-based loaders only.
    """

    @abstractmethod
    def __call__(self, url: str, options: dict) -> RemoteDocument:
        """Retrieve the JSON-LD document at ``url``.

        :param url: the URL to retrieve.
        :param options: loader options (e.g. ``headers``).
        :return: a :class:`RemoteDocument`.
        """
