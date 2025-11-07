"""
Remote document loader using aiohttp.

.. module:: jsonld.documentloader.aiohttp
  :synopsis: Remote document loader using aiohttp

.. moduleauthor:: Olaf Conradi <olaf@conradi.org>
"""

import asyncio
import re
import string
import threading
import urllib.parse as urllib_parse

from pyld.jsonld import (JsonLdError, parse_link_header, LINK_HEADER_REL)


# Background event loop (used when inside an existing async environment)
_background_loop = None
_background_thread = None


def _ensure_background_loop():
    """Start a persistent background event loop if not running."""
    global _background_loop, _background_thread
    if _background_loop is None:
        _background_loop = asyncio.new_event_loop()

        def run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        _background_thread = threading.Thread(
            target=run_loop, args=(_background_loop,), daemon=True)
        _background_thread.start()
    return _background_loop


def aiohttp_document_loader(loop=None, secure=False, **kwargs):
    """
    Create an Asynchronous document loader using aiohttp.

    :param loop: deprecated / ignored (kept for backward compatibility).
    :param secure: require all requests to use HTTPS (default: False).
    :param **kwargs: extra keyword args for the aiohttp request get() call.

    :return: the RemoteDocument loader function.
    """
    import aiohttp

    async def async_loader(url, headers):
        """
        Retrieves JSON-LD at the given URL asynchronously.

        :param url: the URL to retrieve.
        :param headers: the request headers.

        :return: the RemoteDocument.
        """
        try:
            # validate URL
            pieces = urllib_parse.urlparse(url)
            if (not all([pieces.scheme, pieces.netloc]) or
                pieces.scheme not in ['http', 'https'] or
                set(pieces.netloc) > set(
                    string.ascii_letters + string.digits + '-.:')):
                raise JsonLdError(
                    'URL could not be dereferenced; '
                    'only "http" and "https" URLs are supported.',
                    'jsonld.InvalidUrl', {'url': url},
                    code='loading document failed')
            if secure and pieces.scheme != 'https':
                raise JsonLdError(
                    'URL could not be dereferenced; '
                    'secure mode enabled and '
                    'the URL\'s scheme is not "https".',
                    'jsonld.InvalidUrl', {'url': url},
                    code='loading document failed')
            async with aiohttp.ClientSession() as session:
                async with session.get(url,
                                       headers=headers,
                                       **kwargs) as response:
                    # Allow any content_type in trying to parse json
                    # similar to requests library
                    json_body = await response.json(content_type=None)
                    content_type = response.headers.get('content-type')
                    if not content_type:
                        content_type = 'application/octet-stream'
                    doc = {
                        'contentType': content_type,
                        'contextUrl': None,
                        'documentUrl': response.url.human_repr(),
                        'document': json_body
                    }
                    link_header = response.headers.get('link')
                    if link_header:
                        linked_context = parse_link_header(link_header).get(
                            LINK_HEADER_REL)
                        # only 1 related link header permitted
                        if linked_context and content_type != 'application/ld+json':
                          if isinstance(linked_context, list):
                              raise JsonLdError(
                                  'URL could not be dereferenced, '
                                  'it has more than one '
                                  'associated HTTP Link Header.',
                                  'jsonld.LoadDocumentError',
                                  {'url': url},
                                  code='multiple context link headers')
                          doc['contextUrl'] = linked_context['target']
                        linked_alternate = parse_link_header(link_header).get('alternate')
                        # if not JSON-LD, alternate may point there
                        if (linked_alternate and
                                linked_alternate.get('type') == 'application/ld+json' and
                                not re.match(r'^application\/(\w*\+)?json$', content_type)):
                            doc['contentType'] = 'application/ld+json'
                            doc['documentUrl'] = jsonld.prepend_base(url, linked_alternate['target'])

                    return doc
        except JsonLdError as e:
            raise e
        except Exception as cause:
            raise JsonLdError(
                'Could not retrieve a JSON-LD document from the URL.',
                'jsonld.LoadDocumentError', code='loading document failed',
                cause=cause)

    def loader(url, options=None):
        """
        Retrieves JSON-LD at the given URL synchronously.

        Works safely in both synchronous and asynchronous environments.

        :param url: the URL to retrieve.
        :param options: the request options.

        :return: the RemoteDocument.
        """
        if options is None:
            options = {}
        headers = options.get(
            'headers', {'Accept': 'application/ld+json, application/json'})

        # Detect whether we're already in an async environment
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        # Sync environment
        if not running_loop or not running_loop.is_running():
            return asyncio.run(async_loader(url, headers))

        # Inside async environment: use background event loop
        loop = _ensure_background_loop()
        future = asyncio.run_coroutine_threadsafe(async_loader(url, headers), loop)
        return future.result()

    return loader
