"""
Remote document loader using Requests.

.. module:: jsonld.documentloader.requests
  :synopsis: Remote document loader using Requests

.. moduleauthor:: Dave Longley
.. moduleauthor:: Mike Johnson
.. moduleauthor:: Tim McNamara <tim.mcnamara@okfn.org>
.. moduleauthor:: Olaf Conradi <olaf@conradi.org>
"""
import string
import re
import urllib.parse as urllib_parse

from pyld.jsonld import (JsonLdError, parse_link_header, LINK_HEADER_REL)


def requests_document_loader(secure=False, max_link_follows=2, **kwargs):
    """
    Create a Requests document loader.
    Can be used to setup extra Requests args such as verify, cert, timeout,
    or others.
    :param secure: require all requests to use HTTPS (default: False).
    :param max_link_follows: Maximum number of alternate link follows allowed.
    :param **kwargs: extra keyword args for Requests get() call.
    :return: the RemoteDocument loader function.
    """
    import requests

    def loader(url, options={}, link_follow_count=0):
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
            headers = options.get('headers')
            if headers is None:
                headers = {
                    'Accept': 'application/ld+json, application/json'
                }
            response = requests.get(url, headers=headers, **kwargs)

            content_type = response.headers.get('content-type')
            if not content_type:
                content_type = 'application/octet-stream'
            doc = {
                'contentType': content_type,
                'contextUrl': None,
                'documentUrl': response.url,
                'document': None
            }
            try:
                doc['document'] = response.json()
            except json.JSONDecodeError as e:
                # document body is not parseable, continue to check link headers
                pass
            # if content_type in headers['Accept']:
            #    doc['document'] = response.json()
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
                    if link_follow_count >= max_link_follows:
                        raise requests.TooManyRedirects(f"Exceeded maximum link header redirects ({max_link_follows})")
                    return loader(doc['documentUrl'], options=options, link_follow_count=link_follow_count + 1)
            return doc
        except JsonLdError as e:
            raise e
        except Exception as cause:
            raise JsonLdError(
                'Could not retrieve a JSON-LD document from the URL.',
                'jsonld.LoadDocumentError', code='loading document failed',
                cause=cause)

    return loader
