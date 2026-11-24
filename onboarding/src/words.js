// The words of the form in the app language (#431, G10, docs/design/sprachen.md). The German text is the key, so what
// form.json and the scripts say stays the source and every stored value stays German. In the app the page loads
// texte.js first, and T is Texte.t with the catalog the server hands the page; the file for sharing
// (dist/einstieg.html) loads no texte.js, so T gives the German back and the file stays German (Andy, 23.11.2026).
"use strict";

/** A German text in the app language, with {name} filled from `values`; anything but a text passes as it is. */
function T(german, values = {}) {
  if (typeof german !== "string") return german;
  if (typeof Texte !== "undefined") return Texte.t(german, values);
  return german.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
}

if (typeof module !== "undefined") {
  module.exports = { T };
}
