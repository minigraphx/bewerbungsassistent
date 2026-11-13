"use strict";
// Heute (#260, A1): dates and deadlines, the stand by stage, the line under the title and the pass over saved jobs
// (G38). Rows come from UebersichtLogik.mitSchritten. No DOM, so it can be tested (tests/heute.test.cjs).
(function (global) {
  const SAVED = ["Gemerkt", "Bewerben"];
  const APPLIED = ["Beworben", "Gespräch"];
  const CLOSED = [["Zusage", "Zusage", "Zusagen"], ["Absage", "Absage", "Absagen"], ["Verworfen", "verworfen", "verworfen"],
                  ["Zurückgezogen", "zurückgezogen", "zurückgezogen"]];
  const WEEK_DAYS = 7;
  const NUMBER_WORDS = ["", "Eine", "Zwei", "Drei", "Vier", "Fünf", "Sechs", "Sieben", "Acht", "Neun", "Zehn", "Elf", "Zwölf"];

  const day = iso => `${iso.slice(8, 10)}.${iso.slice(5, 7)}.`;
  const plural = (count, [one, many]) => `${count} ${count === 1 ? one : many}`;

  function addDays(iso, days) {
    const date = new Date(`${iso}T12:00:00Z`);
    date.setUTCDate(date.getUTCDate() + days);
    return date.toISOString().slice(0, 10);
  }

  function datesOf({ bewerbung: b, schritt }, interview) {
    const found = [];
    if (SAVED.includes(b.status) && b.frist) found.push({ date: b.frist, text: `Frist für ${[b.stelle, b.firma].filter(Boolean).join(", ")}` });
    if (b.status === "Gespräch" && b.gespraech_am) found.push({ date: b.gespraech_am, text: `${interview} bei ${b.firma}` });
    if (schritt.art === "warten" && schritt.zusatz) found.push({ date: schritt.zusatz, text: `Nachfragen bei ${b.firma}, falls keine Antwort da ist` });
    return found;
  }

  /** Termine und Fristen: deadlines, interviews and follow-ups from today on, soonest first. */
  function dates(rows, today, { max = 5, interview = "Gespräch" } = {}) {
    return rows.flatMap(row => datesOf(row, interview))
      .filter(entry => /^\d{4}-\d{2}-\d{2}$/.test(entry.date) && entry.date >= today)
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(0, max)
      .map(entry => ({ ...entry, day: day(entry.date) }));
  }

  const withStatus = (rows, statuses) => rows.filter(row => statuses.includes(row.bewerbung.status));

  function closedHint(rows) {
    return CLOSED.map(([status, one, many]) => [withStatus(rows, [status]).length, one, many])
      .filter(([count]) => count > 0)
      .map(([count, one, many]) => plural(count, [one, many]))
      .join(", ");
  }

  /** Ihr Stand: { neu, gemerkt, beworben, abgeschlossen }, each { count, hint }. `hits` is { count, last } or null. */
  function stand(rows, hits, today, { interview = ["Gespräch", "Gespräche"] } = {}) {
    const saved = withStatus(rows, SAVED);
    const weekEnd = addDays(today, WEEK_DAYS - 1);
    const dueThisWeek = saved.filter(({ bewerbung: b }) => b.frist && b.frist >= today && b.frist <= weekEnd).length;
    const talks = withStatus(rows, ["Gespräch"]).length;
    return {
      neu: { count: hits ? hits.count : 0, hint: hits?.last ? `aus der Suche vom ${day(hits.last.slice(0, 10))}` : "noch keine Suche" },
      gemerkt: { count: saved.length, hint: dueThisWeek ? `${plural(dueThisWeek, ["Frist", "Fristen"])} in dieser Woche` : "" },
      beworben: { count: withStatus(rows, APPLIED).length, hint: talks ? plural(talks, interview) : "" },
      abgeschlossen: { count: withStatus(rows, CLOSED.map(([status]) => status)).length, hint: closedHint(rows) },
    };
  }

  /** The line under the title as a key of texte.js with its values. */
  function waiting(count) {
    if (count <= 0) return { key: "heute.wartet.nichts", values: {} };
    if (count === 1) return { key: "heute.wartet.eins", values: {} };
    return { key: "heute.wartet.viele", values: { anzahl: NUMBER_WORDS[count] || String(count) } };
  }

  // The pass over saved jobs (G38): one after the other, the person decides, the app changes only the stage.

  /** Ids of the saved jobs not decided yet, in the order of the list (closest deadline first). */
  function passQueue(rows) {
    return withStatus(rows, ["Gemerkt"]).map(row => row.bewerbung.id);
  }

  const passProgress = (index, total) => `${index + 1} von ${total}`;

  function passResult({ bewerben = 0, verworfen = 0, spaeter = 0 } = {}) {
    const parts = [[bewerben, `${bewerben} zum Bewerben`], [verworfen, `${verworfen} verworfen`], [spaeter, `${spaeter} für später`]]
      .filter(([count]) => count > 0).map(([, text]) => text);
    return parts.length ? `Durchgang fertig: ${parts.join(", ")}.` : "Durchgang fertig.";
  }

  const logic = { dates, stand, waiting, passQueue, passProgress, passResult };
  if (typeof module !== "undefined") module.exports = logic;
  else global.HeuteLogic = logic;
})(typeof window !== "undefined" ? window : globalThis);
