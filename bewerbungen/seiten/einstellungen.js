"use strict";
// Page „Erweiterte Einstellungen“ (MIN-348). The key field is sent once and emptied; the key never comes back.
(() => {
  const { holen, senden, status, bestaetigen } = window.App;
  const $ = id => document.getElementById(id);
  const usd = wert => `${Number(wert).toFixed(2)} USD`;
  const SEITE = "bewerbungsbegleiter-seite";
  const anErweiterung = art => window.postMessage({ quelle: SEITE, art }, location.origin);
  const hatErweiterung = () => Boolean(document.documentElement.dataset.bewerbungsbegleiterErweiterung);

  function zeige(stand) {
    $("ohne-schluessel").hidden = stand.gesetzt;
    $("mit-schluessel").hidden = !stand.gesetzt;
    $("kosten-monat").textContent = usd(stand.kosten.monat_usd);
    $("kosten-gesamt").textContent = usd(stand.kosten.gesamt_usd);
    $("kosten-aufrufe").textContent = String(stand.kosten.aufrufe);
    if (stand.gesetzt) ladeSeiten();
  }

  function zeigeEinwilligung(ki) {
    const erteilt = ki.einwilligung.erteilt;
    $("einwilligung-erteilt").hidden = !erteilt;
    $("einwilligung-offen").hidden = erteilt;
    $("einwilligung-link").replaceChildren(...[window.Einwilligung.link(ki.einwilligung)].filter(Boolean));  // none without a built-in address
    if (!erteilt) window.Einwilligung.zeige($("einwilligung-offen"), ki.einwilligung, zeigeEinwilligung);
    status($("einwilligung-meldung"), ki.einladung_fehler || "", ki.einladung_fehler ? "fehler" : "");
  }

  function ladeEinwilligung() {
    holen("/api/ki/status").then(zeigeEinwilligung, fehler => status($("einwilligung-meldung"), fehler.message, "fehler"));
  }

  function zeigeSeiten(stand) {
    $("max-seiten").textContent = String(stand.max_seiten);
    $("seiten").value = stand.seiten.map(seite => seite.adresse).join("\n");
    $("zugriff").hidden = !stand.seiten.length;
  }

  async function ladeSeiten() {
    try {
      zeigeSeiten(await holen("/api/suche/weitere-seiten"));
    } catch (fehler) {
      status($("seiten-meldung"), fehler.message, "fehler");
    }
  }

  async function seitenSpeichern() {
    const seiten = $("seiten").value.split("\n").map(zeile => zeile.trim()).filter(Boolean);
    try {
      zeigeSeiten(await senden("/api/suche/weitere-seiten", { seiten }));
      status($("seiten-meldung"), seiten.length ? "Gespeichert. Die Seiten kommen bei der nächsten Suche dazu." : "Gespeichert.", "ok");
    } catch (fehler) {
      status($("seiten-meldung"), fehler.message, "fehler");
    }
  }

  function zugriffErlauben() {
    if (!hatErweiterung()) {
      status($("seiten-meldung"), "Die Browser-Erweiterung antwortet nicht. Bitte diese Seite im Browser mit der Erweiterung öffnen.", "hinweis");
      return;
    }
    anErweiterung("zugriff-erlauben");
    status($("seiten-meldung"), "Die Erweiterung hat eine eigene Seite geöffnet. Bitte dort erlauben.", "ok");
  }

  function pruefeBereit() {
    $("speichern").disabled = !$("bestaetigt").checked || !$("schluessel").value.trim();
  }

  async function speichern() {
    $("speichern").disabled = true;
    status($("meldung"), "Der Schlüssel wird geprüft …");
    try {
      zeige(await senden("/api/schluessel/speichern", { schluessel: $("schluessel").value, bestaetigt: $("bestaetigt").checked }));
      status($("meldung"), "Gespeichert. Die KI-Aufrufe gehen jetzt direkt an die Claude API.", "ok");
    } catch (fehler) {
      status($("meldung"), fehler.message, "fehler");
    } finally {
      $("schluessel").value = "";
      pruefeBereit();
    }
  }

  async function entfernen() {
    $("entfernen").disabled = true;
    try {
      zeige(await senden("/api/schluessel/entfernen", {}));
      $("bestaetigt").checked = false;
      pruefeBereit();
      anErweiterung("zugriff-abgeben");
      const abgabe = hatErweiterung() ? "" : " Die Erweiterung gibt den Zugriff ab, sobald sie das nächste Mal mit der App verbunden ist.";
      status($("meldung"), `Der Schlüssel ist entfernt. Die App läuft wieder über die Vermittlung.${abgabe}`, "ok");
    } catch (fehler) {
      status($("meldung"), fehler.message, "fehler");
    } finally {
      $("entfernen").disabled = false;
    }
  }

  // What the extension answers about the access: it can fail, and then the page must not claim otherwise.
  window.addEventListener("message", ereignis => {
    const daten = ereignis.data;
    if (ereignis.source !== window || ereignis.origin !== location.origin) return;
    if (!daten || daten.quelle !== "bewerbungsbegleiter-erweiterung" || daten.art !== "antwort") return;
    if (daten.frage === "zugriff-abgeben") {
      const text = daten.antwort && daten.antwort.fehler
        ? `Die Erweiterung konnte den Zugriff nicht abgeben (${daten.antwort.fehler}). Das geht auch in ihren Einstellungen im Browser.`
        : daten.antwort && daten.antwort.spaeter
          ? "Die Erweiterung gibt den Zugriff ab, sobald die laufende Suche oder die offenen Formulare fertig sind."
          : "Die Erweiterung hat den Zugriff auf alle Seiten abgegeben.";
      status($("zugriff-meldung"), text, daten.antwort && daten.antwort.fehler ? "fehler" : "ok");
    }
    if (daten.frage === "zugriff-erlauben" && daten.antwort && daten.antwort.fehler) {
      status($("seiten-meldung"), daten.antwort.fehler, "fehler");
    }
  });

  $("bestaetigt").addEventListener("change", pruefeBereit);
  $("schluessel").addEventListener("input", pruefeBereit);
  $("speichern").addEventListener("click", speichern);
  $("entfernen").addEventListener("click", entfernen);
  $("seiten-speichern").addEventListener("click", seitenSpeichern);
  $("zugriff").addEventListener("click", zugriffErlauben);
  holen("/api/schluessel").then(zeige).catch(fehler => status($("meldung"), fehler.message, "fehler"));
  bestaetigen($("einwilligung-widerruf"), "Wirklich widerrufen? Nochmals klicken", async () => {
    try {
      zeigeEinwilligung(await senden("/api/ki/einwilligung/widerruf", {}));
    } catch (fehler) {
      status($("einwilligung-meldung"), fehler.message, "fehler");
    }
  });
  ladeEinwilligung();
})();
