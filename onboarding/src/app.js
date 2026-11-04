// Flow of the onboarding template: start, one step per section, check and save.
// Depends on validate.js, model.js, dom.js, documents.js, zip.js, uploadstore.js and uploads.js (inlined before this file by build_template.py).
"use strict";

const STORAGE_KEY = "bewerbungsassistent.einstieg.v1";
const MAX_FILE_BYTES = 1000000;
const ZIP_OVERHEAD_BYTES = 1000000;
const AUTOSAVE_DELAY_MS = 400;
const REQUIRED_NOTE = "Felder mit * müssen ausgefüllt sein.";
const EXISTING_DOCUMENTS_NOTE = "Sie haben schon einen Lebenslauf, Arbeitszeugnisse oder frühere Anschreiben? "
  + "Dann müssen Sie nichts abtippen: Im Schritt „Unterlagen“ laden Sie sie hoch. Der Assistent übernimmt daraus Angaben, "
  + "Belege und Ihre eigenen Formulierungen und fragt nur nach, was fehlt.";
const UNSAVED_UPLOADS = "Hochgeladene Unterlagen sind noch nicht gespeichert.";
const FOCUSABLE = "input, textarea, select, button";

const TEXT = {
  job: {
    finishTitle: "Prüfen und speichern",
    finishOk: "Alles Nötige ist ausgefüllt.",
    finishErrors: "Diese Angaben fehlen noch oder passen nicht. Sie können trotzdem speichern und später weitermachen.",
    finishFromDocuments: "Einige Angaben fehlen noch. Das ist in Ordnung: Der Assistent ergänzt sie aus Ihren Unterlagen und fragt nach, was er dort nicht findet.",
    documents: (n) => `Mit ${n === 1 ? "einer Unterlage" : `${n} Unterlagen`}; die Datei wird eine ZIP-Datei.`,
    next: "So geht es weiter: Schicken Sie die Datei an die Person, die Sie im Pilot begleitet, oder öffnen Sie sie später in der App. Mit „Datei laden“ auf der ersten Seite können Sie jederzeit weiterarbeiten.",
  },
  apprenticeship: {
    finishTitle: "Prüfen und speichern",
    finishOk: "Alles Nötige ist ausgefüllt.",
    finishErrors: "Diese Angaben fehlen noch oder passen nicht. Du kannst trotzdem speichern und später weitermachen.",
    finishFromDocuments: "Einige Angaben fehlen noch. Das ist in Ordnung: Der Assistent ergänzt sie aus deinen Unterlagen und fragt nach, was er dort nicht findet.",
    documents: (n) => `Mit ${n === 1 ? "einer Unterlage" : `${n} Unterlagen`}; die Datei wird eine ZIP-Datei.`,
    next: "So geht es weiter: Schick die Datei an die Person, die dich begleitet, oder öffne sie später in der App. Mit „Datei laden“ auf der ersten Seite kannst du jederzeit weiterarbeiten.",
  },
};

