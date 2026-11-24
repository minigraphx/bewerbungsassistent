// Flow of the onboarding template: start, one step per section, check and save.
// Depends on validate.js, model.js, steps.js, dom.js, documents.js, zip.js, uploadstore.js and uploads.js (inlined before this file by build_template.py).
"use strict";

const STORAGE_KEY = "bewerbungsassistent.einstieg.v1";
const MAX_FILE_BYTES = 1000000;
const ZIP_OVERHEAD_BYTES = 1000000;
const AUTOSAVE_DELAY_MS = 400;
const FOCUSABLE = "input, textarea, select, button";

// The words of the last step per track. Functions, so that each is said when shown, in the app language (#432).
const TEXT = {
  job: {
    finishTitle: () => T("Prüfen und speichern"),
    finishOk: () => T("Alles Nötige ist ausgefüllt."),
    finishErrors: () => T("Diese Angaben fehlen noch oder passen nicht. Sie können trotzdem speichern und später weitermachen."),
    finishFromDocuments: () => T("Einige Angaben fehlen noch. Das ist in Ordnung: Die App ergänzt sie aus Ihren Unterlagen und fragt nach, was sie dort nicht findet."),
    documents: (n) => documentsLine(n),
    next: () => T("So geht es weiter: Schicken Sie die Datei an die Person, die Sie im Pilot begleitet, oder öffnen Sie sie später in der App. Mit „Datei laden“ auf der ersten Seite können Sie jederzeit weiterarbeiten."),
  },
  apprenticeship: {
    finishTitle: () => T("Prüfen und speichern"),
    finishOk: () => T("Alles Nötige ist ausgefüllt."),
    finishErrors: () => T("Diese Angaben fehlen noch oder passen nicht. Du kannst trotzdem speichern und später weitermachen."),
    finishFromDocuments: () => T("Einige Angaben fehlen noch. Das ist in Ordnung: Die App ergänzt sie aus deinen Unterlagen und fragt nach, was sie dort nicht findet."),
    documents: (n) => documentsLine(n),
    next: () => T("So geht es weiter: Schick die Datei an die Person, die dich begleitet, oder öffne sie später in der App. Mit „Datei laden“ auf der ersten Seite kannst du jederzeit weiterarbeiten."),
  },
};

function documentsLine(count) {
  return count === 1 ? T("Mit einer Unterlage; die Datei wird eine ZIP-Datei.")
    : T("Mit {anzahl} Unterlagen; die Datei wird eine ZIP-Datei.", { anzahl: count });
}

// The space after a sentence joins it to the next one of the same line.
const APP_TEXT = {
  job: {
    finishErrors: () => T("Diese Angaben fehlen noch oder passen nicht. Ihre Eingaben bleiben gespeichert; Sie können später weitermachen."),
    done: () => `${T("Ihre Angaben sind übernommen.")} `,
    kept: (names) => `${T("Aus Ihrer bisherigen Suche bleibt dabei: {namen}. Entfernen können Sie das unter „Suche“.", { namen: names })} `,
    incomplete: () => `${T("Ihre Unterlagen und Eingaben sind im Datenordner. Es fehlen noch Angaben, darum gibt es noch keinen Lebenslauf. Ergänzen Sie sie hier, wenn Sie so weit sind.")} `,
    intro: () => T("Prüfen Sie die Übersicht. Mit «Angaben übernehmen» erstellt die App daraus Ihren Lebenslauf, Ihr Suchprofil und Ihren Schreibstil."),
    keptVersions: () => T("Ihre bisherigen Angaben bleiben unter {link} erhalten.", keptSlots("link")),
  },
  apprenticeship: {
    finishErrors: () => T("Diese Angaben fehlen noch oder passen nicht. Deine Eingaben bleiben gespeichert; du kannst später weitermachen."),
    done: () => `${T("Deine Angaben sind übernommen.")} `,
    kept: (names) => `${T("Aus deiner bisherigen Suche bleibt dabei: {namen}. Entfernen kannst du das unter „Suche“.", { namen: names })} `,
    incomplete: () => `${T("Deine Unterlagen und Eingaben sind im Datenordner. Es fehlen noch Angaben, darum gibt es noch keinen Lebenslauf. Ergänze sie hier, wenn du so weit bist.")} `,
    intro: () => T("Prüf die Übersicht. Mit «Angaben übernehmen» erstellt die App daraus deinen Lebenslauf, dein Suchprofil und deinen Schreibstil."),
    keptVersions: () => T("Deine bisherigen Angaben bleiben unter {link} erhalten.", keptSlots("link")),
  },
};

const form = JSON.parse(document.getElementById("form-definition").textContent);
let state = { track: null, data: {} };
let step = 0;
let touched = new Set();
let autosaveTimer = null;
let uploads = []; // { category, name, size, data: Uint8Array }; also kept in IndexedDB when possible
let uploadMessages = [];
let uploadsSaved = true; // saved in a file or kept in this browser
let uploadsKept = true; // false if this browser cannot keep them (then the page warns before closing)
let existingBasics = []; // in the app: files in the data folder a take-over would replace
let replaceChoices = {}; // in the app: per existing Markdown file "keep" or "replace" (G26)
let uploadTurn = Promise.resolve(); // in the app: uploads and removals wait for each other
let appProblem = null; // in the app: why the data folder cannot be used, shown on the first page
let uploadsUnderway = 0; // in the app: choices of files not yet in the data folder
let prefillRun = { running: false, problem: null, report: null }; // in the app: suggestions from documents
let prefillTurn = 0; // a run that was overtaken by discarding or loading other answers no longer counts
let choice = null; // in the app: what the setup chose (MIN-369) { track, anrede, rav, gewaehlt }
let pageStateFound = false; // in the app: this page has kept answers before (not only the track of the setup)
let folderTags = []; // in the app: tags already in cv.yaml, varianten.yaml and jobs/ of the data folder (G24)
let cvAnswers = null; // in the app: the answers read from cv.yaml; what it holds never blocks (#167, G23)
let basicsRead = null; // in the app: what the page read back from the Markdown basics, sent along to merge (#217)
let basicsLines = []; // in the app: lines of the basics the form does not know, shown as text (#217)
const backend = typeof createAppBackend === "function" ? createAppBackend() : null; // only in the page of the app

