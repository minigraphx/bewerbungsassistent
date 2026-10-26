"use strict";
(() => {
  const { holen, senden, el, status, url } = window.App;
  const $ = id => document.getElementById(id);
  const meldung = (text, art) => status($("status"), text, art);
  let geladen = "";

  function geaendert() {
    const anders = $("text").value !== geladen;
    $("speichern").disabled = !anders;
    $("verwerfen").disabled = !anders;
    if (anders) meldung("Nicht gespeichert", "hinweis");
  }

  function zeigeVorschau(vorhanden) {
    $("vorschau").replaceChildren(...(vorhanden
      ? [el("figure", {}, el("figcaption", {}, "Vorschau"),
          el("iframe", { src: url("/api/inhalt/vorschau.pdf", { stand: Date.now() }), title: "Vorschau" }))]
      : []));
  }

  async function laden(datei) {
    try {
      const daten = await holen("/api/inhalt", { datei });
      geladen = daten.text;
      $("text").value = daten.text;
      zeigeVorschau(false);
      meldung("");
      geaendert();
      history.replaceState(null, "", "/inhalte?datei=" + encodeURIComponent(datei));
    } catch (fehler) {
      meldung("Laden fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  async function start() {
    try {
      const { dateien } = await holen("/api/inhalte");
      const gewuenscht = new URLSearchParams(location.search).get("datei");
      const erste = dateien.includes(gewuenscht) ? gewuenscht : dateien[0];
      $("datei").replaceChildren(...dateien.map(d => el("option", { value: d, selected: d === erste }, d)));
      if (erste) await laden(erste);
    } catch (fehler) {
      meldung("Laden fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  $("datei").addEventListener("change", e => laden(e.target.value));
  $("text").addEventListener("input", geaendert);
  $("pruefen").addEventListener("click", async () => {
    meldung("Wird geprüft …");
    try {
      const r = await senden("/api/inhalt/pruefen", { text: $("text").value }, { datei: $("datei").value });
      zeigeVorschau(r.vorschau);
      meldung("Gültig" + (r.vorschau ? " – Vorschau rechts" : ""), "ok");
    } catch (fehler) {
      meldung("Ungültig: " + fehler.message, "fehler");
    }
  });
  $("speichern").addEventListener("click", async () => {
    try {
      const r = await senden("/api/inhalt", { text: $("text").value }, { datei: $("datei").value });
      geladen = $("text").value;
      geaendert();
      zeigeVorschau(r.vorschau);
      meldung("Gespeichert. Der Stand davor liegt unter Entwürfe.", "ok");
    } catch (fehler) {
      meldung("Nicht gespeichert: " + fehler.message, "fehler");
    }
  });
  $("verwerfen").addEventListener("click", () => laden($("datei").value));
  window.addEventListener("beforeunload", e => { if ($("text").value !== geladen) e.preventDefault(); });
  start();
})();
