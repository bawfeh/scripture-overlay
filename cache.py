"""
cache.py

Simple in-memory cache for Scripture passages.
"""

from datetime import datetime, timedelta


class PassageCache:


    def __init__(self, ttl_minutes=60):

        self.ttl = timedelta(minutes=ttl_minutes)

        self._cache = {}


    ##############################################################

    def _key(self, provider, reference, version):

        return (

            provider.strip().lower(),

            reference.strip().lower(),

            version.strip().upper()

        )


    ##############################################################

    def get( self, provider, reference, version ):

        key = self._key( provider, reference, version )

        if key not in self._cache:

            return None


        entry = self._cache[key]


        if datetime.now() > entry["expires"]:

            del self._cache[key]

            return None


        return entry["data"]


    ##############################################################

    def put( self, provider, reference, version, passage ):

        key = self._key( provider, reference, version )


        self._cache[key] = {

            "data": passage,

            "expires": datetime.now() + self.ttl

        }


    ##############################################################

    def remove( self, provider, reference, version ):

        key = self._key( provider, reference, version )

        self._cache.pop( key, None )


    ##############################################################

    def clear(self):

        self._cache.clear()


    ##############################################################

    def size(self):

        return len( self._cache )


    ##############################################################

    def remove_expired(self):

        now = datetime.now()


        expired = [

            key

            for key, value

            in self._cache.items()

            if value["expires"] < now

        ]


        for key in expired:

            del self._cache[key]