// Storage: optional convenience; the page works without it.

function applyStored(stored) {
  if (stored && isTrack(form, stored.track)) {
    const marks = cleanSuggestions(stored.suggested);
    state = {
      ...stateFromBundle(form, { format: form.format, version: form.version, track: stored.track, data: stored.data }),
      ...(Object.keys(marks).length ? { suggested: marks } : {}),
    };
    step = Number.isInteger(stored.step) ? Math.max(0, stored.step) : 0;
  }
}

async function loadStored() {
  try {
    if (backend) {
      const overview = await backend.overview();
      choice = overview.wahl || null;
      pageStateFound = Boolean(overview.stand);
      // Nothing entered yet: start in the track of the setup (MIN-369); the start only shows the choice.
      applyStored(overview.stand || (choice ? { track: choice.track, data: {} } : null));
      notTakenOver = Boolean(overview.stand && overview.stand.offen === true);
      // Answers not taken over yet are newer than cv.yaml; otherwise the file counts (G23).
      if (!notTakenOver) state = fillFromCv(form, state, overview.lebenslauf);
      if (!notTakenOver) state = fillFromBasics(form, state, overview.grundlagen && overview.grundlagen.daten);
      takeBasics(overview.grundlagen);
      uploads = overview.unterlagen;
      existingBasics = overview.vorhanden;
      folderTags = Array.isArray(overview.tags) ? overview.tags : [];
      cvAnswers = overview.lebenslauf || null;
      return;
    }
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) applyStored(JSON.parse(raw));
  } catch (error) {
    if (backend) appProblem = error.message;
    else setStatus(T("Gespeicherte Eingaben konnten nicht gelesen werden."));
  }
}

/** What the app read back from the Markdown basics: the answers to merge against and the lines kept as they are. */
function takeBasics(basics) {
  basicsRead = basics && typeof basics.daten === "object" ? basics.daten : null;
  basicsLines = basics && Array.isArray(basics.fremd) ? basics.fremd : [];
}

async function readBasicsAgain() {
  try {
    takeBasics((await backend.overview()).grundlagen);
  } catch (error) {
    setStatus(T("Suchprofil, Stilprofil und Bausteine liessen sich nicht neu lesen: {fehler}", { fehler: error.message }));
    takeBasics(null); // without what is in the files, the next take-over asks per file again (G26)
  }
}

function storeNow() {
  if (backend) {
    backend.keep({ track: state.track, data: state.data, suggested: state.suggested, step, offen: notTakenOver })
      .then(() => setStatus(T("Zwischengespeichert im Datenordner, {zeit}.", { zeit: timeNow() })))
      .catch((error) => setStatus(T("Zwischenspeichern hat nicht geklappt: {fehler}", { fehler: error.message })));
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ track: state.track, data: state.data, step }));
    setStatus(T("Zwischengespeichert auf diesem Gerät, {zeit}.", { zeit: timeNow() }));
  } catch (error) {
    setStatus(T("Zwischenspeichern ist in diesem Browser nicht möglich. Bitte am Ende die Datei speichern."));
  }
}

/** The time as 14:05 in every language, as the app writes dates as 20.11.2026 in every language. */
const timeNow = () => new Date().toLocaleTimeString("de-CH", { hour: "2-digit", minute: "2-digit" });

function scheduleStore() {
  window.clearTimeout(autosaveTimer);
  autosaveTimer = window.setTimeout(storeNow, AUTOSAVE_DELAY_MS);
}

function clearStored() {
  if (backend) {
    backend.discard().catch((error) => setStatus(error.message));
    return;
  }
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    // Nothing stored that could be removed.
  }
}

function setStatus(message) {
  document.getElementById("autosave").textContent = message;
}

const TAKE_OVER_TARGET = "uebernehmen";
const UPLOAD_TARGET = "unterlagen"; // the Übersicht leads here with a CV as PDF (#222): the upload on the start
let notTakenOver = false;
let profileHint = false;

// State changes

function update(newState, { rerender = false } = {}) {
  if (newState.data !== state.data || newState.track !== state.track) notTakenOver = true;
  state = newState;
  scheduleStore();
  if (rerender) render();
}

function goTo(newStep) {
  step = Math.max(0, Math.min(newStep, steps().length - 1));
  uploadMessages = [];
  if (backend) {
    forgetUploadAnnouncement();
    settlePendingKinds(); // a kind still waiting is saved before the page moves on
  }
  scheduleStore();
  render();
  document.getElementById("main").focus();
  window.scrollTo(0, 0);
}

/** Start, (in the shared file) the documents, the five steps of the design (steps.js), take over or save. */
function steps() {
  if (!state.track) return [{ kind: "start" }];
  const groups = stepGroups(sectionsFor(form, state.track), state.track).map((group) => ({ kind: "group", group }));
  return [{ kind: "start" }, ...(backend ? [] : [{ kind: "documents" }]), ...groups, { kind: "finish" }];
}

const inGroup = (group, sectionId) => group.sections.some((s) => s.id === sectionId);

/** Index of the step that holds a section. */
function stepOfSection(sectionId) {
  return steps().findIndex((s) => s.kind === "group" && inGroup(s.group, sectionId));
}

// Validation shown in the page

function currentErrors() {
  // tags from the data folder never block (G24), nor do the values cv.yaml holds (#167, G23)
  const errors = validateBundle(form, draftBundle(form, state), folderTags, cvAnswers);
  return errors.filter((e) => {
    const [sectionId, index] = e.path.split(".");
    const list = state.data[sectionId];
    return !(Array.isArray(list) && /^\d+$/.test(index || "") && isBlankItem(list[Number(index)]));
  });
}

function refreshErrors() {
  const byPath = {};
  for (const error of currentErrors()) {
    byPath[error.path] = [byPath[error.path], messageText(form, state.track, error)].filter(Boolean).join(" ");
  }
  showErrors(document.getElementById("main"), byPath, touched);
}

