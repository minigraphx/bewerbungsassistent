"use strict";
// Entwürfe und Versionen grouped by document (#120): which groups and documents the page shows, and how a
// document's versions split into the newest one and the older ones to fold away. No DOM (tests/entwuerfe_logik.test.cjs).
(function (global) {
  const ALLE = "alle";

  /** The groups to show: one kind of group, or all; with `datei`, only the document of that file. */
  function sichtbar(gruppen, { art = ALLE, datei = "" } = {}) {
    return gruppen
      .filter(g => art === ALLE || g.art === art)
      .map(g => ({ ...g, dokumente: g.dokumente.filter(d => !datei || d.datei === datei) }))
      .filter(g => g.dokumente.length > 0);
  }

  /** The filter buttons: all, then each group with its number of documents. */
  const filter = gruppen => [
    { art: ALLE, titel: "Alle", zahl: gruppen.reduce((n, g) => n + g.dokumente.length, 0) },
    ...gruppen.map(g => ({ art: g.art, titel: g.titel, zahl: g.dokumente.length })),
  ];

  /** Versions come newest first: the newest one is shown, the older ones fold away. */
  function fassungen(dokument) {
    const [neueste, ...aeltere] = dokument.fassungen;
    return { neueste, aeltere };
  }

  /** Label of the folded part, or null when there is nothing older. */
  const aeltereTitel = aeltere => (aeltere.length ? `Ältere Fassungen (${aeltere.length})` : null);

  const logik = { ALLE, sichtbar, filter, fassungen, aeltereTitel };
  if (typeof module !== "undefined") module.exports = logik;
  else global.EntwuerfeLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
