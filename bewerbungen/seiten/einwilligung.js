"use strict";
// Consent before the first AI call (MIN-401): the same block on the setup, application and settings page.
window.Einwilligung = (() => {
  const { senden, el, fragenLink } = window.App;

  function link(stand) {
    return stand.link ? el("p", {}, el("a", { href: stand.link, target: "_blank", rel: "noopener" }, "Datenschutzerklärung lesen")) : null;
  }

  // What pseudonymisation covers (G14); data-text lets a page with its own text set apply it again.
  function ersetzt() {
    const { text } = window.Texte;
    const absatz = el("p", { class: "field__hint", "data-text": "einwilligung.ersetzt" },
      text("einwilligung.ersetzt", document.documentElement.dataset.textsatz));
    window.App.textsatz().then(satz => { absatz.textContent = text("einwilligung.ersetzt", satz); });
    return absatz;
  }

  function grenzen() {
    return el("p", { class: "field__hint" }, fragenLink("was-ersetzt-die-app", "Was die App ersetzt und was nicht"));
  }

  function wartenderCode(stand) {
    return stand.code_wartet ? el("p", {}, "Der Einladungscode aus dem Link wird danach eingelöst.") : null;
  }

  /** Fills `ort` with the text to agree to; `fertig` gets the new AI status once it is given. */
  function zeige(ort, stand, fertig) {
    const haken = el("input", { type: "checkbox" });
    const knopf = el("button", { type: "button", class: "btn btn--primary" }, "Einwilligen");
    const meldung = el("p", { class: "status-line", role: "status", "aria-live": "polite" });
    knopf.disabled = true;
    haken.addEventListener("change", () => { knopf.disabled = !haken.checked; });
    knopf.addEventListener("click", async () => {
      knopf.disabled = true;
      try {
        fertig(await senden("/api/ki/einwilligung", { fassung: stand.fassung, zustimmung: haken.checked }));
      } catch (fehler) {
        window.Meldungen.zeige(meldung, fehler.message, "danger");
        knopf.disabled = !haken.checked;
      }
    });
    const teile = [link(stand), el("label", { class: "schalter" }, haken, " ", stand.text), ersetzt(), grenzen(), wartenderCode(stand), knopf, meldung];
    ort.replaceChildren(...teile.filter(Boolean));
    ort.hidden = false;
  }

  return { zeige, link };
})();
