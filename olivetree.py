"""
olivetree.py

Olive Tree Bible provider.

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

"""


import re, json
from urllib.parse import urlencode
from pathlib import Path

from bs4 import BeautifulSoup


from bible_provider import BibleProvider
from bible_provider import BibleProviderError


class OliveTreeError(BibleProviderError):
    """Raised when a passage or version list cannot be retrieved."""
    pass


def get_verse_number(span):
    """Return the verse number encoded by a passage span, or ``None``."""

    verse_number = span.select_one("sup.versenum")

    if verse_number is not None:

        value = verse_number.get_text(strip=True)

        try:

            return value if "-" in value else int(value)

        except ValueError:

            raise OliveTreeError(f"Unable to parse verse number: {verse_number}.")

    class_match = re.search(
        r"-(\d+)$", " ".join(span.get("class", []))
    )

    if class_match:
        return int(class_match.group(1))

    chapter_element = span.select_one(".chapternum")

    chapter_match = (
        re.search(r"\d+", chapter_element.get_text())
        if chapter_element is not None else None
    )

    return int(chapter_match.group()) if chapter_match else None


class OliveTreeProvider(BibleProvider):

    name = "olivetree"
    label = "Olive Tree"

    BASE_URL = "https://www.olivetree.com/bible"

    DEBUG_FILE = f"debug/debug_{name}.html"

    VERSIONS_LOCATION = f"data/{name}_versions.json"

    VERSIONS_URL = "https://www.olivetree.com/bible/versions/"

    ##################################################################

    def build_url(self, reference, version):

        query = urlencode({
            "query": reference,
            "version": version
        })

        return f"{self.BASE_URL}?{query}"

    ##################################################################

    def parse_html(self, html, reference, version = None):

        soup = BeautifulSoup(html, "lxml")

        #
        # Locate the main passage container
        #

        passage = soup.select_one(
            "div.result-text-style-normal.text-html"
        )

        if passage is None:

            raise OliveTreeError(
                "Unable to locate passage for "
                f"{reference} ({version})!"
            )

        # Decompose any h3 and meta elements that may be present in the passage container
        # if version and version.lower() in ["esv", "rvr1960"]:
        for element in passage.select("h3, meta"):
            element.decompose()
        

        MSG = version and version.lower() == "msg"

        #
        # Extract normalized/canonical reference
        #
        # Olive Tree provides this directly in:
        #
        # <span class="passage-display-bcv">
        #     John 3:16
        # </span>
        #

        normalized_reference = ""

        reference_element = passage.select_one(
            "span.passage-display-bcv"
        )

        if reference_element is None:

            book, _, _, _ = self.parse_reference(reference)
            normalized_book = self.get_book_name(book)
            if normalized_book is not None:
                normalized_reference = reference.replace(book, normalized_book)

        else:

            normalized_reference = (
                reference_element.get_text( " ", strip=True )
            )

        #
        # Build verse list
        #

        verses = []

        verse_counter = 0

        current_number = self.initial_verse(reference)
        # initial_verse = current_number

        current_text = []

        def save_current_verse():
            nonlocal current_number, current_text, verse_counter

            if current_number is None:
                return

            text = " ".join( current_text ).strip()
            text = " ".join( text.split() ).strip()

            if not text:
                current_text = []
                return

            verses.append(
                { "number": current_number, "text": text }
            )

            verse_counter = len(verses)

            current_text = []

        #
        # Olive Tree places verse text in:
        #
        # <span class="text ...">
        #
        # with the verse number in:
        #
        # <sup class="versenum">
        #
        # The outer ``span.text`` may wrap the actual verse spans.  Process
        # only identified verse spans so its combined text is not duplicated.
        # Verse spans are not consistently given an id.  Some responses use
        # only a class such as ``Matt-18-1``; selecting ``span.text[id]``
        # therefore misses the remaining verses.  Skip the outer text
        # wrapper, which has neither a verse id nor a verse-number class.

        for span in passage.select("span.text"):

            if verse_counter >= self.MAX_VERSES:
                break

            class_name = " ".join(span.get("class", []))

            if (
                not span.get("id")
                and not re.search(r"-\d+$", class_name)
            ):
                continue

            # Determine the verse number from the span, including class-only
            # and chapter-number markup used by some Olive Tree responses.
            verse_number = get_verse_number(span)

            if verse_number is not None:
                save_current_verse()
                current_number = verse_number

            # Chapter numbers are markup, not part of the verse text.
            for chapter_number in span.select(".chapternum"):
                chapter_number.decompose()



            if span.select_one("sup.versenum") is not None:
                #
                # Remove the verse number so it
                # does not become part of the text.
                #

                span.select_one("sup.versenum").decompose()

            #
            # Collect verse text.
            #

            text = span.get_text( separator=" ", strip=True )

            text = (" ".join( text.split() )).strip()

            # 
            # Clean up the text from cross-references like [a], [b], (A), (B),
            # ... that are not part of the verse text.
            #
            cross_references = re.findall(r"(\[\s*[a-z]\s*\]|\(\s*[A-Z]\s*\))", text)

            if cross_references:
                for match in cross_references:
                    text = text.replace(match, "").strip() 

            if (
                text
                and (not current_text or current_text[-1] != text)
            ):
                current_text.append(text)

        #
        # Store the final verse.
        #

        if current_number is not None and verse_counter < self.MAX_VERSES:
            save_current_verse()

        if not verses:
            raise OliveTreeError(
                f"Unable to locate Scripture text for "
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
            "reference": reference
        }

    ##################################################################

    def get_versions(self):
        """
        Returns a list of available Bible versions.

        Each version is returned as:

            {
                "name": "King James Version (KJV)",
                "code": "KJV"
            }
        """

        # Read the versions from the VERSIONS_LOCATION file if it exists

        try:
            with open(self.VERSIONS_LOCATION, "r") as f:

                versions = json.load(f)

                return self.validate_versions(versions)

        except FileNotFoundError:

            pass

        # Scrape and extract versions from URL using requests + bs4
        
        response = self.session.get( self.BASE_URL, timeout=self.timeout )

        if response.status_code != 200:

            raise OliveTreeError(
                f"Unable to retrieve versions. "
                f"Status code: {response.status_code}"
            )

        soup = BeautifulSoup( response.text, "lxml" )

        select = soup.select_one("select[name='version']")

        if select is None:

            raise OliveTreeError(
                "Unable to locate Olive Tree "
                "version selector."
            )

        versions = []

        for option in select.find_all( "option" ):

            code = option.get( "value" )

            name = option.get_text( " ", strip=True )

            if not code or not name:

                continue

            #
            # Olive Tree displays names like:
            #
            # King James Version (KJV)
            #
            # We only want the human-readable name
            # in "name".
            #

            match = re.match( r"^(.*?)\s*\(([^()]+)\)\s*$", name )

            if match:

                name = match.group(1).strip()

                code = match.group(2).strip()

            versions.append({ "name": name, "code": code })

        # Save the versions to a VERSIONS_LOCATION file in json format for future use

        path = Path(self.VERSIONS_LOCATION)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, "w") as f:
                json.dump(versions, f, indent=4)
        except OSError as exc:
            raise OliveTreeError(
                f"Unable to save version list to {path}."
            ) from exc

        return self.validate_versions(versions)

    ##################################################################