"use strict";
// A finding of the check as a list line with its buttons (G52, G94, #325), the longest paragraph of a letter over one
// page, and where the focus goes after «So lassen». Texts come from bewerbung-logik.js; bewerbung.js wires the
// actions. A small stand-in DOM tests it (tests/finding_row.test.cjs).
(() => {
  const { el } = window.App;
  const { LONGEST_LABEL } = window.BewerbungLogik;
  const LONGEST_ID = "laengster-absatz";
  const EDIT_LETTER = window.Texte.t("Anschreiben ändern");  // in the app language (#429)

  /**
   * One finding as a list line: `b` from /api/pruefung, `zeile` from BewerbungLogik.befundZeile. A letter over one page
   * waits on a decision, so it has no «×» and its buttons stand on a row of their own, the cut first (as the CV, G92);
   * so does a CV over its limit with no cut left, with «So lassen» alone (#330). Each line with a key carries it, so
   * the focus can find the line again after the list is drawn anew.
   */
  function row(b, zeile, { onCut, onKeep }) {
    const keep = zeile.knopf
      ? el("button", { type: "button", class: "btn btn--sm", onclick: event => onKeep(event.currentTarget) }, zeile.knopf) : null;
    const cut = zeile.cutInLetter
      ? el("button", { type: "button", class: "btn btn--sm btn--primary", onclick: onCut }, zeile.cutInLetter) : null;
    const decision = Boolean(zeile.cutInLetter || zeile.decision);
    const content = decision
      ? el("span", { class: "cut-finding" }, el("span", {}, zeile.text), el("div", { class: "btn-row" }, cut, keep))
      : keep ? el("span", {}, zeile.text, " ", keep) : zeile.text;
    const line = window.Meldungen.listenZeile(document, content, zeile.stufe, decision ? { schliessbar: false } : {});
    return keyed(line, b);
  }

  /** The key on the line; an open one is marked as waiting, a confirmed one can take the focus. */
  function keyed(line, b) {
    if (!b.schluessel) return line;
    line.setAttribute("data-schluessel", b.schluessel);
    line.setAttribute(b.bestaetigt ? "tabindex" : "data-offen", b.bestaetigt ? "-1" : "");
    return line;
  }

  /**
   * The longest paragraph of a letter over one page (G94): a group named by its visible label, the paragraph and a
   * quiet button that opens the letter editor at it (#332). The label is hidden from screen readers, which hear it as
   * the group's name; the button comes after the paragraph in reading order and stands next to the label (stil.css).
   */
  function longest(paragraph, onEdit) {
    return el("div", { class: "letter-longest", id: LONGEST_ID, role: "group", "aria-labelledby": `${LONGEST_ID}-label`, tabindex: "-1" },
      el("span", { class: "letter-longest__label", id: `${LONGEST_ID}-label`, "aria-hidden": "true" }, LONGEST_LABEL),
      paragraph,
      el("button", { type: "button", class: "btn btn--sm btn--quiet letter-longest__edit", onclick: onEdit }, EDIT_LETTER));
  }

  const lines = list => [...list.children].filter(child => child.tagName === "LI");

  /**
   * After «So lassen» the list is drawn anew: the focus goes to the first button of the next finding still open,
   * else of an open one before it; with none left, to the confirmed line itself.
   */
  function focusAfterConfirm(list, schluessel) {
    const all = lines(list);
    const confirmed = all.find(line => line.getAttribute("data-schluessel") === schluessel) || null;
    // the action comes before the «×» that Meldungen appends, so the first button is the one to take
    const open = all.filter(line => line !== confirmed && line.getAttribute("data-offen") !== null && line.querySelector("button"));
    const after = confirmed ? open.find(line => all.indexOf(line) > all.indexOf(confirmed)) : null;
    const target = after || open[0];
    if (target) target.querySelector("button").focus();
    else if (confirmed) confirmed.focus();
  }

  window.FindingRow = { LONGEST_ID, row, keyed, longest, focusAfterConfirm };
})();
