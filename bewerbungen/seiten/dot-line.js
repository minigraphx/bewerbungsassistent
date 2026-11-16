"use strict";
// «·» lines, the same on every page (#331, #337, #340): «Vorschlag der KI · 1 Änderung», «2 Seiten · enger gesetzt».
// A line may break beside an inline-block despite a no-break space, so a «·» between two parts could start a line.
// Each part therefore breaks only as a whole (.whole-part in stil.css) and carries the «·» after it; the plain space
// between two parts is the only place a line breaks. Screen readers skip the «·» and hear a comma.
// No DOM of its own: the page passes App.el, so the helper runs in node (tests/dot_line.test.cjs).
(root => {
  const DOT = "\u00a0·";

  /** `parts` as nodes for replaceChildren or App.el; empty parts are left out, so no «·» stands alone. */
  function render(parts, el) {
    const kept = parts.filter(part => part !== "" && part !== null && part !== undefined);
    const last = kept.length - 1;
    const wholes = kept.map((part, index) => (index === last
      ? el("span", { class: "whole-part" }, part)
      : el("span", { class: "whole-part" },
        part, el("span", { "aria-hidden": "true" }, DOT), el("span", { class: "visually-hidden" }, ","))));
    return wholes.flatMap((whole, index) => (index === 0 ? [whole] : [" ", whole]));
  }

  const api = { render };
  if (typeof module !== "undefined") module.exports = api;
  else root.DotLine = api;
})(typeof window !== "undefined" ? window : globalThis);
