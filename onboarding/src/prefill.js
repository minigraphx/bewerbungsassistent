// Only in the page „Meine Angaben“ of the app: suggestions from uploaded documents, marked until they are checked.
// File names and everything from the AI are only ever set as text.
"use strict";

const PREFILL_TEXT = {
  job: {
    title: "Aus Ihren Unterlagen vorbefüllen",
    text: "Laden Sie Lebenslauf und Zeugnisse hoch. Die KI liest sie und füllt die nächsten Schritte aus, nur leere Felder. Sie prüfen alles.",
    run: "Vorbefüllen",
    byHand: "Lieber von Hand ausfüllen",
    privacy: "Name, Adresse und Kontakte werden ersetzt, bevor der Text zur KI (Anthropic) geht. Namen anderer Personen, etwa auf Zeugnissen, erkennt der Assistent nur nach „Frau“ oder „Herr“. Bilder, Scans und alte Word-Dateien bleiben auf Ihrem Computer.",
    needsName: "Tragen Sie zuerst Ihren Namen ein: So erkennt der Assistent ihn in den Unterlagen und schickt ihn nicht an die KI.",
    goToPerson: "Zu „Person und Kontakt“",
    running: "Die Unterlagen werden gelesen. Das kann ein bis zwei Minuten dauern; Sie können in dieser Zeit weiterarbeiten.",
    finished: "Die Vorschläge aus den Unterlagen sind da. Sie sind im Formular markiert.",
    filled: "Vorschläge stehen bereit. Bitte prüfen Sie jeden Eintrag:",
    nothing: "In den Unterlagen wurden keine passenden Angaben gefunden.",
    kept: "Hier haben Sie schon etwas eingetragen, das bleibt unverändert:",
    skipped: "Nicht gelesen:",
    shortened: "Nur der Anfang wurde gelesen, die Datei ist zu lang:",
    dropped: (n) => `${n === 1 ? "Eine Angabe passte" : `${n} Angaben passten`} nicht ins Formular und ${n === 1 ? "wurde" : "wurden"} weggelassen.`,
    suspicious: "Diese Zeilen in den Unterlagen richten sich an eine KI. Sie wurden nicht befolgt, schauen Sie sie sich an:",
    mark: (source) => `Vorschlag aus ${source}. Bitte prüfen.`,
    confirm: "Stimmt so",
    unchecked: (n) => `${n === 1 ? "Ein Vorschlag" : `${n} Vorschläge`} aus den Unterlagen ${n === 1 ? "ist" : "sind"} noch nicht geprüft. Erst danach lässt sich alles übernehmen.`,
    confirmAll: "Ich habe alle geprüft",
  },
  apprenticeship: {
    title: "Aus deinen Unterlagen vorbefüllen",
    text: "Lade dein Zeugnis oder einen Lebenslauf hoch. Die KI liest sie und füllt die nächsten Schritte aus, nur leere Felder. Du prüfst alles.",
    run: "Vorbefüllen",
    byHand: "Lieber von Hand ausfüllen",
    privacy: "Name, Adresse und Kontakte werden ersetzt, bevor der Text zur KI (Anthropic) geht. Namen anderer Personen, etwa auf Zeugnissen, erkennt der Assistent nur nach „Frau“ oder „Herr“. Bilder, Scans und alte Word-Dateien bleiben auf deinem Computer.",
    needsName: "Trag zuerst deinen Namen ein: So erkennt der Assistent ihn in den Unterlagen und schickt ihn nicht an die KI.",
    goToPerson: "Zu „Person und Kontakt“",
    running: "Die Unterlagen werden gelesen. Das kann ein bis zwei Minuten dauern; du kannst in dieser Zeit weiterarbeiten.",
    finished: "Die Vorschläge aus den Unterlagen sind da. Sie sind im Formular markiert.",
    filled: "Vorschläge stehen bereit. Bitte prüf jeden Eintrag:",
    nothing: "In den Unterlagen wurden keine passenden Angaben gefunden.",
    kept: "Hier hast du schon etwas eingetragen, das bleibt unverändert:",
    skipped: "Nicht gelesen:",
    shortened: "Nur der Anfang wurde gelesen, die Datei ist zu lang:",
    dropped: (n) => `${n === 1 ? "Eine Angabe passte" : `${n} Angaben passten`} nicht ins Formular und ${n === 1 ? "wurde" : "wurden"} weggelassen.`,
    suspicious: "Diese Zeilen in den Unterlagen richten sich an eine KI. Sie wurden nicht befolgt, schau sie dir an:",
    mark: (source) => `Vorschlag aus ${source}. Bitte prüfen.`,
    confirm: "Stimmt so",
    unchecked: (n) => `${n === 1 ? "Ein Vorschlag" : `${n} Vorschläge`} aus den Unterlagen ${n === 1 ? "ist" : "sind"} noch nicht geprüft. Erst danach lässt sich alles übernehmen.`,
    confirmAll: "Ich habe alle geprüft",
  },
};

