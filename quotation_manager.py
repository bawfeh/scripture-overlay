"""
quotation_manager.py

Maintains the currently selected Scripture.

Responsibilities
----------------
1. Store the current reference and version.
2. Retrieve passages using the cache.
3. Keep the current passage in memory.
4. Provide thread-safe access.
"""

from threading import Lock


###########################################################################


class QuotationManager:

    def __init__(
        self,
        provider,
        cache,
        reference="John 3:16",
        version="KJV"
    ):

        self.provider = provider

        self.cache = cache

        self.lock = Lock()

        self.reference = reference.strip()

        self.version = version.strip().upper()

        self.passage = None

        self._load_passage()

    #######################################################################

    def _load_passage(self):

        """
        Loads the current passage.
        Uses the cache whenever possible.
        """

        cached = self.cache.get( self.reference, self.version )

        if cached is not None:

            self.passage = cached

            return

        passage = self.provider.get_passage(
            self.reference,
            self.version
        )

        self.cache.put( self.reference, self.version, passage )

        self.passage = passage

    #######################################################################

    def set( self, reference, version ):

        """
        Changes the current quotation.
        """

        with self.lock:

            reference = reference.strip()

            version = version.strip().upper()

            if (
                reference == self.reference
                and
                version == self.version
            ):
                return

            self.reference = reference

            self.version = version

            self._load_passage()

    #######################################################################

    def get_reference(self):

        with self.lock:

            return self.reference

    #######################################################################

    def get_version(self):

        with self.lock:

            return self.version

    #######################################################################

    def get_passage(self):

        with self.lock:

            return self.passage

    #######################################################################

    def refresh(self):

        """
        Forces a reload from BibleGateway.
        """

        with self.lock:

            self.cache.remove( self.reference, self.version )

            self._load_passage()
