"use strict";
// The dialog «Dossier gestalten» (#322, board A2 of docs/design/unterlagen-erstellen.md, G18, G19, G39). «Für diese
// Bewerbung» (design, design per page, greeting and thanks) is a draft until «Übernehmen»; «Für alle Dossiers» (sign
// and colour, zeichen.js) is saved at once as before. The cover preview follows the draft through the event
// «dossier-entwurf». Typed texts are not lost unasked: «Abbrechen» and Escape ask «Änderungen verwerfen?» first.
(() => {
  const { senden, status } = window.App;
  const W = window.UnterlagenWahl;
  const L = window.DossierDialogLogik;
  const $ = id => document.getElementById(id);
  const dialog = $("dossier-dialog");
  const FOCUSABLE = "button, [href], input, select, textarea, summary, [tabindex]:not([tabindex='-1'])";

  let entry = null;   // the application as last loaded
  let draft = null;   // { design, seiten } while the dialog is open
  let opener = null;
  let openerId = null; // the page may draw the opener anew after «Übernehmen»; its id finds the new one
  let leaving = false; // true while the dialog closes on purpose: discarded, saved, or nothing typed
  let escapeHandled = false; // the key press already answered this Escape; the browser's cancel must not again

  const texts = () => window.DossierTexte;
  const radios = () => [...$("d-design").querySelectorAll("input")];
  const pageSelects = () => [...$("d-seiten").querySelectorAll("select")];
  const tellPreview = seiten => document.dispatchEvent(new CustomEvent("dossier-entwurf", { detail: seiten }));

  function showDraft() {
    for (const radio of radios()) radio.checked = radio.value === draft.design;
    for (const select of pageSelects()) select.value = draft.seiten[select.dataset.seite];
    tellPreview(draft.seiten);
  }

  function ask(shown) {
    $("dossier-verwerfen").hidden = !shown;
    $("dossier-aktionen").hidden = shown;
    (shown ? $("dossier-weiter") : $("dossier-abbrechen")).focus();
  }

  function open(from) {
    if (!entry) return;
    opener = from;
    openerId = from && from.id ? from.id : null;
    draft = W.entwurf(entry);
    $("d-erweitert").open = W.gemischt(entry);
    $("dossier-verwerfen").hidden = true;
    $("dossier-aktionen").hidden = false;
    status($("dossier-dialog-status"), "");
    showDraft();
    texts().oeffnen();
    dialog.showModal();
    const chosen = radios().find(radio => radio.checked);
    if (chosen) chosen.focus();
  }

  function leave() {
    leaving = true;
    dialog.close();
  }

  function cancel() {
    if (L.cancelAction(texts().geaendert()) === "ask") ask(true);
    else leave();
  }

  function discard() {
    texts().verwerfen();
    leave();
  }

  async function apply() {
    $("dossier-uebernehmen").disabled = true;
    let designSaved = false;
    try {
      const body = W.entwurfSpeichern(entry, draft);
      if (body) {
        entry = await senden("/api/bewerbung", body);
        designSaved = true;
      }
      const saved = await texts().speichern();
      const message = L.savedMessage(designSaved, saved);
      leave();
      if (message) document.dispatchEvent(new CustomEvent("dossier-uebernommen", { detail: { meldung: message } }));
    } catch (error) {
      status($("dossier-dialog-status"), `Nicht übernommen: ${error.message}`, "fehler");
      // a saved design shows on the page even if the texts failed
      if (designSaved) document.dispatchEvent(new CustomEvent("dossier-uebernommen", { detail: { meldung: "" } }));
    } finally {
      $("dossier-uebernehmen").disabled = false;
    }
  }

  /** A radio group takes one Tab stop, at its checked radio; hidden and disabled controls take none. */
  function tabStops() {
    return [...dialog.querySelectorAll(FOCUSABLE)].filter(item => {
      if (item.disabled || item.hidden) return false;
      if (item.getClientRects && !item.getClientRects().length) return false;
      return !(item.type === "radio" && !item.checked && radios().includes(item));
    });
  }

  /** After the page has drawn the step anew, a focus left on nothing goes back to the button that opened the dialog. */
  function refocus() {
    const active = document.activeElement;
    if (active && active !== document.body) return;
    const target = openerId ? $(openerId) : null;
    if (target) target.focus();
  }

  // Escape steps back from the question, or cancels like «Abbrechen»
  function escape() {
    if (!$("dossier-verwerfen").hidden) ask(false);
    else cancel();
  }

  function keepFocus(event) {
    if (event.key === "Escape") {
      // handled on the key, Chrome never counts it as a close request and so never closes the dialog by force
      event.preventDefault();
      escapeHandled = true;
      setTimeout(() => { escapeHandled = false; }, 0);
      escape();
      return;
    }
    if (event.key !== "Tab") return;
    const stops = tabStops();
    const target = L.wrapIndex(stops.indexOf(document.activeElement), stops.length, event.shiftKey);
    if (target === -1) return;
    event.preventDefault();
    stops[target].focus();
  }

  $("d-design").addEventListener("change", event => {
    draft = W.entwurfDesign(draft, event.target.value);
    showDraft();
  });
  $("d-seiten").addEventListener("change", event => {
    draft = W.entwurfSeite(draft, event.target.dataset.seite, event.target.value);
    tellPreview(draft.seiten);
  });
  $("dossier-abbrechen").addEventListener("click", cancel);
  $("dossier-uebernehmen").addEventListener("click", apply);
  $("dossier-weiter").addEventListener("click", () => ask(false));
  $("dossier-verwerfen-ja").addEventListener("click", discard);
  dialog.addEventListener("keydown", keepFocus);
  // other close requests (a back gesture, or a browser that sends one after the handled key) take the same way once
  dialog.addEventListener("cancel", event => {
    event.preventDefault();
    if (escapeHandled) return;
    escape();
  });
  // Should a browser still close the dialog by force, typed texts bring it back with the question: never lost unasked.
  dialog.addEventListener("close", () => {
    if (!leaving && texts().geaendert()) {
      dialog.showModal();
      ask(true);
      return;
    }
    leaving = false;
    draft = null;
    tellPreview(null);
    if (opener && opener.isConnected) opener.focus();
  });
  document.addEventListener("bewerbung-geladen", event => { entry = event.detail.bewerbung; });

  window.DossierDialog = { open, refocus };
})();
