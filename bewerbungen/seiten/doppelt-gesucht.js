"use strict";
// «Doppelt gesucht» on Suche einstellen (G106, #377): under the term list one block per pair the search runs twice or
// a broader term covers, with words and costs from GET /api/suche/doppelt; shown only when there is a pair. Nothing
// is removed without a click. After one, the message line of the list says what changed and offers Rückgängig over
// the route of the list; focus goes to that line, since the block it came from is gone.
window.DoppeltGesucht = (() => {
  const { holen, senden, el, status } = window.App;
  const $ = id => document.getElementById(id);
  const RUECKGAENGIG = "Rückgängig";
  const geaendert = () => document.dispatchEvent(new CustomEvent("suchprofil-geaendert"));
  let ladeNummer = 0;

  function melde(text, art, optionen) {
    status($("suchliste-status"), text, art, optionen);
    $("suchliste-status").focus();
  }

  async function rueckgaengig(antwort) {
    try {
      await senden("/api/beruf/rueckgaengig", { beruf: antwort.beruf, vorher: antwort.rueckgaengig, zeile: antwort.zeile });
      melde(antwort.zurueck, "ok");
      geaendert();
    } catch (fehler) {
      melde(fehler.message, "fehler");
    }
  }

  async function entferne(paar, option, knopf) {
    knopf.disabled = true;
    try {
      const antwort = await senden("/api/suche/doppelt/entfernen", { paar: paar.id, seite: option.seite });
      // the action keeps the message until it is used or closed (#215)
      melde(antwort.text, "ok", { aktion: { text: RUECKGAENGIG, ausfuehren: () => rueckgaengig(antwort) } });
    } catch (fehler) {
      melde(fehler.message, "fehler");
    } finally {
      knopf.disabled = false;
      geaendert();  // after a refusal too: the profile may have changed since the page loaded
    }
  }

  async function behalte(paar, knopf) {
    knopf.disabled = true;
    try {
      const { text } = await senden("/api/suche/doppelt/behalten", { paar: paar.id });
      melde(text, "ok");
      await lade();
    } catch (fehler) {
      melde(fehler.message, "fehler");
      knopf.disabled = false;
    }
  }

  function knopf(text, name, klasse, aktion) {
    const button = el("button", { type: "button", class: klasse, "aria-label": name }, text);
    button.addEventListener("click", () => aktion(button));
    return button;
  }

  function block(paar) {
    const entfernen = paar.optionen.map(option =>
      knopf(option.knopf, option.name, "btn btn--sm", button => entferne(paar, option, button)));
    const behalten = knopf(paar.behalten, paar.behalten_name, "btn btn--quiet btn--sm", button => behalte(paar, button));
    return el("li", { class: "doppelt__paar" }, el("p", { class: "doppelt__text" }, paar.text),
      el("div", { class: "doppelt__knoepfe" }, ...entfernen, behalten));
  }

  function zeige(paare) {
    $("doppelt").hidden = !paare.length;
    $("doppelt-liste").replaceChildren(...paare.map(block));
  }

  /** Loads the pairs anew; an apprenticeship search gets none from the server. */
  async function lade() {
    const nummer = ++ladeNummer;
    try {
      const { paare } = await holen("/api/suche/doppelt");
      if (nummer === ladeNummer) zeige(paare);
    } catch (fehler) {
      if (nummer !== ladeNummer) return;
      zeige([]);
      status($("status"), `Doppelt gesuchte Begriffe liessen sich nicht laden: ${fehler.message}`, "fehler");
    }
  }

  return { lade };
})();
