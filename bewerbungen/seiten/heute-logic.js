"use strict";
// Heute (#260, A1): dates and deadlines, the stand by stage, the line under the title and the pass over saved jobs
// (G38). Rows come from UebersichtLogik.mitSchritten. No DOM, so it can be tested (tests/heute.test.cjs). Texts in the
// app language through Texte.t (#419, tests/today_languages.test.cjs).
(function (global) {
  const SAVED = ["Gemerkt", "Bewerben"];
  const APPLIED = ["Beworben", "Gespräch"];
  const CLOSED = ["Zusage", "Absage", "Verworfen", "Zurückgezogen"];
  const WEEK_DAYS = 7;
  const PREPARE_DAYS_AHEAD = 2;  // „rechtzeitig“ in A1: time to read the ad and the letter again
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  const overview = () => (typeof module !== "undefined" ? require("./uebersicht-logik.js") : global.UebersichtLogik);

  const day = iso => `${iso.slice(8, 10)}.${iso.slice(5, 7)}.`;

  /** „Vier“ for the line under the title, up to twelve in words; one has its own sentence. */
  function numberWord(count) {
    const Texte = texts();
    const words = [Texte.t("Zwei"), Texte.t("Drei"), Texte.t("Vier"), Texte.t("Fünf"), Texte.t("Sechs"),
                   Texte.t("Sieben"), Texte.t("Acht"), Texte.t("Neun"), Texte.t("Zehn"), Texte.t("Elf"), Texte.t("Zwölf")];
    return words[count - 2] || String(count);
  }

  function addDays(iso, days) {
    const date = new Date(`${iso}T12:00:00Z`);
    date.setUTCDate(date.getUTCDate() + days);
    return date.toISOString().slice(0, 10);
  }

  /** An interview at a company and the reminder to prepare it, for an apprenticeship an invitation. */
  function interviewTexts(firma, apprenticeship) {
    const Texte = texts();
    return apprenticeship
      ? { date: Texte.t("Einladung bei {firma}", { firma }), prepare: Texte.t("Einladung bei {firma} vorbereiten", { firma }) }
      : { date: Texte.t("Gespräch bei {firma}", { firma }), prepare: Texte.t("Gespräch bei {firma} vorbereiten", { firma }) };
  }

  /** The reminder to prepare an interview (#268): two days ahead, today when that has passed, never on the day. */
  function preparation(date, today, text) {
    const day = addDays(date, -PREPARE_DAYS_AHEAD) > today ? addDays(date, -PREPARE_DAYS_AHEAD) : today;
    return day < date ? [{ date: day, text }] : [];
  }

  // An interview date counts once the application is sent, even if the stage still says Beworben; with one set,
  // following up no longer applies. The follow-up date comes with the step, also while the Job-Room entry is open.
  function datesOf({ bewerbung: b, schritt }, apprenticeship, today) {
    const Texte = texts();
    const found = [];
    if (SAVED.includes(b.status) && b.frist) {
      found.push({ date: b.frist, text: Texte.t("Frist für {stelle}", { stelle: [b.stelle, b.firma].filter(Boolean).join(", ") }) });
    }
    if (APPLIED.includes(b.status) && b.gespraech_am) {
      const { date, prepare } = interviewTexts(b.firma, apprenticeship);
      found.push(...preparation(b.gespraech_am, today, prepare), { date: b.gespraech_am, text: date });
    } else if (b.status === "Beworben" && schritt.zusatz) {
      found.push({ date: schritt.zusatz, text: Texte.t("Nachfragen bei {firma}, falls keine Antwort da ist", { firma: b.firma }) });
    }
    return found;
  }

  /** Termine und Fristen: deadlines, interviews with their preparation and follow-ups from today on, soonest first. */
  function dates(rows, today, { max = 5, apprenticeship = false } = {}) {
    return rows.flatMap(row => datesOf(row, apprenticeship, today))
      .filter(entry => /^\d{4}-\d{2}-\d{2}$/.test(entry.date) && entry.date >= today)
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(0, max)
      .map(entry => ({ ...entry, day: day(entry.date) }));
  }

  const withStatus = (rows, statuses) => rows.filter(row => statuses.includes(row.bewerbung.status));

  function closedHint(rows) {
    return CLOSED.map(status => [status, withStatus(rows, [status]).length])
      .filter(([, count]) => count > 0)
      .map(([status, count]) => overview().abgeschlossenTeil(status, count))
      .join(", ");
  }

  function deadlinesHint(count) {
    const Texte = texts();
    if (!count) return "";
    return count === 1 ? Texte.t("1 Frist in dieser Woche") : Texte.t("{anzahl} Fristen in dieser Woche", { anzahl: count });
  }

  function interviewsHint(count, apprenticeship) {
    const Texte = texts();
    if (!count) return "";
    if (apprenticeship) return count === 1 ? Texte.t("1 Einladung") : Texte.t("{anzahl} Einladungen", { anzahl: count });
    return count === 1 ? Texte.t("1 Gespräch") : Texte.t("{anzahl} Gespräche", { anzahl: count });
  }

  function hitsHint(hits) {
    const Texte = texts();
    return hits?.last ? Texte.t("aus der Suche vom {datum}", { datum: day(hits.last.slice(0, 10)) }) : Texte.t("noch keine Suche");
  }

  /** Ihr Stand: { neu, gemerkt, beworben, abgeschlossen }, each { count, hint }. `hits` is { count, last } or null. */
  function stand(rows, hits, today, { apprenticeship = false } = {}) {
    const saved = withStatus(rows, SAVED);
    const weekEnd = addDays(today, WEEK_DAYS - 1);
    const dueThisWeek = saved.filter(({ bewerbung: b }) => b.frist && b.frist >= today && b.frist <= weekEnd).length;
    return {
      neu: { count: hits ? hits.count : 0, hint: hitsHint(hits) },
      gemerkt: { count: saved.length, hint: deadlinesHint(dueThisWeek) },
      beworben: { count: withStatus(rows, APPLIED).length, hint: interviewsHint(withStatus(rows, ["Gespräch"]).length, apprenticeship) },
      abgeschlossen: { count: withStatus(rows, CLOSED).length, hint: closedHint(rows) },
    };
  }

  /** The line under the title as a key of texte.js with its values. */
  function waiting(count) {
    if (count <= 0) return { key: "heute.wartet.nichts", values: {} };
    if (count === 1) return { key: "heute.wartet.eins", values: {} };
    return { key: "heute.wartet.viele", values: { anzahl: numberWord(count) } };
  }

  /** „Montag, 23. November“ for the line under the title, in the app language; French says the first „1er“. */
  function todayLine(date) {
    const Texte = texts();
    const weekdays = [Texte.t("Sonntag"), Texte.t("Montag"), Texte.t("Dienstag"), Texte.t("Mittwoch"),
                      Texte.t("Donnerstag"), Texte.t("Freitag"), Texte.t("Samstag")];
    const words = { wochentag: weekdays[date.getDay()], tag: date.getDate(), monat: Texte.monthName(date.getMonth() + 1) };
    return date.getDate() === 1 ? Texte.t("{wochentag}, 1. {monat}", words) : Texte.t("{wochentag}, {tag}. {monat}", words);
  }

  // The pass over saved jobs (G38): one after the other, the person decides, the app changes only the stage.

  /** Ids of the saved jobs not decided yet, in the order of the list (closest deadline first). */
  function passQueue(rows) {
    return withStatus(rows, ["Gemerkt"]).map(row => row.bewerbung.id);
  }

  function passProgress(index, total) {
    const Texte = texts();
    return Texte.t("{nummer} von {anzahl}", { nummer: index + 1, anzahl: total });
  }

  function passResult({ bewerben = 0, verworfen = 0, spaeter = 0 } = {}) {
    const Texte = texts();
    const discarded = verworfen === 1 ? Texte.t("1 verworfen") : Texte.t("{anzahl} verworfen", { anzahl: verworfen });
    const parts = [[bewerben, Texte.t("{anzahl} zum Bewerben", { anzahl: bewerben })], [verworfen, discarded],
                   [spaeter, Texte.t("{anzahl} für später", { anzahl: spaeter })]]
      .filter(([count]) => count > 0).map(([, text]) => text);
    return parts.length ? Texte.t("Durchgang fertig: {teile}.", { teile: parts.join(", ") }) : Texte.t("Durchgang fertig.");
  }

  const WEB_LINK = /^https?:\/\//i;

  /**
   * The ad the pass shows (G38): the text, or the lines saying it is missing, why and how to get it (G37), with the
   * link to the ad when it is a web address. `missing` is `text_fehlt` of /api/bewerbung.
   */
  function passAd(job, text, missing) {
    if (!missing && (text || "").trim()) return { text: text.trim() };
    const Texte = texts();
    const lines = [Texte.t("Zu dieser Stelle fehlt der Inseratstext."), missing && missing.grund, missing && missing.weg].filter(Boolean);
    return { zeilen: lines, link: WEB_LINK.test(job.link || "") ? job.link : "" };
  }

  const logic = { dates, stand, waiting, todayLine, passQueue, passProgress, passResult, passAd };
  if (typeof module !== "undefined") module.exports = logic;
  else global.HeuteLogic = logic;
})(typeof window !== "undefined" ? window : globalThis);
