import base64
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from openai import OpenAI


MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def menu_input_part(data: bytes):
    """Build the appropriate Responses API part from the file signature."""
    encoded = base64.b64encode(data).decode("utf-8")
    if data.startswith(b"%PDF-"):
        return {
            "type": "input_file",
            "filename": "menu.pdf",
            "file_data": f"data:application/pdf;base64,{encoded}",
            "detail": "high",
        }

    if data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith((b"GIF87a", b"GIF89a")):
        mime = "image/gif"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError("Choose a PDF, JPEG, PNG, WebP, or GIF menu file.")

    return {
        "type": "input_image",
        "image_url": f"data:{mime};base64,{encoded}",
        "detail": "high",
    }


load_dotenv()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
app = FastAPI()


PAGE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Menu Reader</title>

    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Outfit:wght@500;600;700&display=swap');
        * {
            box-sizing: border-box;
        }

        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            max-width: 760px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #222;
        }

        h1 {
            margin-bottom: 4px;
        }

        .subtitle {
            color: #666;
            margin-bottom: 20px;
        }

        .upload-card {
            background: white;
            padding: 20px;
            border-radius: 16px;
            margin-bottom: 24px;
        }

        .settings-card {
            background: white;
            padding: 20px;
            border-radius: 16px;
            margin-bottom: 16px;
        }

        .settings-card summary {
            cursor: pointer;
            font-size: 17px;
            font-weight: 600;
            padding: 4px 0;
        }

        .settings-card summary:focus-visible {
            outline: 2px solid #222;
            outline-offset: 4px;
        }

        .settings-card[open] summary { margin-bottom: 16px; }
        .settings-card h2 { margin: 0 0 12px; font-size: 20px; }
        .settings-card label { display: block; margin: 12px 0; line-height: 1.4; }
        .settings-card select, .settings-card textarea {
            display: block; width: 100%; margin-top: 6px; padding: 10px;
            border: 1px solid #aaa; border-radius: 8px; font: inherit;
        }
        .settings-card input[type="checkbox"] { width: 20px; height: 20px; vertical-align: middle; }
        .check-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 12px; }
        .settings-help { color: #555; font-size: 14px; line-height: 1.4; }
        .allergy-warning { margin-top: 10px; padding: 10px 12px; background: #fff0e8; border-radius: 10px; line-height: 1.4; }

        input,
        button {
            font-size: 16px;
        }

        .photo-choices { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .photo-choice {
            position: relative;
            display: flex; align-items: center; justify-content: center; gap: 8px;
            min-height: 56px; padding: 10px; border: 2px solid #222;
            border-radius: 12px; font-weight: 600; cursor: pointer; text-align: center;
        }
        .photo-choice:focus-within { outline: 2px solid #222; outline-offset: 3px; }
        .photo-choice input {
            position: absolute; width: 1px; height: 1px; padding: 0;
            opacity: 0; overflow: hidden; clip-path: inset(50%);
        }
        #selectedPhoto { margin: 12px 0; color: #555; overflow-wrap: anywhere; }
        .upload-card button { margin-top: 6px; }

        button {
            width: 100%;
            min-height: 48px;
            border: 0;
            border-radius: 12px;
            background: #222;
            color: white;
            font-weight: 600;
            cursor: pointer;
        }

        button:disabled {
            opacity: 0.5;
            cursor: default;
        }

        #status {
            margin-top: 16px;
            color: #555;
            line-height: 1.5;
        }

        .section {
            margin: 28px 0;
        }

        .section-title {
            font-size: 20px;
            margin: 0 0 12px 0;
        }

        .dish {
            background: white;
            padding: 16px;
            border-radius: 14px;
            margin-bottom: 12px;
        }

        .dish-header {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: flex-start;
        }

        .dish-name {
            font-size: 18px;
            font-weight: 700;
        }

        .price {
            font-weight: 700;
            white-space: nowrap;
        }

        .ingredients {
            margin-top: 8px;
            color: #555;
            line-height: 1.45;
        }

        .note {
            margin-top: 10px;
            padding: 10px 12px;
            background: #f1f1f1;
            border-radius: 10px;
            line-height: 1.4;
        }

        .ask {
            margin-top: 10px;
            padding: 10px 12px;
            background: #fff4cc;
            border-radius: 10px;
            line-height: 1.4;
        }

        .extras-box {
            background: white;
            border-radius: 14px;
            overflow: hidden;
        }

        .extra-row {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            padding: 12px 14px;
            border-bottom: 1px solid #e7e7e7;
        }

        .extra-row:last-child {
            border-bottom: none;
        }

        .extra-name {
            font-weight: 600;
        }

        .extra-meta {
            color: #666;
            font-size: 14px;
            margin-top: 3px;
            text-transform: capitalize;
        }

        .extra-price {
            font-weight: 600;
            white-space: nowrap;
        }

        .excluded-button {
            margin-top: 20px;
            background: #666;
        }

        #excluded {
            display: none;
        }

        .section-note {
            background: #eee;
            padding: 12px 14px;
            border-radius: 10px;
            color: #555;
            margin-bottom: 10px;
        }

        @media (max-width: 500px) {
            body {
                padding: 14px;
            }

            .upload-card {
                padding: 16px;
            }
        }

        /* Forest and mint palette inspired by the linked Green You concept. */
        body {
            background: radial-gradient(circle at top right, #dfeee0 0, transparent 360px), #f2f6ef;
            color: #18372b;
            font-family: "DM Sans", system-ui, sans-serif;
            max-width: 820px;
            padding-top: 24px;
        }
        .hero {
            position: relative; overflow: hidden; isolation: isolate;
            min-height: 205px; padding: 26px 30px; margin-bottom: 18px;
            background: linear-gradient(135deg, #204a37, #123126);
            color: #f9fff8; border-radius: 28px;
            box-shadow: 0 14px 32px rgba(18, 49, 38, .15);
        }
        .hero::after {
            content: ""; position: absolute; z-index: -1; right: -66px; bottom: -100px;
            width: 300px; height: 300px; border: 38px solid rgba(172, 222, 167, .16);
            border-radius: 63% 0 63% 0; transform: rotate(-27deg);
        }
        .brand { display: flex; align-items: center; gap: 11px; font-size: 15px; font-weight: 700; letter-spacing: .02em; }
        .brand-icon { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 50%; background: #d9f0d5; color: #194532; font-size: 20px; }
        .hero h1 { font: 600 clamp(30px, 6vw, 46px)/1.08 "Outfit", system-ui, sans-serif; max-width: 520px; margin: 24px 0 10px; letter-spacing: -.03em; }
        .subtitle { color: #d5e8d9; max-width: 510px; line-height: 1.5; margin: 0; }
        .upload-card, .settings-card, .dish, .extras-box {
            border: 1px solid #dfebdf; box-shadow: 0 7px 22px rgba(28, 70, 47, .055);
        }
        .upload-card, .settings-card { border-radius: 22px; }
        .upload-card { margin-bottom: 14px; }
        .upload-heading { font: 600 20px/1.2 "Outfit", system-ui, sans-serif; margin: 0 0 14px; }
        .photo-choice { border-color: #b9d5bd; background: #f6faf5; color: #204a37; border-radius: 15px; }
        .photo-choice:hover { background: #eaf5e9; border-color: #6caa76; }
        .photo-choice:focus-within { outline-color: #2e7145; }
        #selectedPhoto { color: #57705e; font-size: 13px; }
        button { background: #3c9655; border-radius: 14px; font-family: "Outfit", system-ui, sans-serif; font-size: 18px; }
        button:hover:not(:disabled) { background: #327d48; }
        #status { color: #46684f; }
        .settings-card summary { color: #28523a; }
        .settings-card h2, .section-title { font-family: "Outfit", system-ui, sans-serif; color: #183d2b; }
        .settings-card select, .settings-card textarea { border-color: #b9d5bd; background: #fbfdfa; color: #18372b; }
        .section-title { font-size: 22px; }
        .dish { border-radius: 18px; }
        .dish-name { font-family: "Outfit", system-ui, sans-serif; color: #183d2b; }
        .price { color: #348a4c; }
        .ingredients, .extra-meta { color: #5d7161; }
        .note { background: #e9f5e8; color: #225136; }
        .ask { background: #fff4d9; color: #705329; }
        .allergy-warning { background: #fff0e7; color: #78452d; }
        .excluded-button { background: #476a52; }
        .section-note { background: #e9f1e7; color: #4d6551; }
        @media (max-width: 500px) {
            body { padding: 12px; }
            .hero { padding: 22px; min-height: 205px; border-radius: 24px; }
            .photo-choices { gap: 8px; }
            .photo-choice { padding: 8px; font-size: 14px; }
        }
    </style>
</head>

<body>

<header class="hero">
    <div class="brand"><span class="brand-icon" aria-hidden="true">🌿</span> Menu Reader</div>
    <h1>Find a better bite.</h1>
    <div class="subtitle">Scan a restaurant menu to discover plant-friendly choices, with your preferences in mind.</div>
</header>

<div class="upload-card">
    <h2 class="upload-heading">Start with a menu</h2>
    <div class="photo-choices">
        <label class="photo-choice">
            <input id="cameraPhoto" type="file" accept="image/*" capture="environment">
            <span aria-hidden="true">📷</span> Take photo
        </label>
        <label class="photo-choice">
            <input id="uploadPhoto" type="file" accept="image/jpeg,image/png,image/webp,image/gif,application/pdf,.pdf">
            <span aria-hidden="true">🖼️</span> Photo or PDF
        </label>
    </div>
    <div id="selectedPhoto" aria-live="polite">No menu selected · PDF, JPG, PNG, WebP, or GIF · up to 20 MB</div>

    <button id="analyzeButton">
        Is this good for the world?
    </button>

    <div id="status"></div>
</div>

<details class="settings-card">
    <summary>Preferences (saved automatically)</summary>
    <h2>Your preferences</h2>
    <label for="diet">Diet
        <select id="diet">
            <option value="flexitarian">Flexitarian</option>
            <option value="vegetarian">Vegetarian</option>
            <option value="vegan">Vegan</option>
        </select>
    </label>
    <label><input id="plantFirst" type="checkbox" checked> Prefer plant-based first</label>
    <label><input id="hideMeat" type="checkbox" checked> Hide meat dishes</label>
    <h2>Allergies and ingredients to avoid</h2>
    <div id="allergenChoices" class="check-grid"></div>
    <label for="avoidWords">Other ingredients to avoid (comma or line separated)
        <textarea id="avoidWords" rows="2" placeholder="e.g. cilantro, mushroom"></textarea>
    </label>
    <div class="settings-help">Warnings use only the menu text we can read. Ingredients may be missing, and preparation or cross-contact cannot be checked here. Confirm all allergy concerns with the restaurant.</div>
</details>

<div id="results"></div>


<script>

const cameraInput = document.getElementById("cameraPhoto");
const uploadInput = document.getElementById("uploadPhoto");
const selectedPhoto = document.getElementById("selectedPhoto");
let selectedFile = null;
const analyzeButton = document.getElementById("analyzeButton");
const status = document.getElementById("status");
const results = document.getElementById("results");
const dietInput = document.getElementById("diet");
const plantFirstInput = document.getElementById("plantFirst");
const hideMeatInput = document.getElementById("hideMeat");
const avoidWordsInput = document.getElementById("avoidWords");
const allergenChoices = document.getElementById("allergenChoices");
const STORAGE_KEY = "menu-reader-preferences-v1";
const ALLERGENS = ["dairy", "egg", "peanut", "tree nut", "soy", "gluten", "sesame", "fish", "shellfish"];
const ALLERGEN_TERMS = {
    dairy: ["milk", "cheese", "butter", "cream", "yogurt", "yoghurt", "whey", "casein", "ghee", "feta", "mozzarella", "parmesan", "cheddar", "ricotta", "hollandaise"],
    egg: ["egg", "eggs", "omelette", "omelet", "mayonnaise", "mayo", "aioli", "hollandaise"],
    peanut: ["peanut", "peanuts", "groundnut", "groundnuts"],
    "tree nut": ["almond", "almonds", "walnut", "walnuts", "pecan", "pecans", "cashew", "cashews", "pistachio", "pistachios", "hazelnut", "hazelnuts", "macadamia", "brazil nut", "pine nut", "pinenut", "nut butter"],
    soy: ["soy", "soya", "tofu", "tempeh", "miso", "edamame", "tamari"],
    gluten: ["wheat", "flour", "bread", "toast", "bun", "pasta", "noodle", "couscous", "barley", "rye", "semolina", "seitan", "panko", "breading", "breadcrumb", "muffin", "waffle", "pancake"],
    sesame: ["sesame", "tahini"],
    fish: ["fish", "anchovy", "anchovies", "salmon", "tuna", "cod", "trout", "sardine", "sardines", "fish sauce", "worcestershire"],
    shellfish: ["shrimp", "prawn", "crab", "lobster", "crayfish", "clam", "mussel", "oyster", "scallop", "shellfish"]
};
let menuItems = null;

allergenChoices.innerHTML = ALLERGENS.map((name, index) =>
    `<label><input type="checkbox" value="${name}" id="allergen-${index}"> ${name[0].toUpperCase() + name.slice(1)}</label>`
).join("");

function loadPreferences() {
    try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
        if (["flexitarian", "vegetarian", "vegan"].includes(saved.diet)) dietInput.value = saved.diet;
        if (typeof saved.plantFirst === "boolean") plantFirstInput.checked = saved.plantFirst;
        if (typeof saved.hideMeat === "boolean") hideMeatInput.checked = saved.hideMeat;
        if (typeof saved.avoidWords === "string") avoidWordsInput.value = saved.avoidWords;
        if (Array.isArray(saved.allergens)) {
            allergenChoices.querySelectorAll("input").forEach(input => {
                input.checked = saved.allergens.includes(input.value);
            });
        }
    } catch { /* Private browsing can disable storage. */ }
}

function preferences() {
    return {
        diet: dietInput.value,
        plantFirst: plantFirstInput.checked,
        hideMeat: hideMeatInput.checked,
        allergens: Array.from(allergenChoices.querySelectorAll("input:checked"), input => input.value),
        avoidWords: avoidWordsInput.value
    };
}

function updatePreferences() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences())); } catch {}
    if (menuItems) renderMenu(menuItems);
}

loadPreferences();
document.querySelectorAll(".settings-card input, .settings-card select, .settings-card textarea")
    .forEach(input => input.addEventListener("input", updatePreferences));

analyzeButton.addEventListener("click", analyze);
for (const input of [cameraInput, uploadInput]) {
    input.addEventListener("change", () => {
        if (!input.files.length) return;
        selectedFile = input.files[0];
        (input === cameraInput ? uploadInput : cameraInput).value = "";
        selectedPhoto.textContent = `Selected: ${selectedFile.name || "menu file"}`;
        status.textContent = "";
        menuItems = null;
        results.innerHTML = "";
    });
}


async function analyze() {
    const file = selectedFile;

    if (!file) {
        status.textContent = "Take a photo or choose a menu file first.";
        return;
    }

    if (file.size > 20 * 1024 * 1024) {
        status.textContent = "That file is over 20 MB. Choose a smaller menu file.";
        return;
    }

    analyzeButton.disabled = true;
    analyzeButton.textContent = "Reading menu…";
    status.textContent = "Looking for plant-friendly options…";
    results.innerHTML = "";

    const form = new FormData();
    form.append("photo", file);

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            body: form
        });

        const text = await response.text();

        let data;

        try {
            data = JSON.parse(text);
        } catch {
            throw new Error(text || "The server returned an invalid response.");
        }

        if (!response.ok) {
            throw new Error(
                data.detail ||
                data.error ||
                "The menu could not be analyzed."
            );
        }

        if (!Array.isArray(data.items)) throw new Error("The menu response was incomplete.");
        menuItems = data.items;
        renderMenu(menuItems);

        const dishes = data.items.filter(
            item => item.item_type === "dish"
        );

        status.textContent = `Found ${dishes.length} dishes.`;

    } catch (error) {
        status.textContent = "Error: " + error.message;

    } finally {
        analyzeButton.disabled = false;
        analyzeButton.textContent = "Is this good for the world?";
    }
}


function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatPrice(price) {
    if (!price) {
        return "";
    }

    const cleaned = String(price).replace(/^\\$/, "");
    return "$" + escapeHtml(cleaned);
}

function normalizedWords(value) {
    return " " + String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim() + " ";
}

function containsTerm(text, term) {
    return text.includes(normalizedWords(term));
}

function warningsFor(item) {
    const chosen = preferences();
    const visibleText = normalizedWords([item.name, ...(Array.isArray(item.ingredients) ? item.ingredients : [])].join(" "));
    const warnings = [];
    for (const allergen of chosen.allergens) {
        if ((ALLERGEN_TERMS[allergen] || []).some(term => containsTerm(visibleText, term))) {
            warnings.push(`Possible ${allergen} ingredient in menu text — confirm ingredients and preparation with the restaurant.`);
        }
    }
    const customTerms = [...new Set(chosen.avoidWords.split(/[,\\n]+/).map(s => s.trim()).filter(Boolean))];
    for (const term of customTerms) {
        if (containsTerm(visibleText, term)) {
            warnings.push(`Possible match for “${term}” — confirm with the restaurant.`);
        }
    }
    return warnings;
}

function renderWarnings(item) {
    return warningsFor(item).map(warning =>
        `<div class="allergy-warning">⚠️ ${escapeHtml(warning)}</div>`
    ).join("");
}


function renderDish(item) {
    const ingredients =
        item.ingredients && item.ingredients.length
            ? item.ingredients.map(escapeHtml).join(", ")
            : "No ingredients listed";

    const price = formatPrice(item.price);

    let extra = "";

    if (item.modification) {
        extra += `
            <div class="note">
                🔧 <strong>Modification:</strong>
                ${escapeHtml(item.modification)}
            </div>
        `;
    }

    if (item.ask) {
        extra += `
            <div class="ask">
                💬 <strong>Ask:</strong>
                ${escapeHtml(item.ask)}
            </div>
        `;
    }

    return `
        <div class="dish">
            <div class="dish-header">
                <div class="dish-name">
                    ${escapeHtml(item.name)}
                </div>

                <div class="price">
                    ${price}
                </div>
            </div>

            <div class="ingredients">
                ${ingredients}
            </div>
            <div class="extra-meta">${escapeHtml(String(item.classification || "unknown").replaceAll("_", " "))}</div>

            ${renderWarnings(item)}
            ${extra}
        </div>
    `;
}


function renderSection(title, items) {
    if (!items.length) {
        return "";
    }

    return `
        <section class="section">
            <h2 class="section-title">${title}</h2>
            ${items.map(renderDish).join("")}
        </section>
    `;
}


function renderExtras(title, items) {
    if (!items.length) {
        return "";
    }

    return `
        <section class="section">
            <h2 class="section-title">${title}</h2>

            <div class="extras-box">
                ${items.map(item => `
                    <div class="extra-row">
                        <div>
                            <div class="extra-name">
                                ${escapeHtml(item.name)}
                            </div>

                            <div class="extra-meta">
                                ${escapeHtml(
                                    item.item_type.replaceAll("_", " ")
                                )}
                            </div>
                            ${renderWarnings(item)}
                        </div>

                        <div class="extra-price">
                            ${formatPrice(item.price)}
                        </div>
                    </div>
                `).join("")}
            </div>
        </section>
    `;
}


function renderNotes(items) {
    if (!items.length) {
        return "";
    }

    return `
        <section class="section">
            <h2 class="section-title">Menu notes</h2>

            ${items.map(item => `
                <div class="section-note">
                    ${escapeHtml(item.name)}
                </div>
            `).join("")}
        </section>
    `;
}


function renderMenu(items) {
    const chosen = preferences();
    const dishes = items.filter(item => item.item_type === "dish");
    const visible = [];
    const excluded = [];
    for (const item of dishes) {
        const kind = item.classification;
        const meat = kind === "not_vegetarian";
        const outsideDiet = chosen.diet === "vegan"
            ? kind === "vegetarian" || meat
            : chosen.diet === "vegetarian" && meat;
        if (outsideDiet || (chosen.hideMeat && meat)) excluded.push(item);
        else visible.push(item);
    }

    // Keep the menu's order unless the user asks for plants first.
    if (chosen.plantFirst) {
        const rank = {vegan: 0, vegetarian: 1, possibly_vegetarian: 2, unknown: 3, not_vegetarian: 4};
        visible.sort((a, b) => (rank[a.classification] ?? 3) - (rank[b.classification] ?? 3));
    }

    const extras = items.filter(
        item =>
            item.item_type === "side" ||
            item.item_type === "add_on" ||
            item.item_type === "substitution"
    );

    const sectionNotes = items.filter(
        item => item.item_type === "section_note"
    );

    let html = "";

    if (chosen.allergens.length || chosen.avoidWords.trim()) {
        html += `<div class="allergy-warning">⚠️ Menu text and AI extraction cannot establish allergen safety. Confirm ingredients, substitutions, and cross-contact with the restaurant before ordering.</div>`;
    }
    const uncertain = visible.filter(item => ["possibly_vegetarian", "unknown"].includes(item.classification));
    const listed = visible.filter(item => !["possibly_vegetarian", "unknown"].includes(item.classification));
    html += renderSection("Menu dishes", listed);
    html += renderSection("Needs dietary confirmation", uncertain);
    if (!visible.length) {
        html += `<div class="section-note">No dishes match these display settings. You can view excluded dishes below.</div>`;
    }

    html += renderExtras(
        "Options & substitutions",
        extras
    );

    html += renderNotes(sectionNotes);

    if (excluded.length) {
        html += `
            <button
                type="button"
                class="excluded-button"
                id="excludedButton"
            >
                Show ${excluded.length} excluded dishes
            </button>

            <div id="excluded">
                ${renderSection(
                    "Excluded by your settings",
                    excluded
                )}
            </div>
        `;
    }

    results.innerHTML = html;

    const excludedButton =
        document.getElementById("excludedButton");

    if (excludedButton) {
        excludedButton.addEventListener(
            "click",
            function () {
                const excludedArea =
                    document.getElementById("excluded");

                const isVisible =
                    excludedArea.style.display === "block";

                excludedArea.style.display =
                    isVisible ? "none" : "block";

                excludedButton.textContent =
                    isVisible
                        ? `Show ${excluded.length} excluded dishes`
                        : "Hide excluded dishes";
            }
        );
    }
}

</script>

</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE


@app.post("/analyze")
async def analyze(photo: UploadFile = File(...)):
    try:
        image_bytes = await photo.read(MAX_UPLOAD_BYTES + 1)
        if not image_bytes or len(image_bytes) > MAX_UPLOAD_BYTES:
            return JSONResponse(
                status_code=400,
                content={"error": "Choose a nonempty menu file under 20 MB."},
            )
        try:
            input_part = menu_input_part(image_bytes)
        except ValueError as error:
            return JSONResponse(status_code=400, content={"error": str(error)})

        response = client.responses.create(
            model="gpt-5.6-luna",

            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": """
Read this restaurant menu and extract all food entries you can clearly identify.

The goal is to help someone who prefers plant-based food find useful options quickly.

For every entry, determine both:
1. item_type
2. dietary classification


ITEM TYPE

item_type must be exactly one of:

- dish
- side
- add_on
- substitution
- section_note

Use "dish" only for something a customer could reasonably order as a complete menu item.

Examples:

"Mushroom Omelette"
= dish

"Egg whites +$2"
= substitution

"Gluten-free bread +$2.95"
= substitution

"Add bacon +$3"
= add_on

"Home fries"
= side

A menu instruction or general statement that is not something the customer orders should be:
section_note


DIETARY CLASSIFICATION

classification must be exactly one of:

- vegan
- vegetarian
- possibly_vegetarian
- not_vegetarian
- unknown


RULES

- Use ingredients and descriptions visible on the menu.
- Do not invent ingredients or prices.
- Do not assume cooking methods, cross-contact, shared cooking surfaces,
  butter, or hidden ingredients unless there is a specific reason from
  the dish itself.
- Do not treat ordinary uncertainty as a warning.

If a dish is commonly made with a hidden animal ingredient that could
materially change its classification, put one short and specific
question in "ask".

Examples:

Pad Thai:
"Does the sauce contain fish sauce?"

Refried beans:
"Are the beans made with lard?"

Caesar dressing:
"Does the dressing contain anchovy?"

Do not add generic warnings such as:
"confirm preparation ingredients"
or
"check how it is cooked".


MODIFICATIONS

- Set can_modify to true only when a simple removal or substitution
  would reasonably preserve the dish.

- Do not mark a meat dish as modifiable merely because the meat could
  theoretically be removed.

- For combination meals built around meat, classify them as
  not_vegetarian and set can_modify to false unless the menu explicitly
  offers a relevant substitution.

- If a genuinely useful simple modification exists, describe it briefly.


MENU CONTEXT

Include obvious base ingredients when clearly established by the menu section.

For example, an item under a section explicitly labelled
"Three Egg Omelettes" contains eggs even if the individual description
does not repeat the word "eggs".


PRICE

Return the price as text without adding a currency symbol if possible.

Examples:

"12.95"
"3.00"

If a price cannot be read:
return null.


FIELDS

For every entry return:

name
price
item_type
classification
ingredients
can_modify
modification
ask

If there is no useful modification:
return null.

If there is no specific question worth asking:
return null.

The JSON schema determines the response format.
"""
                        },

                        input_part
                    ]
                }
            ],

            text={
                "format": {
                    "type": "json_schema",
                    "name": "menu_analysis",
                    "strict": True,

                    "schema": {
                        "type": "object",

                        "properties": {
                            "items": {
                                "type": "array",

                                "items": {
                                    "type": "object",

                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        },

                                        "price": {
                                            "type": [
                                                "string",
                                                "null"
                                            ]
                                        },

                                        "item_type": {
                                            "type": "string",
                                            "enum": [
                                                "dish",
                                                "side",
                                                "add_on",
                                                "substitution",
                                                "section_note"
                                            ]
                                        },

                                        "classification": {
                                            "type": "string",
                                            "enum": [
                                                "vegan",
                                                "vegetarian",
                                                "possibly_vegetarian",
                                                "not_vegetarian",
                                                "unknown"
                                            ]
                                        },

                                        "ingredients": {
                                            "type": "array",
                                            "items": {
                                                "type": "string"
                                            }
                                        },

                                        "can_modify": {
                                            "type": "boolean"
                                        },

                                        "modification": {
                                            "type": [
                                                "string",
                                                "null"
                                            ]
                                        },

                                        "ask": {
                                            "type": [
                                                "string",
                                                "null"
                                            ]
                                        }
                                    },

                                    "required": [
                                        "name",
                                        "price",
                                        "item_type",
                                        "classification",
                                        "ingredients",
                                        "can_modify",
                                        "modification",
                                        "ask"
                                    ],

                                    "additionalProperties": False
                                }
                            }
                        },

                        "required": [
                            "items"
                        ],

                        "additionalProperties": False
                    }
                }
            }
        )

        result = json.loads(
            response.output_text
        )

        return result

    except Exception as error:
        print(
            "MENU ANALYSIS ERROR:",
            repr(error)
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": str(error)
            }
        )

