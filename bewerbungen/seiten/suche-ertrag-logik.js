"use strict";
// What the search brings on Suche einstellen (G103, #375), without DOM: the words of the yield line under each term,
// the caption under the list, the empty searches and the places. Every number comes from the app (search_yield.py);
// a «·» line is a list of parts that the page joins with dot-line.js.
(global => {
  const OHNE_ERTRAG = "ohne Ertrag";
  const VERSION_VORHER = "0.3.3";  // the first version that keeps the query behind each hit

  const anzahl = (zahl, eins, viele) => `${zahl} ${zahl === 1 ? eins : viele}`;
  const suchen = zahl => anzahl(zahl, "Suche", "Suchen");
  const suchlaeufe = zahl => anzahl(zahl, "Suchlauf", "Suchläufen");

  const NICHT_GESUCHT = "noch nicht gesucht";

  /** The parts of the yield line of a term or place. One no run has searched yet has none before the first run and
   * says so once there are `laeufe`, e.g. a term added since. */
  function teile(eintrag, laeufe = 0) {
    if (!eintrag || !eintrag.suchen) return laeufe > 0 ? [NICHT_GESUCHT] : [];
    const aussortiert = eintrag.aussortiert > 0 ? `${eintrag.aussortiert} aussortiert` : "";
    if (!eintrag.treffer) return [suchen(eintrag.suchen), "keine Treffer", aussortiert].filter(Boolean);
    const pflicht = eintrag.ohne_pflichtbezug > 0 ? `${eintrag.ohne_pflichtbezug} ohne Pflichtbezug` : "";  // G110
    return [suchen(eintrag.suchen), `${eintrag.treffer} Treffer`, `${eintrag.neu} neu`, `${eintrag.ab_note_4} ab Note 4`, aussortiert,
      pflicht].filter(Boolean);
  }

  const begriffWort = lehrstelle => (lehrstelle ? "Beruf" : "Begriff");

  const woher = laeufe => (laeufe === 1 ? "aus dem letzten Suchlauf" : `aus den letzten ${laeufe} Suchläufen`);

  const PFLICHT_SATZ = " „Ohne Pflichtbezug“: Titel und Inserat nennen keines der Pflichtwörter des Begriffs.";

  /** The one caption on the numbers under the list: from how many runs they come and how a hit counts; with `pflicht`
   * (some hit had no required word, G110) also what that reason means. */
  function hinweis(laeufe, lehrstelle, pflicht = false) {
    if (!laeufe) return `Nach dem nächsten Suchlauf steht hier bei jedem ${begriffWort(lehrstelle)}, was er bringt.`;
    const zaehlen = lehrstelle
      ? "Findet die Suche eine Lehrstelle über mehrere Berufe, zählt sie bei jedem."
      : "Findet die Suche eine Stelle über mehrere Begriffe, zählt sie bei jedem. „Aussortiert“ heisst: Der Titelfilter hat den Titel nicht durchgelassen."
        + (pflicht ? PFLICHT_SATZ : "");
    return `Die Zahlen stammen ${woher(laeufe)}. ${zaehlen}`;
  }

  /** The summary of the details on hits without a required word (G110): how many there were in all. */
  const pflichtTitel = eintraege => `Ohne Pflichtbezug aussortiert (${eintraege.reduce((summe, e) => summe + e.anzahl, 0)})`;

  /** One term of those details, with up to three titles of its own last run. */
  function pflichtZeile(eintrag) {
    const beispiele = (eintrag.beispiele || []).slice(0, 3).map(titel => `„${titel}“`);
    // hits of every search over the runs, not postings counted once («Stellen» since #383)
    const kopf = `„${eintrag.begriff}“: ${eintrag.anzahl} Treffer`;
    if (!beispiele.length) return kopf;
    return eintrag.anzahl === 1 ? `${kopf}, ${beispiele[0]}` : `${kopf}, zum Beispiel ${beispiele.join(", ")}`;
  }

  /** The first line of «Was die Orte bringen»: where the numbers come from and what a place-less search is. */
  function ortHinweis(laeufe) {
    const satzAnfang = woher(laeufe).replace(/^a/, "A");
    return `${satzAnfang}, gezählt wie bei den Suchbegriffen. „Ohne Ort“ sind Suchen ohne Ortsangabe, etwa für die Nischen.`;
  }

  /** Hits from runs before the app kept the query; '' when there are none. */
  function ohneAngabe(zahl, lehrstelle) {
    if (!zahl) return "";
    return `Ohne Angabe: ${zahl} Treffer aus Suchläufen vor Version ${VERSION_VORHER}. `
      + `Über welchen ${begriffWort(lehrstelle)} sie kamen, hat die App damals nicht festgehalten.`;
  }

  const leerTitel = (zahl, lehrstelle) => `Wo ein ${begriffWort(lehrstelle)} nichts findet (${zahl})`;

  const leerZeile = eintrag => `„${eintrag.begriff}“${eintrag.nische ? " (Nische)" : ""} auf ${eintrag.portal}: `
    + `${suchen(eintrag.suchen)} in ${suchlaeufe(eintrag.laeufe)}, kein Treffer.`;

  /** A place the way its portal searches it: a town, a postcode, a region of ictjobs or the cantons of job-room. */
  function ortName(eintrag) {
    const { portal, ort } = eintrag;
    if (!ort) return `${portal}, ohne Ort`;
    if (portal === "jobscout24") return `${portal}, PLZ ${ort}`;
    if (portal === "job-room") return `${portal}, ${ort.includes(",") ? "Kantone" : "Kanton"} ${ort}`;
    return `${portal}, ${eintrag.ort_name || ort}`;
  }

  /** The yield of each term by its name as the term list shows it. */
  const nachBegriff = ertrag => new Map(((ertrag && ertrag.begriffe) || []).map(eintrag => [eintrag.begriff, eintrag]));

  const logik = { OHNE_ERTRAG, teile, hinweis, ortHinweis, ohneAngabe, leerTitel, leerZeile, ortName, nachBegriff, pflichtTitel,
    pflichtZeile };
  if (typeof module !== "undefined") module.exports = logik;
  else global.SucheErtragLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
