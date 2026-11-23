"use strict";
// Example titles per title filter term in Erweitert › Titelfilter (G104, #382), without DOM: per term of the profile
// how many titles of the last run it let through or kept out, with up to three of them. Every title comes from the
// person's own last run (GET /api/suche/ertrag, `titelfilter`, title_examples.py); the page never shows fixed examples.
// Texts in the app language through Texte (#425); terms and titles are data and stay as they are.
(global => {
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const MAX_KURZ = 3; // title_filter.MAX_SHORT
  const GANZES_WORT = /\(\s*ganzes\s+wort\s*\)/i;
  const POSITIV = "positiv";
  const GRUPPEN = [POSITIV, "ausschluss"];

  const keinTitel = () => Texte.t("Im letzten Suchlauf kein Titel.");
  // A short term finds nothing in «Webentwickler»; the caption says why (UI/UX ruling on #382), alike in Sie and du.
  const keinTitelKurz = () => Texte.t("Im letzten Suchlauf kein Titel. Begriffe mit höchstens drei Buchstaben passen nur als ganzes Wort.");
  const vorLauf = () => Texte.t("Beispiele gibt es nach dem nächsten Suchlauf.");
  const leer = () => Texte.t("Kein Titelfilter");
  const titel = art => (art === POSITIV ? Texte.t("Titel, die passen") : Texte.t("Titel, die nicht passen"));

  /** How many titles a term let through (positiv) or kept out (ausschluss), the singular apart. */
  function gezaehlt(art, anzahl) {
    if (art === POSITIV) return anzahl === 1 ? Texte.t("1 Titel durchgelassen") : Texte.t("{anzahl} Titel durchgelassen", { anzahl });
    return anzahl === 1 ? Texte.t("1 Titel aussortiert") : Texte.t("{anzahl} Titel aussortiert", { anzahl });
  }

  const zitiert = beispiele => (beispiele || []).map(beispiel => Texte.t("„{begriff}“", { begriff: beispiel })).join(", ");
  const mitBeispielen = (satz, beispiele) => ((beispiele || []).length
    ? Texte.t("{satz}, zum Beispiel {beispiele}", { satz, beispiele: zitiert(beispiele) }) : satz);

  /** Matches only as a whole word by its length alone, as title_filter.whole_word counts it (letters and digits). */
  const nurKurz = begriff => Boolean(begriff) && !GANZES_WORT.test(begriff)
    && (String(begriff).match(/[\p{L}\p{N}_]/gu) || []).length <= MAX_KURZ;

  /** The caption under a term: how many titles of the last run it let through (positiv) or kept out (ausschluss). */
  function zeile(eintrag, art, begriff) {
    if (!eintrag || !eintrag.anzahl) return nurKurz(begriff) ? keinTitelKurz() : keinTitel();
    return mitBeispielen(gezaehlt(art, eintrag.anzahl), eintrag.beispiele);
  }

  /** After the positive list: the titles kept out because none of its terms is in them. */
  function ohneBegriff(eintrag) {
    if (!eintrag || !eintrag.anzahl) return Texte.t("Ohne passenden Begriff aussortiert: kein Titel.");
    const satz = eintrag.anzahl === 1 ? Texte.t("Ohne passenden Begriff aussortiert: 1 Titel")
      : Texte.t("Ohne passenden Begriff aussortiert: {anzahl} Titel", { anzahl: eintrag.anzahl });
    return mitBeispielen(satz, eintrag.beispiele);
  }

  const nachBegriff = eintraege => new Map((eintraege || []).map(eintrag => [String(eintrag.begriff).toLowerCase(), eintrag]));

  /**
   * What the section shows: per list with terms its title and each term with its caption, and the line after the
   * positive list. `beispiele` is null while the examples are not loaded; `lauf` false until a run recorded some.
   */
  function ansicht(positiv, ausschluss, beispiele) {
    const begriffe = { positiv: positiv || [], ausschluss: ausschluss || [] };
    if (!begriffe.positiv.length && !begriffe.ausschluss.length) return { hinweis: "", gruppen: [], leer: leer() };
    const mitZahlen = Boolean(beispiele && beispiele.lauf);
    const gruppen = GRUPPEN.filter(art => begriffe[art].length).map(art => {
      const erfasst = nachBegriff(mitZahlen ? beispiele[art] : []);
      const eintraege = begriffe[art].map(begriff => ({
        begriff, zeile: mitZahlen ? zeile(erfasst.get(begriff.toLowerCase()), art, begriff) : "",
      }));
      const nachsatz = mitZahlen && art === POSITIV && beispiele.ohne_begriff ? ohneBegriff(beispiele.ohne_begriff) : "";
      return { art, titel: titel(art), eintraege, nachsatz };
    });
    return { hinweis: beispiele && !beispiele.lauf ? vorLauf() : "", gruppen, leer: "" };
  }

  const logik = { get KEIN_TITEL() { return keinTitel(); }, get KEIN_TITEL_KURZ() { return keinTitelKurz(); },
    get VOR_LAUF() { return vorLauf(); }, get LEER() { return leer(); }, zeile, ohneBegriff, ansicht };
  if (typeof module !== "undefined") module.exports = logik;
  else global.TitelfilterLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
