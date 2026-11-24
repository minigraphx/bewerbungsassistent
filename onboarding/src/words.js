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

/** Values that keep their {name} in a T, for a sentence with a link in it: T("… {link} …", keptSlots("link")). */
const keptSlots = (...names) => Object.fromEntries(names.map((name) => [name, `{${name}}`]));

/**
 * A sentence in the app language with nodes in it (#432): each {name} of `text` kept by keptSlots becomes the node
 * `nodes[name]`, the rest stays text. The parts go to el or replaceChildren, so a link stays where the language puts it.
 */
function withNodes(text, nodes) {
  return text.split(/(\{\w+\})/).filter((part) => part !== "").map((part) => {
    const slot = /^\{(\w+)\}$/.exec(part);
    return slot && Object.prototype.hasOwnProperty.call(nodes, slot[1]) ? nodes[slot[1]] : part;
  });
}

if (typeof module !== "undefined") {
  module.exports = { T, keptSlots, withNodes };
}
