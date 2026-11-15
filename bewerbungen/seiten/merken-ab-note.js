"use strict";
// „Alle ab Note … merken“ on Stellen (#214, A3): the app names how many hits and which, the person confirms, then exactly
// those are saved like „Merken“. Only on the tab Neu; the list reloads through the event „treffer-gemerkt“.
(() => {
  const { holen, senden, el, status } = window.App;
  const L = window.MerkenAbNoteLogik;
  const $ = id => document.getElementById(id);
  let vorschau = null;  // the hits the dialog named; only these are sent

  const note = () => L.gueltigeNote($("ab-note").value);
  const meldung = (text, stufe) => status($("status"), text, stufe);

  function zeigeZeile() {
    $("ab-note-zeile").hidden = window.TrefferLogik.reiterAus(location.hash) !== "neu";
  }

  function zeigeKnopf() {
    $("ab-note-knopf").textContent = L.knopfText(note());
  }

  async function fragen() {
    try {
      vorschau = await holen("/api/suche/ab-note", { note: String(note()) });
    } catch (fehler) {
      return meldung(fehler.message, "fehler");
    }
    if (!vorschau.anzahl) return meldung(L.keinerText(vorschau.note), "hinweis");
    const frage = L.bestaetigung(vorschau);
    $("ab-note-titel").textContent = frage.titel;
    $("ab-note-text").replaceChildren(el("p", {}, frage.einleitung),
      el("ul", { class: "dialog__list" }, frage.zeilen.map(zeile => el("li", {}, zeile))), el("p", {}, frage.nachsatz));
    $("ab-note-ok").textContent = frage.ok;
    $("ab-note-dialog").showModal();
  }

  async function merken() {
    $("ab-note-dialog").close();
    const ids = vorschau.treffer.map(t => t.id);
    $("ab-note-knopf").disabled = true;
    try {
      const antwort = await senden("/api/suche/ab-note", { note: vorschau.note, ids });
      meldung(L.ergebnisText(antwort), antwort.uebersprungen.length ? "hinweis" : "ok");
    } catch (fehler) {
      meldung(fehler.message, "fehler");
    } finally {
      $("ab-note-knopf").disabled = false;
      document.dispatchEvent(new CustomEvent("treffer-gemerkt"));
    }
  }

  $("ab-note").replaceChildren(...L.NOTEN.map(wert => el("option", { value: String(wert) }, String(wert))));
  $("ab-note").value = String(L.VORGABE);
  $("ab-note").addEventListener("change", zeigeKnopf);
  $("ab-note-knopf").addEventListener("click", fragen);
  $("ab-note-abbrechen").addEventListener("click", () => $("ab-note-dialog").close());
  $("ab-note-ok").addEventListener("click", merken);
  window.addEventListener("hashchange", zeigeZeile);
  zeigeKnopf();
  zeigeZeile();
})();