// Rendering

function render() {
  const all = steps();
  if (step >= all.length) step = all.length - 1;
  fillPresets(all[step]);
  renderNav(all);
  const main = document.getElementById("main");
  const current = all[step];
  main.replaceChildren(viewFor(current), navButtons(all));
  refreshErrors();
}

/** Presets (#218) for the sections of the step shown; the last step fills every section before taking over. */
function fillPresets(current) {
  const sectionIds = current.kind === "group" ? current.group.sections.map((s) => s.id) : current.kind === "finish" ? null : [];
  const filled = withPresets(form, state, sectionIds);
  if (filled === state) return;
  state = filled;
  scheduleStore();
}

function viewFor(current) {
  if (current.kind === "start") return startView();
  if (current.kind === "documents") return documentsView();
  if (current.kind === "finish") return finishView();
  return groupView(current.group);
}

function stepTitle(s) {
  if (s.kind === "start") return T("Start");
  if (s.kind === "documents") return T(forTrack(form.documents.title, state.track));
  if (s.kind === "finish") return backend ? T("Übernehmen") : T("Speichern");
  return s.group.title;
}

function stepMeta(s) {
  if (s.kind === "start") return backend ? T(forTrack(form.documents.title, state.track)) : T("Stelle oder Lehrstelle");
  if (s.kind === "documents") return T("Lebenslauf, Zeugnisse");
  if (s.kind === "group") return s.group.meta;
  return null;
}

const stepMark = (suggested) => (suggested ? T("Vorschläge prüfen") : T("Angaben fehlen"));

function renderNav(all) {
  // Only where the person has been: on the first visit every step would say that something is missing.
  const errorSections = new Set(currentErrors().filter((e) => touched.has(fieldPath(e.path))).map((e) => e.path.split(".")[0]));
  const items = all.map((s, i) => {
    const sections = s.kind === "group" ? s.group.sections.map((x) => x.id) : [];
    const flagged = sections.some((id) => errorSections.has(id));
    const suggested = sections.some(sectionHasSuggestion);
    const mark = suggested || flagged ? stepMark(suggested) : null;
    const meta = stepMeta(s);
    const position = i === step ? "current" : i < step ? "done" : "todo";
    return el("li", { className: "step", dataset: { state: position, ...(mark ? { mark: suggested ? "suggested" : "flagged" } : {}) } }, el("button", {
      type: "button", className: "step__button", "aria-current": i === step ? "step" : null, onclick: () => goTo(i),
    }, [
      el("span", { className: "step__dot", "aria-hidden": "true" }),
      el("span", { className: "step__label" }, stepTitle(s)),
      meta ? el("span", { className: "step__meta" }, meta) : null,
      mark ? el("span", { className: "step__mark" }, mark) : null,
    ]));
  });
  document.getElementById("steps").replaceChildren(el("ol", { className: "steps" }, items), ...notTakenOverNote(all));
}

/** Changes count only after „Übernehmen“; easy to forget when the search is what one is after. */
function notTakenOverNote(all) {
  if (!backend || !notTakenOver || all[step].kind === "finish") return [];
  const text = state.track === "apprenticeship" ? T("Deine Änderungen sind noch nicht übernommen.") : T("Ihre Änderungen sind noch nicht übernommen.");
  return [el("p", { className: "not-taken-over" }, [
    `${text} `, el("button", { type: "button", className: "link", onclick: () => goTo(all.length - 1) }, T("Zum Übernehmen")),
  ])];
}

/** The search leads here with #feld=<path> (or #feld=uebernehmen): open that step and show the field. */
function openFromAddress() {
  const wanted = new URLSearchParams(window.location.hash.slice(1)).get("feld");
  if (!backend || !wanted) return;
  window.history.replaceState(null, "", window.location.pathname + window.location.search);
  if (wanted === UPLOAD_TARGET) return openUploads();
  if (!state.track || (!pageStateFound && existingBasics.length)) {
    // Imported files without a state of this page: starting over here would ask for everything again.
    profileHint = existingBasics.length > 0;
    return render();
  }
  const all = steps();
  const index = wanted === TAKE_OVER_TARGET ? all.length - 1 : stepOfSection(wanted.split(".")[0]);
  if (index < 0) return;
  goTo(index);
  const field = [...document.querySelectorAll("[data-path]")].find((f) => f.dataset.path === wanted);
  if (!field) return;
  field.classList.add("wanted");
  field.prepend(el("p", { className: "wanted-note" }, T("Hier ergänzen. Es zählt für die Suche, sobald es unter „Übernehmen“ abgeschlossen ist.")));
  field.scrollIntoView({ block: "center" });
  (field.querySelector("input, textarea, select") || field).focus();
}

/** The start holds the one drop area of the app (G84), where the CV the person already has goes too. */
function openUploads() {
  goTo(0);
  const button = document.querySelector(CHOOSE_SELECTOR);
  if (!button) return;
  button.closest(".drop-area").scrollIntoView({ block: "center" });
  button.focus();
}

/** In the app the setup has chosen the track (MIN-369): the start shows the choice and the documents. */
function startView() {
  return backend && choice ? appStartView() : sharedStartView();
}

// Whole sentences per track, so that each language words „eine Stelle“ in its own sentence (#432).
const SEARCHED = { job: () => T("Gesucht wird: eine Stelle"), apprenticeship: () => T("Gesucht wird: eine Lehrstelle") };
const ENTERED_FOR = {
  job: () => T("Die Angaben auf dieser Seite sind für eine Stelle erfasst."),
  apprenticeship: () => T("Die Angaben auf dieser Seite sind für eine Lehrstelle erfasst."),
};
const GO_ON_FOR = { job: () => T("Für eine Stelle weiterfahren"), apprenticeship: () => T("Für eine Lehrstelle weiterfahren") };

