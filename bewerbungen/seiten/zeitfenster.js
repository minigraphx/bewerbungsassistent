"use strict";
// „Zeitfenster“ under Erweitert on Suche einstellen (#208, G32, G57): the window, written to the search profile, and
// the state per portal. Only for the job search; „Zeitfenster ändern“ on Stellen leads here (#zeitfenster).
(() => {
  const { holen, senden, status, el } = window.App;
  const anzeige = window.SucheAnzeige;
  const $ = id => document.getElementById(id);
  const GESPEICHERT = "Gespeichert. Gilt ab der nächsten Suche.";
  const NICHT_GESPEICHERT = "Nicht gespeichert.";

  function zeige(stand) {
    const fuerStellen = stand.art !== "lehrstelle";
    $("zeitfenster").hidden = !fuerStellen;
    if (!fuerStellen) return;
    $("zeitfenster-tage").replaceChildren(...anzeige.zeitfensterWahl(stand.zeitfenster)
      .map(wahl => el("option", { value: String(wahl.wert) }, wahl.text)));
    $("zeitfenster-tage").value = String(stand.zeitfenster);
    $("zeitfenster-portale-teil").hidden = !stand.portale.length;
    $("zeitfenster-portale").replaceChildren(...stand.portale.map(zeile => el("li", {}, anzeige.portalStand(zeile))));
  }

  async function speichere() {
    try {
      zeige(await senden("/api/suche/zeitfenster", { tage: Number($("zeitfenster-tage").value) }));
      status($("zeitfenster-meldung"), GESPEICHERT, "ok");
    } catch (fehler) {
      status($("zeitfenster-meldung"), `${NICHT_GESPEICHERT} ${fehler.message}`, "fehler");
    }
  }

  async function lade() {
    try {
      zeige(await holen("/api/suche/zeitfenster"));
      if (location.hash === "#zeitfenster" && !$("zeitfenster").hidden) {
        $("erweitert").open = true;
        $("zeitfenster-tage").focus();
      }
    } catch (fehler) {
      status($("zeitfenster-meldung"), fehler.message, "fehler");
    }
  }

  $("zeitfenster-tage").addEventListener("change", speichere);
  lade();
})();
