"""Format detection and parsing for document text."""

import json
from pathlib import Path
from typing import Any

from pyld.documentloader.base import RemoteDocument
from pyld.yaml_ld import parse_yaml

CONTENT_TYPES = {
    '.jsonld': 'application/ld+json',
    '.json': 'application/json',
    '.yamlld': 'application/ld+yaml',
    '.yaml': 'application/ld+yaml',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.xhtml': 'application/xhtml+xml',
}


def content_type_from_path(path: Path) -> str | None:
    """Identify a document's media type from its path extension."""
    return CONTENT_TYPES.get(path.suffix.lower())


def parse_document(remote_document: RemoteDocument) -> RemoteDocument:
    """Return a shallow copy with structured document text parsed."""
    return {
        **remote_document,
        'document': parse_document_text(
            remote_document['document'], remote_document['contentType']
        ),
    }


def parse_document_text(document: str, content_type: str) -> Any:
    """Parse structured document text, defaulting to JSON for other media types."""
    if content_type == 'application/ld+yaml':
        return parse_yaml(document)
    else:
        return json.loads(document)
