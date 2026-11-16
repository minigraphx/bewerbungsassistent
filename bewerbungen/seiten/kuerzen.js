"use strict";
// The DOM of cutting with one click (G92, #323): under the finding of a CV over its limit a fieldset with the cuts to
// tick, the first preselected, «Gekürzt neu erstellen» first and «Drei Seiten erlauben»; in the step Lebenslauf what
// this application leaves out, each with «Zurückholen». Texts and order come from kuerzen-logik.js; bewerbung.js
// reloads the page after each answer (`after`) and moves the focus to the new result.
(() => {
  const { el, senden } = window.App;
  const K = window.KuerzenLogik;
  const $ = id => document.getElementById(id);
  const BUSY = { kuerzen: "Wird gekürzt und neu erstellt …", [K.THREE_ID]: "Drei Seiten erlaubt, wird neu erstellt …" };
  const NOTHING_TICKED = "Bitte mindestens eine Kürzung anhaken oder drei Seiten erlauben.";

  function row(option, name) {
    return el("label", { class: "cut-row" },
      el("input", { type: "checkbox", name, value: option.id, checked: option.checked }),
      el("span", { class: "cut-row__text" }, option.text));
  }

  /**
   * The choice under the finding. `entryId` names the application, `note` is the sentence about Meine Angaben in the
   * person's form, and `after(action, answer)` reloads the page and moves the focus (bewerbung.js).
   */
  function chooser(kuerzen, { entryId, note, after }) {
    const name = `kuerzung-${entryId}`;
    const rows = K.rows(kuerzen);
    const status = el("p", { class: "status-line cut-choice__status", role: "status", "aria-live": "polite" });
    const fieldset = el("fieldset", { class: "cut-choice" },
      el("legend", { class: "cut-choice__legend" }, rows.length ? K.LEGEND : "Für diese Bewerbung"),
      ...rows.map(option => row(option, name)));
    const buttons = K.buttons(kuerzen).map(button => el("button", {
      type: "button", class: `btn${button.primary ? " btn--primary" : ""}`, "data-aktion": button.action,
      onclick: () => choose(button.action),
    }, button.text));

    async function choose(action) {
      const ticked = [...fieldset.querySelectorAll(`input[name="${name}"]:checked`)].map(input => input.value);
      const body = K.body(entryId, action, ticked);
      if (!body) {
        status.textContent = NOTHING_TICKED;
        return;
      }
      buttons.forEach(button => { button.disabled = true; });
      status.textContent = BUSY[action];
      try {
        await after(action, await senden("/api/kuerzungen", body));
      } catch (fehler) {
        status.textContent = fehler.message;
        buttons.forEach(button => { button.disabled = false; });
      }
    }

    fieldset.append(el("div", { class: "btn-row cut-choice__actions" }, ...buttons), el("p", { class: "field__hint cut-choice__note" }, note), status);
    return fieldset;
  }

  /** The list in the step Lebenslauf; hidden without anything left out, and without buttons once sent. */
  function showLeftOut(kuerzungen, { entryId, sent, after }) {
    const rows = K.leftOut(kuerzungen);
    $("weggelassen").hidden = !rows.length;
    $("weggelassen-liste").replaceChildren(...rows.map((entry, index) => el("li", { class: "cut-list__row" },
      el("span", { class: "cut-list__text" }, entry.text),
      sent ? null : el("button", { type: "button", class: "btn btn--sm", "aria-label": `${entry.button}: ${entry.text}`,
        onclick: event => takeBack(event.currentTarget, entry, index) }, entry.button))));

    async function takeBack(button, entry, index) {
      button.disabled = true;
      $("weggelassen-status").textContent = "Wird zurückgeholt und neu erstellt …";
      try {
        await after("zurueck", await senden("/api/kuerzungen/zurueckholen", { id: entryId, kuerzung: entry.id }));
        $("weggelassen-status").textContent = "";
        focusAfterTakingBack(index);
      } catch (fehler) {
        button.disabled = false;
        $("weggelassen-status").textContent = fehler.message;
      }
    }
  }

  /** The row that took the place of the one brought back, else the heading of the step. */
  function focusAfterTakingBack(index) {
    const buttons = $("weggelassen-liste").querySelectorAll("button");
    const next = buttons[Math.min(index, buttons.length - 1)];
    if (next && !$("weggelassen").hidden) next.focus();
    else $("lebenslauf-titel").focus();
  }

  window.Kuerzen = { chooser, showLeftOut };
})();
