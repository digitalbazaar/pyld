"""
Representation for a resolved Context.

.. module:: resolved_context
  :synopsis: Creates a ContextResolver

.. moduleauthor:: Dave Longley
.. moduleauthor:: Gregg Kellogg <gregg@greggkellogg.net>
"""

from cachetools import LRUCache

MAX_ACTIVE_CONTEXTS = 10


class ResolvedContext:
    """
    A cached contex document, with a cache indexed by referencing active context.
    """

    def __init__(self, document, remote=False):
        """
        Creates a ResolvedContext with caching for processed contexts
        relative to some other Active Context.

        :param document: the context document.
        :param remote: True if the context was loaded by URL (default False).
        """
        # processor-specific RDF parsers
        self.document = document
        self.remote = remote
        self.cache = LRUCache(maxsize=MAX_ACTIVE_CONTEXTS)
        self._remote_copy = None

    def as_remote(self):
        """
        Returns a remote copy of this context, created once and kept with this
        object, so processed contexts are reused when it is cached.
        """
        if self.remote:
            return self
        if self._remote_copy is None:
            self._remote_copy = ResolvedContext(self.document, remote=True)
        return self._remote_copy

    def get_processed(self, active_ctx):
        """
        Returns any processed context for this resolved context relative to an active context.
        """
        return self.cache.get(active_ctx['_uuid'])

    def set_processed(self, active_ctx, processed_ctx):
        """
        Sets any processed context for this resolved context relative to an active context.
        """
        self.cache[active_ctx['_uuid']] = processed_ctx
