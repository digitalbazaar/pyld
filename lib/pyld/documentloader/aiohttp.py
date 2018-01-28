"""
Remote document loader using aiohttp.

.. module:: jsonld.documentloader.aiohttp
  :synopsis: Remote document loader using aiohttp

.. moduleauthor:: Olaf Conradi <olaf@conradi.org>
"""

import string

from pyld.jsonld import (JsonLdError, urllib_parse,
                         parse_link_header, LINK_HEADER_REL)


def aiohttp_document_loader(loop=None, secure=False, **kwargs):
    """
    Create an Asynchronous document loader using aiohttp.

    :param loop: the event loop used for processing HTTP requests.
    :param secure: require all requests to use HTTPS (default: False).
    :param **kwargs: extra keyword args for the aiohttp request get() call.

    :return: the RemoteDocument loader function.
    """
    import asyncio
    import aiohttp

    if loop is None:
        loop = asyncio.get_event_loop()

    async def async_loader(url):
        """
        Retrieves JSON-LD at the given URL asynchronously.

        :param url: the URL to retrieve.

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
            headers = {
                'Accept': 'application/ld+json, application/json'
            }
            async with aiohttp.ClientSession(loop=loop) as session:
                async with session.get(url,
                                       headers=headers,
                                       **kwargs) as response:
                    # Allow any content_type in trying to parse json
                    # similar to requests library
                    json_body = await response.json(content_type=None)
                    doc = {
                        'contextUrl': None,
                        'documentUrl': response.url.human_repr(),
                        'document': json_body
                    }
                    content_type = response.headers.get('content-type')
                    link_header = response.headers.get('link')
                    if link_header and content_type != 'application/ld+json':
                        link_header = parse_link_header(link_header).get(
                            LINK_HEADER_REL)
                        # only 1 related link header permitted
                        if isinstance(link_header, list):
                            raise JsonLdError(
                                'URL could not be dereferenced, '
                                'it has more than one '
                                'associated HTTP Link Header.',
                                'jsonld.LoadDocumentError',
                                {'url': url},
                                code='multiple context link headers')
                        if link_header:
                            doc['contextUrl'] = link_header['target']
                    return doc
        except JsonLdError as e:
            raise e
        except Exception as cause:
            raise JsonLdError(
                'Could not retrieve a JSON-LD document from the URL.',
                'jsonld.LoadDocumentError', code='loading document failed',
                cause=cause)

    def loader(url):
        """
        Retrieves JSON-LD at the given URL.

        :param url: the URL to retrieve.

        :return: the RemoteDocument.
        """
        return loop.run_until_complete(async_loader(url))

    return loader
