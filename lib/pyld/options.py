"""
TypedDict types for JSON-LD API options.

.. module:: options
  :synopsis: Option dict types for JSON-LD API functions
"""

from collections.abc import Callable
from typing import Any, Literal, TypedDict

from .documentloader.base import DocumentLoader, RemoteDocument

ContextObject = dict[str, Any]
Context = str | ContextObject | list[str | ContextObject]
"""JSON-LD context value: remote URL, inline object, or ordered stack."""

DocumentLoaderCallable = Callable[[str, dict[str, Any]], RemoteDocument]


class DocumentLoaderOptions(TypedDict, total=False):
    """Options shared by APIs that load remote contexts."""

    documentLoader: DocumentLoader | DocumentLoaderCallable
    """The document loader (default: the global default document loader)."""


class ProcessingOptions(DocumentLoaderOptions, total=False):
    """Options shared by JSON-LD processing APIs."""

    base: str
    """The base IRI to use."""

    extractAllScripts: bool
    """`True` to extract all JSON-LD script elements from HTML, `False` to extract just the first (default: `False`)."""

    processingMode: Literal['json-ld-1.0', 'json-ld-1.1']
    """Either `json-ld-1.0` or `json-ld-1.1` (default: `json-ld-1.1`)."""


class ExpandContextOptions(ProcessingOptions, total=False):
    """Processing options that accept an expand context."""

    expandContext: Context
    """A context to expand with."""


class CompactOptions(ExpandContextOptions, total=False):
    documentLoader: DocumentLoader | DocumentLoaderCallable
    """The document loader (default: the global default document loader)."""

    base: str
    """The base IRI to use."""

    extractAllScripts: bool
    """`True` to extract all JSON-LD script elements from HTML, `False` to extract just the first (default: `False`)."""

    processingMode: Literal['json-ld-1.0', 'json-ld-1.1']
    """Either `json-ld-1.0` or `json-ld-1.1` (default: `json-ld-1.1`)."""

    expandContext: Context
    """A context to expand with."""

    compactArrays: bool
    """`True` to compact arrays to single values when appropriate, `False` not to (default: `True`)."""

    graph: bool
    """`True` to always output a top-level graph (default: `False`)."""


class ExpandOptions(ExpandContextOptions, total=False):
    documentLoader: DocumentLoader | DocumentLoaderCallable
    """The document loader (default: the global default document loader)."""

    base: str
    """The base IRI to use."""

    extractAllScripts: bool
    """`True` to extract all JSON-LD script elements from HTML, `False` to extract just the first (default: `False`)."""

    processingMode: Literal['json-ld-1.0', 'json-ld-1.1']
    """Either `json-ld-1.0` or `json-ld-1.1` (default: `json-ld-1.1`)."""

    expandContext: Context
    """A context to expand with."""


class FlattenOptions(ExpandContextOptions, total=False):
    documentLoader: DocumentLoader | DocumentLoaderCallable
    """The document loader (default: the global default document loader)."""

    base: str
    """The base IRI to use."""

    extractAllScripts: bool
    """`True` to extract all JSON-LD script elements from HTML, `False` to extract just the first (default: `True`)."""

    processingMode: Literal['json-ld-1.0', 'json-ld-1.1']
    """Either `json-ld-1.0` or `json-ld-1.1` (default: `json-ld-1.1`)."""

    expandContext: Context
    """A context to expand with."""


class FrameOptions(ExpandContextOptions, total=False):
    documentLoader: DocumentLoader | DocumentLoaderCallable
    """The document loader (default: the global default document loader)."""

    base: str
    """The base IRI to use."""

    extractAllScripts: bool
    """`True` to extract all JSON-LD script elements from HTML, `False` to extract just the first (default: `False`)."""

    processingMode: Literal['json-ld-1.0', 'json-ld-1.1']
    """Either `json-ld-1.0` or `json-ld-1.1` (default: `json-ld-1.1`)."""

    expandContext: Context
    """A context to expand with."""

    embed: Literal['@last', '@always', '@never', '@link']
    """Default `@embed` flag (default: `@last`)."""

    explicit: bool
    """Default `@explicit` flag (default: `False`)."""

    omitDefault: bool
    """Default `@omitDefault` flag (default: `False`)."""

    pruneBlankNodeIdentifiers: bool
    """Remove unnecessary blank node identifiers (default: `True`)."""

    requireAll: bool
    """Default `@requireAll` flag (default: `False`)."""


class NormalizeOptions(ProcessingOptions, total=False):
    documentLoader: DocumentLoader | DocumentLoaderCallable
    """The document loader (default: the global default document loader)."""

    base: str
    """The base IRI to use."""

    extractAllScripts: bool
    """`True` to extract all JSON-LD script elements from HTML, `False` to extract just the first (default: `False`)."""

    processingMode: Literal['json-ld-1.0', 'json-ld-1.1']
    """Either `json-ld-1.0` or `json-ld-1.1` (default: `json-ld-1.1`)."""

    algorithm: Literal['URDNA2015', 'URGNA2012']
    """The algorithm to use (default: `URGNA2012`)."""

    inputFormat: Literal['application/n-quads']
    """The format if input is not JSON-LD: `application/n-quads` for N-Quads."""

    format: Literal['application/n-quads']
    """The format if output is a string: `application/n-quads` for N-Quads."""


class ToRdfOptions(ProcessingOptions, total=False):
    documentLoader: DocumentLoader | DocumentLoaderCallable
    """The document loader (default: the global default document loader)."""

    base: str
    """The base IRI to use."""

    extractAllScripts: bool
    """`True` to extract all JSON-LD script elements from HTML, `False` to extract just the first (default: `True`)."""

    processingMode: Literal['json-ld-1.0', 'json-ld-1.1']
    """Either `json-ld-1.0` or `json-ld-1.1` (default: `json-ld-1.1`)."""

    format: Literal['application/n-quads']
    """The format to use to output a string: `application/n-quads` for N-Quads."""

    produceGeneralizedRdf: bool
    """`True` to output generalized RDF, `False` to produce only standard RDF (default: `False`)."""

    rdfDirection: Literal['i18n-datatype']
    """Only `i18n-datatype` supported."""


class FromRdfOptions(TypedDict, total=False):
    format: Literal['application/n-quads']
    """The format if input is a string: `application/n-quads` for N-Quads (default: `application/n-quads`)."""

    useRdfType: bool
    """`True` to use `rdf:type`, `False` to use `@type` (default: `False`)."""

    useNativeTypes: bool
    """`True` to convert XSD types into native types (boolean, integer, double), `False` not to (default: `True`)."""

    rdfDirection: Literal['i18n-datatype', 'compound-literal']
    """Either `i18n-datatype` or `compound-literal` is supported (default: `None`)."""
