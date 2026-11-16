"use strict";
// What the page Stellen says about a search run (G43): the announcement before a long run, and the progress line while
// the extension runs the searches in stages. No DOM, so it can be tested.
(function (global) {
  /** The announcement under „Jetzt suchen“, only for a long run and only while nothing blocks the start. */
  function umfangText(umfang, sperrgrund) {
    return umfang?.lang && !sperrgrund ? umfang.text : "";
  }

  /** „Suche 32 von 193, Etappe 2 von 7“; empty from an older extension that sends no counts. */
  function stelle(s) {
    if (!s.abfragen) return "";
    return `Suche ${s.nummer} von ${s.abfragen}${s.etappen > 1 ? `, Etappe ${s.etappe} von ${s.etappen}` : ""}`;
  }

  /** „ in Bern“ for the place being searched; empty for a query without place or from an older extension. */
  function ort(s) {
    return s.ort ? ` in ${s.ort}` : "";
  }

  /** The progress line of a running search, from the step the extension reports, as the parts of a «·» line (#342). */
  function laufZeile(s) {
    if (s.phase === "suche") {
      const teile = [`${s.portal}: suche „${s.stichwort}“${ort(s)}, Seite ${s.seite}`, stelle(s)].filter(Boolean);
      return teile.map((teil, index) => (index === teile.length - 1 ? `${teil} …` : teil));
    }
    if (s.phase === "pause") return [`${s.portal}: Pause vor Etappe ${s.etappe} von ${s.etappen}, noch ${s.sekunden} Sekunden …`];
    if (s.phase === "texte") return [`${s.portal}: lese Inserat ${s.fertig + 1} von ${s.von} …`];
    return ["Suche startet …"];
  }

  const logik = { umfangText, laufZeile };
  if (typeof module !== "undefined") module.exports = logik;
  else global.SuchlaufLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
