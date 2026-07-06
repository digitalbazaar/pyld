"""Tests for SqliteCacheRequestsDocumentLoader and HTTP cache behavior."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from pyld import (
    DocumentLoader,
    RequestsDocumentLoader,
    SqliteCacheRequestsDocumentLoader,
)

requests_cache = pytest.importorskip('requests_cache')
CachedSession = requests_cache.CachedSession


class _ContextHandler(BaseHTTPRequestHandler):
    request_count = 0

    def do_GET(self):
        type(self).request_count += 1
        body = json.dumps({
            '@context': {'name': 'http://example.org/name'},
        }).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/ld+json')
        self.send_header('Cache-Control', 'max-age=3600')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


@pytest.fixture
def context_url():
    """Local HTTP server returning JSON-LD with Cache-Control: max-age=3600."""
    _ContextHandler.request_count = 0
    server = HTTPServer(('127.0.0.1', 0), _ContextHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    url = f'http://127.0.0.1:{port}/context.jsonld'
    yield url
    server.shutdown()


def test_requests_document_loader_accepts_custom_session():
    """RequestsDocumentLoader accepts a CachedSession via session=."""
    loader = RequestsDocumentLoader(
        session=CachedSession(backend='memory', cache_control=True))
    assert isinstance(loader, DocumentLoader)
    assert callable(loader)
    loader.session.close()


def test_sqlite_cache_requests_document_loader_is_document_loader():
    """Sqlite loader is a DocumentLoader composing RequestsDocumentLoader."""
    loader = SqliteCacheRequestsDocumentLoader()
    assert isinstance(loader, DocumentLoader)
    assert isinstance(loader._loader, RequestsDocumentLoader)
    assert callable(loader)
    loader.session.close()


def test_sqlite_cache_requests_document_loader_rejects_relative_sqlite_file_path():
    """Relative sqlite_file_path is rejected."""
    with pytest.raises(ValueError, match='absolute path'):
        SqliteCacheRequestsDocumentLoader(
            sqlite_file_path=Path('relative.sqlite'))


def test_http_cache_headers_serve_from_cache_with_cache_control(context_url):
    """With cache_control=True, Cache-Control max-age avoids a second HTTP hit."""
    loader = RequestsDocumentLoader(
        session=CachedSession(
            'test_memory_cache_control',
            backend='memory',
            cache_control=True,
        ))
    loader(context_url)
    loader(context_url)
    assert _ContextHandler.request_count == 1
    loader.session.close()


def test_http_cache_headers_without_cache_control_hits_server_twice(context_url):
    """With cache_control=False, response Cache-Control headers are ignored."""
    loader = RequestsDocumentLoader(
        session=CachedSession(
            'test_memory_no_cache_control',
            backend='memory',
            cache_control=False,
            expire_after=0,
        ))
    loader(context_url)
    loader(context_url)
    assert _ContextHandler.request_count == 2
    loader.session.close()


def test_sqlite_cache_requests_document_loader_persists(context_url, tmp_path):
    """Second loader instance reuses the on-disk SQLite cache."""
    cache_path = tmp_path / 'contexts.sqlite'
    loader = SqliteCacheRequestsDocumentLoader(sqlite_file_path=cache_path)
    loader(context_url)
    assert _ContextHandler.request_count == 1
    loader.session.close()

    _ContextHandler.request_count = 0
    loader = SqliteCacheRequestsDocumentLoader(sqlite_file_path=cache_path)
    loader(context_url)
    assert _ContextHandler.request_count == 0
    loader.session.close()
