"use strict";
// On the page of an application (#226, G65): show the company's hits no more in the search, or show them again.
// The application itself stays as it is; only the search and the list of hits leave the company out.
(() => {
  const { holen, senden } = window.App;
  const $ = id => document.getElementById(id);
  const WIEDER = "Wieder in der Suche zeigen";
  let satz = "stelle-sie";
  let firma = "";
  let stand = null;  // { schluessel, ausgeschlossen } of the company as last loaded

  const t = (schluessel, werte) => window.Texte.text(schluessel, satz, werte);
  const meldung = (inhalt, stufe) => window.Meldungen.zeige($("firma-ausschliessen-status"), inhalt, stufe);

  function zeige() {
    const knopf = $("firma-ausschliessen");
    knopf.hidden = !stand || !stand.schluessel;
    knopf.disabled = false;
    if (stand) knopf.textContent = stand.ausgeschlossen ? WIEDER : t("firmen.ausschliessen");
  }

  async function lade(name) {
    firma = name || "";
    if (!firma) {
      stand = null;
      return zeige();
    }
    try {
      stand = (await holen("/api/firmen/ausgeschlossen", { firma })).firma;
    } catch (fehler) {
      stand = null;  // without the list the page still works, only without this button
      meldung(`Ob ${firma} in der Suche gezeigt wird, liess sich nicht laden. ${fehler.message}`, "hinweis");
    }
    zeige();
  }

  async function umschalten() {
    $("firma-ausschliessen").disabled = true;
    try {
      if (stand.ausgeschlossen) {
        stand = (await senden("/api/firmen/wieder-zeigen", { schluessel: stand.schluessel })).firma;
        meldung(`${firma}: Die Suche zeigt die Inserate wieder.`, "ok");
      } else {
        stand = (await senden("/api/firmen/ausschliessen", { name: firma })).firma;
        meldung(t("firmen.ausgeschlossen", { firma }), "ok");
      }
    } catch (fehler) {
      meldung(`${firma}: nicht geändert. ${fehler.message}`, "fehler");
    }
    zeige();
  }

  window.App.textsatz().then(gewaehlt => { satz = gewaehlt; zeige(); })
    .catch(fehler => meldung(`Texte für ${firma || "die Firma"}: ${fehler.message}`, "hinweis"));
  document.addEventListener("bewerbung-geladen", event => {
    const name = event.detail?.bewerbung?.firma || "";
    if (name !== firma) lade(name);
  });
  $("firma-ausschliessen").addEventListener("click", umschalten);
})();
