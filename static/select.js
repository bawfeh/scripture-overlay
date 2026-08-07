const referenceBox =
    document.getElementById("reference");

const versionBox =
    document.getElementById("version");

const preview =
    document.getElementById("preview");

const submit =
    document.getElementById("submit");

const leftPlus =
    document.getElementById("left-plus");

const leftMinus =
    document.getElementById("left-minus");

const rightPlus =
    document.getElementById("right-plus");

const rightMinus =
    document.getElementById("right-minus");

const firstVerseDisplay =
    document.getElementById("first-verse");

const lastVerseDisplay =
    document.getElementById("last-verse");

//////////////////////////////////////////////////////////////////////

function parseReference(text)
{
    const m =
        text.match(
            /^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$/
        );

    if (!m)
        return null;

    return {

        book: m[1],

        chapter: parseInt(m[2]),

        first: parseInt(m[3]),

        last:
            m[4]
                ? parseInt(m[4])
                : parseInt(m[3])

    };
}

//////////////////////////////////////////////////////////////////////

function refreshVerseNumbers()
{
    const r =
        parseReference(
            referenceBox.value
        );

    if (!r)
        return;


    firstVerseDisplay.textContent =
        r.first;


    lastVerseDisplay.textContent =
        r.last;
}

//////////////////////////////////////////////////////////////////////

function updateReference(ref)
{
    if (ref.first == ref.last)
    {
        referenceBox.value =
            `${ref.book} ${ref.chapter}:${ref.first}`;
    }
    else
    {
        referenceBox.value =
            `${ref.book} ${ref.chapter}:${ref.first}-${ref.last}`;
    }

    refreshVerseNumbers();

    updatePreview();
}

//////////////////////////////////////////////////////////////////////

leftPlus.onclick = () =>
{
    const r = parseReference(referenceBox.value);

    if (!r)
        return;

    if (r.first < r.last)
        r.first++;
    else return;

    updateReference(r);
};

//////////////////////////////////////////////////////////////////////

leftMinus.onclick = () =>
{
    const r = parseReference(referenceBox.value);

    if (!r)
        return;

    if (r.first > 1)
        r.first--;
    else return;

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
    
        if (!r)
            return;
    
        if (r.last > r.first)
            r.last--;
        else return;
    
        updateReference(r);
};

//////////////////////////////////////////////////////////////////////

function updatePreview()
{
    preview.textContent =
        `${referenceBox.value} (${versionBox.value})`;
}

//////////////////////////////////////////////////////////////////////

referenceBox.oninput =
    updatePreview;

versionBox.onchange =
    updatePreview;

//////////////////////////////////////////////////////////////////////

submit.onclick = async function ()
{
    const response =
        await fetch(
            "/select",
            {

                method: "POST",

                headers:
                {
                    "Content-Type":
                        "application/json"
                },

                body:
                    JSON.stringify(
                    {
                        reference:
                            referenceBox.value,

                        version:
                            versionBox.value
                    })

            });

    const result =
        await response.json();

    alert(
        `Updated to\n\n${result.reference} (${result.version})`
    );
};

//////////////////////////////////////////////////////////////////////

updatePreview();