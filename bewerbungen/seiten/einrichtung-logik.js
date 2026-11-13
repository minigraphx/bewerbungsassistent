"use strict";
// Setup logic without a page. Step „Erweiterung“ (MIN-407): a version from the store lags behind the app after every
// release, and only a hand-loaded extension can do anything about a difference. Step „Datei“: the choice per file (G26).
// Which steps show, which store button leads and what the end still lists (#219, tests/einrichtung_quickwins.test.cjs).
// The AI is no step (G60, #272): the window „KI einrichten“ sets it up, opened from the setup or wherever it is needed.
(function (global) {
  /** The steps in order. The data folder is a line of the first step; „Datei“ only shows with a file in Downloads,
   *  otherwise it is reached under „Erweitert“ and shows while it is the current one. */
  function schritte({ installiert, einstiegDatei, jetzt = "" }) {
    if (!installiert) return ["gesucht"];
    const datei = einstiegDatei || jetzt === "vorlage" ? ["vorlage"] : [];
    return ["gesucht", ...datei, "erweiterung"];
  }

  /** „edge“, „chrome“ or „andere“ from the user agent; other Chromium browsers have no store of ours. */
  function browserVon(userAgent) {
    const ua = String(userAgent || "");
    if (/\bEdg(?:A|iOS)?\//.test(ua)) return "edge";
    if (/\b(?:OPR|Opera|Vivaldi|YaBrowser|SamsungBrowser)\//.test(ua)) return "andere";
    return /\b(?:Chrome|Chromium)\//.test(ua) ? "chrome" : "andere";
  }

  /** One main store button: the own browser's, Chrome where the browser is another. */
  function storeKnoepfe(browser) {
    return browser === "edge" ? { haupt: "edge", leise: "chrome" } : { haupt: "chrome", leise: "edge" };
  }

  const OFFEN = {
    ki: { id: "ki", titel: "KI", text: "Noch nicht verbunden. Ohne KI gibt es keine Noten und keine Entwürfe.", knopf: "KI einrichten",
          aktion: "ki-einrichten" },
    erweiterung: { id: "erweiterung", titel: "Erweiterung", text: "Noch nicht geladen. Ohne sie sucht die App nicht auf den Portalen.",
                   knopf: "Erweiterung laden", ziel: "#erweiterung" },
  };

  /** What is still open at the end, each with its button; the extension only where the app can bring it. */
  function offenePunkte({ kiVerbunden, erweiterungMoeglich, erweiterungGeladen }) {
    return [!kiVerbunden && OFFEN.ki, erweiterungMoeglich && !erweiterungGeladen && OFFEN.erweiterung].filter(Boolean);
  }

  const abschlussTitel = offen => (offen.length ? "Fast fertig" : "Alles eingerichtet");

  /** „fehlt“, „veraltet“ (a reload helps) or „bereit“. */
  function erweiterungZustand(geladen, mitgebracht, entpackt) {
    if (!geladen) return "fehlt";
    return entpackt && mitgebracht && geladen !== mitgebracht ? "veraltet" : "bereit";
  }

  // Step „Datei“ (G26): existing Markdown files are kept unless the person picks replacing, per file.
  const ZEICHEN = { gleich: "  ", weg: "− ", neu: "+ ", luecke: "…" };

  function startWahl(dateien) {
    return Object.fromEntries(dateien.map(d => [d.datei, "behalten"]));
  }

  function zuErsetzen(wahl) {
    return Object.keys(wahl).filter(datei => wahl[datei] === "ersetzen");
  }

  function zeilenZeichen(art) {
    return ZEICHEN[art] || "  ";
  }

  const logik = { erweiterungZustand, startWahl, zuErsetzen, zeilenZeichen, schritte, browserVon, storeKnoepfe, offenePunkte,
                  abschlussTitel };
  if (typeof module !== "undefined") module.exports = logik;
  else global.EinrichtungLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