function choiceCard() {
  const parts = [SEARCHED[choice.track]()];
  if (choice.track === "job") parts.push(choice.anrede === "du" ? T("Anrede: du") : T("Anrede: Sie"));
  parts.push(choice.rav ? T("RAV: ja") : T("RAV: nein"));
  const differs = state.track && state.track !== choice.track;
  return el("section", { className: "card choice-card", "aria-label": T("Wahl aus der Einrichtung") }, [
    el("p", { className: "choice-card__line" }, [
      el("strong", {}, dotLine(parts)), " ",
      el("a", { href: "/einrichtung#gesucht" }, T("Ändern")),
    ]),
    el("p", { className: "hint" }, choice.gewaehlt
      ? T("Gewählt in der Einrichtung. Eine Änderung passt die Texte und die Suche an.")
      : T("Abgeleitet aus dem Suchprofil, noch nicht in der Einrichtung gewählt. Eine Änderung passt die Texte und die Suche an.")),
    differs ? el("p", { className: "suggestion" }, [
      `${ENTERED_FOR[state.track]()} `,
      el("button", { type: "button", className: "link", onclick: () => update({ ...state, track: choice.track }, { rerender: true }) },
        GO_ON_FOR[choice.track]()),
    ]) : null,
  ]);
}

function loadFileLine() {
  const fileInput = el("input", { type: "file", accept: ".json,.zip,application/json,application/zip", className: "visually-hidden", tabIndex: -1, "aria-hidden": "true", onchange: loadFile });
  return [
    el("p", { className: "secondary" }, [
      `${T("Schon angefangen oder von Claude vorbereitet?")} `,
      el("button", { type: "button", className: "link", onclick: () => fileInput.click() }, T("Datei laden")),
      fileInput,
    ]),
    el("p", { id: "load-message", role: "status" }),
  ];
}

/** „Inhalte als Text“ in the app, „Inhalte“ on the start shown without the setup's choice; a link either way. */
const contentLink = (text) => ({ link: el("a", { href: "/inhalte" }, text) });

function profileHintLine(linkText) {
  return el("p", { className: "wanted-note" }, withNodes(
    T("Das steht in Ihrem Suchprofil, Abschnitt „Region“. Am einfachsten ergänzen Sie es unter {link}.", keptSlots("link")),
    contentLink(linkText)));
}

function existingBasicsLine(linkText) {
  return el("p", { className: "hint" }, withNodes(
    T("Ihre Grundlagen sind schon im Datenordner. Kleine Änderungen machen Sie am einfachsten unter {link}.", keptSlots("link")),
    contentLink(linkText)));
}

function appProblemLine() {
  return el("p", { className: "error", role: "alert" }, [`${appProblem} `, el("a", { href: "/einrichtung" }, T("Zur Einrichtung"))]);
}

function appStartView() {
  return el("section", { className: "start start--app" }, [
    el("h2", { className: "visually-hidden" }, T("Start")),
    profileHint ? profileHintLine(T("Inhalte als Text")) : null,
    appProblem ? appProblemLine() : null,
    choiceCard(),
    prefillCard(prefillCardContext()),
    existingBasics.length ? existingBasicsLine(T("Inhalte als Text")) : null,
    ...loadFileLine(),
  ]);
}

/** What the card on the start of the app shows; also for drawing its run area anew (appestimate.js). */
function prefillCardContext() {
  return {
    form, track: state.track, uploads, messages: uploadMessages, run: prefillRun, notes: uploadNotes,
    announcement: uploadAnnouncement, estimate: prefillEstimate, hasName: hasName(), titleOf: sectionTitle,
    onRun: runPrefill, onGoTo: goToSection, onAddFiles: addDroppedFiles, onChangeKind: changeUploadKind,
    onLeaveKind: leaveUploadKind, onRemove: removeDroppedUpload, onByHand: () => goTo(1), onEstimate: retryEstimate,
  };
}

function sharedStartView() {
  const choose = (track) => {
    update({ ...state, track });
    touched = new Set();
    goTo(1);
  };
  const trackButton = (track, title, text) => el("button", {
    type: "button", className: `track${state.track === track ? " selected" : ""}`,
    "aria-pressed": String(state.track === track), onclick: () => choose(track),
  }, [el("strong", {}, title), el("span", {}, text)]);
  return el("section", { className: "start" }, [
    el("h2", {}, T("Worum geht es?")),
    el("p", {}, backend
      ? T("Hier erfassen Sie Schritt für Schritt alles, was der Bewerbungsbegleiter braucht: Lebenslauf, Suche, Stärken und Ton der Anschreiben. Am Schluss übernehmen Sie alles in die App.")
      : T("Hier erfassen Sie Schritt für Schritt alles, was der Bewerbungsbegleiter braucht: Lebenslauf, Suche, Stärken und Ton der Anschreiben. Am Schluss speichern Sie eine Datei.")),
    profileHint ? profileHintLine(T("Inhalte")) : null,
    appProblem ? appProblemLine() : null,
    existingBasics.length ? existingBasicsLine(T("Inhalte")) : null,
    el("div", { className: "tracks" }, [
      trackButton("job", T("Ich suche eine Stelle"), T("Lebenslauf, Anschreiben und Stellensuche")),
      trackButton("apprenticeship", T("Ich suche eine Lehrstelle"), T("Für Schülerinnen und Schüler: Schnupperlehren, Schule, Motivationsschreiben")),
    ]),
    el("p", { className: "secondary" }, T("Sie haben schon einen Lebenslauf, Zeugnisse oder frühere Anschreiben? Dann müssen Sie nichts abtippen: Im Schritt „Unterlagen“ laden Sie sie hoch. Die App übernimmt daraus Angaben, Belege und Ihre eigenen Formulierungen und fragt nur nach, was fehlt.")),
    ...loadFileLine(),
  ]);
}

function documentsView() {
  return uploadsView({
    form, track: state.track, uploads, messages: uploadMessages, kept: uploadsKept,
    onAdd: addUploads, onRemove: removeUpload, onSkip: () => goTo(steps().length - 1),
  });
}

// Suggestions from documents (page of the app)

const sectionTitle = (id) => T(forTrack(form.sections.find((s) => s.id === id).title, state.track));

function sectionHasSuggestion(id) {
  return Object.keys(state.suggested || {}).some((key) => key.split(".")[0] === id);
}

