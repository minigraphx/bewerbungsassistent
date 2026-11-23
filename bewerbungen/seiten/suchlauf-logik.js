"use strict";
// What the page Stellen says about a search run (G43): the announcement before a long run, and the progress line while
// the extension runs the searches in stages. No DOM, so it can be tested.
(function (global) {
  // Durations read like the cost lines (#347): the page loads treffer-logik.js first.
  const { seconds } = typeof module !== "undefined" ? require("./treffer-logik.js") : global.TrefferLogik;
  // Texts in the app language (#422); the page loads texte.js first.
  const Texte = { t: (deutsch, werte) => (typeof module !== "undefined" ? require("./texte.js") : global.Texte).t(deutsch, werte) };

  /** The announcement under „Jetzt suchen“, only for a long run and only while nothing blocks the start. */
  function umfangText(umfang, sperrgrund) {
    return umfang?.lang && !sperrgrund ? umfang.text : "";
  }

  /** „Suche 32 von 193, Etappe 2 von 7 …“, always the last part; empty from an older extension that sends no counts. */
  function stelle(s) {
    if (!s.abfragen) return "";
    const werte = { nummer: s.nummer, abfragen: s.abfragen, etappe: s.etappe, etappen: s.etappen };
    return s.etappen > 1 ? Texte.t("Suche {nummer} von {abfragen}, Etappe {etappe} von {etappen} …", werte)
      : Texte.t("Suche {nummer} von {abfragen} …", werte);
  }

  /** „jobs.ch: suche „Data“ in Bern, Seite 2“, with „ …“ when nothing follows; the term and the place stay as they are. */
  function suche(s, zuletzt) {
    const werte = { portal: s.portal, stichwort: s.stichwort, ort: s.ort, seite: s.seite };
    if (s.ort) {
      return zuletzt ? Texte.t("{portal}: suche „{stichwort}“ in {ort}, Seite {seite} …", werte)
        : Texte.t("{portal}: suche „{stichwort}“ in {ort}, Seite {seite}", werte);
    }
    return zuletzt ? Texte.t("{portal}: suche „{stichwort}“, Seite {seite} …", werte)
      : Texte.t("{portal}: suche „{stichwort}“, Seite {seite}", werte);
  }

  /** The progress line of a running search, from the step the extension reports, as the parts of a «·» line (#342). */
  function laufZeile(s) {
    if (s.phase === "suche") {
      const zaehler = stelle(s);
      return [suche(s, !zaehler), zaehler].filter(Boolean);
    }
    if (s.phase === "pause") {
      return [Texte.t("{portal}: Pause vor Etappe {etappe} von {etappen}, noch {dauer} …",
        { portal: s.portal, etappe: s.etappe, etappen: s.etappen, dauer: seconds(s.sekunden) })];
    }
    if (s.phase === "texte") {
      return [Texte.t("{portal}: lese Inserat {nummer} von {von} …", { portal: s.portal, nummer: s.fertig + 1, von: s.von })];
    }
    return [Texte.t("Suche startet …")];
  }

  const logik = { umfangText, laufZeile };
  if (typeof module !== "undefined") module.exports = logik;
  else global.SuchlaufLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
