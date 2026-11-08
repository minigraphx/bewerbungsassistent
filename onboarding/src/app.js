// Flow of the onboarding template: start, one step per section, check and save.
// Depends on validate.js, model.js, steps.js, dom.js, documents.js, zip.js, uploadstore.js and uploads.js (inlined before this file by build_template.py).
"use strict";

const STORAGE_KEY = "bewerbungsassistent.einstieg.v1";
const MAX_FILE_BYTES = 1000000;
const ZIP_OVERHEAD_BYTES = 1000000;
const AUTOSAVE_DELAY_MS = 400;
const REQUIRED_NOTE = "Felder mit * müssen ausgefüllt sein.";
const EXISTING_DOCUMENTS_NOTE = "Sie haben schon einen Lebenslauf, Arbeitszeugnisse oder frühere Anschreiben? "
  + "Dann müssen Sie nichts abtippen: Im Schritt „Unterlagen“ laden Sie sie hoch. Die App übernimmt daraus Angaben, "
  + "Belege und Ihre eigenen Formulierungen und fragt nur nach, was fehlt.";
const UNSAVED_UPLOADS = "Hochgeladene Unterlagen sind noch nicht gespeichert.";
const FOCUSABLE = "input, textarea, select, button";

const TEXT = {
  job: {
    finishTitle: "Prüfen und speichern",
    finishOk: "Alles Nötige ist ausgefüllt.",
    finishErrors: "Diese Angaben fehlen noch oder passen nicht. Sie können trotzdem speichern und später weitermachen.",
    finishFromDocuments: "Einige Angaben fehlen noch. Das ist in Ordnung: Die App ergänzt sie aus Ihren Unterlagen und fragt nach, was sie dort nicht findet.",
    documents: (n) => `Mit ${n === 1 ? "einer Unterlage" : `${n} Unterlagen`}; die Datei wird eine ZIP-Datei.`,
    next: "So geht es weiter: Schicken Sie die Datei an die Person, die Sie im Pilot begleitet, oder öffnen Sie sie später in der App. Mit „Datei laden“ auf der ersten Seite können Sie jederzeit weiterarbeiten.",
  },
  apprenticeship: {
    finishTitle: "Prüfen und speichern",
    finishOk: "Alles Nötige ist ausgefüllt.",
    finishErrors: "Diese Angaben fehlen noch oder passen nicht. Du kannst trotzdem speichern und später weitermachen.",
    finishFromDocuments: "Einige Angaben fehlen noch. Das ist in Ordnung: Die App ergänzt sie aus deinen Unterlagen und fragt nach, was sie dort nicht findet.",
    documents: (n) => `Mit ${n === 1 ? "einer Unterlage" : `${n} Unterlagen`}; die Datei wird eine ZIP-Datei.`,
    next: "So geht es weiter: Schick die Datei an die Person, die dich begleitet, oder öffne sie später in der App. Mit „Datei laden“ auf der ersten Seite kannst du jederzeit weiterarbeiten.",
  },
};

