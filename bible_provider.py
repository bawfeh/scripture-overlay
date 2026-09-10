from abc import ABC, abstractmethod
import re
import json
from pathlib import Path

import requests

# from olivetree import OliveTreeError
# from biblegateway import BibleGatewayError
# from biblecom import BibleComError


class BibleProviderError(Exception):
    """Base exception for Bible providers."""
    pass


class BibleProvider(ABC):

    name = "unknown"
    label = "Unknown Provider"

    USER_AGENT = (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/138.0 Safari/537.36"
    )
    

    PROVIDERS = {
        "biblegateway": "BibleGateway",
        "olivetree": "Olive Tree",
        "biblecom": "Bible.com",
        "aibible": "AI Bot"
    }

    DEBUG_FILE = "debug/debug.html"

    DEFAULT_REFERENCE = "John 3:16"

    DEFAULT_VERSION = "KJV"

    MAX_VERSES = 4 # max. number of verses to fetch

    BIBLE_BOOK_ALIASES_FILE = Path("data/bible_book_aliases.json")

    BOOK_LOOKUP = {}  # alias -> canonical book name

    ##################################################################

    def __init__(self, timeout=20):

        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": self.USER_AGENT
        })

        # Load once when this module is imported
        BIBLE_BOOK_ALIASES = self.load_book_aliases()

        self.BOOK_LOOKUP = self.build_book_lookup(BIBLE_BOOK_ALIASES)

    ##################################################################

    def get_provider_name(self):

        return self.name

    ##################################################################

    def initial_verse(self, reference):

        match = re.search(
            r":\s*(\d+)", reference.strip()
        )

        if match:
            return int(match.group(1))

        return 1

    ##################################################################

    def validate_versions(self, versions):

        if not isinstance(versions, list):

            raise BibleProviderError(
                "Version list must be a list."
            )

        for version in versions:

            if not isinstance(version, dict):

                raise BibleProviderError(
                    "Each version must be a dictionary."
                )

            if "name" not in version:

                raise BibleProviderError(
                    "Version is missing 'name'."
                )

            if "code" not in version:

                raise BibleProviderError(
                    "Version is missing 'code'."
                )

            if not version["name"]:

                raise BibleProviderError(
                    "Version name cannot be empty."
                )

            if not version["code"]:

                raise BibleProviderError(
                    "Version code cannot be empty."
                )

        return versions

    ##################################################################

    def output_ref(self, reference, verses, MSG = False):
        """ adjust the reference to match number of verses fetched """

        if not verses:
            return reference, 0

        if MSG:
            # adjust cut-off for The Message translation
            verse_count = 0
            cut_off = 0
            for v in verses:
                cut_off += 1
                if isinstance(v["number"], str): # The Message version
                    start, end = v["number"].split("-")
                    verse_count += int(end) - int(start) + 1
                else:
                    start, end = v["number"], v["number"]
                    verse_count += 1
                if verse_count >= self.MAX_VERSES:
                    break

        else:

            cut_off = min(self.MAX_VERSES, len(verses))

        if '-' in reference:

            requested_end = reference.split('-')[-1]

            limit_end = verses[cut_off - 1]["number"]

            if MSG:

                if isinstance(limit_end, str):
                    limit_end = limit_end.split('-')[-1]

                first_verse = verses[0]["number"]

                if isinstance(first_verse, str):
                    requested_start = reference.split('-')[0].split(':')[-1]
                    reference = reference.replace(
                        requested_start, str(first_verse.split('-')[0])
                    )

            if requested_end.strip():
                reference = reference.replace(
                    requested_end, str(limit_end)
                )

        elif ':'  not in reference:
            
            # reference is a book and chapter only, e.g. "John 3"
            # adjust the reference to include the last verse number
            # based on the number of verses fetched
            if len(verses) > 0:
                last_verse_number = verses[cut_off - 1]["number"]
                if isinstance(last_verse_number, str):
                    last_verse_number = last_verse_number.split('-')[-1]
                reference = f"{reference}:1-{last_verse_number}"

        elif ':' in reference and (len(verses) == 1 and MSG):

            # reference is a book, chapter, and a single verse, e.g. "John 3:16"
            # but the Message translation may have multiple verses in a single verse number, e.g. "John 3:16-17"
            last_verse_number = verses[0]["number"]
            if isinstance(last_verse_number, str):
                reference = f"{reference.split(':')[0]}:{last_verse_number}"

        return reference, cut_off

    ##################################################################

    def parse_reference(self, reference):


        match = re.match(
            r"^(?P<book>.+?)\s+"
            r"(?P<chapter>\d+)"
            r"(?::(?P<verses>[\d\-]+))?$",
            reference.strip()
        )

        if match is None:

            raise BibleProviderError(
                f"Unable to parse Scripture reference: {reference}"
            )

        book = match.group("book")

        chapter = match.group("chapter")

        if not(book and chapter):
            raise BibleProviderError(
                f"Unable to parse Scripture reference: {reference}"
            )

        book = book.strip()

        chapter = int(chapter.strip())

        verses = match.group("verses")

        verse_start = int(self.initial_verse(reference))

        verse_end = None

        if (verses is not None):

            if ('-' in verses):
                verse_aux = verses.split('-')[-1].strip()
                if len(verse_aux) > 0:
                    verse_end = int(verse_aux)

            else:

                verse_end = verse_start
                
        if verse_end is None:
            verse_end = verse_start + self.MAX_VERSES - 1

        return (
            book,
            chapter,
            verse_start,
            verse_end
        )

    ##################################################################

    def fetch_html(self, reference, version):

        url = self.build_url(
            reference, version
        )

        print("Fetching...", url)

        response = self.session.get(
            url, timeout=self.timeout
        )

        if response.status_code != 200:

            raise BibleProviderError(
                f"Unable to retrieve passage. "
                f"Status code: {response.status_code}"
            )

        html = response.text


        # --------------------------------------------------------------
        # Detect Bible.com's client challenge page
        # --------------------------------------------------------------
        html_lower = html.lower()

        if (
            "<title>client challenge</title>" in html_lower
            or "_fs-ch-" in html_lower
        ):
            raise BibleProviderError(
                "Bible.com returned a client challenge instead of "
                "the requested Bible passage."
            )

        Path(self.DEBUG_FILE) \
        .parent.mkdir( parents=True, exist_ok=True )

        Path( self.DEBUG_FILE ) \
        .write_text( html, encoding="utf-8" )

        return html

    ##################################################################

    def get_passage(self, reference, version):

        try:
            html = self.fetch_html(reference, version)

        except BibleProviderError as exc:
            print(exc)
            raise BibleProviderError(
                f"HTML fetch error ==> ({exc})"
            ) from exc

        try:
            parsed = self.parse_html(html, reference, version)

        except BibleProviderError as exc:
            raise BibleProviderError(
                f"HTML parsing error ==> ({exc})"
            ) from exc

        return {
            "reference": parsed["reference"],
            "version": version,
            "verses": parsed["verses"]
        }

    ##################################################################
    
    def get_default_version(self):

        return self.DEFAULT_VERSION

    ##################################################################

    def get_default_reference(self):

        return self.DEFAULT_REFERENCE

    ##################################################################

    def normalize_alias(self, alias):
        """
        Normalize a Bible book alias.

        - Converts to lowercase
        - Removes all whitespace

        Examples:
            '1 Th'  -> '1th'
            '1Th'   -> '1th'
            ' Matt ' -> 'matt'
        """

        if not isinstance(alias, str):
            return ""

        return "".join(alias.lower().split())

    ##################################################################

    def load_book_aliases(self):
        """
        Load the canonical Bible book aliases from JSON.
        """

        with open(self.BIBLE_BOOK_ALIASES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    ##################################################################


    def build_book_lookup(self, book_aliases):
        """
        Build a reverse lookup:

            alias -> canonical book name
        """

        lookup = {}

        for book, aliases in book_aliases.items():

            # The canonical name is also a valid input
            names = [book] + aliases

            for name in names:
                lookup[self.normalize_alias(name)] = book

        return lookup

    ##################################################################

    def get_book_name(self, alias):
        """
        Return the canonical Bible book name.

        Returns None if no match is found.
        """

        normalized = self.normalize_alias(alias)

        if not normalized:
            return None

        return self.BOOK_LOOKUP.get(normalized)

    ##################################################################

    @abstractmethod
    def build_url(self, reference, version):
        """
        Build the URL for the requested passage.

        Returns
        -------
        str
            The URL to fetch the passage.   
        """
        pass

    ##################################################################

    @abstractmethod
    def parse_html(self, html, reference, version = None):
        """
        Parse the HTML response and extract the passage text.

        Returns
        -------
        dict
            A dictionary with the following keys:
            - "reference": The reference for the passage.
            - "verses": A list of the verses in the passage.
        """
        pass

    ##################################################################

    @abstractmethod
    def get_versions(self):
        """
        Return available Bible versions.

        Returns
        -------
        list of dict
            Each version must have the form:

            {
                "name": "King James Version",
                "code": "KJV"
            }
        """
        pass

    ##################################################################


DEFAULT_PROVIDER = "biblegateway"


def get_provider(name=DEFAULT_PROVIDER):

    """
    Create and return a Bible provider instance.
    """

    from biblegateway import BibleGatewayProvider
    from olivetree import OliveTreeProvider
    from biblecom import BibleComProvider

    # AIBible is optional; the other providers must remain usable when it is absent.
    try:
        from aibible import AIBibleProvider
    except ImportError:
        AIBibleProvider = None

    provider_classes = [
        BibleGatewayProvider,
        OliveTreeProvider,
        BibleComProvider,
    ]
    if AIBibleProvider is not None:
        provider_classes.append(AIBibleProvider)

    providers = {
        provider_class.name: provider_class
        for provider_class in provider_classes
    }

    if name is None:
        name = DEFAULT_PROVIDER

    if not isinstance(name, str):

        raise ValueError(
            "Bible provider name must be a string."
        )

    name = name.strip().lower()

    if name not in providers:

        available = ", ".join( sorted(providers.keys()) )

        raise ValueError(
            f"Unknown Bible provider: '{name}'. "
            f"Available providers: {available}"
        )

    provider_class = providers[name]

    return provider_class()