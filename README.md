# Scripture Overlay

A lightweight Flask-based Scripture display application designed for use with a browser or OBS Browser Source. Scripture passages are retrieved from BibleGateway and displayed in a configurable overlay.

## Preview

<img src="docs/screenshots/scripture-display.png" width="700">

The application includes a selection interface:

<img src="docs/screenshots/scripture-select.png" width="500">


## Requirements

* Python 3.10 or later
* Flask
* Requests
* BeautifulSoup4
* Watchdog is **no longer required** in the current architecture
* An internet connection for retrieving Scripture passages from BibleGateway

Install the Python dependencies with:

```bash
pip install -r requirements.txt
```

## Launching the Application

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd <repository-directory>
```

Start the Flask server:

```bash
python app.py
```

The application runs by default at:

```text
http://localhost:8080/
```

## Operating the Application

### Scripture Display

Open:

```text
http://localhost:8080/
```

This is the main Scripture display and can be used as an **OBS Browser Source**.

### Scripture Selection

Open:

```text
http://localhost:8080/select
```

The selection interface allows you to:

* Enter a Bible reference.
* Select a Bible version.
* Adjust the first verse using `−` and `+`.
* Adjust the last verse using `−` and `+`.
* Review the complete selection before submitting.
* Submit the selection to update the Scripture display.

After submission, the new passage becomes the current passage used by the main display.

## OBS Usage

Add the following URL as an OBS **Browser Source**:

```text
http://localhost:8080/
```

Set the Browser Source dimensions to match the desired display/overlay resolution.

The display periodically polls the `/scripture` endpoint for changes. Scripture is not re-fetched from BibleGateway unless the selected reference or version changes.

## API Endpoints

| Endpoint     | Purpose                                          |
| ------------ | ------------------------------------------------ |
| `/`          | Scripture display                                |
| `/select`    | Scripture selection interface                    |
| `/scripture` | Returns the current Scripture as JSON            |
| `/quotation` | Returns the current reference and version        |
| `/health`    | Returns application status and cache information |

Example:

```bash
curl http://localhost:8080/scripture
```

## Caching

The application maintains an in-memory cache of retrieved Scripture passages.

When the same reference and Bible version are requested again, the cached passage is used rather than making another request to BibleGateway.

Changing either the reference or the version causes the application to retrieve the new passage when it is not already cached.

## Acknowledgements

**BibleGateway**
Scripture passages are retrieved from [BibleGateway](https://www.biblegateway.com/passage/) using the Bible translation selected by the user.

**ChatGPT / OpenAI**
The architecture, software design, and implementation of this application were developed with assistance from ChatGPT, an AI assistant developed by OpenAI.

BibleGateway and OpenAI are independent organizations and do not endorse or sponsor this application.