function prefillReport(answer, merged) {
  return {
    filled: merged.filled, kept: merged.kept, read: answer.read, skipped: answer.skipped, shortened: answer.shortened,
    dropped: answer.dropped, suspicious: answer.suspicious_lines,
  };
}

const sectionLinks = (ids, ctx) => el("ul", {}, ids.map((id) => el("li", {}, el("button", {
  type: "button", className: "link", onclick: () => ctx.onGoTo(id),
}, ctx.titleOf(id)))));

function reportView(report, ctx, text) {
  return el("div", { role: "status" }, [
    report.filled.length ? el("p", {}, text.filled) : null,
    report.filled.length ? sectionLinks(report.filled, ctx) : null,
    report.read.length && !report.filled.length && !report.kept.length ? el("p", {}, text.nothing) : null,
    report.kept.length ? el("p", {}, `${text.kept} ${report.kept.map(ctx.titleOf).join(", ")}.`) : null,
    report.dropped ? el("p", { className: "hint" }, text.dropped(report.dropped)) : null,
    report.shortened.length ? el("p", { className: "hint" }, `${text.shortened} ${report.shortened.join(", ")}.`) : null,
    report.skipped.length ? el("p", {}, text.skipped) : null,
    report.skipped.length ? el("ul", {}, report.skipped.map((s) => el("li", {}, `${s.name}: ${s.reason}`))) : null,
    report.suspicious.length ? el("p", { className: "error" }, text.suspicious) : null,
    report.suspicious.length ? el("ul", {}, report.suspicious.map((line) => el("li", {}, line))) : null,
  ]);
}

/**
 * The card on the start (MIN-369): documents per category, then „Vorbefüllen“ or „Lieber von Hand ausfüllen“.
 * ctx: { form, track, uploads, messages, run: { running, problem, report }, hasName, titleOf(id), onRun(), onGoTo(id),
 *        onAdd(category, FileList), onRemove(index), onByHand() }
 */
function prefillCard(ctx) {
  const text = PREFILL_TEXT[ctx.track];
  const uploadText = UPLOAD_TEXT[ctx.track];
  const canRun = ctx.uploads.length > 0 && ctx.hasName;
  return el("section", { className: "card prefill-card", "aria-labelledby": "prefill-title" }, [
    el("h2", { id: "prefill-title" }, text.title),
    el("p", {}, text.text),
    el("div", { id: "upload-messages", className: "error", role: "alert" }, ctx.messages.map((m) => el("p", {}, m))),
    el("div", { className: "prefill-card__files" }, ctx.form.documents.categories.map((category) => categoryView(ctx, category, uploadText))),
    ctx.uploads.length && !ctx.hasName
      ? el("p", {}, [text.needsName, " ", el("button", { type: "button", className: "link", onclick: () => ctx.onGoTo("person") }, text.goToPerson)])
      : null,
    el("div", { className: "prefill-card__actions" }, [
      canRun ? el("button", { type: "button", className: "primary", id: "prefill", disabled: ctx.run.running, onclick: ctx.onRun }, text.run) : null,
      el("button", { type: "button", className: canRun ? "link" : "primary", onclick: ctx.onByHand }, text.byHand),
    ]),
    ctx.run.running ? el("p", { role: "status" }, text.running) : null,
    ctx.run.problem ? el("p", { className: "error", role: "alert" }, ctx.run.problem) : null,
    ctx.run.report ? reportView(ctx.run.report, ctx, text) : null,
    el("p", { className: "hint" }, `${text.privacy} ${uploadText.app}`),
  ]);
}

/** The mark above a suggested entry; `key` is the item („work.0“) or section („style“). */
function suggestionMark(key, source, onConfirm) {
  const text = PREFILL_TEXT[state.track];
  const where = source.place ? `${source.file}, ${source.place}` : source.file;
  return el("p", { className: "suggestion", dataset: { suggestion: key } }, [
    text.mark(where), " ",
    el("button", { type: "button", className: "link", onclick: () => onConfirm(key) }, text.confirm),
  ]);
}

/** On the last step: what is still unchecked keeps the take-over back. */
function uncheckedView(ctx) {
  const text = PREFILL_TEXT[ctx.track];
  return el("div", { className: "summary", id: "unchecked" }, [
    el("p", {}, text.unchecked(ctx.count)),
    sectionLinks(ctx.sections, ctx),
    el("button", { type: "button", id: "confirm-all", onclick: ctx.onConfirmAll }, text.confirmAll),
  ]);
}
