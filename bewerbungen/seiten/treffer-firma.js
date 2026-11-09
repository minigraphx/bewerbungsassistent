"use strict";
// kununu on Stellen suchen (G35, #190, docs/design/firmen.md): a text badge after the company name in the hit row,
// and a company line in the detail column. Grey only, never the accent, bars or words of the fit grade.
// The hit row is a button, so the badge holds no link; its full wording is part of the button's name.
(() => {
  const { el } = window.App;
  const logik = window.FirmenLogik;
  const NEUER_TAB = ", öffnet neuen Tab";

  /** The badge, or null when kununu has nothing to show for this company. */
  function marke(firma) {
    const m = logik.marke(firma);
    if (!m) return null;
    return el("span", { class: "kununu-mark", "data-art": m.art },
      el("span", { "aria-hidden": "true" }, m.text), el("span", { class: "visually-hidden" }, `, ${m.vorlesen}`));
  }

  function aktion(firma, a) {
    const name = el("span", { class: "visually-hidden" }, `: ${firma.name}${NEUER_TAB}`);
    if (a.art === "pruefen") {
      return el("button", { type: "button", class: "btn btn--sm", onclick: () => window.open(a.href, "_blank", "noopener,noreferrer") }, a.text, name);
    }
    return el("a", { class: a.art === "suchen" ? "btn btn--sm btn--quiet" : "btn btn--sm", href: a.href, target: "_blank",
      rel: "noopener noreferrer" }, a.text, name);
  }

  function wertBlock(zeile) {
    return el("div", { class: "rating", "data-state": zeile.wenige ? "few" : null },
      el("span", { class: "rating__value" }, el("b", {}, zeile.wert), " von 5"),
      ...zeile.angaben.map(angabe => el("span", { class: "rating__meta" }, angabe)));
  }

  /** The company line under the AI's assessment; `alle` names the link to the page Firmen or Lehrbetriebe. */
  function zeile(firma, heute, { lehrstelle = false, alle = "Alle Firmen" } = {}) {
    if (!firma) return null;
    const z = logik.firmenZeile(firma, heute, { lehrstelle });
    const satz = z.zustand === "fehler" ? el("p", { class: "status-line", "data-level": "warning" }, z.satz)
      : z.satz ? el("p", { class: "rating__state rating__state--quiet" }, z.satz) : null;
    return el("section", { class: "company-line", "aria-labelledby": "firma-titel" },
      el("h3", { class: "company-line__title", id: "firma-titel" }, z.titel),
      z.wert ? wertBlock(z) : null, satz,
      z.datum ? el("p", { class: "company-line__date" }, z.datum) : null,
      el("div", { class: "btn-row" }, ...z.aktionen.map(a => aktion(firma, a)),
        el("a", { class: "btn btn--sm btn--quiet", href: "/firmen" }, alle)));
  }

  window.TrefferFirma = { marke, zeile };
})();
