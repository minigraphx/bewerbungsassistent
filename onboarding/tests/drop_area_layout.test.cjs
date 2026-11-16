// The rows of the drop area on „Meine Angaben“ (G84, #270), laid out by a real browser: the generated page of the app
// with its own styles and fonts, the card drawn by prefillCard. Invented file names only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { pathToFileURL } = require("node:url");

const ROOT = path.join(__dirname, "..", "..");
const PAGE = path.join(ROOT, "bewerbungen", "seiten", "angaben.html");
const FONTS = path.join(ROOT, "lebenslauf", "fonts");
const SCRIPTS = ["bewerbungen/seiten/dateien-logik.js", ...["validate.js", "model.js", "dom.js", "documents.js", "uploads.js",
  "kindguess.js", "droparea.js", "prefill.js"].map((name) => `onboarding/src/${name}`)];
const CHROMES = [process.env.CHROME_PATH, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"];
const CHROME = CHROMES.find((candidate) => candidate && fs.existsSync(candidate));
const SKIP = CHROME ? false : "no Chrome or Chromium on this computer";
const ARROW_PX = 20; // the arrow of a closed select
const UPLOADS = [
  ["lebenslauf-bisher", "Lebenslauf_Muster.pdf"], ["zeugnisse", "Schnupperlehre_Bericht_Muster.pdf"],
  ["zertifikate", "Multicheck.png"], ["anschreiben-bisher", "Motivationsschreiben_Muster.pdf"],
].map(([category, name]) => ({ category, name, size: 120000, datei: `dokumente/${category}/${name}` }));

// Runs in the page: one card per form of address, then what the rows measure, written into the page for --dump-dom.
const MEASURE = `
(async () => {
  const form = FORM;
  const main = document.getElementById("main");
  main.textContent = "";
  for (const track of ["job", "apprenticeship"]) {
    const start = el("section", { className: "start start--app" }, [prefillCard({
      form, track, uploads: UPLOADS, messages: [], notes: {}, announcement: "", hasName: true,
      run: { running: false, waiting: false, problem: null, report: null }, titleOf: (id) => id,
      onRun() {}, onGoTo() {}, onAddFiles() {}, onChangeKind() {}, onRemove() {}, onByHand() {},
    })]);
    start.dataset.track = track;
    main.append(start);
  }
  await document.fonts.ready;
  const canvas = document.createElement("canvas").getContext("2d");
  const box = (node) => node.getBoundingClientRect();
  const cards = [...document.querySelectorAll("[data-track]")].map((start) => ({
    track: start.dataset.track,
    rows: [...start.querySelectorAll(".drop-file")].map((row) => {
      const select = row.querySelector("select");
      const style = getComputedStyle(select);
      canvas.font = style.font;
      const longest = Math.max(...[...select.options].map((o) => canvas.measureText(o.textContent).width));
      const [info, actions] = [box(row.querySelector(".drop-file__info")), box(row.querySelector(".drop-file__actions"))];
      return { name: row.querySelector(".drop-file__name").textContent, infoTop: info.top, infoBottom: info.bottom,
        actionsTop: actions.top, actionsRight: actions.right, rowRight: box(row).right, selectLeft: box(select).left,
        selectWidth: select.clientWidth, removeCut: row.querySelector(".remove").scrollWidth > row.querySelector(".remove").clientWidth,
        needed: longest + parseFloat(style.paddingLeft) + parseFloat(style.paddingRight) + ${ARROW_PX} };
    }),
  }));
  const measured = JSON.stringify({ cards, pageWidth: document.documentElement.scrollWidth, fonts: document.fonts.check("16px 'DM Sans'") });
  if (parent !== window) return parent.postMessage(measured, "*");
  const out = document.createElement("pre");
  out.id = "measured";
  out.textContent = measured;
  document.body.append(out);
})();`;
// Headless Chrome keeps its window at least 500 px wide: a narrower page is laid out in a frame of that width.
const NARROW_FRAME = (width) => `<!doctype html><body style="margin:0">
  <iframe src="angaben.html" style="border:0;width:${width}px;height:900px"></iframe>
  <script>addEventListener("message", (e) => { const out = document.createElement("pre"); out.id = "measured";
    out.textContent = e.data; document.body.append(out); });</script></body>`;
const MIN_WINDOW_PX = 500;

function measure(width) {
  const html = fs.readFileSync(PAGE, "utf8")
    .replace(/<meta http-equiv="Content-Security-Policy"[^>]*>/, "")
    .replace(/<script\b[\s\S]*?<\/script>/g, "")
    .replace(/url\("\/fonts\//g, `url("${pathToFileURL(FONTS).href}/`)
    .replace("</body>", () => `<script>${SCRIPTS.map((name) => fs.readFileSync(path.join(ROOT, name), "utf8")).join("\n;\n")}
      const FORM = ${fs.readFileSync(path.join(ROOT, "onboarding", "form.json"), "utf8")};
      const UPLOADS = ${JSON.stringify(UPLOADS)};
      ${MEASURE}</script></body>`);
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), "drop-area-layout-"));
  try {
    fs.writeFileSync(path.join(folder, "angaben.html"), html);
    const narrow = width < MIN_WINDOW_PX;
    const file = path.join(folder, narrow ? "frame.html" : "angaben.html");
    if (narrow) fs.writeFileSync(file, NARROW_FRAME(width));
    const run = spawnSync(CHROME, ["--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
      `--user-data-dir=${path.join(folder, "profile")}`, "--allow-file-access-from-files",
      `--window-size=${Math.max(width, MIN_WINDOW_PX)},900`, "--virtual-time-budget=5000", "--dump-dom", pathToFileURL(file).href],
    { encoding: "utf8", timeout: 60000 });
    const found = /<pre id="measured">([\s\S]*?)<\/pre>/.exec(run.stdout || "");
    assert.ok(found, `the page measured nothing: ${run.stderr}`);
    return JSON.parse(found[1].replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&"));
  } finally {
    fs.rmSync(folder, { recursive: true, force: true });
  }
}

test("at 1280 px every row keeps its kind and „Entfernen“ beside the name, in Sie and du, the selects aligned", { skip: SKIP }, () => {
  const { cards, pageWidth, fonts } = measure(1280);
  assert.ok(fonts, "DM Sans is loaded, as in the app");
  assert.ok(pageWidth <= 1280, `no horizontal scroll (${pageWidth} px)`);
  for (const { track, rows } of cards) {
    assert.equal(rows.length, UPLOADS.length, track);
    for (const row of rows) {
      assert.ok(row.actionsTop < row.infoBottom, `${track}: the select of ${row.name} is on the line of its name`);
      assert.equal(row.removeCut, false, `${track}: „Entfernen“ of ${row.name} is whole`);
      assert.ok(row.needed <= row.selectWidth, `${track}: every kind fits the select (${row.needed} > ${row.selectWidth})`);
      assert.ok(row.actionsRight <= row.rowRight + 0.5, `${track}: ${row.name} stays in the card`);
    }
    assert.equal(new Set(rows.map((r) => `${r.selectLeft}/${r.selectWidth}`)).size, 1, `${track}: the selects line up`);
  }
});

test("at 375 px the kind goes below the name, whole, and nothing scrolls sideways", { skip: SKIP }, () => {
  const { cards, pageWidth } = measure(375);
  assert.ok(pageWidth <= 375, `no horizontal scroll (${pageWidth} px)`);
  for (const { track, rows } of cards) {
    for (const row of rows) {
      assert.ok(row.actionsTop >= row.infoBottom - 0.5, `${track}: the select of ${row.name} is below its name`);
      assert.equal(row.removeCut, false, `${track}: „Entfernen“ of ${row.name} is whole`);
      assert.ok(row.needed <= row.selectWidth, `${track}: every kind fits the select (${row.needed} > ${row.selectWidth})`);
      assert.ok(row.actionsRight <= row.rowRight + 0.5, `${track}: ${row.name} stays in the card`);
    }
  }
});
