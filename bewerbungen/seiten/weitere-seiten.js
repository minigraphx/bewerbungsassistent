"use strict";
// „Weitere Seiten durchsuchen“ on Suche einstellen (MIN-348, #263, G57): the addresses, only with an own API key.
// Without one the card says where the key goes; the extension is asked for access to the sites it lists.
(() => {
  const { holen, senden, status } = window.App;
  const $ = id => document.getElementById(id);
  const SEITE = "bewerbungsbegleiter-seite";
  const hatErweiterung = () => Boolean(document.documentElement.dataset.bewerbungsbegleiterErweiterung);
  const meldung = (text, stufe) => status($("seiten-meldung"), text, stufe);

  function zeige(stand) {
    $("weitere-seiten").hidden = false;
    $("seiten-mit-schluessel").hidden = !stand.eigener_schluessel;
    $("seiten-ohne-schluessel").hidden = stand.eigener_schluessel;
    $("max-seiten").textContent = String(stand.max_seiten);
    $("seiten").value = stand.seiten.map(seite => seite.adresse).join("\n");
    $("zugriff").hidden = !stand.seiten.length;
  }

  async function lade() {
    try {
      zeige(await holen("/api/suche/weitere-seiten"));
      if (location.hash === "#weitere-seiten") $("weitere-seiten").scrollIntoView();
    } catch (fehler) {
      meldung(fehler.message, "fehler");
    }
  }

  async function speichern() {
    const seiten = $("seiten").value.split("\n").map(zeile => zeile.trim()).filter(Boolean);
    try {
      zeige(await senden("/api/suche/weitere-seiten", { seiten }));
      meldung(seiten.length ? "Gespeichert. Die Seiten kommen bei der nächsten Suche dazu." : "Gespeichert.", "ok");
    } catch (fehler) {
      meldung(fehler.message, "fehler");
    }
  }

  function zugriffErlauben() {
    if (!hatErweiterung()) {
      meldung("Die Browser-Erweiterung antwortet nicht. Bitte diese Seite im Browser mit der Erweiterung öffnen.", "hinweis");
      return;
    }
    window.postMessage({ quelle: SEITE, art: "zugriff-erlauben" }, location.origin);
    meldung("Die Erweiterung hat eine eigene Seite geöffnet. Bitte dort erlauben.", "ok");
  }

  // The extension can refuse; then the page must not claim otherwise.
  window.addEventListener("message", ereignis => {
    const daten = ereignis.data;
    if (ereignis.source !== window || ereignis.origin !== location.origin) return;
    if (!daten || daten.quelle !== "bewerbungsbegleiter-erweiterung" || daten.art !== "antwort") return;
    if (daten.frage === "zugriff-erlauben" && daten.antwort && daten.antwort.fehler) meldung(daten.antwort.fehler, "fehler");
  });

  $("seiten-speichern").addEventListener("click", speichern);
  $("zugriff").addEventListener("click", zugriffErlauben);
  lade();
})();
