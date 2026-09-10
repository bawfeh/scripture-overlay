"""
aibible.py

AI Bible provider.

Uses an AI model to retrieve a Bible passage.

Given:

    reference = "John 3:16-18"
    version   = "LSG"

returns:

    {
        "reference": "...",
        "version": "...",
        "verses": [
            {
                "number": 16,
                "text": "..."
            },
            ...
        ]
    }

IMPORTANT:
This provider relies on an AI model to reproduce the requested
Bible text. It should therefore be considered experimental.
"""

import json
import os

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled at runtime when dependency is missing.
    OpenAI = None

from bible_provider import BibleProvider, Path
from bible_provider import BibleProviderError


class AIBibleError(BibleProviderError):
    """Raised when the AI Bible passage cannot be retrieved."""
    pass


class AIBibleProvider(BibleProvider):

    name = "aibible"

    # MODEL = "gpt-5.6-luna"
    MODEL = "openrouter/free"

    API_KEY_ENV_VAR = "OPENROUTER_API_KEY"

    label = f"AI Bot ({MODEL})"

    DEBUG_FILE = f"debug/debug_{name}.html"

    VERSIONS_LOCATION = f"data/biblegateway_versions.json"

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.PROVIDERS[self.name] = self.label

        api_key = os.getenv(self.API_KEY_ENV_VAR)

        if not api_key:

            Path(self.DEBUG_FILE) \
            .parent.mkdir( parents=True, exist_ok=True ) \
            .write_text( f"Error: {self.API_KEY_ENV_VAR} environment variable is not set.", encoding="utf-8" )

            raise AIBibleError(
                f"{self.API_KEY_ENV_VAR} environment variable is not set."
            )

        if OpenAI is None:
            raise AIBibleError(
                "The openai package is required for the AI Bible provider."
            )

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )

    ##################################################################

    def write_debug_file(self, content):

        debug_file = Path(self.DEBUG_FILE)
        debug_file.parent.mkdir(parents=True, exist_ok=True)
        debug_file.write_text(content, encoding="utf-8")

    ##################################################################

    def fetch_html(self, reference, version):

        """
        Retrieve a Bible passage using an AI model.
        """

        # Parse the reference and version into a tuple for AI Bible provider.
        reference, version = self.build_url(reference, version)
        
        # print(f"DEBUG: reference - {reference}, version - {version}")

        if not reference:

            self.write_debug_file( f"Error: Bible reference is required." )

            raise AIBibleError("Bible reference is required.")

        if not version:
            
            self.write_debug_file( f"Error: Bible version is required." )

            raise AIBibleError("Bible version is required.")

        prompt = f"""
                Retrieve the exact Bible passage requested below.

                Bible reference: {reference}

                Bible translation/version: {version}

                Instructions:

                1. Return only the requested passage.
                2. Do not summarize.
                3. Do not explain the passage.
                4. Do not add commentary.
                5. Preserve the wording of the specified translation as accurately
                as possible.
                6. Return one object for each verse.
                7. The verse number must be numeric, except for the Message translation which groups verses into paragraphs. 
                    In that case, return the paragraph number as a string.
                8. Do not include footnotes, cross references, headings, or commentary.
                9. If the requested translation cannot be reliably identified,
                report an error instead of silently substituting another translation.
                """

        try:

            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Bible passage retrieval assistant. "
                            "Return only the requested Bible passage."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "bible_passage",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "reference": {
                                    "type": "string"
                                },
                                "version": {
                                    "type": "string"
                                },
                                "verses": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "number": {
                                                "type": "integer"
                                            },
                                            "text": {
                                                "type": "string"
                                            }
                                        },
                                        "required": [
                                            "number",
                                            "text"
                                        ],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": [
                                "reference",
                                "version",
                                "verses"
                            ],
                            "additionalProperties": False
                        }
                    }
                }
            )

        except Exception as e:
            
            self.write_debug_file( f"Error: AI Bible request failed: {e}" )

            raise AIBibleError(
                f"AI Bible request for {reference} ({version}) failed: {e}"
            ) from e

        try:

            # data = json.loads(response.output_text)
            data = json.loads(
                response.choices[0].message.content
            )

        except (json.JSONDecodeError, AttributeError, TypeError, IndexError, KeyError) as e:

            self.write_debug_file( f"Error: AI returned an invalid response: {e}" )

            raise AIBibleError(
                f"AI returned an invalid response for {reference} ({version})."
            ) from e

        if not isinstance(data, dict):
            self.write_debug_file("Error: AI returned an invalid response object.")
            raise AIBibleError(
                f"AI returned an invalid response for {reference} ({version})."
            )

        if not data.get("verses"):

            self.write_debug_file( f"Error: AI did not return any Bible verses." )

            raise AIBibleError(
                "AI did not return any Bible verses."
            )

        return data

    ##################################################################

    def build_url(self, reference, version):
        """
        Parses the reference and version into a tuple for AI Bible provider.
        AI Bible provider does not use a URL, but this method is required to conform to the interface.

        Returns
        -------
        tuple
            A tuple containing the reference and version.
        """

        book, chapter, start_verse, end_verse = self.parse_reference(reference)

        normalized_book = self.get_book_name(book)

        parse_reference = f"{normalized_book or book} {chapter}:{start_verse}" \
            + (f"-{end_verse}" if end_verse != start_verse else "")

        return (
            parse_reference,
            version
        )

    ##################################################################

    def parse_html(self, html, reference, version = None):

        # html is expected to be a dictionary returned by fetch_html

        if html is None: 
            self.write_debug_file( f"Error: Unable to locate passage." )
            raise AIBibleError(f"Unable to locate passage for {reference} ({version}).")

        verses = html.get("verses", [])

        if not verses:
            self.write_debug_file( f"Error: Unable to locate Scripture text." )

            raise AIBibleError(
                f"Unable to locate Scripture text for {reference} ({version})."
            )

        # Update reference to match AI returned reference
        if reference != html.get("reference"):
            reference = html.get("reference")

        # if reference != html.get("reference"):
        #     self.write_debug_file( f"Error: Reference mismatch: requested '{reference}', but AI returned '{html.get('reference')}'." )
        #     raise AIBibleError(
        #         f"Reference mismatch: requested '{reference}', "
        #         f"but AI returned '{html.get('reference')}'."
        #     )

        if version and version != html.get("version"):
            self.write_debug_file( f"Error: Version mismatch: requested '{version}', but AI returned '{html.get('version')}'." )
            raise AIBibleError(
                f"Version mismatch: requested '{version}', "
                f"but AI returned '{html.get('version')}'."
            )

        # Impose a cut-off on the number of verses to output

        MSG = version and version.lower() == "msg"

        reference, cut_off = self.output_ref(
            reference, verses, MSG
        )


        return {

            "verses": verses[:cut_off],

            "reference": reference,

        }

    
    ##################################################################

    def get_versions(self):
        """
        Returns a list of available Bible versions from BibleGateway."""

        # Read the versions from the VERSIONS_LOCATION file if it exists

        try:
            with open(self.VERSIONS_LOCATION, "r") as f:

                versions = json.load(f)

                return self.validate_versions(versions)

        except FileNotFoundError as e:

            self.write_debug_file( f"BibleGateway versions file not found: {self.VERSIONS_LOCATION}" )
            raise AIBibleError(
                f"BibleGateway versions file not found: {self.VERSIONS_LOCATION}"
            ) from e

        except (json.JSONDecodeError, OSError, TypeError, ValueError) as e:
            self.write_debug_file(
                f"Error: Unable to read BibleGateway versions file: {e}"
            )
            raise AIBibleError(
                f"Unable to read BibleGateway versions file: {self.VERSIONS_LOCATION}"
            ) from e


    ##################################################################