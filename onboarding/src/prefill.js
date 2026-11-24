// Only in the page „Meine Angaben“ of the app: suggestions from uploaded documents, marked until they are checked.
// File names and everything from the AI are only ever set as text.
"use strict";

// The words of the card, said when they are shown, so they follow the app language (#433). One sentence per number:
// French and English do not build „Angabe passte“ and „Angaben passten“ from the same parts.
const PREFILL_SHARED = {
  run: () => T("Vorbefüllen"),
  byHand: () => T("Lieber von Hand ausfüllen"),
  goToPerson: () => T("Zu „Person und Kontakt“"),
  busy: () => T("Wird gelesen …"),
  finished: () => T("Die Vorschläge aus den Unterlagen sind da. Sie sind im Formular markiert."),
  nothing: () => T("In den Unterlagen wurden keine passenden Angaben gefunden."),
  skipped: () => T("Nicht gelesen:"),
  shortened: (files) => T("Nur der Anfang wurde gelesen, die Datei ist zu lang: {dateien}.", { dateien: files }),
  dropped: (n) => (n === 1 ? T("Eine Angabe passte nicht ins Formular und wurde weggelassen.")
    : T("{anzahl} Angaben passten nicht ins Formular und wurden weggelassen.", { anzahl: n })),
  mark: (source) => T("Vorschlag aus {quelle}. Bitte prüfen.", { quelle: source }),
  confirm: () => T("Stimmt so"),
  unchecked: (n) => (n === 1 ? T("Ein Vorschlag aus den Unterlagen ist noch nicht geprüft. Erst danach lässt sich alles übernehmen.")
    : T("{anzahl} Vorschläge aus den Unterlagen sind noch nicht geprüft. Erst danach lässt sich alles übernehmen.", { anzahl: n })),
  confirmAll: () => T("Ich habe alle geprüft"),
};
const PREFILL_TEXT = {
  job: {
    ...PREFILL_SHARED,
    title: () => T("Aus Ihren Unterlagen vorbefüllen"),
    privacy: () => T("Name, Adresse und Kontakte werden ersetzt, bevor der Text zur KI (Anthropic) geht. Namen anderer Personen, etwa auf Zeugnissen, erkennt die App nur nach einer Anrede wie „Frau“, „Herr“, „Madame“, „Monsieur“, „Mr“ oder „Ms“. Bilder, Scans und alte Word-Dateien bleiben auf Ihrem Computer."),
    needsName: () => T("Tragen Sie zuerst Ihren Namen ein: So erkennt die App ihn in den Unterlagen und schickt ihn nicht an die KI."),
    running: (minutes) => T("Die Unterlagen werden gelesen. Das dauert etwa {dauer}; Sie können in dieser Zeit weiterarbeiten.", { dauer: minutesText(minutes) }),
    noneReadable: () => T("Keine dieser Dateien geht an die KI. Bilder, Scans und alte Word-Dateien ergänzen Sie von Hand."),
    filled: () => T("Vorschläge stehen bereit. Bitte prüfen Sie jeden Eintrag:"),
    kept: (sections) => T("Hier haben Sie schon etwas eingetragen, das bleibt unverändert: {abschnitte}.", { abschnitte: sections }),
    suspicious: () => T("Diese Zeilen in den Unterlagen richten sich an eine KI. Sie wurden nicht befolgt, schauen Sie sie sich an:"),
  },
  apprenticeship: {
    ...PREFILL_SHARED,
    title: () => T("Aus deinen Unterlagen vorbefüllen"),
    privacy: () => T("Name, Adresse und Kontakte werden ersetzt, bevor der Text zur KI (Anthropic) geht. Namen anderer Personen, etwa auf Zeugnissen, erkennt die App nur nach einer Anrede wie „Frau“, „Herr“, „Madame“, „Monsieur“, „Mr“ oder „Ms“. Bilder, Scans und alte Word-Dateien bleiben auf deinem Computer."),
    needsName: () => T("Trag zuerst deinen Namen ein: So erkennt die App ihn in den Unterlagen und schickt ihn nicht an die KI."),
    running: (minutes) => T("Die Unterlagen werden gelesen. Das dauert etwa {dauer}; du kannst in dieser Zeit weiterarbeiten.", { dauer: minutesText(minutes) }),
    noneReadable: () => T("Keine dieser Dateien geht an die KI. Bilder, Scans und alte Word-Dateien ergänzt du von Hand."),
    filled: () => T("Vorschläge stehen bereit. Bitte prüf jeden Eintrag:"),
    kept: (sections) => T("Hier hast du schon etwas eingetragen, das bleibt unverändert: {abschnitte}.", { abschnitte: sections }),
    suspicious: () => T("Diese Zeilen in den Unterlagen richten sich an eine KI. Sie wurden nicht befolgt, schau sie dir an:"),
  },
};

