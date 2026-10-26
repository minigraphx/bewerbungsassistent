"use strict";
(() => {
  const { holen, senden, el, status, url, bestaetigen } = window.App;
  const $ = id => document.getElementById(id);
  const meldung = (text, art) => status($("status"), text, art);

  function zeit(iso) {
    const d = new Date(iso);
    return d.toLocaleString("de-CH", { dateStyle: "medium", timeStyle: "short" });
  }

  function zeigeText(text) {
    $("ansicht").hidden = false;
    $("ansicht").textContent = text;
    $("ansicht").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  async function ansehen(e) {
    if (e.datei.endsWith(".pdf")) {
      window.open(url("/api/entwurf/roh", { id: e.id }), "_blank", "noopener");
      return;
    }
    const daten = await holen("/api/entwurf", { id: e.id });
    zeigeText(daten.text ?? "Inhalt ist binär und lässt sich nicht als Text anzeigen.");
  }

  async function vergleichen(e, vorher) {
    const { diff } = await holen("/api/entwurf/vergleich", { a: vorher.id, b: e.id });
    zeigeText(diff || "Keine Unterschiede.");
  }

  function aktionen(e, vorher) {
    const loeschen = el("button", { class: "gefahr", disabled: e.genutzt, title: e.genutzt ? "Genutzt: " + e.genutzt_fuer.join(", ") : "" }, "Löschen");
    bestaetigen(loeschen, "Wirklich löschen?", async () => {
      try {
        await senden("/api/entwurf/loeschen", { id: e.id });
        meldung("Entwurf gelöscht", "ok");
        laden();
      } catch (fehler) { meldung(fehler.message, "fehler"); }
    });
    const herstellen = el("button", {}, "Wiederherstellen");
    bestaetigen(herstellen, "Datei überschreiben?", async () => {
      try {
        const r = await senden("/api/entwurf/wiederherstellen", { id: e.id });
        meldung(`${r.datei} wiederhergestellt (der Stand davor ist als Entwurf gesichert)`, "ok");
        laden();
      } catch (fehler) { meldung(fehler.message, "fehler"); }
    });
    const knoepfe = [
      el("button", { onclick: () => ansehen(e).catch(f => meldung(f.message, "fehler")) }, "Ansehen"),
      vorher ? el("button", { onclick: () => vergleichen(e, vorher).catch(f => meldung(f.message, "fehler")) }, "Vergleich mit vorher") : null,
      herstellen, loeschen,
    ];
    return el("div", { class: "knoepfe" }, knoepfe);
  }

  function zeige(entwuerfe) {
    const zeilen = entwuerfe.map((e, i) => {
      const vorher = entwuerfe.slice(i + 1).find(x => x.datei === e.datei);
      return el("tr", {},
        el("td", {}, zeit(e.zeit)), el("td", {}, e.datei), el("td", {}, e.beschreibung),
        el("td", {}, e.genutzt ? e.genutzt_fuer.join(", ") : "–"), el("td", {}, aktionen(e, vorher)));
    });
    $("entwuerfe").replaceChildren(...zeilen);
    $("leer").hidden = zeilen.length > 0;
  }

  async function laden() {
    try {
      const gewaehlt = $("datei").value;
      const daten = await holen("/api/entwuerfe", gewaehlt ? { datei: gewaehlt } : {});
      $("datei").replaceChildren(el("option", { value: "" }, "Alle Dateien"),
        ...daten.dateien.map(d => el("option", { value: d, selected: d === gewaehlt }, d)));
      zeige(daten.entwuerfe);
    } catch (fehler) {
      meldung("Laden fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  async function versionen() {
    try {
      const daten = await holen("/api/versionen");
      $("versionen-hinweis").textContent = daten.hinweis;
      const karten = daten.versionen.map(v => el("div", { class: "karte" },
        el("strong", {}, v.nachricht), el("div", { class: "leise" }, `${zeit(v.datum)} · ${v.commit.slice(0, 10)}`),
        el("ul", {}, v.dateien.map(d => el("li", {}, d.startsWith("versendet/")
          ? el("a", { href: url("/api/versendet", { datei: d }), target: "_blank", rel: "noopener" }, d) : d)))));
      $("versionen").replaceChildren(...(karten.length ? karten : [el("p", { class: "leer" }, "Noch nichts versendet.")]));
    } catch (fehler) {
      meldung("Versionen nicht lesbar: " + fehler.message, "fehler");
    }
  }

  $("datei").addEventListener("change", laden);
  laden();
  versionen();
})();
