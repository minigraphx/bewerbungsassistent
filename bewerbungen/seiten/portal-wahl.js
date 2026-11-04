"use strict";
// Which portals the search uses (MIN-388): a box per portal, for everybody. Someone in a craft finds nothing on ictjobs.
window.PortalWahl = (() => {
  const { senden, el, status } = window.App;
  const $ = id => document.getElementById(id);

  function zeile(portal, wahl, neuLaden) {
    const kasten = el("input", { type: "checkbox" });
    kasten.checked = portal.an;
    kasten.addEventListener("change", async () => {
      const aus = wahl.filter(p => (p.name === portal.name ? !kasten.checked : !p.an)).map(p => p.name);
      try {
        await senden("/api/suche/einstellungen", { portale_aus: aus });
        status($("portale-meldung"), "");
        neuLaden();
      } catch (fehler) {
        kasten.checked = !kasten.checked;
        status($("portale-meldung"), fehler.message, "hinweis");
      }
    });
    return el("li", {}, el("label", { class: "auswahl" }, kasten, ` ${portal.name}`, el("span", { class: "leise" }, ` (${portal.hinweis})`)));
  }

  function zeige(wahl, lehrstelle, neuLaden) {
    $("portale-titel").textContent = lehrstelle ? "Wo suchst du?" : "Wo suchen Sie?";
    $("portale-liste").replaceChildren(...wahl.map(portal => zeile(portal, wahl, neuLaden)));
  }

  return { zeige };
})();