// Cost and time before the run (G85, #271): the same words as „Alle prüfen“ (TrefferLogik.estimateLine, G44), in CHF
// with the budget of the mediation's month (G46, G98), or its one-time credit when it names no renewal (G80). One text
// for Sie and du.
const ESTIMATE_WORDS = {
  files: (n) => (n === 1 ? T("1 Datei geht an die KI.") : T("{anzahl} Dateien gehen an die KI.", { anzahl: n })),
  uploading: () => T("Die Dateien werden noch hochgeladen. Danach nennt die App Kosten und Dauer."),
  estimating: () => T("Kosten und Dauer werden geschätzt …"),
  over: (money, monthly) => (monthly ? T("Im Budget sind noch {betrag}, das reicht vielleicht nicht.", { betrag: money })
    : T("Im Guthaben sind noch {betrag}, das reicht vielleicht nicht.", { betrag: money })),
  notRead: () => T("Geht nicht an die KI:"),
  shortened: () => T("Nur der Anfang geht an die KI, die Datei ist zu lang:"),
  failed: (reason) => T("Die Schätzung fehlt: {grund}", { grund: reason }),
  retry: () => T("Neu schätzen"),
};
const ESTIMATE_NONE = { phase: "none", answer: null, problem: null };
const STATUS_ID = "prefill-status";
const FILES_ID = "prefill-files";
const RETRY_ID = "prefill-retry";

// Number and unit never part at the end of a line (#336), as in treffer-logik.js; read aloud as a space.
const NBSP = "\u00a0";
const minutesText = (n) => (n === 1 ? T("{anzahl}{nbsp}Minute", { anzahl: n, nbsp: NBSP })
  : T("{anzahl}{nbsp}Minuten", { anzahl: n, nbsp: NBSP }));
const moneyText = (amount, currency) => `${currency || "USD"}${NBSP}${Number(amount).toFixed(2)}`;
const withCredit = (answer) => typeof answer.guthaben === "number";
const creditUsedUp = (answer) => withCredit(answer) && answer.guthaben <= 0;
const readyAnswer = (estimate) => (estimate && estimate.phase === "ready" ? estimate.answer : null);
const estimatePending = (estimate) => Boolean(estimate) && ["uploading", "estimating"].includes(estimate.phase);

/** What the line shows: for the first moment of estimating again the estimate before it, so a quick answer does not flicker. */
function shownEstimate(estimate) {
  const current = estimate || ESTIMATE_NONE;
  if (current.phase !== "estimating" || current.slow) return current;
  return current.held || { ...current, quiet: true };
}

/** Whether „Vorbefüllen“ can start now: the estimate stands, a file goes to the AI and there is credit left. */
function runAllowed(ctx) {
  const answer = readyAnswer(ctx.estimate);
  return Boolean(answer) && answer.anzahl > 0 && !creditUsedUp(answer) && !ctx.run.running;
}

/** „anfordern“ as the link of #315 where texte.js is loaded, as in the app. */
const withRequestLink = (sentence) => (typeof Texte === "undefined" ? [sentence] : Texte.withCodeRequestLink(sentence, appEl));

