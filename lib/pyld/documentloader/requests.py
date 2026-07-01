"""
Remote document loader using Requests.

.. module:: jsonld.documentloader.requests
  :synopsis: Remote document loader using Requests

.. moduleauthor:: Dave Longley
.. moduleauthor:: Mike Johnson
.. moduleauthor:: Tim McNamara <tim.mcnamara@okfn.org>
.. moduleauthor:: Olaf Conradi <olaf@conradi.org>
"""
import re
import string
import urllib.parse as urllib_parse

from pyld import iri_resolver
from pyld.documentloader.base import DocumentLoader, RemoteDocument
from pyld.jsonld import LINK_HEADER_REL, JsonLdError, parse_link_header


class RequestsDocumentLoader(DocumentLoader):
    """Remote document loader using Requests."""

    def __init__(self, secure=False, session=None, **kwargs):
        if session is None:
            import requests

            session = requests.Session()
        self.session = session
        self.secure = secure
        self.kwargs = kwargs

    def __call__(self, url, options=None) -> RemoteDocument:
        """
        Retrieves JSON-LD at the given URL.

        :param url: the URL to retrieve.

        :return: the RemoteDocument.
        """
        if options is None:
            options = {}
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
            if self.secure and pieces.scheme != 'https':
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
            response = self.session.get(url, headers=headers, **self.kwargs)

            content_type = response.headers.get('content-type')
            if not content_type:
                content_type = 'application/octet-stream'
            doc = {
                'contentType': content_type,
                'contextUrl': None,
                'documentUrl': response.url,
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
                    doc['documentUrl'] = iri_resolver.resolve(
                        linked_alternate['target'], url)
                    return self(doc['documentUrl'], options=options)
            doc['document'] = response.json()
            return doc
        except JsonLdError as e:
            raise e
        except Exception as cause:
            raise JsonLdError(
                'Could not retrieve a JSON-LD document from the URL.',
                'jsonld.LoadDocumentError',
                code='loading document failed') from cause


def requests_document_loader(secure=False, **kwargs):
    """
    Create a Requests document loader.

    Can be used to setup extra Requests args such as verify, cert, timeout,
    or others.

    :param secure: require all requests to use HTTPS (default: False).
    :param **kwargs: extra keyword args for Requests get() call.

    :return: the RemoteDocument loader function.
    """
    return RequestsDocumentLoader(secure=secure, **kwargs)
