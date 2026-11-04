"use strict";
// Page „Erweiterte Einstellungen“ (MIN-348). The key field is sent once and emptied; the key never comes back.
(() => {
  const { holen, senden, status } = window.App;
  const $ = id => document.getElementById(id);
  const usd = wert => `${Number(wert).toFixed(2)} USD`;

  function zeige(stand) {
    $("ohne-schluessel").hidden = stand.gesetzt;
    $("mit-schluessel").hidden = !stand.gesetzt;
    $("kosten-monat").textContent = usd(stand.kosten.monat_usd);
    $("kosten-gesamt").textContent = usd(stand.kosten.gesamt_usd);
    $("kosten-aufrufe").textContent = String(stand.kosten.aufrufe);
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
      status($("meldung"), "Der Schlüssel ist entfernt. Die App läuft wieder über die Vermittlung.", "ok");
    } catch (fehler) {
      status($("meldung"), fehler.message, "fehler");
    } finally {
      $("entfernen").disabled = false;
    }
  }

  $("bestaetigt").addEventListener("change", pruefeBereit);
  $("schluessel").addEventListener("input", pruefeBereit);
  $("speichern").addEventListener("click", speichern);
  $("entfernen").addEventListener("click", entfernen);
  holen("/api/schluessel").then(zeige).catch(fehler => status($("meldung"), fehler.message, "fehler"));
})();