/** The credit afterwards, a warning when the estimate is above it, or that it is used up; null without credit. */
function creditLine(answer) {
  if (!withCredit(answer)) return null;
  const usedUp = creditUsedUp(answer);
  if (!usedUp && answer.kosten > answer.guthaben) {
    const monthly = typeof Texte !== "undefined" && Texte.budgetMonth(answer) !== null;
    return el("p", { className: "prefill-card__credit warning" }, ESTIMATE_WORDS.over(moneyText(answer.guthaben, answer.waehrung), monthly));
  }
  const about = TrefferLogik.estimateLine({ ...answer, guthaben: null });
  const sentence = TrefferLogik.estimateLine({ ...answer, reicht_fuer: null }).slice(about.length).trim();
  return el("p", { className: `prefill-card__credit${usedUp ? " error" : ""}` }, withRequestLink(sentence));
}

function namedList(title, lines) {
  return lines.length ? [el("p", {}, title), el("ul", { className: "prefill-card__files" }, lines.map((line) => el("li", {}, line)))] : [];
}

function readyLines(answer, text) {
  return answer.anzahl
    ? [el("p", {}, `${ESTIMATE_WORDS.files(answer.anzahl)} ${TrefferLogik.estimateLine({ ...answer, guthaben: null })}`), creditLine(answer)]
    : [el("p", {}, text.noneReadable())];
}

/** What stands under the button: the running text, else the estimate in its state. */
function estimateLines(ctx, text) {
  if (ctx.run.running) return [el("p", {}, text.running(ctx.run.minutes))];
  const estimate = shownEstimate(ctx.estimate);
  if (estimate.phase === "uploading") return [el("p", {}, ESTIMATE_WORDS.uploading())];
  if (estimate.phase === "failed") {
    return [el("p", { className: "error" }, ESTIMATE_WORDS.failed(estimate.problem)),
      el("button", { type: "button", id: RETRY_ID, className: "link", onclick: ctx.onEstimate }, ESTIMATE_WORDS.retry())];
  }
  if (estimate.phase === "ready") return readyLines(estimate.answer, text);
  return estimate.quiet ? [] : [el("p", {}, ESTIMATE_WORDS.estimating())];
}

/** The files left out or shortened, beside the status: read when the button is, not again at every change. */
function filesView(ctx) {
  const answer = ctx.run.running ? null : readyAnswer(shownEstimate(ctx.estimate));
  return el("div", { id: FILES_ID, className: "prefill-card__left-out" }, answer ? [
    ...namedList(ESTIMATE_WORDS.notRead(), (answer.nicht_gelesen || []).map((s) => fileMessage(s.name, s.grund))),
    ...namedList(ESTIMATE_WORDS.shortened(), answer.gekuerzt || []),
  ] : []);
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
    report.filled.length ? el("p", {}, text.filled()) : null,
    report.filled.length ? sectionLinks(report.filled, ctx) : null,
    report.read.length && !report.filled.length && !report.kept.length ? el("p", {}, text.nothing()) : null,
    report.kept.length ? el("p", {}, text.kept(report.kept.map(ctx.titleOf).join(", "))) : null,
    report.dropped ? el("p", { className: "hint" }, text.dropped(report.dropped)) : null,
    report.shortened.length ? el("p", { className: "hint" }, text.shortened(report.shortened.join(", "))) : null,
    report.skipped.length ? el("p", {}, text.skipped()) : null,
    report.skipped.length ? el("ul", {}, report.skipped.map((s) => el("li", {}, fileMessage(s.name, s.reason)))) : null,
    report.suspicious.length ? el("p", { className: "error" }, text.suspicious()) : null,
    report.suspicious.length ? el("ul", {}, report.suspicious.map((line) => el("li", {}, line))) : null,
  ]);
}

/**
 * The card on the start (MIN-369, G84): one area for all documents, a row per file with its kind, then „Vorbefüllen“
 * or „Lieber von Hand ausfüllen“. Without files only intro, area and hint, and filling in by hand leads.
 * ctx: { form, track, uploads, messages, notes (datei → recognised by name), announcement,
 *        run: { running, minutes, problem, report }, estimate: { phase: none|uploading|estimating|ready|failed, answer, problem,
 *        while estimating also held (the estimate before) and slow (the answer takes longer than a moment) },
 *        hasName, titleOf(id), onRun(), onGoTo(id), onAddFiles(FileList), onChangeKind(upload, category), onRemove(index),
 *        onByHand(), onEstimate() }
 */
