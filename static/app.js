/**************************************************************************
 * Scripture Overlay
 *
 * app.js
 *
 * Continuously polls the backend for the currently selected Scripture.
 * If the Scripture changes, the overlay fades to the new passage.
 **************************************************************************/

"use strict";

const POLL_INTERVAL = 3000;          // milliseconds
const FADE_TIME = 800;               // milliseconds
const SCRIPTURE_ENDPOINT = "/scripture";
const MAX_VERSES = 4;                  // maximum number of verses to display

const referenceElement = document.getElementById("reference");
const verseElement     = document.getElementById("verse");
const versionElement   = document.getElementById("version");
const card             = document.getElementById("scripture-card");

let currentReference = "";
let currentVersion   = "";


/**********************************************************************
 * Fade Helpers
 **********************************************************************/

function fadeOut(element)
{
    element.classList.remove("fade-in");
    element.classList.add("fade-out");
}

function fadeIn(element)
{
    element.classList.remove("fade-out");
    element.classList.add("fade-in");
}

/**********************************************************************
 * Fit font size to card
 **********************************************************************/

function fitFont()
{
    let size = 48;

    while (size >= 20)
    {
        card.style.setProperty(
            "--base-font-size",
            `${size}px`
        );

        if (verseElement.scrollHeight <= verseElement.clientHeight)
            break;

        size--;
    }
}


/**********************************************************************
 * Update Display
 **********************************************************************/

async function updateDisplay(data)
{
    fadeOut(card);

    await sleep(FADE_TIME);

    referenceElement.textContent = data.reference;
    versionElement.textContent   = data.version;

    verseElement.innerHTML = "";

    data.verses.slice(0, MAX_VERSES).forEach(v => {

        const div = document.createElement("div");

        div.className = "verse";

        div.innerHTML =
            `<span class="verse-number">${v.number}</span>
             <span class="verse-text">${v.text}</span>`;

        verseElement.appendChild(div);

    });

    fitFont(); // Fit font size to card

    fadeIn(card);

    currentReference = data.reference;
    currentVersion   = data.version;
}


/**********************************************************************
 * Sleep
 **********************************************************************/

function sleep(ms)
{
    return new Promise(resolve => setTimeout(resolve, ms));
}


/**********************************************************************
 * Fetch Scripture
 **********************************************************************/

async function fetchScripture()
{
    try
    {
        const response = await fetch(SCRIPTURE_ENDPOINT, {
            cache: "no-store"
        });

        if (!response.ok)
        {
            throw new Error(response.statusText);
        }

        const data = await response.json();

        const changed =
            data.reference !== currentReference ||
            data.version   !== currentVersion   

        if (changed)
        {
            await updateDisplay(data);
        }

    }
    catch(error)
    {
        console.error("Unable to retrieve Scripture.");

        console.error(error);
    }
}


/**********************************************************************
 * Initialisation
 **********************************************************************/

async function initialise()
{
    await fetchScripture();

    setInterval(fetchScripture, POLL_INTERVAL);
}


document.addEventListener("DOMContentLoaded", initialise);