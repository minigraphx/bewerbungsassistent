"use strict";
// The switches of the term proposal (#371, G102): a real checkbox in a label per term, in the card of its change or
// under «Bisherige Begriffe». Built once per proposal and afterwards only updated in place, so the focus stays on the
// chip just switched. Every chip stays in the tab order, as a checkbox would; the UI/UX review (#389) chose that over
// arrow keys within a group. The state and its words come from SuchbegriffeLogik.
(() => {
  const { el } = window.App;
  const L = window.SuchbegriffeLogik;
  let chips = [];
  let karten = [];
  let legenden = [];

  /** Forgets the switches of the proposal shown before. */
  function beginne() {
    chips = [];
    karten = [];
    legenden = [];
  }

  /** The name is followed by a hidden comma and the word, so a screen reader hears „Trainer, bleibt“. */
  function chip(daten, wechsel) {
    const box = el("input", { type: "checkbox", class: "term__box" });
    const komma = el("span", { class: "visually-hidden" }, ", ");
    const wort = el("span", { class: "term__word" });
    const label = el("label", { class: "term" }, box, el("span", { class: "term__check", "aria-hidden": "true" }),
      el("span", { class: "term__name" }, daten.begriff), komma, wort);
    box.addEventListener("change", () => wechsel(daten, box.checked));
    const eintrag = { daten, box, komma, wort, label };
    chips = [...chips, eintrag];
    return eintrag;
  }

  function liste(daten, wechsel) {
    const eintraege = daten.map(d => chip(d, wechsel));
    return el("ul", { class: "terms" }, ...eintraege.map(eintrag => el("li", {}, eintrag.label)));
  }

  /** The chips of a change, and the caption its checkbox gets while only some of them are on. */
  function karte(aenderung, haken, wechsel) {
    const teilweise = el("p", { class: "caption", id: `${haken.getAttribute("id")}-teilweise` }, L.TEILWEISE);
    teilweise.hidden = true;
    karten = [...karten, { aenderung, haken, teilweise }];
    return { liste: liste(L.chips(aenderung), wechsel), teilweise };
  }

  /** One fieldset per area with current terms; its legend carries the total and takes the focus from the reason line. */
  function bisherige(bereiche, wechsel) {
    return bereiche.map(bereich => {
      const legende = el("legend", { class: "terms-current__legend", tabindex: "-1" });
      legenden = [...legenden, { schluessel: bereich.schluessel, legende }];
      return el("fieldset", { class: "terms-current__area" }, legende, liste(bereich.chips, wechsel));
    });
  }

  const legende = schluessel => (legenden.find(l => l.schluessel === schluessel) || {}).legende || null;

  function zeichneChip(eintrag, an) {
    const wort = L.chipWort(eintrag.daten, an);
    eintrag.box.checked = an;
    if (eintrag.wort.textContent !== wort) eintrag.wort.textContent = wort;
    eintrag.wort.hidden = !wort;
    eintrag.komma.hidden = !wort;
    eintrag.label.className = `term term--switch term--${eintrag.daten.art} ${an ? "is-on" : "is-off"}`;
  }

  /** Every chip, checkbox and total as the switches stand; nothing is drawn anew. */
  function zeichne(auswahl, erlaubt) {
    for (const eintrag of chips) zeichneChip(eintrag, L.chipAn(auswahl, eintrag.daten));
    for (const { aenderung, haken, teilweise } of karten) {
      const stand = L.karteStand(auswahl, aenderung);
      haken.checked = stand === "alle";
      haken.indeterminate = stand === "teilweise";
      teilweise.hidden = stand !== "teilweise";
    }
    const zaehlung = L.zaehlung(auswahl, erlaubt);
    for (const { schluessel, legende: element } of legenden) {
      const bereich = zaehlung.find(z => z.schluessel === schluessel);
      element.replaceChildren(...window.DotLine.render(L.legendeTeile(bereich), el));
    }
  }

  window.SuchbegriffeSchalter = { beginne, karte, bisherige, legende, zeichne };
})();
