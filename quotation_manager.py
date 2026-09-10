"""
quotation_manager.py

Manages the currently selected Bible provider, reference,
and Bible version.
"""

from bible_provider import (
    get_provider,
    BibleProviderError
)


class QuotationManager:

    def __init__(
        self, provider, cache
    ):

        self.cache = cache

        #
        # The provider argument may be either:
        #
        #     "biblegateway"
        #
        # or an already-created provider object.
        #
        if isinstance(provider, str):

            self.provider = get_provider( provider )

        else:

            self.provider = provider

        self.reference = ""

        self.version = ""

    ##################################################################

    def set( self, provider, reference, version ):

        """
        Set the current provider, Scripture reference,
        and Bible version.
        """

        #
        # Normalize input
        #

        provider = provider.strip().lower()

        reference = reference.strip()

        version = version.strip().upper()

        #
        # Create the requested provider.
        #

        self.provider = get_provider( provider )

        #
        # Store the selected Scripture.
        #

        self.reference = reference

        self.version = version

    ##################################################################

    def get_provider(self):

        """
        Return the current provider object.
        """

        return self.provider

    ##################################################################

    def get_provider_name(self):

        """
        Return the name of the current provider.
        """

        return self.provider.name

    #######################################################################

    def get_provider_versions(self):

        return self.provider.get_versions()

    #######################################################################

    def get_providers(self):

        return self.provider.PROVIDERS

    ##################################################################

    def get_reference(self):

        return self.reference

    ##################################################################

    def get_version(self):

        return self.version

    ##################################################################

    def is_cached(self):
        """
        Checks if the managed reference, version, and provider name 
        are already in the cache memory
        """
        # generate lowercase tuple
        key = self.cache._key( self.provider.name, self.reference, self.version )

        return (key in self.cache._cache)

    def get_passage(self):

        """
        Return the currently selected Scripture.

        The cache is keyed by:

            provider
            reference
            version

        so the same Scripture/version can safely exist in the
        cache for multiple providers.
        """

        if not self.reference:

            return None

        if not self.version:

            return None

        provider = self.provider.name

        #
        # Look in the cache first.
        #

        passage = self.cache.get( provider, self.reference, self.version )

        if passage is not None:

            return passage

        #
        # Retrieve from provider.
        #

        try:

            passage = self.provider.get_passage( self.reference, self.version )

        except Exception as e:
            raise e

        #
        # Store in cache.
        #

        self.cache.put( provider, self.reference, self.version, passage )

        return passage