"use strict";
// Entwürfe und Versionen grouped by document (#120): which groups and documents the page shows, and how a
// document's versions split into the newest one and the older ones to fold away. "Nur verwendete" (#240) keeps the
// documents that went out with an application. No DOM (tests/entwuerfe_logik.test.cjs).
(function (global) {
  const ALLE = "alle";

  /** The documents of a group that count: all, or with `nurVerwendet` only those sent with an application. */
  const zaehlende = (g, nurVerwendet) => g.dokumente.filter(d => !nurVerwendet || d.verwendet);

  /** The groups to show: one kind of group, or all; with `datei`, only the document of that file. A used
   * document keeps all its versions, the older ones too. */
  function sichtbar(gruppen, { art = ALLE, datei = "", nurVerwendet = false } = {}) {
    return gruppen
      .filter(g => art === ALLE || g.art === art)
      .map(g => ({ ...g, dokumente: zaehlende(g, nurVerwendet).filter(d => !datei || d.datei === datei) }))
      .filter(g => g.dokumente.length > 0);
  }

  /** The filter buttons: all, then each group with its number of documents. */
  const filter = (gruppen, { nurVerwendet = false } = {}) => [
    { art: ALLE, titel: "Alle", zahl: gruppen.reduce((n, g) => n + zaehlende(g, nurVerwendet).length, 0) },
    ...gruppen.map(g => ({ art: g.art, titel: g.titel, zahl: zaehlende(g, nurVerwendet).length })),
  ];

  /** What a document card shows: on top the newest version, or with `nurVerwendet` the versions that went out;
   * the rest folds away, so no version leaves the page. */
  function ansicht(dokument, { nurVerwendet = false } = {}) {
    if (!nurVerwendet) {
      const { neueste, aeltere } = fassungen(dokument);
      return { oben: [neueste], gefaltet: aeltere, faltTitel: aeltereTitel(aeltere) };
    }
    const gesendet = f => (f.versendet || []).length > 0;
    const gefaltet = dokument.fassungen.filter(f => !gesendet(f));
    return { oben: dokument.fassungen.filter(gesendet), gefaltet,
      faltTitel: gefaltet.length ? `Nicht versendete Fassungen (${gefaltet.length})` : null };
  }

  const tag = iso => iso.split("-").reverse().join(".");

  /** Which applications a version went out with, or null when it never did. */
  function versandText(fassung) {
    const gesendet = fassung.versendet || [];
    if (!gesendet.length) return null;
    const teile = gesendet.map(v => (v.firma && v.datum ? `an ${v.firma} am ${tag(v.datum)}` : `(${v.zweck})`));
    return "versendet " + teile.join(" und ");
  }

  /** The choice "Nur verwendete" as the page stores it, so it stays across reloads. */
  const gespeichert = wert => wert === "1";
  const speicherwert = an => (an ? "1" : "0");

  /** Versions come newest first: the newest one is shown, the older ones fold away. */
  function fassungen(dokument) {
    const [neueste, ...aeltere] = dokument.fassungen;
    return { neueste, aeltere };
  }

  /** Label of the folded part, or null when there is nothing older. */
  const aeltereTitel = aeltere => (aeltere.length ? `Ältere Fassungen (${aeltere.length})` : null);

  const logik = { ALLE, sichtbar, filter, fassungen, aeltereTitel, ansicht, versandText, gespeichert, speicherwert };
  if (typeof module !== "undefined") module.exports = logik;
  else global.EntwuerfeLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