/** Open the step of a section and bring the section into view. */
function goToSection(id) {
  const index = stepOfSection(id);
  if (index < 0) return;
  goTo(index);
  const part = document.querySelector(`[data-section="${id}"]`);
  if (part && index === step && steps()[index].group.sections[0].id !== id) part.scrollIntoView({ block: "start" });
}

const hasName = () => Boolean(((state.data.person || {}).name || "").trim()) || existingBasics.includes("cv.yaml");

function forgetPrefillRun() {
  prefillTurn += 1;
  prefillRun = { running: false, problem: null, report: null };
}

/** The person may be typing elsewhere meanwhile: the new values must show at once, and the focus stays. */
function renderKeepingFocus() {
  const path = document.activeElement?.closest?.("[data-path]")?.dataset.path;
  render();
  if (path) focusFirst(`[data-path="${path}"]`);
}

/**
 * The running text stands right after the button, which may sit at the bottom edge of the window. The focus goes to
 * it: the button is drawn anew, disabled, and the focus would fall to the page.
 */
function revealPrefillStatus() {
  const status = document.getElementById(STATUS_ID);
  if (!status) return;
  status.scrollIntoView({ block: "nearest" });
  status.focus({ preventScroll: true });
}

async function runPrefill() {
  if (!runAllowed(prefillCardContext())) return; // the estimate changed since the button was drawn (G85)
  const turn = ++prefillTurn;
  const track = state.track;
  const isCurrent = () => turn === prefillTurn && track === state.track;
  const minutes = prefillEstimate.answer.dauer_minuten;
  let finished;
  try {
    const answer = await startPrefill({
      show: () => { prefillRun = { running: true, minutes, problem: null, report: null }; renderKeepingFocus(); },
      reveal: revealPrefillStatus,
      pendingUploads: backend ? pendingDocumentWork : () => (uploadsUnderway ? uploadTurn : null),
      isCurrent,
      ask: () => backend.prefill(track, state.data),
    });
    if (answer === null || !isCurrent()) return;
    const merged = applySuggestions(form, state, answer.suggestions);
    update(merged.state);
    finished = { problem: null, report: prefillReport(answer, merged) };
  } catch (error) {
    if (turn !== prefillTurn) return;
    finished = { problem: error.message, report: null };
  }
  prefillRun = { running: false, ...finished };
  const onStatus = document.activeElement?.id === STATUS_ID;
  renderKeepingFocus();
  if (onStatus) document.getElementById(STATUS_ID)?.focus(); // drawn anew, the line keeps the focus it was given
  if (steps()[step].kind !== "start") setStatus(finished.problem || PREFILL_TEXT[track].finished());
}

function confirmSuggestion(key) {
  update(confirmSuggestions(state, [key]), { rerender: true });
}

function suggestionNote(key) {
  const source = (state.suggested || {})[key];
  return source ? suggestionMark(key, source, confirmSuggestion) : null;
}

/** One upload or removal after the other, so the list from the app is always the latest one. */
function inTurn(work) {
  uploadTurn = uploadTurn.then(work);
  return uploadTurn;
}

/** The person may have moved on while a large file was on its way. */
function focusOnDocuments(category) {
  if (["start", "documents"].includes(steps()[step].kind)) focusFirst(`[data-category="${category}"]`);
}

/** In the app every document goes straight to the data folder; the list of the app is the truth afterwards. */
async function sendDocuments(entries, messages) {
  let list = uploads;
  const problems = [...messages];
  for (const entry of entries) {
    try {
      list = (await backend.addDocument(state.track, entry.category, entry.name, entry.data)).unterlagen;
    } catch (error) {
      problems.push(T("{datei}: {fehler}", { datei: entry.name, fehler: error.message }));
    }
  }
  setUploads(list, problems);
}

async function sendChosen(category, chosen) {
  const { accepted, messages } = planUploads(form, state.track, uploads, category, chosen);
  let read;
  try {
    read = await Promise.all(accepted.map(async ({ index, ...entry }) => (
      { ...entry, data: new Uint8Array(await chosen[index].arrayBuffer()) })));
  } catch (error) {
    setUploads(uploads, [...messages, T("Eine Datei liess sich nicht lesen. Bitte nochmals wählen.")]);
    return;
  }
  await sendDocuments(read, messages);
  focusOnDocuments(category);
}

async function addUploads(category, fileList) {
  const chosen = Array.from(fileList);
  if (backend) {
    uploadsUnderway += 1;
    return inTurn(async () => {
      try {
        await sendChosen(category, chosen);
      } finally {
        uploadsUnderway -= 1;
      }
    });
  }
  const { accepted, messages } = planUploads(form, state.track, uploads, category, chosen);
  try {
    const read = await Promise.all(accepted.map(async ({ index, ...entry }) => (
      { ...entry, data: new Uint8Array(await chosen[index].arrayBuffer()) })));
    setUploads([...uploads, ...read], messages);
  } catch (error) {
    setUploads(uploads, [...messages, T("Eine Datei liess sich nicht lesen. Bitte nochmals wählen.")]);
  }
  focusFirst(`[data-category="${category}"]`);
}

async function removeUpload(index) {
  const { category, datei } = uploads[index];
  if (backend) {
    return inTurn(async () => {
      try {
        setUploads((await backend.removeDocument(datei)).unterlagen, []);
      } catch (error) {
        setUploads(uploads, [error.message]);
      }
      focusOnDocuments(category);
    });
  }
  setUploads(uploads.filter((_, i) => i !== index), []);
  focusFirst(`[data-category="${category}"]`);
}

function setUploads(list, messages) {
  uploads = list;
  uploadMessages = messages;
  uploadsSaved = backend ? true : list.length === 0;
  if (!backend || ["start", "finish"].includes(steps()[step].kind)) render();
  if (!backend) keepUploadsNow();
}

async function keepUploadsNow() {
  const kept = await keepUploads(uploads);
  if (kept !== uploadsKept) {
    uploadsKept = kept;
    if (steps()[step].kind === "documents") render();
  }
  if (kept) uploadsSaved = true;
}

