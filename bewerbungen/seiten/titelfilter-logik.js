"use strict";
// Example titles per title filter term in Erweitert › Titelfilter (G104, #382), without DOM: per term of the profile
// how many titles of the last run it let through or kept out, with up to three of them. Every title comes from the
// person's own last run (GET /api/suche/ertrag, `titelfilter`, title_examples.py); the page never shows fixed examples.
(global => {
  const KEIN_TITEL = "Im letzten Suchlauf kein Titel.";
  const VOR_LAUF = "Beispiele gibt es nach dem nächsten Suchlauf.";
  const LEER = "Kein Titelfilter";
  const GRUPPEN = [
    { art: "positiv", titel: "Titel, die passen", verb: "durchgelassen" },
    { art: "ausschluss", titel: "Titel, die nicht passen", verb: "aussortiert" },
  ];

  const zitiert = beispiele => (beispiele || []).map(titel => `„${titel}“`).join(", ");
  const mitBeispielen = (satz, beispiele) => ((beispiele || []).length ? `${satz}, zum Beispiel ${zitiert(beispiele)}` : satz);

  /** The caption under a term: how many titles of the last run it let through (positiv) or kept out (ausschluss). */
  function zeile(eintrag, art) {
    if (!eintrag || !eintrag.anzahl) return KEIN_TITEL;
    const verb = GRUPPEN.find(gruppe => gruppe.art === art).verb;
    return mitBeispielen(`${eintrag.anzahl} Titel ${verb}`, eintrag.beispiele);
  }

  /** After the positive list: the titles kept out because none of its terms is in them. */
  function ohneBegriff(eintrag) {
    if (!eintrag || !eintrag.anzahl) return "Ohne passenden Begriff aussortiert: kein Titel.";
    return mitBeispielen(`Ohne passenden Begriff aussortiert: ${eintrag.anzahl} Titel`, eintrag.beispiele);
  }

  const nachBegriff = eintraege => new Map((eintraege || []).map(eintrag => [String(eintrag.begriff).toLowerCase(), eintrag]));

  /**
   * What the section shows: per list with terms its title and each term with its caption, and the line after the
   * positive list. `beispiele` is null while the examples are not loaded; `lauf` false until a run recorded some.
   */
  function ansicht(positiv, ausschluss, beispiele) {
    const begriffe = { positiv: positiv || [], ausschluss: ausschluss || [] };
    if (!begriffe.positiv.length && !begriffe.ausschluss.length) return { hinweis: "", gruppen: [], leer: LEER };
    const mitZahlen = Boolean(beispiele && beispiele.lauf);
    const gruppen = GRUPPEN.filter(gruppe => begriffe[gruppe.art].length).map(gruppe => {
      const erfasst = nachBegriff(mitZahlen ? beispiele[gruppe.art] : []);
      const eintraege = begriffe[gruppe.art].map(begriff => ({
        begriff, zeile: mitZahlen ? zeile(erfasst.get(begriff.toLowerCase()), gruppe.art) : "",
      }));
      const nachsatz = mitZahlen && gruppe.art === "positiv" && beispiele.ohne_begriff ? ohneBegriff(beispiele.ohne_begriff) : "";
      return { art: gruppe.art, titel: gruppe.titel, eintraege, nachsatz };
    });
    return { hinweis: beispiele && !beispiele.lauf ? VOR_LAUF : "", gruppen, leer: "" };
  }

  const logik = { KEIN_TITEL, VOR_LAUF, LEER, zeile, ohneBegriff, ansicht };
  if (typeof module !== "undefined") module.exports = logik;
  else global.TitelfilterLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
