"use strict";
(() => {
  const { holen, senden, el, status, pdfAdresse } = window.App;
  const $ = id => document.getElementById(id);
  const meldung = (text, art) => status($("status"), text, art);
  let dateien = [];
  let geladen = "";
  let aktuelle = null;
  let alsText = new URLSearchParams(location.search).get("ansicht") === "text";

  const datei = () => $("datei").value;
  const hatPdf = () => (dateien.find(d => d.datei === datei()) || {}).pdf === true;
  const ungespeichert = () => $("text").value !== geladen;

  function geaendert() {
    $("speichern").disabled = !ungespeichert();
    $("verwerfen").disabled = !ungespeichert();
    if (ungespeichert()) meldung("Nicht gespeichert", "hinweis");
  }

  function merken() {
    const parameter = new URLSearchParams({ datei: datei() });
    if (alsText) parameter.set("ansicht", "text");
    history.replaceState(null, "", "/inhalte?" + parameter);
  }

  async function zeigePdf() {
    meldung("PDF wird erstellt …");
    try {
      const gewaehlt = datei();
      const adresse = await pdfAdresse("/api/inhalt/pdf", { datei: gewaehlt }, "ansicht");
      if (gewaehlt !== datei()) return;  // inzwischen andere Datei gewählt
      $("pdf").src = adresse;
      meldung(ungespeichert() ? "Die Ansicht zeigt den gespeicherten Stand; Änderungen im Text sind noch nicht gespeichert." : "",
        ungespeichert() ? "hinweis" : "");
    } catch (fehler) {
      $("pdf").removeAttribute("src");
      meldung("PDF nicht möglich: " + fehler.message + " – mit „Als Text“ prüfen und korrigieren.", "fehler");
    }
  }

  // Ansicht wählen: PDF (Standard) oder Text-Editor; Datenlisten ohne PDF immer als Text
  function ansicht() {
    const text = alsText || !hatPdf();
    $("ansicht-pdf").hidden = text;
    $("ansicht-text").hidden = !text;
    $("hinweis").hidden = hatPdf();
    $("umschalten").hidden = !hatPdf();
    $("umschalten").textContent = alsText ? "Als PDF" : "Als Text";
    $("umschalten").setAttribute("aria-pressed", String(alsText));
    merken();
    if (!text) return zeigePdf();
    if (!ungespeichert()) meldung("");
  }

  function zeigeVorschau(adresse) {
    $("vorschau").replaceChildren(...(adresse
      ? [el("figure", {}, el("figcaption", {}, "Vorschau"), el("iframe", { src: adresse, title: "Vorschau" }))]
      : []));
  }

  async function laden() {
    try {
      const daten = await holen("/api/inhalt", { datei: datei() });
      geladen = daten.text;
      aktuelle = datei();
      $("text").value = daten.text;
      zeigeVorschau(null);
      geaendert();
      await ansicht();
    } catch (fehler) {
      meldung("Laden fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  async function vorschauText() {
    if (!hatPdf()) return null;
    return pdfAdresse("/api/inhalt/vorschau.pdf", { stand: Date.now() }, "vorschau");
  }

  async function start() {
    try {
      ({ dateien } = await holen("/api/inhalte"));
      const gewuenscht = new URLSearchParams(location.search).get("datei");
      const erste = dateien.some(d => d.datei === gewuenscht) ? gewuenscht : (dateien[0] || {}).datei;
      $("datei").replaceChildren(...dateien.map(d => el("option", { value: d.datei, selected: d.datei === erste }, d.titel)));
      if (erste) await laden();
    } catch (fehler) {
      meldung("Laden fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  $("datei").addEventListener("change", () => {
    if (!ungespeichert()) return laden();
    $("datei").value = aktuelle;
    meldung("Erst speichern oder „Änderungen verwerfen“, dann die Datei wechseln.", "hinweis");
  });
  $("umschalten").addEventListener("click", () => { alsText = !alsText; ansicht(); });
  $("text").addEventListener("input", geaendert);
  $("pruefen").addEventListener("click", async () => {
    meldung("Wird geprüft …");
    try {
      const r = await senden("/api/inhalt/pruefen", { text: $("text").value }, { datei: datei() });
      zeigeVorschau(r.vorschau ? await vorschauText() : null);
      meldung("Gültig" + (r.vorschau ? " – Vorschau rechts" : ""), "ok");
    } catch (fehler) {
      meldung("Ungültig: " + fehler.message, "fehler");
    }
  });
  $("speichern").addEventListener("click", async () => {
    try {
      const r = await senden("/api/inhalt", { text: $("text").value }, { datei: datei() });
      geladen = $("text").value;
      geaendert();
      zeigeVorschau(r.vorschau ? await vorschauText() : null);
      meldung("Gespeichert. Der Stand davor liegt unter Entwürfe.", "ok");
    } catch (fehler) {
      meldung("Nicht gespeichert: " + fehler.message, "fehler");
    }
  });
  $("verwerfen").addEventListener("click", laden);
  window.addEventListener("beforeunload", e => { if (ungespeichert()) e.preventDefault(); });
  start();
})();
