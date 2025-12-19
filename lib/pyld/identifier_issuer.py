class IdentifierIssuer(object):
    """
    An IdentifierIssuer issues unique identifiers, keeping track of any
    previously issued identifiers.
    """

    def __init__(self, prefix):
        """
        Initializes a new IdentifierIssuer.

        :param prefix: the prefix to use ('<prefix><counter>').
        """
        self.prefix = prefix
        self.counter = 0
        self.existing = {}
        self.order = []

        """
        Gets the new identifier for the given old identifier, where if no old
        identifier is given a new identifier will be generated.

        :param [old]: the old identifier to get the new identifier for.

        :return: the new identifier.
        """
    def get_id(self, old=None):
        # return existing old identifier
        if old and old in self.existing:
            return self.existing[old]

        # get next identifier
        id_ = self.prefix + str(self.counter)
        self.counter += 1

        # save mapping
        if old is not None:
            self.existing[old] = id_
            self.order.append(old)

        return id_

    def has_id(self, old):
        """
        Returns True if the given old identifier has already been assigned a
        new identifier.

        :param old: the old identifier to check.

        :return: True if the old identifier has been assigned a new identifier,
          False if not.
        """
        return old in self.existing
