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

from multiprocessing.util import DEBUG
import re
from urllib.parse import urlencode
from pathlib import Path

import requests
from bs4 import BeautifulSoup


class BibleGatewayError(Exception):
    """Raised when a passage cannot be retrieved."""
    pass


class BibleGatewayProvider:

    BASE_URL = "https://www.biblegateway.com/passage/"

    USER_AGENT = (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/138.0 Safari/537.36"
    )

    def __init__(self, timeout=20):

        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": self.USER_AGENT
        })

    ##################################################################

    def build_url(self, reference, version):

        query = urlencode({
            "search": reference,
            "version": version
        })

        return f"{self.BASE_URL}?{query}"


    ##################################################################

    def initial_verse(self, reference):
        """
        Returns the first verse number contained in a Scripture reference.

        Examples
        --------
        Matthew 3               -> 1
        Matthew 3:1             -> 1
        Matthew 3:1-5           -> 1
        Matthew 3:15-17         -> 15
        John 3:16              -> 16
        Romans 8:28-39         -> 28
        1 Corinthians 13       -> 1
        1 Corinthians 13:4-8   -> 4

        If no verse is present, returns 1.
        """

        reference = reference.strip()

        #
        # Look for ":<verse>"
        #

        match = re.search(r":\s*(\d+)", reference)

        if match:

            return int(match.group(1))

        #
        # Chapter only
        #

        return 1

    ##################################################################

    def fetch_html(self, reference, version):

        url = self.build_url(reference, version)

        print("Fetching:", url)

        response = self.session.get(url, timeout=self.timeout)

        print("Status:", response.status_code)
        print("Final URL:", response.url)

        html = response.text

        Path("debug/last_response.html").write_text(
            html,
            encoding="utf-8"
        )

        return html

    ##################################################################

    def parse_html(self, html, reference):

        soup = BeautifulSoup(html, "lxml")


        normalized_reference = ""

        meta = soup.find("meta", property="og:title")

        if meta:
            content = meta["content"]
            normalized_reference = content.replace("Bible Gateway passage: ", "").split(" - ")[0]

        passage = soup.select_one("div.passage-content")

        if passage is None:
            raise BibleGatewayError("Unable to locate passage.")

        std_text = (
            passage.select_one("div.std-text")
            or passage.select_one("div.text-html")
        )

        if std_text is None:
            raise BibleGatewayError("Unable to locate Scripture text.")

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

        #
        # Iterate over every verse span
        #

        for span in std_text.select("span.text"):

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

                if text:

                    verses.append({

                        "number": current_number,

                        "text": text

                    })

                current_number = int(
                    verse_number.get_text(strip=True)
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

        if current_number is not None:

            text = " ".join(current_text).strip()

            text = " ".join(text.split())

            verses.append(
                {
                    "number": current_number,
                    "text": text
                }
            )

        return {

            "verses": verses,

            "reference": normalized_reference or reference

        }

    ##################################################################

    def get_passage(self, reference, version):

        print(f"Retrieving passage: {reference} ({version})")

        html = self.fetch_html( reference,   version )

        parsed = self.parse_html(html, reference)

        return {

            "reference": parsed["reference"],

            "version": version,

            "verses": parsed["verses"]

        }