function prefillCard(ctx) {
  const text = PREFILL_TEXT[ctx.track];
  const uploadText = UPLOAD_TEXT[ctx.track];
  const hasFiles = ctx.uploads.length > 0;
  return el("section", { className: "card prefill-card", "aria-labelledby": "prefill-title", ...dropHandlers(ctx) }, [
    el("h2", { id: "prefill-title" }, text.title()),
    el("p", {}, DROP_TEXT[ctx.track].intro()),
    dropAreaView(ctx),
    el("p", { className: "hint" }, DROP_TEXT[ctx.track].hint()),
    el("div", { id: "upload-messages", className: "error", role: "alert" }, ctx.messages.map((m) => el("p", {}, m))),
    dropFilesView(ctx),
    el("p", { id: "upload-status", className: "drop-status", role: "status" }, ctx.announcement || ""),
    hasFiles && !ctx.hasName
      ? el("p", {}, [text.needsName(), " ", el("button", { type: "button", className: "link", onclick: () => ctx.onGoTo("person") }, text.goToPerson())])
      : null,
    prefillRunArea(ctx),
    ctx.run.report ? reportView(ctx.run.report, ctx, text) : null,
    hasFiles ? el("p", { className: "hint" }, `${text.privacy()} ${uploadText.app()}`) : null,
  ]);
}

/**
 * The buttons, right under them a problem of the run, then what the run costs and takes or what it waits for (G85)
 * and which files are left out. Without any file for the AI there is no run button; filling in by hand leads.
 */
function prefillRunArea(ctx) {
  const text = PREFILL_TEXT[ctx.track];
  const hasFiles = ctx.uploads.length > 0;
  const answer = readyAnswer(shownEstimate(ctx.estimate));
  const canRun = hasFiles && ctx.hasName && !(answer && answer.anzahl === 0);
  const uploading = Boolean(ctx.estimate) && ctx.estimate.phase === "uploading"; // also the very first files
  const withLine = hasFiles || uploading;
  return el("div", { className: "prefill-card__run" }, [
    el("div", { className: "prefill-card__actions" }, [
      canRun ? el("button", {
        type: "button", className: `primary${ctx.run.running ? " busy" : ""}`, id: "prefill", disabled: !runAllowed(ctx),
        "aria-busy": ctx.run.running ? "true" : null, "aria-describedby": `${STATUS_ID} ${FILES_ID}`, onclick: ctx.onRun,
      }, ctx.run.running ? text.busy() : text.run()) : null,
      el("button", { type: "button", id: "prefill-by-hand", className: canRun ? "link" : "primary", onclick: ctx.onByHand }, text.byHand()),
    ]),
    ctx.run.problem ? el("p", { id: "prefill-problem", className: "error", role: "alert" }, ctx.run.problem) : null,
    withLine ? el("div", {
      id: STATUS_ID, className: "prefill-card__status", role: "status", tabIndex: -1,
      "aria-busy": !ctx.run.running && estimatePending(ctx.estimate) ? "true" : null,
    }, estimateLines(ctx, text)) : null,
    withLine ? filesView(ctx) : null,
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
    el("button", { type: "button", className: "link", onclick: () => onConfirm(key) }, text.confirm()),
  ]);
}

/** On the last step: what is still unchecked keeps the take-over back. */
function uncheckedView(ctx) {
  const text = PREFILL_TEXT[ctx.track];
  return el("div", { className: "summary", id: "unchecked" }, [
    el("p", {}, text.unchecked(ctx.count)),
    sectionLinks(ctx.sections, ctx),
    el("button", { type: "button", id: "confirm-all", onclick: ctx.onConfirmAll }, text.confirmAll()),
  ]);
}
