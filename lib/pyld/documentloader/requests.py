"""
Remote document loader using Requests.

.. module:: jsonld.documentloader.requests
  :synopsis: Remote document loader using Requests

.. moduleauthor:: Dave Longley
.. moduleauthor:: Mike Johnson
.. moduleauthor:: Tim McNamara <tim.mcnamara@okfn.org>
.. moduleauthor:: Olaf Conradi <olaf@conradi.org>
"""
from __future__ import absolute_import

import string

from pyld.jsonld import (JsonLdError, urllib_parse,
                         parse_link_header, LINK_HEADER_REL)


def requests_document_loader(secure=False, **kwargs):
    """
    Create a Requests document loader.

    Can be used to setup extra Requests args such as verify, cert, timeout,
    or others.

    :param secure: require all requests to use HTTPS (default: False).
    :param **kwargs: extra keyword args for Requests get() call.

    :return: the RemoteDocument loader function.
    """
    import requests

    def loader(url):
        """
        Retrieves JSON-LD at the given URL.

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
                    'URL could not be dereferenced; only "http" and "https" '
                    'URLs are supported.',
                    'jsonld.InvalidUrl', {'url': url},
                    code='loading document failed')
            if secure and pieces.scheme != 'https':
                raise JsonLdError(
                    'URL could not be dereferenced; secure mode enabled and '
                    'the URL\'s scheme is not "https".',
                    'jsonld.InvalidUrl', {'url': url},
                    code='loading document failed')
            headers = {
                'Accept': 'application/ld+json, application/json'
            }
            response = requests.get(url, headers=headers, **kwargs)

            doc = {
                'contextUrl': None,
                'documentUrl': response.url,
                'document': response.json()
            }
            content_type = response.headers.get('content-type')
            link_header = response.headers.get('link')
            if link_header and content_type != 'application/ld+json':
                link_header = parse_link_header(link_header).get(
                    LINK_HEADER_REL)
                # only 1 related link header permitted
                if isinstance(link_header, list):
                    raise JsonLdError(
                        'URL could not be dereferenced, it has more than one '
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

    return loader
