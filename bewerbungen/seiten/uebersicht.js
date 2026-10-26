"use strict";
(() => {
  const { holen, senden, el, status, datum } = window.App;
  const $ = id => document.getElementById(id);
  // Spalten: Schlüssel im Register, Überschrift, Art (bestimmt die Sortierung)
  const SPALTEN = [
    ["firma", "Firma", "text"], ["stelle", "Stelle", "text"], ["status", "Status", "status"],
    ["passung", "Passung", "zahl"], ["eingetragen_am", "Eingetragen", "datum"],
    ["beworben_am", "Beworben", "datum"], ["absage_am", "Absage", "datum"], ["variante", "Variante", "text"],
  ];
  let alle = [];
  let statusReihe = [];
  let sortierung = { spalte: null, richtung: 1 };  // null = Reihenfolge des Servers (nach Status)

  function wert(b, spalte, art) {
    const w = b[spalte];
    if (art === "status") return statusReihe.indexOf(w);
    if (art === "zahl") return typeof w === "number" ? w : null;
    return w ? String(w).toLowerCase() : null;  // ISO-Datum sortiert als Text richtig
  }

  // Leere Werte immer ans Ende, unabhängig von der Richtung
  function vergleiche(a, b) {
    const [spalte, , art] = SPALTEN.find(([s]) => s === sortierung.spalte);
    const x = wert(a, spalte, art), y = wert(b, spalte, art);
    if (x === null || y === null) return (x === null) - (y === null);
    return (x < y ? -1 : x > y ? 1 : 0) * sortierung.richtung;
  }

  function kopf() {
    $("kopf").replaceChildren(...SPALTEN.map(([spalte, text, art]) => {
      const aktiv = sortierung.spalte === spalte;
      const pfeil = aktiv ? (sortierung.richtung === 1 ? " ▲" : " ▼") : "";
      const knopf = el("button", { type: "button", class: "sortieren", onclick: () => sortiere(spalte, art) }, text + pfeil);
      return el("th", { "aria-sort": aktiv ? (sortierung.richtung === 1 ? "ascending" : "descending") : "none" }, knopf);
    }));
  }

  function sortiere(spalte, art) {
    // Erster Klick: Text und Status aufsteigend, Zahlen und Daten absteigend (beste Note, neuestes Datum zuerst)
    const richtung = sortierung.spalte === spalte ? -sortierung.richtung : (art === "zahl" || art === "datum" ? -1 : 1);
    sortierung = { spalte, richtung };
    zeige();
  }

  function zeile(b) {
    const link = el("a", { href: "/bewerbung?id=" + encodeURIComponent(b.id) }, b.firma);
    return el("tr", {},
      el("td", {}, link),
      el("td", {}, b.stelle),
      el("td", {}, el("span", { class: "marke-status", "data-status": b.status }, b.status)),
      el("td", { class: "zahl" }, b.passung ?? ""),
      el("td", {}, datum(b.eingetragen_am)),
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
    const sortiert = sortierung.spalte ? [...auswahl].sort(vergleiche) : auswahl;
    kopf();
    $("liste").replaceChildren(...sortiert.map(zeile));
    $("leer").hidden = sortiert.length > 0;
  }

  async function laden() {
    try {
      const daten = await holen("/api/bewerbungen");
      alle = daten.bewerbungen;
      statusReihe = daten.status;
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
