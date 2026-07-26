"""
SQLite-backed HTTP cache document loader using requests-cache.

.. module:: jsonld.documentloader.requests_sqlite_cache
  :synopsis: Persistent SQLite HTTP caching for Requests document loader
"""
from functools import cached_property
from pathlib import Path

from pyld.documentloader.base import DocumentLoader, RemoteDocument
from pyld.documentloader.requests import RequestsDocumentLoader


def _resolve_sqlite_file_path(sqlite_file_path: Path | None) -> Path:
    """Return absolute path to the SQLite cache file."""
    from platformdirs import user_cache_dir

    if sqlite_file_path is None:
        return (Path(user_cache_dir('pyld')) / 'http_cache.sqlite').resolve()
    path = Path(sqlite_file_path).expanduser()
    if not path.is_absolute():
        raise ValueError(
            'sqlite_file_path must be an absolute path to the .sqlite file')
    return path.resolve()


class SqliteCacheRequestsDocumentLoader(DocumentLoader):
    """Remote document loader with persistent SQLite HTTP caching.

    The cache file is created when the first document is loaded, not when the
    loader is constructed.

    :param secure: require all requests to use HTTPS (default: False).
    :param sqlite_file_path: absolute path to the ``.sqlite`` cache file; when
        omitted, defaults to the platform user cache directory under ``pyld/``.
    """

    def __init__(
        self,
        secure: bool = False,
        *,
        sqlite_file_path: Path | None = None,
    ):
        self.secure = secure
        self.sqlite_file_path = _resolve_sqlite_file_path(sqlite_file_path)

    @cached_property
    def session(self):
        """The ``requests_cache.CachedSession`` backing this loader."""
        from requests_cache import CachedSession

        return CachedSession(
            cache_name=str(self.sqlite_file_path),
            backend='sqlite',
            cache_control=True,
            # Cache JSON-LD contexts persistently by default; Cache-Control and
            # related response headers still override this when present.
            expire_after=-1,
        )

    @cached_property
    def _loader(self) -> RequestsDocumentLoader:
        return RequestsDocumentLoader(secure=self.secure, session=self.session)

    def __call__(self, url, options=None) -> RemoteDocument:
        return self._loader(url, options=options)
