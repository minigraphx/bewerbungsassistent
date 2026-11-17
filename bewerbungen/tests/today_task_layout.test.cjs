// The rows under „Danach“ on Heute (#352), laid out by a real browser: uebersicht.html with its own styles and fonts,
// each row built like auchZeile in uebersicht.js, its title and line from uebersicht-logik.js and texte.js.
// On a narrow screen the button goes below the text, so the text keeps the width of the row.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { pathToFileURL } = require("node:url");

const SEITEN = path.join(__dirname, "..", "seiten");
const FONTS = path.join(__dirname, "..", "..", "lebenslauf", "fonts");
const PAGE = path.join(SEITEN, "uebersicht.html");
const STYLES = ["stil.css", "heute.css"];
const SCRIPTS = ["texte.js", "dot-line.js", "uebersicht-logik.js"];
const CHROMES = [process.env.CHROME_PATH, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"];
const CHROME = CHROMES.find((candidate) => candidate && fs.existsSync(candidate));
const SKIP = CHROME ? false : "no Chrome or Chromium on this computer";
// Headless Chrome keeps its window at least 500 px wide: a narrower page is laid out in a frame of that width.
const MIN_WINDOW_PX = 500;
const NARROW_WIDTHS = [320, 375, 480];
const WIDE_WIDTH = 1280;
const SUB_PIXEL = 0.5;

// Runs in the page: one row per kind of task on Heute, then what each row measures, posted or written into the page.
const MEASURE = `
(async () => {
  const t = (key, values) => Texte.text(key, "stelle-sie", values);
  const el = (tag, attributes, ...children) => {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes || {})) node.setAttribute(name, value);
    for (const child of children.flat()) if (child !== null && child !== undefined) node.append(child);
    return node;
  };
  const title = (art, count = 1, extra = {}) => UebersichtLogik.schrittText({ art, ...extra }, count, t).titel;
  const row = (heading, under, button) => el("li", { class: "today__task" },
    el("span", { class: "today__task-text" }, el("strong", {}, heading),
      under.length ? el("span", { class: "today__meta" }, DotLine.render(under, el)) : null),
    el("button", { type: "button", class: "btn" }, button));
  const rows = [
    row(title("entscheiden", 5), [t("heute.durchgang.anzahl", { anzahl: 5 }), t("heute.durchgang.unter")], "Durchgang beginnen"),
    row(title("abschicken", 3), ["Muster AG, Beispiel GmbH, Probe SA"], "Formulare öffnen"),
    row(title("abschicken"), ["Projektleiterin Muster, Muster AG", "Frist 30.11.2026"], "Formular öffnen"),
    row(title("rav", 2), ["Muster AG, Beispiel GmbH"], "Jetzt eintragen"),
    row(title("freigeben"), ["Sachbearbeiter Beispiel, Beispiel GmbH", "Entwurf ist fertig"], "Anschreiben lesen"),
    row(title("link"), ["Fachfrau Probe, Probe SA", "dann füllt die Erweiterung es aus"], "Link eintragen"),
    row(title("gespraech"), ["Mitarbeiter Muster, Muster AG"], "Termin eintragen"),
    row(title("warten", 1, { zusatz: "2026-12-01" }), ["Assistentin Beispiel, Beispiel GmbH"], "Bewerbung öffnen"),
    row("7 neue Treffer ansehen", ["Suche vom 16.11.2026"], "Treffer ansehen"),
  ];
  document.getElementById("steht-an").hidden = false;
  document.getElementById("auch").hidden = false;
  document.getElementById("auch-liste").replaceChildren(...rows);
  await document.fonts.ready;
  const box = (node) => node.getBoundingClientRect();
  const lines = (node) => Math.round(box(node).height / parseFloat(getComputedStyle(node).lineHeight));
  const measured = JSON.stringify({
    pageWidth: document.documentElement.scrollWidth,
    fonts: document.fonts.check("16px 'DM Sans'"),
    rows: [...document.querySelectorAll(".today__task")].map((task) => {
      const [text, button, heading] = [task.querySelector(".today__task-text"), task.querySelector(".btn"), task.querySelector("strong")];
      const style = getComputedStyle(task);
      return { title: heading.textContent, rowLeft: box(task).left + parseFloat(style.paddingLeft),
        rowRight: box(task).right - parseFloat(style.paddingRight), textLeft: box(text).left, textRight: box(text).right,
        textTop: box(text).top, textBottom: box(text).bottom, buttonTop: box(button).top, buttonLeft: box(button).left,
        buttonRight: box(button).right, titleLines: lines(heading) };
    }),
  });
  if (parent !== window) return parent.postMessage(measured, "*");
  const out = document.createElement("pre");
  out.id = "measured";
  out.textContent = measured;
  document.body.append(out);
})();`;

const NARROW_FRAME = (width) => `<!doctype html><body style="margin:0">
  <iframe src="uebersicht.html" style="border:0;width:${width}px;height:1400px"></iframe>
  <script>addEventListener("message", (e) => { const out = document.createElement("pre"); out.id = "measured";
    out.textContent = e.data; document.body.append(out); });</script></body>`;

const read = (name) => fs.readFileSync(path.join(SEITEN, name), "utf8");

/** uebersicht.html as one file: its styles inline with the fonts on disk, no page scripts, the measuring script last. */
function pageHtml() {
  const styles = STYLES.map(read).join("\n").replace(/url\("\/fonts\//g, `url("${pathToFileURL(FONTS).href}/`);
  return read("uebersicht.html")
    .replace(/<link rel="stylesheet"[^>]*>\s*/g, "")
    .replace("</head>", () => `<style>${styles}</style></head>`)
    .replace(/<script\b[\s\S]*?<\/script>/g, "")
    .replace("</body>", () => `<script>${SCRIPTS.map(read).join("\n;\n")}\n${MEASURE}</script></body>`);
}

function measure(width) {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), "today-task-layout-"));
  try {
    fs.writeFileSync(path.join(folder, "uebersicht.html"), pageHtml());
    const narrow = width < MIN_WINDOW_PX;
    const file = path.join(folder, narrow ? "frame.html" : "uebersicht.html");
    if (narrow) fs.writeFileSync(file, NARROW_FRAME(width));
    const run = spawnSync(CHROME, ["--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
      `--user-data-dir=${path.join(folder, "profile")}`, "--allow-file-access-from-files",
      `--window-size=${Math.max(width, MIN_WINDOW_PX)},1400`, "--virtual-time-budget=5000", "--dump-dom", pathToFileURL(file).href],
    { encoding: "utf8", timeout: 60000 });
    const found = /<pre id="measured">([\s\S]*?)<\/pre>/.exec(run.stdout || "");
    assert.ok(found, `the page measured nothing: ${run.stderr}`);
    return JSON.parse(found[1].replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&"));
  } finally {
    fs.rmSync(folder, { recursive: true, force: true });
  }
}

test("the rows measured here are built like auchZeile in uebersicht.js", () => {
  const source = read("uebersicht.js");
  assert.ok(source.includes('el("li", { class: "today__task" },'), "a task is an li.today__task");
  assert.ok(source.includes('el("span", { class: "today__task-text" }, el("strong", {}, titel),'), "its text is a span with a strong title");
  assert.ok(source.includes('el("span", { class: "today__meta" }, dotLine(unter))'), "the line under it is a «·» line");
  assert.ok(source.includes('const klasse = danach ? "btn" : "btn btn--primary";'), "the button of a task is a plain .btn");
});

for (const width of NARROW_WIDTHS) {
  test(`at ${width} px every task puts its button below its text, and the text keeps the row's width`, { skip: SKIP }, () => {
    const { rows, pageWidth, fonts } = measure(width);
    assert.ok(fonts, "DM Sans is loaded, as in the app");
    assert.ok(pageWidth <= width, `no horizontal scroll (${pageWidth} px)`);
    assert.equal(rows.length, 9, "one row per kind of task");
    for (const row of rows) {
      assert.ok(row.buttonTop >= row.textBottom - SUB_PIXEL, `«${row.title}»: the button is below the text`);
      assert.ok(row.textRight >= row.rowRight - SUB_PIXEL, `«${row.title}»: the text reaches the right edge (${row.textRight} < ${row.rowRight})`);
      assert.ok(Math.abs(row.buttonLeft - row.rowLeft) <= SUB_PIXEL, `«${row.title}»: the button starts at the left edge`);
      assert.ok(row.buttonRight <= row.rowRight + SUB_PIXEL, `«${row.title}»: the button stays in the row`);
    }
    const pass = rows[0];
    assert.ok(pass.titleLines <= 2, `«${pass.title}» takes at most two lines (${pass.titleLines})`);
  });
}

test(`at ${WIDE_WIDTH} px every task keeps its button beside its text, on the right`, { skip: SKIP }, () => {
  const { rows, pageWidth } = measure(WIDE_WIDTH);
  assert.ok(pageWidth <= WIDE_WIDTH, `no horizontal scroll (${pageWidth} px)`);
  for (const row of rows) {
    assert.ok(row.buttonTop < row.textBottom, `«${row.title}»: the button is on the line of the text`);
    assert.ok(row.buttonLeft >= row.textRight, `«${row.title}»: the button is right of the text`);
    assert.ok(Math.abs(row.buttonRight - row.rowRight) <= SUB_PIXEL, `«${row.title}»: the button sits at the right edge`);
  }
});
