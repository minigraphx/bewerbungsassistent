"use strict";
(() => {
  const { holen, senden, el, status, datum } = window.App;
  const $ = id => document.getElementById(id);
  let alle = [];

  function zeile(b) {
    const link = el("a", { href: "/bewerbung?id=" + encodeURIComponent(b.id) }, b.firma);
    return el("tr", {},
      el("td", {}, link),
      el("td", {}, b.stelle),
      el("td", {}, el("span", { class: "marke-status", "data-status": b.status }, b.status)),
      el("td", {}, datum(b.beworben_am)),
      el("td", {}, datum(b.absage_am)),
      el("td", {}, b.variante || ""),
    );
  }

  function zeige() {
    const suche = $("suche").value.trim().toLowerCase();
    const filter = $("statusfilter").value;
    const auswahl = alle.filter(b =>
      (!filter || b.status === filter) &&
      (!suche || `${b.firma} ${b.stelle} ${b.notiz || ""}`.toLowerCase().includes(suche)));
    $("liste").replaceChildren(...auswahl.map(zeile));
    $("leer").hidden = auswahl.length > 0;
  }

  async function laden() {
    try {
      const daten = await holen("/api/bewerbungen");
      alle = daten.bewerbungen;
      $("statusfilter").replaceChildren(el("option", { value: "" }, "Alle Status"),
        ...daten.status.map(s => el("option", { value: s }, `${s} (${alle.filter(b => b.status === s).length})`)));
      zeige();
    } catch (fehler) {
      status($("status"), "Laden fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  $("suche").addEventListener("input", zeige);
  $("statusfilter").addEventListener("change", zeige);
  $("anlegen").addEventListener("click", async () => {
    try {
      const b = await senden("/api/bewerbung/neu", { firma: $("neu-firma").value, stelle: $("neu-stelle").value });
      location.href = "/bewerbung?id=" + encodeURIComponent(b.id);
    } catch (fehler) {
      status($("status"), "Anlegen fehlgeschlagen: " + fehler.message, "fehler");
    }
  });
  laden();
})();
