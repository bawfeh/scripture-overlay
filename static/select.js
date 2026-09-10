const providerBox = document.getElementById("provider");
const referenceBox = document.getElementById("reference");
const versionBox = document.getElementById("version");
const preview = document.getElementById("preview");
const submit = document.getElementById("submit");

const leftPlus = document.getElementById("left-plus");
const leftMinus = document.getElementById("left-minus");
const rightPlus = document.getElementById("right-plus");
const rightMinus = document.getElementById("right-minus");

const rangeLeft = document.getElementById("range-left");
const rangeRight = document.getElementById("range-right");

const firstVerseDisplay = document.getElementById("first-verse");
const lastVerseDisplay = document.getElementById("last-verse");

const initialProvider = "{{ provider }}";
const initialVersion = "{{ version }}";
const defaultFirstVerse = 1;
const defaultLastVerse = 4;

//////////////////////////////////////////////////////////////////////

function parseReference(text)
{
    const m = text.match(/^(.+?)\s+(\d+)(?::(\d+)(?:-(\d+))?)?$/);

    if (!m)
        return null;

    const chapter = parseInt(m[2]);
    const firstVerse = m[3] ? parseInt(m[3]) : defaultFirstVerse;
    const lastVerse = m[4] ? parseInt(m[4]) : m[3] ? parseInt(m[3]) : defaultLastVerse;

    return {
        book: m[1],
        chapter: chapter,
        first: firstVerse,
        last: lastVerse
    };
}

//////////////////////////////////////////////////////////////////////

function refreshVerseNumbers()
{
    const r = parseReference(referenceBox.value);

    if (!r)
        return;

    firstVerseDisplay.textContent = r.first;
    lastVerseDisplay.textContent = r.last;
}

//////////////////////////////////////////////////////////////////////

function updateReference(ref)
{
    if (ref.first == ref.last)
        referenceBox.value =
            `${ref.book} ${ref.chapter}:${ref.first}`;
    else
        referenceBox.value =
            `${ref.book} ${ref.chapter}:${ref.first}-${ref.last}`;

    refreshVerseNumbers();
    updatePreview();
}

//////////////////////////////////////////////////////////////////////

leftPlus.onclick = () =>
{
    const r = parseReference(referenceBox.value);

    if (!r || r.first >= r.last)
        return;

    r.first++;
    updateReference(r);
};

//////////////////////////////////////////////////////////////////////

leftMinus.onclick = () =>
{
    const r = parseReference(referenceBox.value);

    if (!r || r.first <= 1)
        return;

    r.first--;
    updateReference(r);
};

//////////////////////////////////////////////////////////////////////

rightPlus.onclick = () =>
{
    const r = parseReference(referenceBox.value);

    if (!r)
        return;

    r.last++;
    updateReference(r);
};

//////////////////////////////////////////////////////////////////////

rightMinus.onclick = () =>
{
    const r = parseReference(referenceBox.value);

    if (!r || r.last <= r.first)
        return;

    r.last--;
    updateReference(r);
};

//////////////////////////////////////////////////////////////////////

rangeLeft.onclick = () =>
{
    const r = parseReference(referenceBox.value);

    if (!r || r.first <= 1)
        return;

    r.first--;
    r.last--;

    updateReference(r);
};

//////////////////////////////////////////////////////////////////////

rangeRight.onclick = () =>
{
    const r = parseReference(referenceBox.value);

    if (!r)
        return;

    r.first++;
    r.last++;

    updateReference(r);
};

//////////////////////////////////////////////////////////////////////

function updatePreview()
{
    if (!providerBox.value ||
        !referenceBox.value ||
        !versionBox.value)
    {
        preview.textContent = "";
        return;
    }

    preview.textContent =
        `${referenceBox.value} (${versionBox.value})`;
}

//////////////////////////////////////////////////////////////////////

async function loadVersions(provider)
{
    const response =
        await fetch(`/versions/${provider}`);

    if (!response.ok)
    {
        alert("Unable to retrieve Bible versions.");
        return;
    }

    const data =
        await response.json();

    versionBox.innerHTML = "";

    for (const version of data.versions)
    {
        const option =
            document.createElement("option");

        option.value =
            version.code;

        option.textContent =
            `${version.name} (${version.code})`;

        versionBox.appendChild(option);
    }

    versionBox.value =
        data.default_version;

    referenceBox.value =
        data.default_reference;

    refreshVerseNumbers();
}

//////////////////////////////////////////////////////////////////////

providerBox.onchange = async function()
{
    await loadVersions(providerBox.value);
    updatePreview();
};

referenceBox.oninput = function()
{
    refreshVerseNumbers();
    updatePreview();
};

versionBox.onchange = updatePreview;

//////////////////////////////////////////////////////////////////////

const submitOnEnter = function(event)
{
    if (event.key === "Enter" || event.code === "Enter")
    {
        event.preventDefault();
        submit.click();
    }
};

referenceBox.onkeydown = submitOnEnter;
versionBox.onkeydown = submitOnEnter;
leftPlus.onkeydown = submitOnEnter;
rightPlus.onkeydown = submitOnEnter;
leftMinus.onkeydown = submitOnEnter;
rightMinus.onkeydown = submitOnEnter;
rangeLeft.onkeydown = submitOnEnter;
rangeRight.onkeydown = submitOnEnter;
providerBox.onkeydown = submitOnEnter;

//////////////////////////////////////////////////////////////////////

submit.onclick = async function()
{
    const provider = providerBox.value;
    const reference = referenceBox.value.trim();
    const version = versionBox.value;

    if (!provider || !reference || !version)
    {
        alert("Please select a provider, reference and version.");
        return;
    }

    submit.disabled = true;

    try
    {
        const response = await fetch(
            "/select",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    provider: provider,
                    reference: reference,
                    version: version
                })
            }
        );

        const result = await response.json();

        if (!response.ok || !result.success)
            throw new Error(
                result.error || "Unable to update Scripture."
            );

        alert(
            `Reference Updated to\n\n${result.reference} ` +
            `(${result.version})\n${result.provider}`
        );
    }
    catch (error)
    {
        console.error(error);
        alert(error.message);
    }
    finally
    {
        submit.disabled = false;
    }
};

//////////////////////////////////////////////////////////////////////

async function initialise()
{
    refreshVerseNumbers();

    providerBox.value = initialProvider;

    await loadVersions(
        initialProvider,
        initialVersion
    );

    updatePreview();
}

initialise();