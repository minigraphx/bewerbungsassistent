// Only in the page „Meine Angaben“ of the app: suggestions from uploaded documents, marked until they are checked.
// File names and everything from the AI are only ever set as text.
"use strict";

const PREFILL_TEXT = {
  job: {
    title: "Aus Ihren Unterlagen vorbefüllen",
    run: "Vorbefüllen",
    byHand: "Lieber von Hand ausfüllen",
    privacy: "Name, Adresse und Kontakte werden ersetzt, bevor der Text zur KI (Anthropic) geht. Namen anderer Personen, etwa auf Zeugnissen, erkennt die App nur nach „Frau“ oder „Herr“. Bilder, Scans und alte Word-Dateien bleiben auf Ihrem Computer.",
    needsName: "Tragen Sie zuerst Ihren Namen ein: So erkennt die App ihn in den Unterlagen und schickt ihn nicht an die KI.",
    goToPerson: "Zu „Person und Kontakt“",
    running: "Die Unterlagen werden gelesen. Das kann ein bis zwei Minuten dauern; Sie können in dieser Zeit weiterarbeiten.",
    busy: "Wird gelesen …",
    waiting: "Die Unterlagen werden noch hochgeladen. Danach liest die App sie, ohne dass Sie nochmals klicken.",
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
    run: "Vorbefüllen",
    byHand: "Lieber von Hand ausfüllen",
    privacy: "Name, Adresse und Kontakte werden ersetzt, bevor der Text zur KI (Anthropic) geht. Namen anderer Personen, etwa auf Zeugnissen, erkennt die App nur nach „Frau“ oder „Herr“. Bilder, Scans und alte Word-Dateien bleiben auf deinem Computer.",
    needsName: "Trag zuerst deinen Namen ein: So erkennt die App ihn in den Unterlagen und schickt ihn nicht an die KI.",
    goToPerson: "Zu „Person und Kontakt“",
    running: "Die Unterlagen werden gelesen. Das kann ein bis zwei Minuten dauern; du kannst in dieser Zeit weiterarbeiten.",
    busy: "Wird gelesen …",
    waiting: "Die Unterlagen werden noch hochgeladen. Danach liest die App sie, ohne dass du nochmals klickst.",
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
 * The card on the start (MIN-369, G84): one area for all documents, a row per file with its kind, then „Vorbefüllen“
 * or „Lieber von Hand ausfüllen“. Without files only intro, area and hint, and filling in by hand leads.
 * ctx: { form, track, uploads, messages, notes (datei → recognised by name), announcement, run: { running, problem, report },
 *        hasName, titleOf(id), onRun(), onGoTo(id), onAddFiles(FileList), onChangeKind(upload, category), onRemove(index),
 *        onByHand() }
 */
function prefillCard(ctx) {
  const text = PREFILL_TEXT[ctx.track];
  const uploadText = UPLOAD_TEXT[ctx.track];
  const hasFiles = ctx.uploads.length > 0;
  const canRun = hasFiles && ctx.hasName;
  return el("section", { className: "card prefill-card", "aria-labelledby": "prefill-title", ...dropHandlers(ctx) }, [
    el("h2", { id: "prefill-title" }, text.title),
    el("p", {}, DROP_TEXT[ctx.track].intro),
    dropAreaView(ctx),
    el("p", { className: "hint" }, DROP_TEXT[ctx.track].hint),
    el("div", { id: "upload-messages", className: "error", role: "alert" }, ctx.messages.map((m) => el("p", {}, m))),
    dropFilesView(ctx),
    el("p", { id: "upload-status", className: "drop-status", role: "status" }, ctx.announcement || ""),
    hasFiles && !ctx.hasName
      ? el("p", {}, [text.needsName, " ", el("button", { type: "button", className: "link", onclick: () => ctx.onGoTo("person") }, text.goToPerson)])
      : null,
    el("div", { className: "prefill-card__run" }, [
      el("div", { className: "prefill-card__actions" }, [
        canRun ? el("button", {
          type: "button", className: `primary${ctx.run.running ? " busy" : ""}`, id: "prefill", disabled: ctx.run.running,
          "aria-busy": ctx.run.running ? "true" : null, onclick: ctx.onRun,
        }, ctx.run.running ? text.busy : text.run) : null,
        el("button", { type: "button", className: canRun ? "link" : "primary", onclick: ctx.onByHand }, text.byHand),
      ]),
      runLine(ctx.run, text),
    ]),
    ctx.run.report ? reportView(ctx.run.report, ctx, text) : null,
    hasFiles ? el("p", { className: "hint" }, `${text.privacy} ${uploadText.app}`) : null,
  ]);
}

/** Right after the buttons, so it is seen where the person clicked: what runs, or what went wrong. */
function runLine(run, text) {
  if (run.running) return el("p", { id: "prefill-status", className: "prefill-card__status", role: "status" }, run.waiting ? text.waiting : text.running);
  if (run.problem) return el("p", { id: "prefill-status", className: "error", role: "alert" }, run.problem);
  return null;
}

/**
 * The click on „Vorbefüllen“ (#156): the busy state shows and is brought into view before anything is awaited.
 * Uploads still on their way finish first, because the app reads only what has arrived; the page says so meanwhile.
 * steps: { show(run), reveal(), pendingUploads() → Promise or null, isCurrent() → boolean, ask() → Promise }
 * Resolves to the answer of ask(), or null when another run or other answers overtook this one.
 */
async function startPrefill(steps) {
  const pending = steps.pendingUploads();
  steps.show({ running: true, waiting: Boolean(pending), problem: null, report: null });
  steps.reveal();
  if (pending) {
    await pending.then(() => null, () => null); // a failed upload has its own message in the list
    if (!steps.isCurrent()) return null;
    steps.show({ running: true, waiting: false, problem: null, report: null });
    steps.reveal(); // the new files in the list may have pushed the text out of view
  }
  return steps.ask();
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
