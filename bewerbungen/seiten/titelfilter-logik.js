"use strict";
// Example titles per title filter term in Erweitert › Titelfilter (G104, #382), without DOM: per term of the profile
// how many titles of the last run it let through or kept out, with up to three of them. Every title comes from the
// person's own last run (GET /api/suche/ertrag, `titelfilter`, title_examples.py); the page never shows fixed examples.
(global => {
  const KEIN_TITEL = "Im letzten Suchlauf kein Titel.";
  // A short term finds nothing in «Webentwickler»; the caption says why (UI/UX ruling on #382), alike in Sie and du.
  const KEIN_TITEL_KURZ = `${KEIN_TITEL} Begriffe mit höchstens drei Buchstaben passen nur als ganzes Wort.`;
  const MAX_KURZ = 3; // title_filter.MAX_SHORT
  const GANZES_WORT = /\(\s*ganzes\s+wort\s*\)/i;
  const VOR_LAUF = "Beispiele gibt es nach dem nächsten Suchlauf.";
  const LEER = "Kein Titelfilter";
  const GRUPPEN = [
    { art: "positiv", titel: "Titel, die passen", verb: "durchgelassen" },
    { art: "ausschluss", titel: "Titel, die nicht passen", verb: "aussortiert" },
  ];

  const zitiert = beispiele => (beispiele || []).map(titel => `„${titel}“`).join(", ");
  const mitBeispielen = (satz, beispiele) => ((beispiele || []).length ? `${satz}, zum Beispiel ${zitiert(beispiele)}` : satz);

  /** Matches only as a whole word by its length alone, as title_filter.whole_word counts it (letters and digits). */
  const nurKurz = begriff => Boolean(begriff) && !GANZES_WORT.test(begriff)
    && (String(begriff).match(/[\p{L}\p{N}_]/gu) || []).length <= MAX_KURZ;

  /** The caption under a term: how many titles of the last run it let through (positiv) or kept out (ausschluss). */
  function zeile(eintrag, art, begriff) {
    if (!eintrag || !eintrag.anzahl) return nurKurz(begriff) ? KEIN_TITEL_KURZ : KEIN_TITEL;
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
        begriff, zeile: mitZahlen ? zeile(erfasst.get(begriff.toLowerCase()), gruppe.art, begriff) : "",
      }));
      const nachsatz = mitZahlen && gruppe.art === "positiv" && beispiele.ohne_begriff ? ohneBegriff(beispiele.ohne_begriff) : "";
      return { art: gruppe.art, titel: gruppe.titel, eintraege, nachsatz };
    });
    return { hinweis: beispiele && !beispiele.lauf ? VOR_LAUF : "", gruppen, leer: "" };
  }

  const logik = { KEIN_TITEL, KEIN_TITEL_KURZ, VOR_LAUF, LEER, zeile, ohneBegriff, ansicht };
  if (typeof module !== "undefined") module.exports = logik;
  else global.TitelfilterLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
