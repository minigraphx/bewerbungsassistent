"use strict";
// On the page of an application (#226, G65): show the company's hits no more in the search, or show them again.
// The application itself stays as it is; only the search and the list of hits leave the company out. The same
// words as on a hit and on Firmen (#303).
(() => {
  const { holen } = window.App;
  const $ = id => document.getElementById(id);
  let satz = "stelle-sie";
  let firma = "";
  let stand = null;  // { schluessel, ausgeschlossen } of the company as last loaded

  const t = (schluessel, werte) => window.Texte.text(schluessel, satz, werte);
  const meldung = (inhalt, stufe) => window.Meldungen.zeige($("firma-ausschliessen-status"), inhalt, stufe);

  function zeige() {
    const knopf = $("firma-ausschliessen");
    knopf.hidden = !stand || !stand.schluessel;
    knopf.disabled = false;
    if (stand) knopf.textContent = t(stand.ausgeschlossen ? "firmen.wieder-zeigen" : "firmen.ausschliessen");
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
      meldung(window.Texte.t("Ob {firma} in der Suche gezeigt wird, liess sich nicht laden. {fehler}", { firma, fehler: fehler.message }),
        "hinweis");
    }
    zeige();
  }

  async function umschalten() {
    $("firma-ausschliessen").disabled = true;
    try {
      if (stand.ausgeschlossen) {
        stand = await window.FirmenAusschluss.wiederZeigen(stand.schluessel);
        meldung(t("firmen.wieder-gezeigt", { firma }), "ok");
      } else {
        stand = await window.FirmenAusschluss.ausschliessen(firma);
        meldung(t("firmen.ausgeschlossen", { firma }), "ok");
      }
    } catch (fehler) {
      meldung(`${t("firmen.nicht-geaendert", { firma })} ${fehler.message}`, "fehler");
    }
    zeige();
  }

  window.App.textsatz().then(gewaehlt => { satz = gewaehlt; zeige(); })
    .catch(fehler => meldung(window.Texte.t("Texte für {firma}: {fehler}",
      { firma: firma || window.Texte.t("die Firma"), fehler: fehler.message }), "hinweis"));
  document.addEventListener("bewerbung-geladen", event => {
    const name = event.detail?.bewerbung?.firma || "";
    if (name !== firma) lade(name);
  });
  $("firma-ausschliessen").addEventListener("click", umschalten);
})();
