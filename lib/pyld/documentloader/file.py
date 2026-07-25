"""
Local filesystem document loader for ``file:`` URLs.

.. module:: jsonld.documentloader.file
  :synopsis: FileDocumentLoader for local JSON-LD documents
"""

from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from pyld.documentloader.base import DocumentLoader, RemoteDocument
from pyld.jsonld import JsonLdError

CONTENT_TYPES = {
    '.jsonld': 'application/ld+json',
    '.json': 'application/json',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.xhtml': 'application/xhtml+xml',
}


class FileDocumentLoader(DocumentLoader):
    """Document loader that reads local files for `file:` URLs.

    Accepts `file:` URLs, scheme-less absolute paths, and `pathlib.Path`
    instances. Any other scheme raises `JsonLdError`. When `root` is set,
    only paths that resolve under that directory are served.

    :param root: optional directory that confines readable paths; when set,
        paths that resolve outside this directory are refused.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root).resolve() if root is not None else None

    def __call__(
        self, url: str | Path, options: dict | None = None
    ) -> RemoteDocument:
        """Retrieve the JSON-LD document at `url`.

        :param url: a `file:` URL, scheme-less absolute path, or
          `pathlib.Path`.
        :param options: loader options (unused; accepted for interface parity).
        :return: a `RemoteDocument`.
        """
        if options is None:
            options = {}

        fragment = ''
        if isinstance(url, Path):
            path = url.resolve()
        else:
            parts = urlparse(url)
            if parts.scheme == 'file':
                path_text = parts.path
            elif parts.scheme == '':
                path_text = url
            else:
                raise JsonLdError(
                    'URL could not be dereferenced; only "file" URLs are '
                    'supported.',
                    'jsonld.InvalidUrl',
                    {'url': url},
                    code='loading document failed',
                )
            path = Path(url2pathname(path_text)).resolve()
            fragment = parts.fragment

        if self.root is not None and not path.is_relative_to(self.root):
            raise JsonLdError(
                'URL could not be dereferenced; path is outside the '
                'configured root.',
                'jsonld.LoadDocumentError',
                {'url': url, 'root': str(self.root)},
                code='loading document failed',
            )

        content_type = CONTENT_TYPES.get(path.suffix.lower())
        if content_type is None:
            raise JsonLdError(
                'URL could not be dereferenced; unsupported file extension.',
                'jsonld.LoadDocumentError',
                {'url': url, 'suffix': path.suffix},
                code='loading document failed',
            )

        try:
            document = path.read_text(encoding='utf-8')
        except OSError as cause:
            raise JsonLdError(
                'Could not retrieve a JSON-LD document from the URL.',
                'jsonld.LoadDocumentError',
                {'url': url},
                code='loading document failed',
            ) from cause

        document_url = path.as_uri()
        if fragment:
            document_url = f'{document_url}#{fragment}'
        return {
            'contentType': content_type,
            'contextUrl': None,
            'documentUrl': document_url,
            'document': document,
        }
