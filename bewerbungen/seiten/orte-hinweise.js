"use strict";
// The place notices of «Region und Pensum» on Suche einstellen (G107, #380), with words and costs from
// GET /api/suche/orte-hinweise: a jobs.ch place in a canton another place already covers, and the nudge from several
// jobscout24 postcodes to its regions. Nothing is removed without a click; after one, the message line of the card
// says what changed and offers Rückgängig, and the focus goes there, since the notice it came from is gone.
window.OrteHinweise = (() => {
  const { holen, senden, el, status } = window.App;
  const $ = id => document.getElementById(id);
  const geaendert = () => document.dispatchEvent(new CustomEvent("suchprofil-geaendert"));
  let ladeNummer = 0;

  function melde(text, art, optionen) {
    status($("region-meldung"), text, art, optionen);
    $("region-meldung").focus();
  }

  async function rueckgaengig(antwort) {
    try {
      const { text } = await senden("/api/suche/orte-hinweise/rueckgaengig", { ort: antwort.ort, vorher: antwort.rueckgaengig });
      melde(text, "ok");
      geaendert();
    } catch (fehler) {
      melde(fehler.message, "fehler");
    }
  }

  async function entferne(hinweis, knopf) {
    knopf.disabled = true;
    try {
      const antwort = await senden("/api/suche/orte-hinweise/entfernen", { ort: hinweis.ort });
      // the action keeps the message until it is used or closed (#215)
      melde(antwort.text, "ok", { aktion: { text: window.Texte.t("Rückgängig"), ausfuehren: () => rueckgaengig(antwort) } });
    } catch (fehler) {
      melde(fehler.message, "fehler");
    } finally {
      knopf.disabled = false;
      geaendert();  // after a refusal too: the profile may have changed since the page loaded
    }
  }

  async function behalte(hinweis, knopf) {
    knopf.disabled = true;
    try {
      const { text } = await senden("/api/suche/orte-hinweise/behalten", { ort: hinweis.ort });
      melde(text, "ok");
      await lade();
    } catch (fehler) {
      melde(fehler.message, "fehler");
      knopf.disabled = false;
    }
  }

  function knopf(text, klasse, aktion) {
    const button = el("button", { type: "button", class: klasse }, text);
    button.addEventListener("click", () => aktion(button));
    return button;
  }

  function block(hinweis) {
    return el("li", { class: "doppelt__paar" }, el("p", { class: "doppelt__text" }, hinweis.text),
      el("div", { class: "doppelt__knoepfe" },
        knopf(hinweis.knopf, "btn btn--sm", button => entferne(hinweis, button)),
        knopf(hinweis.behalten, "btn btn--quiet btn--sm", button => behalte(hinweis, button))));
  }

  function zeige({ orte, plz }) {
    $("orte-doppelt").hidden = !orte.length;
    $("orte-doppelt-liste").replaceChildren(...orte.map(block));
    $("plz-hinweis").hidden = !plz;
    $("plz-hinweis-text").textContent = plz ? plz.text : "";
    $("plz-hinweis-knopf").textContent = plz ? plz.knopf : "";
  }

  function reportNoticesFailed(fehler) {
    status($("status"), window.Texte.t("Hinweise zu den Orten liessen sich nicht laden: {fehler}", { fehler: fehler.message }), "fehler");
  }

  /** Loads the notices anew; an apprenticeship search gets none from the server. */
  async function lade() {
    const nummer = ++ladeNummer;
    try {
      const hinweise = await holen("/api/suche/orte-hinweise");
      if (nummer === ladeNummer) zeige(hinweise);
    } catch (fehler) {
      if (nummer !== ladeNummer) return;
      zeige({ orte: [], plz: null });
      reportNoticesFailed(fehler);
    }
  }

  $("plz-hinweis-knopf").addEventListener("click", () => window.SucheRahmen.oeffneRegionen());

  return { lade };
})();