const APP_TEXT = {
  job: {
    finishErrors: "Diese Angaben fehlen noch oder passen nicht. Ihre Eingaben bleiben gespeichert; Sie können später weitermachen.",
    done: "Ihre Angaben sind übernommen. ",
    kept: (names) => `Aus Ihrer bisherigen Suche bleibt dabei: ${names}. Entfernen können Sie das unter „Suche“. `,
    incomplete: "Ihre Unterlagen und Eingaben sind im Datenordner. Es fehlen noch Angaben, darum gibt es noch keinen Lebenslauf. Ergänzen Sie sie hier, wenn Sie so weit sind. ",
    intro: "Prüfen Sie die Übersicht. Mit «Angaben übernehmen» erstellt die App daraus Ihren Lebenslauf, Ihr Suchprofil und Ihren Schreibstil.",
    kept_versions: "Ihre bisherigen Angaben bleiben unter ",
  },
  apprenticeship: {
    finishErrors: "Diese Angaben fehlen noch oder passen nicht. Deine Eingaben bleiben gespeichert; du kannst später weitermachen.",
    done: "Deine Angaben sind übernommen. ",
    kept: (names) => `Aus deiner bisherigen Suche bleibt dabei: ${names}. Entfernen kannst du das unter „Suche“. `,
    incomplete: "Deine Unterlagen und Eingaben sind im Datenordner. Es fehlen noch Angaben, darum gibt es noch keinen Lebenslauf. Ergänze sie hier, wenn du so weit bist. ",
    intro: "Prüf die Übersicht. Mit «Angaben übernehmen» erstellt die App daraus deinen Lebenslauf, dein Suchprofil und deinen Schreibstil.",
    kept_versions: "Deine bisherigen Angaben bleiben unter ",
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
let uploadTurn = Promise.resolve(); // in the app: uploads and removals wait for each other
let appProblem = null; // in the app: why the data folder cannot be used, shown on the first page
let uploadsUnderway = 0; // in the app: choices of files not yet in the data folder
let prefillRun = { running: false, waiting: false, problem: null, report: null }; // in the app: suggestions from documents
let prefillTurn = 0; // a run that was overtaken by discarding or loading other answers no longer counts
let choice = null; // in the app: what the setup chose (MIN-369) { track, anrede, rav, gewaehlt }
let pageStateFound = false; // in the app: this page has kept answers before (not only the track of the setup)
let folderTags = []; // in the app: tags already in cv.yaml, varianten.yaml and jobs/ of the data folder (G24)
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
      uploads = overview.unterlagen;
      existingBasics = overview.vorhanden;
      folderTags = Array.isArray(overview.tags) ? overview.tags : [];
      return;
    }
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) applyStored(JSON.parse(raw));
  } catch (error) {
    if (backend) appProblem = error.message;
    else setStatus("Gespeicherte Eingaben konnten nicht gelesen werden.");
  }
}

function storeNow() {
  if (backend) {
    backend.keep({ track: state.track, data: state.data, suggested: state.suggested, step, offen: notTakenOver })
      .then(() => setStatus(`Zwischengespeichert im Datenordner, ${new Date().toLocaleTimeString("de-CH", { hour: "2-digit", minute: "2-digit" })}.`))
      .catch((error) => setStatus(`Zwischenspeichern hat nicht geklappt: ${error.message}`));
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ track: state.track, data: state.data, step }));
    const time = new Date().toLocaleTimeString("de-CH", { hour: "2-digit", minute: "2-digit" });
    setStatus(`Zwischengespeichert auf diesem Gerät, ${time}.`);
  } catch (error) {
    setStatus("Zwischenspeichern ist in diesem Browser nicht möglich. Bitte am Ende die Datei speichern.");
  }
}

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
const WANTED_NOTE = "Hier ergänzen. Es zählt für die Suche, sobald es unter „Übernehmen“ abgeschlossen ist.";
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
  const errors = validateBundle(form, draftBundle(form, state), folderTags); // tags from the data folder never block (G24)
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
  renderNav(all);
  const main = document.getElementById("main");
  const current = all[step];
  main.replaceChildren(viewFor(current), navButtons(all));
  refreshErrors();
}

function viewFor(current) {
  if (current.kind === "start") return startView();
  if (current.kind === "documents") return documentsView();
  if (current.kind === "finish") return finishView();
  return groupView(current.group);
}

function stepTitle(s) {
  if (s.kind === "start") return "Start";
  if (s.kind === "documents") return forTrack(form.documents.title, state.track);
  if (s.kind === "finish") return backend ? "Übernehmen" : "Speichern";
  return s.group.title;
}

function stepMeta(s) {
  if (s.kind === "start") return backend ? forTrack(form.documents.title, state.track) : "Stelle oder Lehrstelle";
  if (s.kind === "documents") return "Lebenslauf, Zeugnisse";
  if (s.kind === "group") return s.group.meta;
  return null;
}

const STEP_MARKS = { flagged: "Angaben fehlen", suggested: "Vorschläge prüfen" };

