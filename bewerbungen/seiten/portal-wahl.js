"use strict";
// Which portals the search uses (MIN-388): a box per portal, for everybody. Someone in a craft finds nothing on ictjobs.
window.PortalWahl = (() => {
  const { senden, el, status } = window.App;
  const $ = id => document.getElementById(id);

  function zeile(portal, kaesten, neuLaden) {
    const kasten = kaesten.get(portal.name);
    kasten.checked = portal.an;
    kasten.addEventListener("change", async () => {
      // From the boxes, not from the list at load time: a second click comes before the page has reloaded.
      const aus = [...kaesten].filter(([, box]) => !box.checked).map(([name]) => name);
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
    const kaesten = new Map(wahl.map(portal => [portal.name, el("input", { type: "checkbox" })]));
    $("portale-liste").replaceChildren(...wahl.map(portal => zeile(portal, kaesten, neuLaden)));
  }

  return { zeige };
})();
