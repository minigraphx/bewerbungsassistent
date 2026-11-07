"use strict";
// Setup step „Erweiterung“ without a page (MIN-407). A version from the store lags behind the app after every release,
// and only a hand-loaded extension can do anything about a difference.
(function (global) {
  /** „fehlt“, „veraltet“ (a reload helps) or „bereit“. */
  function erweiterungZustand(geladen, mitgebracht, entpackt) {
    if (!geladen) return "fehlt";
    return entpackt && mitgebracht && geladen !== mitgebracht ? "veraltet" : "bereit";
  }

  const logik = { erweiterungZustand };
  if (typeof module !== "undefined") module.exports = logik;
  else global.EinrichtungLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
