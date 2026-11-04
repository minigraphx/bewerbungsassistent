// Only in the page „Meine Angaben“ of the app: suggestions from uploaded documents, marked until they are checked.
// File names and everything from the AI are only ever set as text.
"use strict";

const PREFILL_TEXT = {
  job: {
    title: "Aus Unterlagen vorbefüllen",
    privacy: "Der Text aus PDF-, Word- und Textdateien geht an die KI (Anthropic), ohne Ihren Namen, Ihre Adresse und Ihre Kontaktangaben. Namen anderer Personen, etwa auf Zeugnissen, erkennt der Assistent nur nach „Frau“ oder „Herr“. Bilder und alte Word-Dateien bleiben auf diesem Computer. Die Vorschläge kommen ins Formular, nur in leere Felder; in die App übernommen wird erst, wenn Sie alles geprüft haben.",
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
    title: "Aus Unterlagen vorbefüllen",
    privacy: "Der Text aus PDF-, Word- und Textdateien geht an die KI (Anthropic), ohne deinen Namen, deine Adresse und deine Kontaktangaben. Namen anderer Personen, etwa auf Zeugnissen, erkennt der Assistent nur nach „Frau“ oder „Herr“. Bilder und alte Word-Dateien bleiben auf diesem Computer. Die Vorschläge kommen ins Formular, nur in leere Felder; in die App übernommen wird erst, wenn du alles geprüft hast.",
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

/** ctx: { track, run: { running, problem, report }, uploads, hasName, titleOf(id), onRun(), onGoTo(id) } */
function prefillView(ctx) {
  const text = PREFILL_TEXT[ctx.track];
  if (!ctx.uploads.length && !ctx.run.report) return null;
  return el("section", { className: "prefill item" }, [
    el("h3", {}, text.title),
    el("p", { className: "hint" }, text.privacy),
    ctx.hasName
      ? el("button", { type: "button", className: "primary", id: "prefill", disabled: ctx.run.running, onclick: ctx.onRun }, text.title)
      : el("p", {}, [text.needsName, " ", el("button", { type: "button", className: "link", onclick: () => ctx.onGoTo("person") }, text.goToPerson)]),
    ctx.run.running ? el("p", { role: "status" }, text.running) : null,
    ctx.run.problem ? el("p", { className: "error", role: "alert" }, ctx.run.problem) : null,
    ctx.run.report ? reportView(ctx.run.report, ctx, text) : null,
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