/** Uploads kept from an earlier visit; only those that still pass the rules. */
async function restoreUploads() {
  if (backend) return; // loadStored brought the list of the app
  const kept = await keptUploads();
  const valid = kept.filter((u, i) => validateDocuments(form, kept.slice(0, i + 1).map(({ category, name, size }) => ({ category, name, size })))
    .every((e) => e.path !== `documents.${i}`));
  if (!valid.length) return;
  uploads = valid;
  render();
}

/** One step: its sections one below the other, so every mark and every missing field stays in sight. */
function groupView(group) {
  const track = state.track;
  const required = group.sections.some((s) => shownFields(s, track).some((f) => f.required));
  const single = group.sections.length === 1;
  return el("section", { className: "group" }, [
    el("h2", {}, group.title),
    required ? el("p", { className: "hint" }, T("Felder mit * müssen ausgefüllt sein.")) : null,
    ...group.sections.map((s) => sectionView(s, single)),
  ]);
}

function sectionView(section, single) {
  const track = state.track;
  const intro = T(forTrack(section.intro, track));
  const header = [
    single ? null : el("h3", {}, T(forTrack(section.title, track))),
    intro ? el("p", { className: "intro" }, intro) : null,
  ];
  const attrs = { className: "part", dataset: { section: section.id } };
  if (!section.repeat) {
    const item = state.data[section.id] || {};
    return el("section", attrs, [...header, suggestionNote(section.id), ...shownFields(section, track).map((f) => fieldFor(section, f, [section.id, f.id], item[f.id])), otherLinesView(section.id)]);
  }
  const list = Array.isArray(state.data[section.id]) ? state.data[section.id] : [];
  const max = entryLimit(form, section); // the CV takes as many entries as cv.yaml may hold (G30)
  const itemTitle = T(forTrack(section.itemTitle, track));
  const items = list.map((item, index) => el("fieldset", { className: "item", dataset: { item: `${section.id}.${index}` } }, [
    el("legend", {}, `${itemTitle} ${index + 1}`),
    suggestionNote(`${section.id}.${index}`),
    ...shownFields(section, track).map((f) => fieldFor(section, f, [section.id, index, f.id], item[f.id])),
    el("button", {
      type: "button", className: "remove",
      onclick: () => {
        update(removeItem(state, section.id, index), { rerender: true });
        focusFirst(`[data-item="${section.id}.${index}"]`, `[data-item="${section.id}.${index - 1}"]`, `[data-section="${section.id}"] .add`, "h2");
      },
    }, T("{eintrag} {nummer} entfernen", { eintrag: itemTitle, nummer: index + 1 })),
  ]));
  const add = list.length < max
    ? el("button", {
      type: "button", className: "add",
      onclick: () => {
        update(addItem(state, section.id), { rerender: true });
        focusFirst(`[data-item="${section.id}.${list.length}"]`);
      },
    }, T("+ {eintrag} hinzufügen", { eintrag: itemTitle }))
    : el("p", { className: "hint" }, T("Höchstens {anzahl} Einträge.", { anzahl: max }));
  return el("section", attrs, [...header, ...items, add, otherLinesView(section.id)]);
}

/** Lines of the basics the form does not know (#217): shown as text with the way to change them; saving keeps them. */
function otherLinesView(sectionId) {
  const groups = basicsLines.filter((group) => group.abschnitt === sectionId);
  if (!groups.length) return null;
  const files = [...new Map(groups.map((group) => [group.datei, basicsTitle(group)])).entries()];
  const count = groups.reduce((sum, group) => sum + group.zeilen.length, 0);
  const named = files.map(([, title]) => T("„{titel}“", { titel: title })).reduce((list, name) => T("{a} und {b}", { a: list, b: name }));
  return el("details", { className: "other-lines" }, [
    el("summary", {}, count === 1 ? T("Eine weitere Zeile aus {dateien}", { dateien: named })
      : T("{anzahl} weitere Zeilen aus {dateien}", { anzahl: count, dateien: named })),
    el("p", { className: "hint" }, T("Diese Zeilen kennt das Formular nicht. Beim Speichern bleiben sie, wie sie sind.")),
    // the heading is the file's own, in the German of the search profile, and stays as it is
    ...groups.map((group) => el("div", { className: "other-lines__group" }, [
      el("p", { className: "other-lines__heading" }, `${basicsTitle(group)}, ${group.ueberschrift}`),
      el("pre", {}, group.zeilen.join("\n")),
    ])),
    el("p", {}, dotLine(files.map(([datei, title]) => el("a", {
      href: `/inhalte?${new URLSearchParams({ datei, ansicht: "text" })}`,
    }, T("{titel} unter „Inhalte als Text“ ändern", { titel: title }))))),
  ]);
}

// The basics by file, as basics_slots.TITLES names them; a file of a newer app keeps the title it came with.
const BASICS_TITLES = {
  "suchprofil.md": () => T("Suchprofil"),
  "anschreiben/stil.md": () => T("Stilprofil"),
  "anschreiben/bausteine.md": () => T("Bausteine"),
};
const basicsTitle = (group) => (Object.prototype.hasOwnProperty.call(BASICS_TITLES, group.datei) ? BASICS_TITLES[group.datei]() : group.titel);

/** After a rerender: focus the first control inside the first selector that matches (headings get focus too). */
function focusFirst(...selectors) {
  const main = document.getElementById("main");
  for (const selector of selectors) {
    const target = main.querySelector(selector);
    if (!target) continue;
    const control = target.matches(FOCUSABLE) ? target : target.querySelector(FOCUSABLE);
    if (control) return control.focus();
    target.tabIndex = -1;
    return target.focus();
  }
  return main.focus();
}

function fieldFor(section, field, path, value) {
  const pathText = path.join(".");
  return fieldView(fieldRules(form, section, field), {
    track: state.track, value, path: pathText, cantons: form.cantons, tagSuggestions: knownTags(form, state, folderTags),
    onChange: (v) => update(setValue(state, path, v)),
    onBlur: () => { touched = new Set(touched).add(pathText); refreshErrors(); },
  });
}

