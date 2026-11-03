// Flow of the onboarding template: start, one step per section, check and save.
// Depends on validate.js, model.js and dom.js (inlined before this file by build_template.py).
"use strict";

const STORAGE_KEY = "bewerbungsassistent.einstieg.v1";
const MAX_FILE_BYTES = 1000000;
const AUTOSAVE_DELAY_MS = 400;
const REQUIRED_NOTE = "Felder mit * müssen ausgefüllt sein.";
const EXISTING_DOCUMENTS_NOTE = "Sie haben schon einen Lebenslauf, Arbeitszeugnisse oder frühere Anschreiben? "
  + "Dann müssen Sie nichts abtippen: Geben Sie sie Claude mit dem Skill „einstieg“. Claude übernimmt daraus Angaben, "
  + "Belege und Ihre eigenen Formulierungen und bereitet eine Datei vor. Diese laden Sie hier und prüfen und ergänzen nur noch.";
const FOCUSABLE = "input, textarea, select, button";

const TEXT = {
  job: {
    finishTitle: "Prüfen und speichern",
    finishOk: "Alles Nötige ist ausgefüllt.",
    finishErrors: "Diese Angaben fehlen noch oder passen nicht. Sie können trotzdem speichern und später weitermachen.",
    next: "So geht es weiter: Schicken Sie die Datei an die Person, die Sie im Pilot begleitet, oder öffnen Sie sie später in der App. Mit „Datei laden“ auf der ersten Seite können Sie jederzeit weiterarbeiten.",
  },
  apprenticeship: {
    finishTitle: "Prüfen und speichern",
    finishOk: "Alles Nötige ist ausgefüllt.",
    finishErrors: "Diese Angaben fehlen noch oder passen nicht. Du kannst trotzdem speichern und später weitermachen.",
    next: "So geht es weiter: Schick die Datei an die Person, die dich begleitet, oder öffne sie später in der App. Mit „Datei laden“ auf der ersten Seite kannst du jederzeit weiterarbeiten.",
  },
};

const form = JSON.parse(document.getElementById("form-definition").textContent);
let state = { track: null, data: {} };
let step = 0;
let touched = new Set();
let autosaveTimer = null;

// Storage: optional convenience; the page works without it.

function loadStored() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const stored = JSON.parse(raw);
    if (stored && isTrack(form, stored.track)) {
      state = stateFromBundle(form, { format: form.format, version: form.version, track: stored.track, data: stored.data });
      step = Number.isInteger(stored.step) ? Math.max(0, stored.step) : 0;
    }
  } catch (error) {
    setStatus("Gespeicherte Eingaben konnten nicht gelesen werden.");
  }
}

function storeNow() {
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
  scheduleStore();
  render();
  document.getElementById("main").focus();
  window.scrollTo(0, 0);
}

function steps() {
  if (!state.track) return [{ kind: "start" }];
  return [{ kind: "start" }, ...sectionsFor(form, state.track).map((s) => ({ kind: "section", section: s })), { kind: "finish" }];
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
  const view = current.kind === "start" ? startView() : current.kind === "finish" ? finishView() : sectionView(current.section);
  main.replaceChildren(view, navButtons(all));
  refreshErrors();
}

function renderNav(all) {
  const errorSections = new Set(currentErrors().map((e) => e.path.split(".")[0]));
  const items = all.map((s, i) => {
    const title = s.kind === "start" ? "Start" : s.kind === "finish" ? "Speichern" : forTrack(s.section.title, state.track);
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
  const fileInput = el("input", { type: "file", accept: ".json,application/json", className: "visually-hidden", tabIndex: -1, "aria-hidden": "true", onchange: loadFile });
  return el("section", { className: "start" }, [
    el("h2", {}, "Worum geht es?"),
    el("p", {}, "Hier erfassen Sie Schritt für Schritt alles, was der Bewerbungsassistent braucht: Lebenslauf, Suche, Stärken und Ton der Anschreiben. Am Schluss speichern Sie eine Datei."),
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
  const summary = errors.length
    ? el("div", { className: "summary" }, [
      el("p", {}, text.finishErrors),
      el("ul", {}, errors.map((e) => el("li", {}, el("button", {
        type: "button", className: "link", onclick: () => goTo(stepOf(e.path)),
      }, describe(form, state.track, e))))),
    ])
    : el("p", { className: "ok" }, text.finishOk);
  const confirmBox = el("p", { className: "confirm", hidden: true }, [
    "Alle Eingaben auf diesem Gerät löschen? ",
    el("button", { type: "button", className: "danger", onclick: clearAll }, "Ja, löschen"),
    " ",
    el("button", { type: "button", onclick: () => { confirmBox.hidden = true; } }, "Abbrechen"),
  ]);
  return el("section", {}, [
    el("h2", {}, text.finishTitle),
    summary,
    el("button", { type: "button", className: "primary", onclick: saveFile }, "Datei speichern"),
    el("p", {}, text.next),
    el("p", { className: "secondary" }, el("button", { type: "button", className: "link", onclick: () => { confirmBox.hidden = false; } }, "Alles löschen")),
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

// Files

function saveFile() {
  const bundle = collectBundle(form, state, new Date());
  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = el("a", { href: url, download: fileName() });
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function fileName() {
  const name = ((state.data.person || {}).name || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return name ? `einstieg-${name}.json` : "einstieg.json";
}

function loadFile(event) {
  const file = event.target.files[0];
  const message = document.getElementById("load-message");
  if (!file) return;
  if (file.size > MAX_FILE_BYTES) {
    message.textContent = "Die Datei ist zu gross für eine Einstiegsdatei.";
    return;
  }
  file.text().then((content) => {
    state = stateFromBundle(form, JSON.parse(content));
    touched = new Set();
    goTo(1);
    storeNow();
  }).catch((error) => {
    message.textContent = error instanceof BundleError ? error.message : "Die Datei ist keine gültige Einstiegsdatei.";
  });
}

function clearAll() {
  window.clearTimeout(autosaveTimer);
  clearStored();
  state = { track: null, data: {} };
  touched = new Set();
  step = 0;
  render();
  document.getElementById("main").focus();
  setStatus("Alle Eingaben auf diesem Gerät wurden gelöscht.");
}

loadStored();
render();
