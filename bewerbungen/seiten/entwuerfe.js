"use strict";
(() => {
  const { holen, senden, el, status, url, datum, bestaetigen, pdfAdresse, zeitpunkt: zeit } = window.App;
  const $ = id => document.getElementById(id);
  const meldung = (text, art) => status($("status"), text, art);

  const Logik = window.EntwuerfeLogik;

  function zeigeText(text) {
    $("pdf-ansicht").hidden = true;
    $("ansicht").hidden = false;
    $("ansicht").textContent = text;
    $("ansicht").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  async function alsText(e) {
    const daten = await holen("/api/entwurf", { id: e.id });
    zeigeText(daten.text ?? "Inhalt ist binär und lässt sich nicht als Text anzeigen.");
  }

  // Ansehen: als PDF, wenn der Dateityp eines hat (Lebenslauf, Anschreiben, Markdown); sonst als Text
  async function ansehen(e) {
    if (!e.pdf) return alsText(e);
    meldung("PDF wird erstellt …");
    try {
      $("pdf").src = await pdfAdresse("/api/entwurf/pdf", { id: e.id });
      $("pdf-titel").textContent = `${e.titel} · ${zeit(e.zeit)}`;
      $("ansicht").hidden = true;
      $("pdf-ansicht").hidden = false;
      $("pdf-ansicht").scrollIntoView({ behavior: "smooth", block: "nearest" });
      meldung("");
    } catch (fehler) {
      meldung("Als PDF nicht möglich (" + fehler.message + "), daher als Text.", "hinweis");
      await alsText(e);
    }
  }

  async function vergleichen(alt, neu) {
    const { diff } = await holen("/api/entwurf/vergleich", { a: alt.id, b: neu.id });
    zeigeText(diff || "Keine Unterschiede.");
  }

  const knopf = (text, aktion) => el("button", { type: "button", class: "btn btn--sm", onclick: () => aktion().catch(f => meldung(f.message, "fehler")) }, text);

  function loeschenKnopf(e) {
    const knopfLoeschen = el("button", { type: "button", class: "btn btn--sm gefahr", disabled: e.genutzt, title: e.genutzt ? "Genutzt: " + e.genutzt_fuer.join(", ") : "" }, "Löschen");
    bestaetigen(knopfLoeschen, "Wirklich löschen?", async () => {
      try {
        await senden("/api/entwurf/loeschen", { id: e.id });
        meldung("Entwurf gelöscht", "ok");
        laden();
      } catch (fehler) { meldung(fehler.message, "fehler"); }
    });
    return knopfLoeschen;
  }

  function zurueckholenKnopf(e, dokument) {
    const knopfHolen = el("button", { type: "button", class: "btn btn--sm" }, "Zurückholen");
    bestaetigen(knopfHolen, "Diese Fassung zurückholen?", async () => {
      try {
        await senden("/api/entwurf/wiederherstellen", { id: e.id });
        meldung(`${dokument.titel} zurückgeholt (der Stand davor ist als Entwurf gesichert)`, "ok");
        laden();
      } catch (fehler) { meldung(fehler.message, "fehler"); }
    });
    return knopfHolen;
  }

  // One version: when, what, whether it was sent, and what can be done with it
  function fassung(e, knoepfe) {
    return el("li", { class: "drafts__version" },
      el("div", {}, el("time", { datetime: e.zeit }, zeit(e.zeit)), " · ", e.beschreibung || "ohne Beschreibung",
        e.genutzt ? el("span", { class: "leise", title: e.genutzt_fuer.join(", ") }, " · versendet") : null),
      el("div", { class: "knoepfe" }, knoepfe.filter(Boolean)));
  }

  function dokumentKarte(dokument) {
    const { neueste, aeltere } = Logik.fassungen(dokument);
    const alsTextKnopf = e => (e.pdf && !e.datei.endsWith(".pdf") ? knopf("Als Text", () => alsText(e)) : null);
    const oben = fassung(neueste, [knopf("Ansehen", () => ansehen(neueste)), alsTextKnopf(neueste),
      aeltere.length ? knopf("Vergleich mit vorher", () => vergleichen(aeltere[0], neueste)) : null, loeschenKnopf(neueste)]);
    const titel = Logik.aeltereTitel(aeltere);
    const gefaltet = titel ? el("details", { class: "drafts__older" }, el("summary", {}, titel),
      el("ul", {}, aeltere.map(e => fassung(e, [knopf("Ansehen", () => ansehen(e)), alsTextKnopf(e),
        knopf("Mit neuester vergleichen", () => vergleichen(e, neueste)), zurueckholenKnopf(e, dokument), loeschenKnopf(e)])))) : null;
    return el("article", { class: "karte drafts__doc" }, el("h4", {}, dokument.titel), el("ul", {}, [oben]), gefaltet);
  }

  function zeigeFilter(gruppen) {
    const knoepfe = Logik.filter(gruppen).map(f => el("button", {
      type: "button", class: "btn btn--sm", "aria-pressed": String(f.art === filterArt),
      onclick: () => { filterArt = f.art; zeige(); },
    }, f.titel, " ", el("span", { class: "num" }, String(f.zahl))));
    $("filter").replaceChildren(...knoepfe);
    $("filter").hidden = Boolean(nurDatei) || gruppen.length < 2;
  }

  let gruppen = [];
  let filterArt = Logik.ALLE;
  const nurDatei = new URLSearchParams(location.search).get("datei") || "";

  function zeige() {
    zeigeFilter(gruppen);
    const sichtbar = Logik.sichtbar(gruppen, { art: filterArt, datei: nurDatei });
    $("gruppen").replaceChildren(...sichtbar.map(g => el("section", { class: "drafts__group" },
      el("h3", {}, g.titel), ...g.dokumente.map(dokumentKarte))));
    $("leer").hidden = sichtbar.length > 0;
    $("nur-datei").hidden = !nurDatei;
  }

  async function laden() {
    try {
      ({ gruppen } = await holen("/api/entwuerfe"));
      if (!gruppen.some(g => g.art === filterArt)) filterArt = Logik.ALLE;
      zeige();
    } catch (fehler) {
      meldung("Laden fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  async function versionen() {
    try {
      const daten = await holen("/api/versionen");
      $("versionen-hinweis").textContent = daten.hinweis;
      const karten = daten.versionen.map(v => el("div", { class: "karte" },
        el("strong", {}, v.nachricht), el("div", { class: "leise" }, v.commit ? `${datum(v.datum)} · Git ${v.commit.slice(0, 10)}` : datum(v.datum)),
        el("ul", {}, v.dateien.map(d => el("li", {}, d.startsWith("versendet/")
          ? el("a", { href: url("/api/versendet", { datei: d }), target: "_blank", rel: "noopener" }, d) : d)))));
      $("versionen").replaceChildren(...(karten.length ? karten : [el("p", { class: "leer" }, "Noch nichts versendet.")]));
    } catch (fehler) {
      meldung("Versionen nicht lesbar: " + fehler.message, "fehler");
    }
  }

  laden();
  versionen();
})();
