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
    running: (minutes) => `Die Unterlagen werden gelesen. Das dauert etwa ${minutesText(minutes)}; Sie können in dieser Zeit weiterarbeiten.`,
    busy: "Wird gelesen …",
    noneReadable: "Keine dieser Dateien geht an die KI. Bilder, Scans und alte Word-Dateien ergänzen Sie von Hand.",
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
    running: (minutes) => `Die Unterlagen werden gelesen. Das dauert etwa ${minutesText(minutes)}; du kannst in dieser Zeit weiterarbeiten.`,
    busy: "Wird gelesen …",
    noneReadable: "Keine dieser Dateien geht an die KI. Bilder, Scans und alte Word-Dateien ergänzt du von Hand.",
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

// Cost and time before the run (G85, #271): the same words as „Alle prüfen“ (TrefferLogik.estimateLine, G44), in CHF
// with the credit of the mediation (G46, G80). One text for Sie and du.
const ESTIMATE_WORDS = {
  files: (n) => (n === 1 ? "1 Datei geht an die KI." : `${n} Dateien gehen an die KI.`),
  uploading: "Die Dateien werden noch hochgeladen. Danach nennt die App Kosten und Dauer.",
  estimating: "Kosten und Dauer werden geschätzt …",
  over: (money) => `Im Guthaben sind noch ${money}, das reicht vielleicht nicht.`,
  notRead: "Geht nicht an die KI:",
  shortened: "Nur der Anfang geht an die KI, die Datei ist zu lang:",
  failed: (reason) => `Die Schätzung fehlt: ${reason}`,
  retry: "Neu schätzen",
};
const ESTIMATE_NONE = { phase: "none", answer: null, problem: null };
const STATUS_ID = "prefill-status";

const minutesText = (n) => (n === 1 ? "1 Minute" : `${n} Minuten`);
const moneyText = (amount, currency) => `${currency || "USD"} ${Number(amount).toFixed(2)}`;
const withCredit = (answer) => typeof answer.guthaben === "number";
const creditUsedUp = (answer) => withCredit(answer) && answer.guthaben <= 0;
const readyAnswer = (estimate) => (estimate && estimate.phase === "ready" ? estimate.answer : null);

/** Whether „Vorbefüllen“ can start now: the estimate stands, a file goes to the AI and there is credit left. */
function runAllowed(ctx) {
  const answer = readyAnswer(ctx.estimate);
  return Boolean(answer) && answer.anzahl > 0 && !creditUsedUp(answer) && !ctx.run.running;
}

/** App.el of the other pages takes `class` and its children one by one; texte.js builds the link with it. */
const appEl = (tag, attrs, ...children) => el(tag, Object.fromEntries(Object.entries(attrs || {})
  .map(([key, value]) => [key === "class" ? "className" : key, value])), children);

/** „anfordern“ as the link of #315 where texte.js is loaded, as in the app. */
const withRequestLink = (sentence) => (typeof Texte === "undefined" ? [sentence] : Texte.withCodeRequestLink(sentence, appEl));

/** The credit afterwards, a warning when the estimate is above it, or that it is used up; null without credit. */
function creditLine(answer) {
  if (!withCredit(answer)) return null;
  const usedUp = creditUsedUp(answer);
  if (!usedUp && answer.kosten > answer.guthaben) {
    return el("p", { className: "prefill-card__credit warning" }, ESTIMATE_WORDS.over(moneyText(answer.guthaben, answer.waehrung)));
  }
  const about = TrefferLogik.estimateLine({ ...answer, guthaben: null });
  const sentence = TrefferLogik.estimateLine({ ...answer, reicht_fuer: null }).slice(about.length).trim();
  return el("p", { className: `prefill-card__credit${usedUp ? " error" : ""}` }, withRequestLink(sentence));
}

function namedList(title, lines) {
  return lines.length ? [el("p", {}, title), el("ul", { className: "prefill-card__files" }, lines.map((line) => el("li", {}, line)))] : [];
}