function finishView() {
  const text = TEXT[state.track];
  const errors = currentErrors();
  const onlyMissing = uploads.length > 0 && errors.every((e) => e.code === "required");
  const summary = errors.length
    ? el("p", {}, onlyMissing ? text.finishFromDocuments() : (backend ? APP_TEXT[state.track].finishErrors() : text.finishErrors()))
    : el("p", { className: "ok" }, text.finishOk());
  const confirmBox = el("p", { className: "confirm", hidden: true }, [
    `${backend ? T("Alle Eingaben dieser Seite verwerfen? Hochgeladene Unterlagen und schon übernommene Angaben bleiben.") : T("Alle Eingaben auf diesem Gerät löschen?")} `,
    el("button", { type: "button", className: "danger", onclick: clearAll }, backend ? T("Ja, verwerfen") : T("Ja, löschen")),
    " ",
    el("button", { type: "button", onclick: () => { confirmBox.hidden = true; } }, T("Abbrechen")),
  ]);
  const unchecked = uncheckedSuggestions(form, state);
  const finishing = backend ? [
    unchecked.length ? uncheckedView({
      track: state.track, sections: [...new Set(unchecked.map((key) => key.split(".")[0]))], count: unchecked.length, titleOf: sectionTitle,
      onGoTo: goToSection, onConfirmAll: () => update(confirmSuggestions(state, unchecked), { rerender: true }),
    }) : null,
    el("button", { type: "button", className: "primary", id: "take-over", disabled: unchecked.length > 0, onclick: () => takeOver(null) }, T("Angaben übernehmen")),
    el("p", { id: "save-message", role: "alert", className: "error" }),
    el("div", { id: "replace-choice", hidden: true }),
    el("button", { type: "button", className: "primary", id: "replace", hidden: true, onclick: () => takeOver(chosenReplacements(replaceChoices)) }, T("Mit dieser Wahl übernehmen")),
    el("p", { id: "take-over-done", role: "status", className: "ok", hidden: true }),
    el("p", { className: "hint" }, withNodes(APP_TEXT[state.track].keptVersions(), { link: el("a", { href: "/entwuerfe" }, T("Entwürfe und Versionen")) })),
  ] : [
    el("button", { type: "button", className: "primary", onclick: saveFile }, T("Datei speichern")),
    el("p", { id: "save-message", role: "alert", className: "error" }),
    el("p", {}, text.next()),
  ];
  return el("section", {}, [
    el("h2", {}, backend ? T("Übernehmen") : text.finishTitle()),
    backend ? el("p", { className: "intro" }, APP_TEXT[state.track].intro()) : null,
    summary,
    reviewList(errors),
    uploads.length && !backend ? el("p", { className: "hint" }, text.documents(uploads.length)) : null,
    ...finishing,
    el("p", { className: "secondary" }, el("button", { type: "button", className: "link", onclick: () => { confirmBox.hidden = false; } }, backend ? T("Eingaben verwerfen") : T("Alles löschen"))),
    confirmBox,
  ]);
}

/** One line per step: complete, or what is missing with a link to it. */
function reviewList(errors) {
  const groups = steps().map((s, index) => ({ s, index })).filter(({ s }) => s.kind === "group");
  return el("ul", { className: "review" }, groups.map(({ s, index }) => {
    const missing = errors.filter((e) => inGroup(s.group, e.path.split(".")[0]));
    return el("li", { className: "review__row" }, [
      el("div", { className: "review__text" }, [
        el("strong", {}, s.group.title),
        missing.length
          ? el("ul", { className: "review__missing" }, missing.map((e) => el("li", {}, el("button", {
            type: "button", className: "link", onclick: () => goTo(stepOf(e.path)),
          }, describe(form, state.track, e)))))
          : groupHasContent(s.group)
            ? el("span", { className: "review__state" }, T("Vollständig"))
            : el("span", { className: "review__state review__state--empty" }, T("Nichts eingetragen, nicht nötig")),
      ]),
      el("button", { type: "button", className: "review__open", onclick: () => goTo(missing.length ? stepOf(missing[0].path) : index) },
        missing.length ? T("Ergänzen") : T("Ansehen")),
    ]);
  }));
}

function groupHasContent(group) {
  return group.sections.some((s) => {
    const value = state.data[s.id];
    return Array.isArray(value) ? value.some((item) => !isBlankItem(item)) : Boolean(value) && !isBlankItem(value);
  });
}

function stepOf(path) {
  const index = stepOfSection(path.split(".")[0]);
  touched = new Set([...touched, ...currentErrors().map((e) => fieldPath(e.path))]);
  return index < 0 ? step : index;
}

/** Path of the field an error belongs to: list errors ("searchJob.cantons.0") point to a line of the field. */
function fieldPath(errorPath) {
  const parts = errorPath.split(".");
  const isLine = parts.length > 2 && /^\d+$/.test(parts[parts.length - 1]);
  return isLine ? parts.slice(0, -1).join(".") : errorPath;
}

function navButtons(all) {
  const back = step > 0 ? el("button", { type: "button", onclick: () => goTo(step - 1) }, T("Zurück: {schritt}", { schritt: stepTitle(all[step - 1]) })) : null;
  const forward = step > 0 && step < all.length - 1
    ? el("button", { type: "button", className: "primary", onclick: () => { markStepTouched(all[step]); goTo(step + 1); } }, T("Weiter: {schritt}", { schritt: stepTitle(all[step + 1]) }))
    : null;
  return el("div", { className: "nav-buttons" }, [back, forward]);
}

function markStepTouched(current) {
  if (current.kind !== "group") return;
  touched = new Set([...touched, ...currentErrors().filter((e) => inGroup(current.group, e.path.split(".")[0])).map((e) => fieldPath(e.path))]);
}

// Taking over into the data folder (page of the app)