const APP_TEXT = {
  job: {
    finishErrors: "Diese Angaben fehlen noch oder passen nicht. Ihre Eingaben bleiben gespeichert; Sie können später weitermachen.",
    done: "Ihre Angaben sind übernommen. ",
    incomplete: "Ihre Unterlagen und Eingaben sind im Datenordner. Es fehlen noch Angaben, darum gibt es noch keinen Lebenslauf. Ergänzen Sie sie hier, wenn Sie so weit sind. ",
  },
  apprenticeship: {
    finishErrors: "Diese Angaben fehlen noch oder passen nicht. Deine Eingaben bleiben gespeichert; du kannst später weitermachen.",
    done: "Deine Angaben sind übernommen. ",
    incomplete: "Deine Unterlagen und Eingaben sind im Datenordner. Es fehlen noch Angaben, darum gibt es noch keinen Lebenslauf. Ergänze sie hier, wenn du so weit bist. ",
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
const backend = typeof createAppBackend === "function" ? createAppBackend() : null; // only in the page of the app

// Storage: optional convenience; the page works without it.

function applyStored(stored) {
  if (stored && isTrack(form, stored.track)) {
    state = stateFromBundle(form, { format: form.format, version: form.version, track: stored.track, data: stored.data });
    step = Number.isInteger(stored.step) ? Math.max(0, stored.step) : 0;
  }
}

async function loadStored() {
  try {
    if (backend) {
      const overview = await backend.overview();
      applyStored(overview.stand);
      uploads = overview.unterlagen;
      existingBasics = overview.vorhanden;
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
    backend.keep({ track: state.track, data: state.data, step })
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

// State changes

function update(newState, { rerender = false } = {}) {
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

function steps() {
  if (!state.track) return [{ kind: "start" }];
  return [
    { kind: "start" }, { kind: "documents" },
    ...sectionsFor(form, state.track).map((s) => ({ kind: "section", section: s })), { kind: "finish" },
  ];
}

// Validation shown in the page

function currentErrors() {
  const errors = validateBundle(form, draftBundle(form, state));
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
  return sectionView(current.section);
}

function stepTitle(s) {
  if (s.kind === "start") return "Start";
  if (s.kind === "documents") return forTrack(form.documents.title, state.track);
  if (s.kind === "finish") return backend ? "Übernehmen" : "Speichern";
  return forTrack(s.section.title, state.track);
}

function renderNav(all) {
  const errorSections = new Set(currentErrors().map((e) => e.path.split(".")[0]));
  const items = all.map((s, i) => {
    const title = stepTitle(s);
    const flagged = s.kind === "section" && errorSections.has(s.section.id);
    return el("li", {}, el("button", {
      type: "button", className: `step${i === step ? " current" : ""}${flagged ? " flagged" : ""}`,
      "aria-current": i === step ? "step" : null, onclick: () => goTo(i),
    }, title));
  });
  document.getElementById("steps").replaceChildren(el("ol", {}, items));
}

function startView() {
  const choose = (track) => {
    update({ ...state, track });
    touched = new Set();
    goTo(1);
  };
  const trackButton = (track, title, text) => el("button", {
    type: "button", className: `track${state.track === track ? " selected" : ""}`,
    "aria-pressed": String(state.track === track), onclick: () => choose(track),
  }, [el("strong", {}, title), el("span", {}, text)]);
  const fileInput = el("input", { type: "file", accept: ".json,.zip,application/json,application/zip", className: "visually-hidden", tabIndex: -1, "aria-hidden": "true", onchange: loadFile });
  return el("section", { className: "start" }, [
    el("h2", {}, "Worum geht es?"),
    el("p", {}, `Hier erfassen Sie Schritt für Schritt alles, was der Bewerbungsassistent braucht: Lebenslauf, Suche, Stärken und Ton der Anschreiben. ${backend ? "Am Schluss übernehmen Sie alles in die App." : "Am Schluss speichern Sie eine Datei."}`),
    appProblem ? el("p", { className: "error", role: "alert" }, [`${appProblem} `, el("a", { href: "/einrichtung" }, "Zur Einrichtung")]) : null,
    existingBasics.length ? el("p", { className: "hint" }, ["Ihre Grundlagen sind schon im Datenordner. Kleine Änderungen machen Sie am einfachsten unter ", el("a", { href: "/inhalte" }, "Inhalte"), "."]) : null,
    el("div", { className: "tracks" }, [
      trackButton("job", "Ich suche eine Stelle", "Lebenslauf, Anschreiben und Stellensuche"),
      trackButton("apprenticeship", "Ich suche eine Lehrstelle", "Für Schülerinnen und Schüler: Schnupperlehren, Schule, Motivationsschreiben"),
    ]),
    el("p", { className: "secondary" }, [
      "Schon angefangen oder von Claude vorbereitet? ",
      el("button", { type: "button", className: "link", onclick: () => fileInput.click() }, "Datei laden"),
      fileInput,
    ]),
    el("p", { className: "secondary" }, EXISTING_DOCUMENTS_NOTE),
    el("p", { id: "load-message", role: "status" }),
  ]);
}

function documentsView() {
  return uploadsView({
    form, track: state.track, uploads, messages: uploadMessages, kept: uploadsKept,
    app: Boolean(backend),
    onAdd: addUploads, onRemove: removeUpload, onSkip: () => goTo(steps().length - 1),
  });
}

/** One upload or removal after the other, so the list from the app is always the latest one. */
function inTurn(work) {
  uploadTurn = uploadTurn.then(work);
  return uploadTurn;
}

/** The person may have moved on while a large file was on its way. */
function focusOnDocuments(category) {
  if (steps()[step].kind === "documents") focusFirst(`[data-category="${category}"]`);
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
  if (backend) return inTurn(() => sendChosen(category, chosen));
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
  if (!backend || ["documents", "finish"].includes(steps()[step].kind)) render();
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

function sectionView(section) {
  const track = state.track;
  const intro = forTrack(section.intro, track);
  const hasRequired = fieldsFor(section, track).some((f) => f.required);
  const header = [
    el("h2", {}, forTrack(section.title, track)),
    intro ? el("p", { className: "intro" }, intro) : null,
    hasRequired ? el("p", { className: "hint" }, REQUIRED_NOTE) : null,
  ];
  if (!section.repeat) {
    const item = state.data[section.id] || {};
    return el("section", {}, [...header, ...fieldsFor(section, track).map((f) => fieldFor(section, f, [section.id, f.id], item[f.id]))]);
  }
  const list = Array.isArray(state.data[section.id]) ? state.data[section.id] : [];
  const max = section.maxItems ?? form.limits.repeatItems;
  const itemTitle = forTrack(section.itemTitle, track);
  const items = list.map((item, index) => el("fieldset", { className: "item", dataset: { item: `${section.id}.${index}` } }, [
    el("legend", {}, `${itemTitle} ${index + 1}`),
    ...fieldsFor(section, track).map((f) => fieldFor(section, f, [section.id, index, f.id], item[f.id])),
    el("button", {
      type: "button", className: "remove",
      onclick: () => {
        update(removeItem(state, section.id, index), { rerender: true });
        focusFirst(`[data-item="${section.id}.${index}"]`, `[data-item="${section.id}.${index - 1}"]`, ".add", "h2");
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
  return el("section", {}, [...header, ...items, add]);
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
    track: state.track, value, path: pathText,
    onChange: (v) => update(setValue(state, path, v)),
    onBlur: () => { touched = new Set(touched).add(pathText); refreshErrors(); },
  });
}

function finishView() {
  const text = TEXT[state.track];
  const errors = currentErrors();
  const onlyMissing = uploads.length > 0 && errors.every((e) => e.code === "required");
  const summary = errors.length
    ? el("div", { className: "summary" }, [
      el("p", {}, onlyMissing ? text.finishFromDocuments : (backend ? APP_TEXT[state.track].finishErrors : text.finishErrors)),
      el("ul", {}, errors.map((e) => el("li", {}, el("button", {
        type: "button", className: "link", onclick: () => goTo(stepOf(e.path)),
      }, describe(form, state.track, e))))),
    ])
    : el("p", { className: "ok" }, text.finishOk);
  const confirmBox = el("p", { className: "confirm", hidden: true }, [
    backend ? "Alle Eingaben dieser Seite verwerfen? Hochgeladene Unterlagen und schon übernommene Angaben bleiben. " : "Alle Eingaben auf diesem Gerät löschen? ",
    el("button", { type: "button", className: "danger", onclick: clearAll }, backend ? "Ja, verwerfen" : "Ja, löschen"),
    " ",
    el("button", { type: "button", onclick: () => { confirmBox.hidden = true; } }, "Abbrechen"),
  ]);
  const finishing = backend ? [
    el("button", { type: "button", className: "primary", id: "take-over", onclick: () => takeOver(false) }, "In die App übernehmen"),
    el("button", { type: "button", className: "danger", id: "replace", hidden: true, onclick: () => takeOver(true) }, "Vorhandene Dateien ersetzen"),
    el("p", { id: "save-message", role: "alert", className: "error" }),
    el("p", { id: "take-over-done", role: "status", className: "ok", hidden: true }),
  ] : [
    el("button", { type: "button", className: "primary", onclick: saveFile }, "Datei speichern"),
    el("p", { id: "save-message", role: "alert", className: "error" }),
    el("p", {}, text.next),
  ];
  return el("section", {}, [
    el("h2", {}, backend ? "Prüfen und übernehmen" : text.finishTitle),
    summary,
    uploads.length && !backend ? el("p", { className: "hint" }, text.documents(uploads.length)) : null,
    ...finishing,
    el("p", { className: "secondary" }, el("button", { type: "button", className: "link", onclick: () => { confirmBox.hidden = false; } }, backend ? "Eingaben verwerfen" : "Alles löschen")),
    confirmBox,
  ]);
}

function stepOf(path) {
  const sectionId = path.split(".")[0];
  const index = steps().findIndex((s) => s.kind === "section" && s.section.id === sectionId);
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
  const back = step > 0 ? el("button", { type: "button", onclick: () => goTo(step - 1) }, "Zurück") : null;
  const forward = step > 0 && step < all.length - 1
    ? el("button", { type: "button", className: "primary", onclick: () => { markStepTouched(all[step]); goTo(step + 1); } }, "Weiter")
    : null;
  return el("div", { className: "nav-buttons" }, [back, forward]);
}

function markStepTouched(current) {
  if (current.kind !== "section") return;
  const prefix = `${current.section.id}`;
  touched = new Set([...touched, ...currentErrors().filter((e) => e.path.split(".")[0] === prefix).map((e) => fieldPath(e.path))]);
}

// Taking over into the data folder (page of the app)

async function takeOver(replace) {
  const message = document.getElementById("save-message");
  const done = document.getElementById("take-over-done");
  const replaceButton = document.getElementById("replace");
  message.textContent = "";
  done.hidden = true;
  replaceButton.hidden = true;
  try {
    window.clearTimeout(autosaveTimer);
    storeNow();
    const result = await backend.takeOver(collectBundle(form, state, new Date()), replace);
    existingBasics = result.geschrieben.length ? result.geschrieben : existingBasics;
    done.hidden = false;
    done.replaceChildren(
      result.unvollstaendig
        ? APP_TEXT[state.track].incomplete
        : APP_TEXT[state.track].done,
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
});