function readyLines(answer, text) {
  const lines = answer.anzahl
    ? [el("p", {}, `${ESTIMATE_WORDS.files(answer.anzahl)} ${TrefferLogik.estimateLine({ ...answer, guthaben: null })}`), creditLine(answer)]
    : [el("p", {}, text.noneReadable)];
  return [
    ...lines,
    ...namedList(ESTIMATE_WORDS.notRead, (answer.nicht_gelesen || []).map((s) => `${s.name}: ${s.grund}`)),
    ...namedList(ESTIMATE_WORDS.shortened, answer.gekuerzt || []),
  ];
}

/** What stands under the button: the running text, else the estimate in its state. */
function estimateLines(ctx, text) {
  if (ctx.run.running) return [el("p", {}, text.running(ctx.run.minutes))];
  const estimate = ctx.estimate || ESTIMATE_NONE;
  if (estimate.phase === "uploading") return [el("p", {}, ESTIMATE_WORDS.uploading)];
  if (estimate.phase === "failed") {
    return [el("p", { className: "error" }, ESTIMATE_WORDS.failed(estimate.problem)),
      el("button", { type: "button", className: "link", onclick: ctx.onEstimate }, ESTIMATE_WORDS.retry)];
  }
  if (estimate.phase === "ready") return readyLines(estimate.answer, text);
  return [el("p", {}, ESTIMATE_WORDS.estimating)];
}

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
 * ctx: { form, track, uploads, messages, notes (datei → recognised by name), announcement,
 *        run: { running, minutes, problem, report }, estimate: { phase: none|uploading|estimating|ready|failed, answer, problem },
 *        hasName, titleOf(id), onRun(), onGoTo(id), onAddFiles(FileList), onChangeKind(upload, category), onRemove(index),
 *        onByHand(), onEstimate() }
 */
function prefillCard(ctx) {
  const text = PREFILL_TEXT[ctx.track];
  const uploadText = UPLOAD_TEXT[ctx.track];
  const hasFiles = ctx.uploads.length > 0;
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
    prefillRunArea(ctx),
    ctx.run.report ? reportView(ctx.run.report, ctx, text) : null,
    hasFiles ? el("p", { className: "hint" }, `${text.privacy} ${uploadText.app}`) : null,
  ]);
}

/**
 * The buttons, right under them what the run costs and takes or what it waits for (G85), then a problem of the run.
 * Without any file for the AI there is no run button; filling in by hand leads.
 */
function prefillRunArea(ctx) {
  const text = PREFILL_TEXT[ctx.track];
  const hasFiles = ctx.uploads.length > 0;
  const answer = readyAnswer(ctx.estimate);
  const canRun = hasFiles && ctx.hasName && !(answer && answer.anzahl === 0);
  const uploading = Boolean(ctx.estimate) && ctx.estimate.phase === "uploading"; // also the very first files
  return el("div", { className: "prefill-card__run" }, [
    el("div", { className: "prefill-card__actions" }, [
      canRun ? el("button", {
        type: "button", className: `primary${ctx.run.running ? " busy" : ""}`, id: "prefill", disabled: !runAllowed(ctx),
        "aria-busy": ctx.run.running ? "true" : null, "aria-describedby": STATUS_ID, onclick: ctx.onRun,
      }, ctx.run.running ? text.busy : text.run) : null,
      el("button", { type: "button", id: "prefill-by-hand", className: canRun ? "link" : "primary", onclick: ctx.onByHand }, text.byHand),
    ]),
    hasFiles || uploading ? el("div", { id: STATUS_ID, className: "prefill-card__status", role: "status", tabIndex: -1 }, estimateLines(ctx, text)) : null,
    ctx.run.problem ? el("p", { id: "prefill-problem", className: "error", role: "alert" }, ctx.run.problem) : null,
  ]);
}

/**
 * The click on „Vorbefüllen“ (#156): the busy state shows and is brought into view before anything is awaited.
 * The button waits for the estimate, so uploads have arrived; a kind saved by leaving its select on this very click
 * is still awaited, because the app reads only what has arrived.
 * steps: { show(), reveal(), pendingUploads() → Promise or null, isCurrent() → boolean, ask() → Promise }
 * Resolves to the answer of ask(), or null when another run or other answers overtook this one.
 */
async function startPrefill(steps) {
  const pending = steps.pendingUploads();
  steps.show();
  steps.reveal();
  if (pending) {
    await pending.then(() => null, () => null); // a failed move has its own message in the list
    if (!steps.isCurrent()) return null;
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