/** replace: null on the first try (existing Markdown files come back as a choice), else the files chosen for replacing. */
async function takeOver(replace) {
  if (uncheckedSuggestions(form, state).length) return render();
  const message = document.getElementById("save-message");
  const done = document.getElementById("take-over-done");
  message.textContent = "";
  done.hidden = true;
  showReplaceChoice([]);
  try {
    window.clearTimeout(autosaveTimer);
    storeNow();
    const sent = state; // a change while this runs is not taken over
    const result = await backend.takeOver(collectBundle(form, state, new Date()), replace, basicsRead);
    const present = [...result.geschrieben, ...(result.unveraendert || []), ...(result.nicht_ersetzt || [])];
    existingBasics = present.length ? present : existingBasics;
    notTakenOver = state !== sent || Boolean(result.unvollstaendig);
    storeNow();
    await readBasicsAgain();
    done.hidden = false;
    done.replaceChildren(
      result.unvollstaendig
        ? APP_TEXT[state.track].incomplete()
        : APP_TEXT[state.track].done(),
      (result.behalten || []).length ? APP_TEXT[state.track].kept(result.behalten.join(", ")) : "",
      (result.nicht_ersetzt || []).length ? `${T("Unverändert geblieben: {dateien}.", { dateien: result.nicht_ersetzt.join(", ") })} ` : "",
      result.hinweis ? `${result.hinweis} ` : "",
      ...dotLine([result.hinweis ? el("a", { href: "/inhalte" }, T("Zu den Inhalten")) : "", el("a", { href: "/" }, T("Zu den Bewerbungen"))]),
    );
  } catch (error) {
    message.textContent = error.message;
    replaceChoices = defaultReplaceChoices(error.existing ? error.choice : []);
    showReplaceChoice(error.existing ? error.choice : []);
  }
}

/** The choice per existing Markdown file with its differences; nothing to choose hides it. */
function showReplaceChoice(changes) {
  const box = document.getElementById("replace-choice");
  const button = document.getElementById("replace");
  if (!box || !button) return;
  box.hidden = changes.length === 0;
  button.hidden = changes.length === 0;
  box.replaceChildren(...(changes.length ? [replaceChoiceView({
    changes, choices: replaceChoices,
    onChoose: (file, value) => { replaceChoices = { ...replaceChoices, [file]: value }; },
  })] : []));
}

// Files

async function saveFile() {
  const now = new Date();
  const json = JSON.stringify(collectBundle(form, state, now), null, 2);
  try {
    if (!uploads.length) {
      download(new Blob([json], { type: "application/json" }), fileName("json"));
      return;
    }
    const zip = await createZip(uploadZipEntries(new TextEncoder().encode(json), uploads), { date: now, compress: true });
    download(new Blob([zip], { type: "application/zip" }), fileName("zip"));
    uploadsSaved = true;
  } catch (error) {
    document.getElementById("save-message").textContent = T("Speichern hat nicht geklappt. Bitte in einem aktuellen Browser nochmals versuchen.");
  }
}

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const link = el("a", { href: url, download: name });
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function fileName(extension) {
  const name = ((state.data.person || {}).name || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return name ? `einstieg-${name}.${extension}` : `einstieg.${extension}`;
}

async function loadFile(event) {
  const file = event.target.files[0];
  const message = document.getElementById("load-message");
  if (!file) return;
  const isZip = /\.zip$/i.test(file.name);
  const limit = isZip ? form.documents.maxTotalBytes + MAX_FILE_BYTES + ZIP_OVERHEAD_BYTES : MAX_FILE_BYTES;
  if (file.size > limit) {
    message.textContent = T("Die Datei ist zu gross für eine Einstiegsdatei.");
    return;
  }
  try {
    const loaded = isZip ? await readUploadZip(file) : { bundle: await file.text(), uploads: [] };
    state = stateFromBundle(form, JSON.parse(loaded.bundle));
    notTakenOver = true;
    basicsRead = null; // a file to take over: existing basics are a choice per file again (G26)
    forgetPrefillRun();
    if (!backend) uploads = loaded.uploads;
    uploadMessages = [];
    uploadsSaved = true;
    touched = new Set();
    goTo(1);
    storeNow();
    if (backend) {
      const sent = inTurn(() => sendDocuments(loaded.uploads, []));
      requestEstimate();
      await sent;
    }
    else keepUploadsNow();
  } catch (error) {
    const known = error instanceof BundleError || error instanceof UploadError || error instanceof ZipError;
    message.textContent = known ? error.message : T("Die Datei ist keine gültige Einstiegsdatei.");
  }
}

async function readUploadZip(file) {
  const limits = { maxEntries: maxUploadEntries(form), maxTotalBytes: form.documents.maxTotalBytes + MAX_FILE_BYTES };
  const entries = await readZip(new Uint8Array(await file.arrayBuffer()), limits);
  const { bundle, uploads: found } = splitUploadZip(form, entries);
  if (bundle.length > MAX_FILE_BYTES) throw new UploadError(T("Die Antworten in der Datei sind zu gross."));
  return { bundle: new TextDecoder("utf-8", { fatal: true }).decode(bundle), uploads: found };
}

function clearAll() {
  window.clearTimeout(autosaveTimer);
  clearStored();
  state = { track: null, data: {} };
  notTakenOver = false;
  basicsRead = null;
  forgetPrefillRun();
  if (!backend) {
    uploads = [];
    keepUploads([]);
  }
  uploadMessages = [];
  uploadsSaved = true;
  touched = new Set();
  step = 0;
  render();
  document.getElementById("main").focus();
  setStatus(backend ? T("Die Eingaben dieser Seite wurden verworfen.") : T("Alle Eingaben auf diesem Gerät wurden gelöscht."));
}

window.addEventListener("beforeunload", (event) => {
  if (uploadsSaved) return;
  event.preventDefault();
  event.returnValue = T("Hochgeladene Unterlagen sind noch nicht gespeichert."); // older browsers show a dialog only with a value
});

if (backend) {
  guardPageDrops(document); // a file dropped beside the drop area must not replace the page (G84)
  trackPointer(document); // a kind saved while a button is pressed waits for its click
}

loadStored().then(() => {
  render();
  restoreUploads();
  openFromAddress();
  if (backend) requestEstimate(); // documents from an earlier visit are still in the data folder
});