function renderNav(all) {
  // Only where the person has been: on the first visit every step would say that something is missing.
  const errorSections = new Set(currentErrors().filter((e) => touched.has(fieldPath(e.path))).map((e) => e.path.split(".")[0]));
  const items = all.map((s, i) => {
    const sections = s.kind === "group" ? s.group.sections.map((x) => x.id) : [];
    const flagged = sections.some((id) => errorSections.has(id));
    const suggested = sections.some(sectionHasSuggestion);
    const mark = suggested ? STEP_MARKS.suggested : flagged ? STEP_MARKS.flagged : null;
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
  const text = state.track === "apprenticeship" ? "Deine Änderungen sind noch nicht übernommen." : "Ihre Änderungen sind noch nicht übernommen.";
  return [el("p", { className: "not-taken-over" }, [
    `${text} `, el("button", { type: "button", className: "link", onclick: () => goTo(all.length - 1) }, "Zum Übernehmen"),
  ])];
}

/** The search leads here with #feld=<path> (or #feld=uebernehmen): open that step and show the field. */
function openFromAddress() {
  const wanted = new URLSearchParams(window.location.hash.slice(1)).get("feld");
  if (!backend || !wanted) return;
  window.history.replaceState(null, "", window.location.pathname + window.location.search);
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
  field.prepend(el("p", { className: "wanted-note" }, WANTED_NOTE));
  field.scrollIntoView({ block: "center" });
  (field.querySelector("input, textarea, select") || field).focus();
}

const TRACK_WORDS = { job: "eine Stelle", apprenticeship: "eine Lehrstelle" };

/** In the app the setup has chosen the track (MIN-369): the start shows the choice and the documents. */
function startView() {
  return backend && choice ? appStartView() : sharedStartView();
}

function choiceCard() {
  const parts = [`Gesucht wird: ${TRACK_WORDS[choice.track]}`];
  if (choice.track === "job") parts.push(`Anrede: ${choice.anrede === "du" ? "du" : "Sie"}`);
  parts.push(`RAV: ${choice.rav ? "ja" : "nein"}`);
  const differs = state.track && state.track !== choice.track;
  return el("section", { className: "card choice-card", "aria-label": "Wahl aus der Einrichtung" }, [
    el("p", { className: "choice-card__line" }, [
      el("strong", {}, parts.join(" · ")), " ",
      el("a", { href: "/einrichtung#gesucht" }, "Ändern"),
    ]),
    el("p", { className: "hint" }, choice.gewaehlt
      ? "Gewählt in der Einrichtung. Eine Änderung passt die Texte und die Suche an."
      : "Abgeleitet aus dem Suchprofil, noch nicht in der Einrichtung gewählt. Eine Änderung passt die Texte und die Suche an."),
    differs ? el("p", { className: "suggestion" }, [
      `Die Angaben auf dieser Seite sind für ${TRACK_WORDS[state.track]} erfasst. `,
      el("button", { type: "button", className: "link", onclick: () => update({ ...state, track: choice.track }, { rerender: true }) },
        `Für ${TRACK_WORDS[choice.track]} weiterfahren`),
    ]) : null,
  ]);
}

function loadFileLine() {
  const fileInput = el("input", { type: "file", accept: ".json,.zip,application/json,application/zip", className: "visually-hidden", tabIndex: -1, "aria-hidden": "true", onchange: loadFile });
  return [
    el("p", { className: "secondary" }, [
      "Schon angefangen oder von Claude vorbereitet? ",
      el("button", { type: "button", className: "link", onclick: () => fileInput.click() }, "Datei laden"),
      fileInput,
    ]),
    el("p", { id: "load-message", role: "status" }),
  ];
}

function appStartView() {
  return el("section", { className: "start start--app" }, [
    el("h2", { className: "visually-hidden" }, "Start"),
    profileHint ? el("p", { className: "wanted-note" }, ["Das steht in Ihrem Suchprofil, Abschnitt „Region“. Am einfachsten ergänzen Sie es unter ", el("a", { href: "/inhalte" }, "Inhalte als Text"), "."]) : null,
    appProblem ? el("p", { className: "error", role: "alert" }, [`${appProblem} `, el("a", { href: "/einrichtung" }, "Zur Einrichtung")]) : null,
    choiceCard(),
    prefillCard({
      form, track: state.track, uploads, messages: uploadMessages, run: prefillRun,
      hasName: hasName(), titleOf: sectionTitle, onRun: runPrefill, onGoTo: goToSection,
      onAdd: addUploads, onRemove: removeUpload, onByHand: () => goTo(1),
    }),
    existingBasics.length ? el("p", { className: "hint" }, ["Ihre Grundlagen sind schon im Datenordner. Kleine Änderungen machen Sie am einfachsten unter ", el("a", { href: "/inhalte" }, "Inhalte als Text"), "."]) : null,
    ...loadFileLine(),
  ]);
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
    el("h2", {}, "Worum geht es?"),
    el("p", {}, `Hier erfassen Sie Schritt für Schritt alles, was der Bewerbungsbegleiter braucht: Lebenslauf, Suche, Stärken und Ton der Anschreiben. ${backend ? "Am Schluss übernehmen Sie alles in die App." : "Am Schluss speichern Sie eine Datei."}`),
    profileHint ? el("p", { className: "wanted-note" }, ["Das steht in Ihrem Suchprofil, Abschnitt „Region“. Am einfachsten ergänzen Sie es unter ", el("a", { href: "/inhalte" }, "Inhalte"), "."]) : null,
    appProblem ? el("p", { className: "error", role: "alert" }, [`${appProblem} `, el("a", { href: "/einrichtung" }, "Zur Einrichtung")]) : null,
    existingBasics.length ? el("p", { className: "hint" }, ["Ihre Grundlagen sind schon im Datenordner. Kleine Änderungen machen Sie am einfachsten unter ", el("a", { href: "/inhalte" }, "Inhalte"), "."]) : null,
    el("div", { className: "tracks" }, [
      trackButton("job", "Ich suche eine Stelle", "Lebenslauf, Anschreiben und Stellensuche"),
      trackButton("apprenticeship", "Ich suche eine Lehrstelle", "Für Schülerinnen und Schüler: Schnupperlehren, Schule, Motivationsschreiben"),
    ]),
    el("p", { className: "secondary" }, EXISTING_DOCUMENTS_NOTE),
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

const sectionTitle = (id) => forTrack(form.sections.find((s) => s.id === id).title, state.track);

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
  prefillRun = { running: false, waiting: false, problem: null, report: null };
}

/** The person may be typing elsewhere meanwhile: the new values must show at once, and the focus stays. */
function renderKeepingFocus() {
  const path = document.activeElement?.closest?.("[data-path]")?.dataset.path;
  render();
  if (path) focusFirst(`[data-path="${path}"]`);
}

/** The running text stands right after the button, which may sit at the bottom edge of the window. */
function revealPrefillStatus() {
  const status = document.getElementById("prefill-status");
  if (status) status.scrollIntoView({ block: "nearest" });
}

async function runPrefill() {
  const turn = ++prefillTurn;
  const track = state.track;
  const isCurrent = () => turn === prefillTurn && track === state.track;
  let finished;
  try {
    const answer = await startPrefill({
      show: (run) => { prefillRun = run; renderKeepingFocus(); },
      reveal: revealPrefillStatus,
      pendingUploads: () => (uploadsUnderway ? uploadTurn : null),
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
  prefillRun = { running: false, waiting: false, ...finished };
  renderKeepingFocus();
  if (steps()[step].kind !== "start") setStatus(finished.problem || PREFILL_TEXT[track].finished);
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
      problems.push(`${entry.name}: ${error.message}`);
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
    setUploads(uploads, [...messages, "Eine Datei liess sich nicht lesen. Bitte nochmals wählen."]);
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
    setUploads(uploads, [...messages, "Eine Datei liess sich nicht lesen. Bitte nochmals wählen."]);
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
  const required = group.sections.some((s) => fieldsFor(s, track).some((f) => f.required));
  const single = group.sections.length === 1;
  return el("section", { className: "group" }, [
    el("h2", {}, group.title),
    required ? el("p", { className: "hint" }, REQUIRED_NOTE) : null,
    ...group.sections.map((s) => sectionView(s, single)),
  ]);
}

function sectionView(section, single) {
  const track = state.track;
  const intro = forTrack(section.intro, track);
  const header = [
    single ? null : el("h3", {}, forTrack(section.title, track)),
    intro ? el("p", { className: "intro" }, intro) : null,
  ];
  const attrs = { className: "part", dataset: { section: section.id } };
  if (!section.repeat) {
    const item = state.data[section.id] || {};
    return el("section", attrs, [...header, suggestionNote(section.id), ...fieldsFor(section, track).map((f) => fieldFor(section, f, [section.id, f.id], item[f.id]))]);
  }
  const list = Array.isArray(state.data[section.id]) ? state.data[section.id] : [];
  const max = section.maxItems ?? form.limits.repeatItems;
  const itemTitle = forTrack(section.itemTitle, track);
  const items = list.map((item, index) => el("fieldset", { className: "item", dataset: { item: `${section.id}.${index}` } }, [
    el("legend", {}, `${itemTitle} ${index + 1}`),
    suggestionNote(`${section.id}.${index}`),
    ...fieldsFor(section, track).map((f) => fieldFor(section, f, [section.id, index, f.id], item[f.id])),
    el("button", {
      type: "button", className: "remove",
      onclick: () => {
        update(removeItem(state, section.id, index), { rerender: true });
        focusFirst(`[data-item="${section.id}.${index}"]`, `[data-item="${section.id}.${index - 1}"]`, `[data-section="${section.id}"] .add`, "h2");
      },
    }, `${itemTitle} ${index + 1} entfernen`),
  ]));
  const add = list.length < max
    ? el("button", {
      type: "button", className: "add",
      onclick: () => {
        update(addItem(state, section.id), { rerender: true });
        focusFirst(`[data-item="${section.id}.${list.length}"]`);
      },
    }, `+ ${itemTitle} hinzufügen`)
    : el("p", { className: "hint" }, `Höchstens ${max} Einträge.`);
  return el("section", attrs, [...header, ...items, add]);
}

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
  return fieldView(field, {
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
    ? el("p", {}, onlyMissing ? text.finishFromDocuments : (backend ? APP_TEXT[state.track].finishErrors : text.finishErrors))
    : el("p", { className: "ok" }, text.finishOk);
  const confirmBox = el("p", { className: "confirm", hidden: true }, [
    backend ? "Alle Eingaben dieser Seite verwerfen? Hochgeladene Unterlagen und schon übernommene Angaben bleiben. " : "Alle Eingaben auf diesem Gerät löschen? ",
    el("button", { type: "button", className: "danger", onclick: clearAll }, backend ? "Ja, verwerfen" : "Ja, löschen"),
    " ",
    el("button", { type: "button", onclick: () => { confirmBox.hidden = true; } }, "Abbrechen"),
  ]);
  const unchecked = uncheckedSuggestions(form, state);
  const finishing = backend ? [
    unchecked.length ? uncheckedView({
      track: state.track, sections: [...new Set(unchecked.map((key) => key.split(".")[0]))], count: unchecked.length, titleOf: sectionTitle,
      onGoTo: goToSection, onConfirmAll: () => update(confirmSuggestions(state, unchecked), { rerender: true }),
    }) : null,
    el("button", { type: "button", className: "primary", id: "take-over", disabled: unchecked.length > 0, onclick: () => takeOver(false) }, "Angaben übernehmen"),
    el("button", { type: "button", className: "danger", id: "replace", hidden: true, onclick: () => takeOver(true) }, "Vorhandene Dateien ersetzen"),
    el("p", { id: "save-message", role: "alert", className: "error" }),
    el("p", { id: "take-over-done", role: "status", className: "ok", hidden: true }),
    el("p", { className: "hint" }, [APP_TEXT[state.track].kept_versions, el("a", { href: "/entwuerfe" }, "Entwürfe und Versionen"), " erhalten."]),
  ] : [
    el("button", { type: "button", className: "primary", onclick: saveFile }, "Datei speichern"),
    el("p", { id: "save-message", role: "alert", className: "error" }),
    el("p", {}, text.next),
  ];
  return el("section", {}, [
    el("h2", {}, backend ? "Übernehmen" : text.finishTitle),
    backend ? el("p", { className: "intro" }, APP_TEXT[state.track].intro) : null,
    summary,
    reviewList(errors),
    uploads.length && !backend ? el("p", { className: "hint" }, text.documents(uploads.length)) : null,
    ...finishing,
    el("p", { className: "secondary" }, el("button", { type: "button", className: "link", onclick: () => { confirmBox.hidden = false; } }, backend ? "Eingaben verwerfen" : "Alles löschen")),
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
            ? el("span", { className: "review__state" }, "Vollständig")
            : el("span", { className: "review__state review__state--empty" }, "Nichts eingetragen, nicht nötig"),
      ]),
      el("button", { type: "button", className: "review__open", onclick: () => goTo(missing.length ? stepOf(missing[0].path) : index) },
        missing.length ? "Ergänzen" : "Ansehen"),
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
  const back = step > 0 ? el("button", { type: "button", onclick: () => goTo(step - 1) }, `Zurück: ${stepTitle(all[step - 1])}`) : null;
  const forward = step > 0 && step < all.length - 1
    ? el("button", { type: "button", className: "primary", onclick: () => { markStepTouched(all[step]); goTo(step + 1); } }, `Weiter: ${stepTitle(all[step + 1])}`)
    : null;
  return el("div", { className: "nav-buttons" }, [back, forward]);
}

function markStepTouched(current) {
  if (current.kind !== "group") return;
  touched = new Set([...touched, ...currentErrors().filter((e) => inGroup(current.group, e.path.split(".")[0])).map((e) => fieldPath(e.path))]);
}

// Taking over into the data folder (page of the app)

async function takeOver(replace) {
  if (uncheckedSuggestions(form, state).length) return render();
  const message = document.getElementById("save-message");
  const done = document.getElementById("take-over-done");
  const replaceButton = document.getElementById("replace");
  message.textContent = "";
  done.hidden = true;
  replaceButton.hidden = true;
  try {
    window.clearTimeout(autosaveTimer);
    storeNow();
    const sent = state; // a change while this runs is not taken over
    const result = await backend.takeOver(collectBundle(form, state, new Date()), replace);
    const present = [...result.geschrieben, ...(result.unveraendert || [])];
    existingBasics = present.length ? present : existingBasics;
    notTakenOver = state !== sent || Boolean(result.unvollstaendig);
    storeNow();
    done.hidden = false;
    done.replaceChildren(
      result.unvollstaendig
        ? APP_TEXT[state.track].incomplete
        : APP_TEXT[state.track].done,
      (result.behalten || []).length ? APP_TEXT[state.track].kept(result.behalten.join(", ")) : "",
      result.hinweis ? `${result.hinweis} ` : "",
      result.hinweis ? el("a", { href: "/inhalte" }, "Zu den Inhalten") : "",
      result.hinweis ? " · " : "",
      el("a", { href: "/" }, "Zu den Bewerbungen"),
    );
  } catch (error) {
    message.textContent = error.message;
    replaceButton.hidden = !error.existing;
  }
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
    document.getElementById("save-message").textContent = "Speichern hat nicht geklappt. Bitte in einem aktuellen Browser nochmals versuchen.";
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
    message.textContent = "Die Datei ist zu gross für eine Einstiegsdatei.";
    return;
  }
  try {
    const loaded = isZip ? await readUploadZip(file) : { bundle: await file.text(), uploads: [] };
    state = stateFromBundle(form, JSON.parse(loaded.bundle));
    notTakenOver = true;
    forgetPrefillRun();
    if (!backend) uploads = loaded.uploads;
    uploadMessages = [];
    uploadsSaved = true;
    touched = new Set();
    goTo(1);
    storeNow();
    if (backend) await inTurn(() => sendDocuments(loaded.uploads, []));
    else keepUploadsNow();
  } catch (error) {
    const known = error instanceof BundleError || error instanceof UploadError || error instanceof ZipError;
    message.textContent = known ? error.message : "Die Datei ist keine gültige Einstiegsdatei.";
  }
}

async function readUploadZip(file) {
  const limits = { maxEntries: maxUploadEntries(form), maxTotalBytes: form.documents.maxTotalBytes + MAX_FILE_BYTES };
  const entries = await readZip(new Uint8Array(await file.arrayBuffer()), limits);
  const { bundle, uploads: found } = splitUploadZip(form, entries);
  if (bundle.length > MAX_FILE_BYTES) throw new UploadError("Die Antworten in der Datei sind zu gross.");
  return { bundle: new TextDecoder("utf-8", { fatal: true }).decode(bundle), uploads: found };
}

function clearAll() {
  window.clearTimeout(autosaveTimer);
  clearStored();
  state = { track: null, data: {} };
  notTakenOver = false;
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
  setStatus(backend ? "Die Eingaben dieser Seite wurden verworfen." : "Alle Eingaben auf diesem Gerät wurden gelöscht.");
}

window.addEventListener("beforeunload", (event) => {
  if (uploadsSaved) return;
  event.preventDefault();
  event.returnValue = UNSAVED_UPLOADS; // older browsers show a dialog only with a value
});

loadStored().then(() => {
  render();
  restoreUploads();
  openFromAddress();
});
