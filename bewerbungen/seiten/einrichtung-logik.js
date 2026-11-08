"use strict";
// Setup logic without a page. Step „Erweiterung“ (MIN-407): a version from the store lags behind the app after every
// release, and only a hand-loaded extension can do anything about a difference. Step „Datei“: the choice per file (G26).
(function (global) {
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

  const logik = { erweiterungZustand, startWahl, zuErsetzen, zeilenZeichen };
  if (typeof module !== "undefined") module.exports = logik;
  else global.EinrichtungLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
