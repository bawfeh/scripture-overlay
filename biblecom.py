"""
biblecom.py

Bible.com / YouVersion provider.

Given

    reference = "John 3:16"
    version   = "KJV"

returns

    {
        "reference": "...",
        "version": "...",
        "verses": [
            {
                "number": 16,
                "text": "..."
            }
        ]
    }

Bible.com URLs use the following structure:

    https://www.bible.com/bible/{bible_id}/{passage}.{version}

For example:

    https://www.bible.com/bible/1/JHN.3.16.KJV

"""


import re, json
from pathlib import Path

# import requests
from bs4 import BeautifulSoup

from bible_provider import BibleProvider
from bible_provider import BibleProviderError


class BibleComError(BibleProviderError):
    """Raised when a passage or version list cannot be retrieved."""
    pass


class BibleComProvider(BibleProvider):

    name = "biblecom"
    label = "Bible.com"

    BASE_URL = "https://www.bible.com/bible"

    DEBUG_FILE = f"debug/debug_{name}.html"

    VERSIONS_LOCATION = f"data/{name}_versions.json"

    BOOK_CODES_LOCATION = f"data/{name}_codes.json"

    #
    # Bible.com / YouVersion Bible IDs.
    #
    # These IDs are part of the Bible.com URL structure.
    #
    # KJV:
    #   https://www.bible.com/bible/1/JHN.3.16.KJV
    #
    # Additional translations can be added as they are verified.
    #

    VERSIONS = {}

    try:
        with open(VERSIONS_LOCATION, "r") as f:

            VERSIONS = json.load(f)

    except FileNotFoundError:

        pass

    ##################################################################

    def get_version_info(self, version):

        version = version.strip().upper()

        info = self.VERSIONS.get(version)

        if info is None:

            raise BibleComError(
                f"Unsupported Bible.com version: {version}"
            )

        return info

    ##################################################################

    def normalize_book(self, book):

        """
        Converts common Bible book names/abbreviations into the
        three-letter Bible.com book code.

        Examples
        --------
        John            -> JHN
        Matthew         -> MAT
        1 Corinthians   -> 1CO
        2 Corinthians   -> 2CO
        Psalms          -> PSA
        Revelation      -> REV
        """

        book_name = self.get_book_name(book) or book

        book = book_name.strip()

        normalized = " ".join( book.split() )

        # Read the book codes from the BOOK_CODES_LOCATION file if it exists

        BOOK_CODES = {}

        try:
            with open(self.BOOK_CODES_LOCATION, "r") as f:

                BOOK_CODES = json.load(f)

        except FileNotFoundError:

            pass


        code = BOOK_CODES.get(normalized)

        if code is None:

            raise BibleComError(
                f"Unknown Bible book: {book}"
            )

        return code

    ##################################################################

    def build_url(self, reference, version):

        """
        Converts a human-readable Scripture reference into a
        Bible.com URL.

        Examples
        --------
        John 3:16
            -> /bible/1/JHN.3.16.KJV

        John 3:16-18
            -> /bible/1/JHN.3.16-18.KJV

        John 3
            -> /bible/1/JHN.3.KJV
        """

        info = self.get_version_info(version)

        bible_id = info["id"]

        # reference = reference.strip()

        #
        # Separate book from chapter/verse portion.
        #
        # The book may contain a leading number, e.g.
        # "1 Corinthians".
        #

        book, chapter, _, _ = self.parse_reference(reference)

        book_code = self.normalize_book(book)

        passage = (
            f"{book_code}."
            f"{chapter}."
            f"{version.upper()}"
        )

        return (
            f"{self.BASE_URL}/"
            f"{bible_id}/"
            f"{passage}"
        )


    ##################################################################


    def parse_html(self, html, reference, version = None):

        soup = BeautifulSoup(html, "lxml")

        book, chapter, requested_start, requested_end \
                = self.parse_reference(reference)

        normalized_book = self.get_book_name(book)

        normalized_reference = (
            reference.replace(book, normalized_book) if normalized_book else ""
        )

        book = self.normalize_book(book)
            
        verses = []        
        # Try to find verses with data-usfm attribute on .ChapterContent-module__cat7xG__verse spans (ESV format)
        verse_containers = soup.select("span[class*='__verse'][data-usfm]")
        
        # Fallback to old format if no verse containers found
        if not verse_containers:
            verse_containers = soup.select("span[data-usfm]")

        MSG = version and version.lower() == "msg"  # Track possible message translation

        verse_count = 0
                        
        for verse in verse_containers:

            usfm = verse.get("data-usfm")

            if not usfm:
                continue

            # Possible verse grouping with MSG version
            groupings = usfm.split('+')

            if not groupings:
                continue

            grouped_verses = (len(groupings) > 1)

            verse_range = [1, 1]  # default range

            try:
                usfm_book, usfm_chapter, verse_number = groupings[0].split(".")
                usfm_chapter = int(usfm_chapter)
                verse_number = int(verse_number)

            except ValueError:
                continue

            if usfm_book != book:
                continue

            if usfm_chapter != chapter:
                continue

            if grouped_verses:
                verse_end = int(groupings[-1].split('.')[2])
                verse_range = [verse_number, verse_end]
                verse_number = str(verse_number) + '-' + str(verse_end)
                # MSG = True  # characteristic of The Message translation

                if ((requested_start not in verse_range) and 
                    (requested_end not in verse_range)):
                    continue

            else:
                if (verse_number < requested_start or 
                    verse_number > requested_end):
                    continue

            # Get all content spans within this verse, including content inside
            # italic/other formatting spans.
            content_spans = verse.select("span[class*='__content']")

            if content_spans:
                text = " ".join(
                    span.get_text(" ", strip=True)
                    for span in content_spans
                )
            else:
                text = verse.get_text(" ", strip=True)

            # Normalize whitespace
            text = (" ".join(text.split())).strip()

            # 
            # Clean up the text from cross-references like [a], [b], (A), (B),
            # ... that are not part of the verse text.
            #
            cross_references = re.findall(r"(\[\s*[a-z]\s*\]|\(\s*[A-Z]\s*\))", text)

            if cross_references:

                for match in cross_references:
                    text = text.replace(match, "").strip() 

            if text:
                verses.append({
                    "number": verse_number,
                    "text": text
                })
                verse_count += max(1, verse_range[1]-verse_range[0])

            if verse_count > self.MAX_VERSES:
                break

        if not verses:
            raise BibleComError(
                "Unable to locate Scripture text for "
                f"{normalized_reference or reference} "
                f"({version})!"
            )

        # Impose a cut-off on the number of verses to output

        reference, cut_off = self.output_ref(
            normalized_reference or reference, 
            verses, MSG
        )


        return {
            "reference" : reference,
            "verses" : verses[:cut_off]
        }

    ##################################################################

    def get_versions(self):

        """
        Returns the Bible.com versions configured by this provider.

        Bible.com uses numeric Bible IDs in its URLs, so the mapping
        is maintained in VERSIONS.

        Failed versions so far:

        // "NMV": {
        //     "id": "2135",
        //     "name": "New Messianic Version Bible (NMV)"
        // },
        
        """

        versions = []

        for code, info in self.VERSIONS.items():
            #
            # Bible.com displays names like:
            #
            # King James Version (KJV)
            #
            # We only want the human-readable name
            # in "name".
            #

            match = re.match( r"^(.*?)\s*\(([^()]+)\)\s*$", info["name"] )

            if match:
                name = match.group(1).strip()
            else:
                name = info["name"].strip()

            versions.append({ "name": name, "code": code })

        return self.validate_versions(versions)

    ##################################################################