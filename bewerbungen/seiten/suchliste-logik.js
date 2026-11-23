"use strict";
// The order of the search terms on Suche einstellen (#285, G87), without DOM: moving a term, the place under the
// pointer while dragging, and what the page says and names. The server checks the whole order again (search_terms.py).
// What it says comes in the app language through Texte.t (#424); terms and portals are data and stay as they are.
(global => {
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };

  /** The list with the term at `von` moved to `nach`; the list it got stays as it is. */
  function verschoben(liste, von, nach) {
    const ohne = [...liste.slice(0, von), ...liste.slice(von + 1)];
    return [...ohne.slice(0, nach), liste[von], ...ohne.slice(nach)];
  }

  /** Where the dragged row belongs: as many places down as other rows have their middle above the pointer. */
  const zielIndex = (mitten, von, y) => mitten.filter((mitte, index) => index !== von && mitte < y).length;

  const ansage = (name, stelle, anzahl) => Texte.t("„{name}“ steht jetzt an Stelle {stelle} von {anzahl}.", { name, stelle, anzahl });

  // The accessible names say which term a button moves, since the arrows alone do not.
  const knopfNamen = name => ({ hoch: Texte.t("{name} nach oben", { name }), runter: Texte.t("{name} nach unten", { name }),
    entfernen: Texte.t("{name} entfernen", { name }) });

  /**
   * G105: the caption of a term limited to some portals, as parts of a «·» line; none for a term without a limit.
   * With only some of them off it names those, since the term still runs on the rest.
   */
  function portalTeile(eintrag) {
    if (!eintrag || !Array.isArray(eintrag.portale) || !eintrag.portale.length) return [];
    const nur = Texte.t("nur {portale}", { portale: eintrag.portale.join(", ") });
    if (eintrag.aus) return [nur, Texte.t("ausgeschaltet")];
    const aus = Array.isArray(eintrag.ausgeschaltet) ? eintrag.ausgeschaltet : [];
    if (!aus.length) return [nur];
    // one portal or several: French agrees the word with them
    return [nur, aus.length === 1 ? Texte.t("{portal} ausgeschaltet", { portal: aus[0] })
      : Texte.t("{portale} ausgeschaltet", { portale: aus.join(", ") })];
  }

  /**
   * The whole caption of a term: its portals (G105), then its required words (G110), «Pflichtbezug: Informatik, ICT».
   * @param {object|undefined} portalEintrag  the entry of `begriff_portale`
   * @param {string[]|undefined} woerter  the required words
   * @returns {string[]}
   */
  function zusatzTeile(portalEintrag, woerter) {
    const liste = Array.isArray(woerter) ? woerter : [];
    const pflicht = liste.length === 1 ? [Texte.t("Pflichtbezug: {wort}", { wort: liste[0] })]
      : liste.length ? [Texte.t("Pflichtbezug: {woerter}", { woerter: liste.join(", ") })] : [];
    return [...portalTeile(portalEintrag), ...pflicht];
  }

  const logik = { verschoben, zielIndex, ansage, knopfNamen, portalTeile, zusatzTeile };
  if (typeof module !== "undefined") module.exports = logik;
  else global.SuchlisteLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
