// Step "Unterlagen" of the template: choose existing documents per category, list and remove them.
// Files are kept in IndexedDB (uploadstore.js) where the browser allows it; they go into the saved ZIP.
// Depends on dom.js, model.js and documents.js (inlined before this file by build_template.py).
"use strict";

// Said when they are shown, so they follow the app language (#433); the file for sharing stays German.
const UPLOAD_TEXT = {
  job: {
    kept: () => T("Die Dateien bleiben in diesem Browser auf diesem Gerät, auch nach dem Schliessen, und kommen mit in die gespeicherte Datei. „Alles löschen“ im letzten Schritt entfernt sie."),
    memory: () => T("Dieser Browser kann die Dateien nicht aufbewahren (z.B. im privaten Fenster). Speichern Sie am Schluss die Datei, sonst müssen Sie sie nach dem Schliessen neu wählen."),
    choose: () => T("Dateien wählen"),
    skip: () => T("Weiter zum Speichern"),
    app: () => T("Die Dateien kommen sofort in Ihren Datenordner (Ordner „dokumente“) und bleiben auf diesem Computer."),
    skipHint: () => T("Mit Unterlagen können Sie die übrigen Schritte auslassen oder nur ausfüllen, was Sie gerade wissen."),
    full: (max) => T("Höchstens {max} Dateien. Entfernen Sie eine, wenn Sie eine andere wählen möchten.", { max }),
  },
  apprenticeship: {
    kept: () => T("Die Dateien bleiben in diesem Browser auf diesem Gerät, auch nach dem Schliessen, und kommen mit in die gespeicherte Datei. „Alles löschen“ im letzten Schritt entfernt sie."),
    memory: () => T("Dieser Browser kann die Dateien nicht aufbewahren (z.B. im privaten Fenster). Speichere am Schluss die Datei, sonst musst du sie nach dem Schliessen neu wählen."),
    choose: () => T("Dateien wählen"),
    skip: () => T("Weiter zum Speichern"),
    app: () => T("Die Dateien kommen sofort in deinen Datenordner (Ordner „dokumente“) und bleiben auf diesem Computer."),
    skipHint: () => T("Mit Unterlagen kannst du die übrigen Schritte auslassen oder nur ausfüllen, was du gerade weisst."),
    full: (max) => T("Höchstens {max} Dateien. Entferne eine, wenn du eine andere wählen möchtest.", { max }),
  },
};
const BYTES_PER_KB = 1000;

const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);

function formatSize(bytes) {
  if (bytes < BYTES_PER_KB * BYTES_PER_KB) return T("{zahl} KB", { zahl: Math.max(1, Math.round(bytes / BYTES_PER_KB)) });
  return T("{zahl} MB", { zahl: (bytes / (BYTES_PER_KB * BYTES_PER_KB)).toLocaleString("de-CH", { maximumFractionDigits: 1 }) });
}

/**
 * The step view of the shared file. ctx: { form, track, uploads, messages, kept, onAdd(category, FileList), onRemove(index), onSkip() }.
 * In the app the categories are part of the card on the start (prefill.js); `app` is the line about the data folder there.
 * File names come from the person's computer and are only ever set as text.
 */
function uploadsView(ctx) {
  const { form, track, uploads } = ctx;
  const text = UPLOAD_TEXT[track];
  const rules = form.documents;
  return el("section", { className: "uploads" }, [
    el("h2", {}, T(forTrack(rules.title, track))),
    el("p", { className: "intro" }, T(forTrack(rules.intro, track))),
    el("p", { className: "hint" }, ctx.kept ? text.kept() : text.memory()),
    el("div", { id: "upload-messages", className: "error", role: "alert" }, ctx.messages.map((m) => el("p", {}, m))),
    ...rules.categories.map((category) => categoryView(ctx, category, text)),
    uploads.length ? el("p", { className: "secondary" }, [
      text.skipHint(), " ",
      el("button", { type: "button", className: "link", onclick: ctx.onSkip }, text.skip()),
    ]) : null,
  ]);
}

function categoryView(ctx, category, text) {
  const { form, track, uploads } = ctx;
  const id = nextId("u");
  const accept = allowedExtensions(form, category).map((ext) => `.${ext}`).join(",");
  const input = el("input", {
    type: "file", multiple: true, accept, className: "visually-hidden", tabIndex: -1, "aria-hidden": "true",
    onchange: (e) => ctx.onAdd(category.id, e.target.files),
  });
  const files = uploads
    .map((upload, index) => ({ upload, index }))
    .filter(({ upload }) => upload.category === category.id)
    .map(({ upload, index }) => el("li", {}, [
      el("span", { className: "file-name" }, upload.name),
      el("span", { className: "file-size" }, formatSize(upload.size)),
      el("button", { type: "button", className: "remove", "aria-label": T("{name} entfernen", { name: upload.name }),
        onclick: () => ctx.onRemove(index) }, T("Entfernen")),
    ]));
  const { count, maxFiles } = categoryRoom(form, uploads, category.id);
  const full = count >= maxFiles; // the file dialog cannot be told how many files it may take
  const hint = T("{hinweis}. Erlaubt: {dateitypen}.",
    { hinweis: capitalize(T(forTrack(category.hint, track))), dateitypen: allowedText(form, category) });
  return el("fieldset", { className: "item upload-category", "aria-describedby": `${id}-hint` }, [
    el("legend", {}, T(forTrack(category.title, track))),
    el("p", { className: "hint", id: `${id}-hint` }, hint),
    files.length ? el("ul", { className: "files" }, files) : null,
    el("button", {
      type: "button", className: "add", dataset: { category: category.id }, disabled: full,
      "aria-describedby": full ? `${id}-full` : null, onclick: () => input.click(),
    }, `+ ${text.choose()}`),
    full ? el("p", { className: "hint limit-note", id: `${id}-full` }, text.full(maxFiles)) : null,
    input,
  ]);
}
