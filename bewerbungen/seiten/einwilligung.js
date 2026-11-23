"use strict";
// Consent before the first AI call (MIN-401): the full block in the setup, elsewhere one line that opens it (#222).
window.Einwilligung = (() => {
  const { senden, el, fragenLink } = window.App;
  // Texts through Texte.t (#416); texte.js comes first on every page.
  const { Texte } = window;
  const aus = () => Texte.t("Die KI ist noch aus.");
  const einschalten = () => Texte.t("KI einschalten");

  function link(stand) {
    return stand.link
      ? el("p", {}, el("a", { href: stand.link, target: "_blank", rel: "noopener" }, Texte.t("Datenschutzerklärung lesen"))) : null;
  }

  // What pseudonymisation covers (G14); data-text lets a page with its own text set apply it again.
  function ersetzt() {
    const absatz = el("p", { class: "field__hint", "data-text": "einwilligung.ersetzt" },
      Texte.text("einwilligung.ersetzt", document.documentElement.dataset.textsatz));
    window.App.textsatz().then(satz => { absatz.textContent = Texte.text("einwilligung.ersetzt", satz); });
    return absatz;
  }

  function grenzen() {
    return el("p", { class: "field__hint" }, fragenLink("was-ersetzt-die-app", Texte.t("Was die App ersetzt und was nicht")));
  }

  function wartenderCode(stand) {
    return stand.code_wartet ? el("p", {}, Texte.t("Der Einladungscode aus dem Link wird danach eingelöst.")) : null;
  }

  /** The text to agree to with its tick and button, the same wherever it shows (G14). */
  function teile(stand, fertig) {
    const haken = el("input", { type: "checkbox" });
    const knopf = el("button", { type: "button", class: "btn btn--primary" }, Texte.t("Einwilligen"));
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
    return { text: [link(stand), el("label", { class: "schalter" }, haken, " ", stand.text), ersetzt(), grenzen(), wartenderCode(stand)].filter(Boolean),
      knopf, meldung };
  }

  /** Fills `ort` with the text to agree to; `fertig` gets the new AI status once it is given. Used by the setup. */
  function zeige(ort, stand, fertig) {
    const { text, knopf, meldung } = teile(stand, fertig);
    ort.replaceChildren(...text, knopf, meldung);
    ort.hidden = false;
  }

  /**
   * Outside the setup the consent is no block in the middle of the work: one line with „KI einschalten“, which opens
   * the unchanged text in a dialog. `fertig` gets the new AI status once it is given, after the dialog closed.
   */
  function zeile(ort, stand, fertig) {
    const titel = `einwilligung-titel-${ort.id || "zeile"}`;
    const dialog = el("dialog", { class: "dialog einwilligung", "aria-labelledby": titel });
    const { text, knopf, meldung } = teile(stand, neu => {
      dialog.close();
      fertig(neu);
    });
    const abbrechen = el("button", { type: "button", class: "btn" }, Texte.t("Abbrechen"));
    abbrechen.addEventListener("click", () => dialog.close());
    dialog.replaceChildren(el("h2", { class: "dialog__title", id: titel }, einschalten()), ...text, meldung,
      el("div", { class: "dialog__actions" }, abbrechen, knopf));
    const oeffnen = el("button", { type: "button", class: "btn btn--sm" }, einschalten());
    oeffnen.addEventListener("click", () => dialog.showModal());
    ort.replaceChildren(el("p", { class: "einwilligung__zeile" }, `${aus()} `, oeffnen), dialog);
    ort.hidden = false;
  }

  return { zeige, zeile, link };
})();
