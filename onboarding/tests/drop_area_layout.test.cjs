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
const SCRIPTS = ["bewerbungen/seiten/dateien-logik.js", "bewerbungen/seiten/treffer-logik.js", "bewerbungen/seiten/texte.js",
  ...["words.js", "validate.js", "model.js", "dom.js", "documents.js", "uploads.js", "kindguess.js", "droparea.js", "prefill.js"]
    .map((name) => `onboarding/src/${name}`)];
// The line under „Vorbefüllen“ (G85, #271) at its longest: credit used up with the link, and a file left out.
const ESTIMATES = {
  job: { anzahl: 3, kosten: 0.07, dauer_minuten: 2, waehrung: "CHF", guthaben: 0, danach: 0, gekuerzt: ["Lebenslauf_Muster.pdf"],
    nicht_gelesen: [{ name: "Multicheck.png", grund: "Bild: Darin lässt sich nichts unkenntlich machen, darum geht es nicht an die KI. Angaben von Hand ergänzen." }] },
  apprenticeship: { anzahl: 3, kosten: 0.07, dauer_minuten: 2, waehrung: "CHF", guthaben: 4.25, danach: 4.18, gekuerzt: [], nicht_gelesen: [] },
};
const MIN_TARGET_PX = 44;
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
      run: { running: false, problem: null, report: null }, titleOf: (id) => id,
      estimate: { phase: "ready", answer: ESTIMATES[track], problem: null },
      onRun() {}, onGoTo() {}, onAddFiles() {}, onChangeKind() {}, onRemove() {}, onByHand() {}, onEstimate() {},
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
    run: (() => {
      const [button, line] = [box(start.querySelector("#prefill")), box(start.querySelector("#prefill-status"))];
      return { buttonBottom: button.bottom, buttonLeft: button.left, lineTop: line.top, lineLeft: line.left,
        controls: [...start.querySelectorAll(".prefill-card__run :is(button, a)")]
          .map((c) => ({ name: c.textContent, width: box(c).width, height: box(c).height })) };
    })(),
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
      const ESTIMATES = ${JSON.stringify(ESTIMATES)};
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

function targetsAreLargeEnough(cards) {
  for (const { track, run } of cards) {
    assert.ok(run.controls.some((c) => c.name.startsWith("anfordern")) || track !== "job", `${track}: the link to a new code is there`);
    for (const control of run.controls) {
      assert.ok(control.width >= MIN_TARGET_PX && control.height >= MIN_TARGET_PX,
        `${track}: „${control.name}“ is at least 44×44 px (${control.width}×${control.height})`);
    }
  }
}

test("at 1280 px the cost line sits right under „Vorbefüllen“, and every control there is 44 px", { skip: SKIP }, () => {
  const { cards } = measure(1280);
  for (const { track, run } of cards) {
    assert.ok(run.lineTop >= run.buttonBottom, `${track}: the line is below the button`);
    assert.ok(run.lineTop - run.buttonBottom <= 24, `${track}: right below it (${run.lineTop - run.buttonBottom} px)`);
    assert.ok(Math.abs(run.lineLeft - run.buttonLeft) <= 1, `${track}: aligned with the button`);
  }
  targetsAreLargeEnough(cards);
});

test("at 375 px the cost line and its controls fit without sideways scroll", { skip: SKIP }, () => {
  const { cards, pageWidth } = measure(375);
  assert.ok(pageWidth <= 375, `no horizontal scroll (${pageWidth} px)`);
  targetsAreLargeEnough(cards);
});
