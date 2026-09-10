"""
biblegateway.py

BibleGateway provider.

Given

    reference = "Matt. 3:1-5"
    version   = "KJV"

returns

    {
        "reference": "...",
        "version": "...",
        "text": "..."
    }

"""

# from multiprocessing.util import DEBUG
# import re            
import json
import re
from urllib.parse import urlencode
from pathlib import Path

from bs4 import BeautifulSoup

from bible_provider import BibleProvider
from bible_provider import BibleProviderError


class BibleGatewayError(BibleProviderError):
    """Raised when a passage cannot be retrieved."""
    pass

class BibleGatewayProvider(BibleProvider):
    
    name = "biblegateway"
    label = "BibleGateway"

    BASE_URL = "https://www.biblegateway.com/passage/"

    DEBUG_FILE = f"debug/debug_{name}.html"

    # DEFAULT_REFERENCE = "John 3:16"

    # DEFAULT_VERSION = "KJV"

    VERSIONS_URL = "https://www.biblegateway.com/versions/"

    VERSIONS_LOCATION = f"data/{name}_versions.json"

    ##################################################################

    def build_url(self, reference, version):

        query = urlencode({
            "search": reference,
            "version": version
        })

        return f"{self.BASE_URL}?{query}"

    ##################################################################

    def parse_html(self, html, reference, version = None):

        soup = BeautifulSoup(html, "lxml")

        normalized_reference = ""

        MSG = version and version.lower() == "msg"

        meta = soup.find("meta", property="og:title")

        if meta:
            
            content = meta["content"]
            normalized_reference = content.replace("Bible Gateway passage: ", "").split(" - ")[0]

        else:

            book, _, _, _ = self.parse_reference(reference)
            normalized_book = self.get_book_name(book)
            if normalized_book is not None:
                normalized_reference = reference.replace(book, normalized_book)

        passage = soup.select_one("div.passage-content")

        if passage is None:
            raise BibleGatewayError(
                "Unable to locate passage for "
                f"{normalized_reference or reference} "
                f"({version})"
            )

        std_text = (
            passage.select_one("div.std-text")
            or passage.select_one("div.text-html")
        )

        if std_text is None:
            raise BibleGatewayError(
                "Unable to locate Scripture text for "
                f"{normalized_reference or reference} "
                f"({version})!"
            )

        #
        # Remove unwanted elements
        #

        for element in std_text.select(
            "sup.crossreference,"
            "sup.footnote,"
            "div.footnotes,"
            "a.full-chap-link"
        ):
            element.decompose()

        #
        # Remove chapter number
        #

        for chapter in std_text.select("span.chapternum"):
            chapter.decompose()
            

        h3 = std_text.find("h3")

        if h3 is not None:
            h3.decompose()

        ##################################################################
        # Build verse list
        ##################################################################

        verses = []

        current_number = self.initial_verse(reference)

        current_text = []

        verse_counter = 0

        #
        # Iterate over every verse span until we reach the maximum number of verses
        #

        for span in std_text.select("span.text"):

            if verse_counter >= self.MAX_VERSES:
                break

            #
            # Does this span begin with a verse number?
            #

            verse_number = span.find("sup", class_="versenum")

            if verse_number is not None:

                #
                # Save previous verse
                #

                text = " ".join(current_text).strip()

                text = " ".join(text.split())

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

                        "number": current_number,

                        "text": text

                    })

                    verse_counter = len(verses)

                verse_number_value = verse_number.get_text(strip=True)
                
                current_number = (verse_number_value 
                    if ('-' in verse_number_value) 
                    else int( verse_number_value )
                )

                verse_number.decompose()

                current_text = []

            #
            # Collect text
            #

            text = span.get_text(
                separator=" ",
                strip=True
            )

            text = " ".join(text.split())

            if text:

                current_text.append(text)

        #
        # Store last verse
        #

        if current_number is not None and verse_counter < self.MAX_VERSES:

            text = " ".join(current_text).strip()

            text = " ".join(text.split())

            verses.append(
                {
                    "number": current_number,
                    "text": text
                }
            )

        if not verses:
            raise BibleGatewayError(
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

            "verses": verses[:cut_off],

            "reference": reference,

        }


    ##################################################################

    def get_versions(self):
        """
        Returns a list of available Bible versions 
        First scrapes the versions from the BibleGateway website and then validates them against the VERSIONS dictionary."""

        # Read the versions from the VERSIONS_LOCATION file if it exists

        try:
            with open(self.VERSIONS_LOCATION, "r") as f:

                versions = json.load(f)

                return self.validate_versions(versions)

        except FileNotFoundError:

            pass

        response = self.session.get( self.VERSIONS_URL, timeout=self.timeout )

        if response.status_code != 200:
            raise BibleGatewayError(
                f"Unable to retrieve versions. "
                f"Status code: {response.status_code}"
            )

        soup = BeautifulSoup( response.text, "lxml" )

        versions = []

        for option in soup.select( 'select[name="version"] option' ):

            code = option.get("value")

            name = option.get_text( " ", strip=True )

            if not code or not name:
                continue

            # Ignore language headings and spacers
            if option.get("class"):
                if "lang" in option["class"]:
                    continue

                if "spacer" in option["class"]:
                    continue

            versions.append({ "name": name, "code": code })

        # Save the versions to a VERSIONS_LOCATION file in json format for future use

        with open(Path(self.VERSIONS_LOCATION), "w") as f:

            json.dump(versions, f, indent=4)

        return self.validate_versions(versions)


    ##################################################################