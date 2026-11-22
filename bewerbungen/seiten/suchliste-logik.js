"use strict";
// The order of the search terms on Suche einstellen (#285, G87), without DOM: moving a term, the place under the
// pointer while dragging, and what the page says and names. The server checks the whole order again (search_terms.py).
(global => {
  /** The list with the term at `von` moved to `nach`; the list it got stays as it is. */
  function verschoben(liste, von, nach) {
    const ohne = [...liste.slice(0, von), ...liste.slice(von + 1)];
    return [...ohne.slice(0, nach), liste[von], ...ohne.slice(nach)];
  }

  /** Where the dragged row belongs: as many places down as other rows have their middle above the pointer. */
  const zielIndex = (mitten, von, y) => mitten.filter((mitte, index) => index !== von && mitte < y).length;

  const ansage = (name, stelle, anzahl) => `„${name}“ steht jetzt an Stelle ${stelle} von ${anzahl}.`;

  // The accessible names say which term a button moves, since the arrows alone do not.
  const knopfNamen = name => ({ hoch: `${name} nach oben`, runter: `${name} nach unten`, entfernen: `${name} entfernen` });

  /**
   * G105: the caption of a term limited to some portals, as parts of a «·» line; none for a term without a limit.
   * With only some of them off it names those, since the term still runs on the rest.
   */
  function portalTeile(eintrag) {
    if (!eintrag || !Array.isArray(eintrag.portale) || !eintrag.portale.length) return [];
    const nur = `nur ${eintrag.portale.join(", ")}`;
    if (eintrag.aus) return [nur, "ausgeschaltet"];
    const aus = Array.isArray(eintrag.ausgeschaltet) ? eintrag.ausgeschaltet : [];
    return aus.length ? [nur, `${aus.join(", ")} ausgeschaltet`] : [nur];
  }

  const logik = { verschoben, zielIndex, ansage, knopfNamen, portalTeile };
  if (typeof module !== "undefined") module.exports = logik;
  else global.SuchlisteLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
