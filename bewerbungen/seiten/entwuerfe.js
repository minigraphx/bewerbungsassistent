"use strict";
// Page „Entwürfe und Versionen“. Its texts come in the app language (#430); titles, notes, file names and what the
// server says stay as they come.
(() => {
  const { holen, senden, el, status, url, datum, bestaetigen, pdfAdresse, zeitpunkt: zeit } = window.App;
  /** A «·» line of whole parts (#342, dot-line.js): never starts with «·», screen readers hear commas. */
  const dotLine = parts => window.DotLine.render(parts, el);
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
    zeigeText(daten.text ?? window.Texte.t("Inhalt ist binär und lässt sich nicht als Text anzeigen."));
  }

  // Ansehen: als PDF, wenn der Dateityp eines hat (Lebenslauf, Anschreiben, Markdown); sonst als Text
  async function ansehen(e) {
    if (!e.pdf) return alsText(e);
    meldung(window.Texte.t("PDF wird erstellt …"));
    try {
      $("pdf").src = await pdfAdresse("/api/entwurf/pdf", { id: e.id });
      $("pdf-titel").replaceChildren(...dotLine([e.titel, zeit(e.zeit)]));
      $("ansicht").hidden = true;
      $("pdf-ansicht").hidden = false;
      $("pdf-ansicht").scrollIntoView({ behavior: "smooth", block: "nearest" });
      meldung("");
    } catch (fehler) {
      meldung(window.Texte.t("Als PDF nicht möglich ({fehler}), daher als Text.", { fehler: fehler.message }), "hinweis");
      await alsText(e);
    }
  }

  async function vergleichen(alt, neu) {
    const { diff } = await holen("/api/entwurf/vergleich", { a: alt.id, b: neu.id });
    zeigeText(diff || window.Texte.t("Keine Unterschiede."));
  }

  const knopf = (text, aktion) => el("button", { type: "button", class: "btn btn--sm", onclick: () => aktion().catch(f => meldung(f.message, "fehler")) }, text);

  function loeschenKnopf(e) {
    const genutzt = e.genutzt ? window.Texte.t("Genutzt: {zwecke}", { zwecke: e.genutzt_fuer.join(", ") }) : "";
    const knopfLoeschen = el("button", { type: "button", class: "btn btn--sm gefahr", disabled: e.genutzt, title: genutzt },
                             window.Texte.t("Löschen"));
    bestaetigen(knopfLoeschen, window.Texte.t("Wirklich löschen?"), async () => {
      try {
        await senden("/api/entwurf/loeschen", { id: e.id });
        meldung(window.Texte.t("Entwurf gelöscht"), "ok");
        laden();
      } catch (fehler) { meldung(fehler.message, "fehler"); }
    });
    return knopfLoeschen;
  }

  function zurueckholenKnopf(e, dokument) {
    const knopfHolen = el("button", { type: "button", class: "btn btn--sm" }, window.Texte.t("Zurückholen"));
    bestaetigen(knopfHolen, window.Texte.t("Diese Fassung zurückholen?"), async () => {
      try {
        await senden("/api/entwurf/wiederherstellen", { id: e.id });
        meldung(window.Texte.t("{titel} zurückgeholt (der Stand davor ist als Entwurf gesichert)", { titel: dokument.titel }), "ok");
        laden();
      } catch (fehler) { meldung(fehler.message, "fehler"); }
    });
    return knopfHolen;
  }

  // One version: when, what, with which application it went out, and what can be done with it
  function fassung(e, knoepfe) {
    const versendet = Logik.versandText(e);
    return el("li", { class: "drafts__version" },
      el("div", {}, dotLine([el("time", { datetime: e.zeit }, zeit(e.zeit)), e.beschreibung || window.Texte.t("ohne Beschreibung"),
        versendet ? el("span", { class: "drafts__sent" }, versendet) : null])),
      el("div", { class: "knoepfe" }, knoepfe.filter(Boolean)));
  }

  // The buttons of a version: the newest compares with the one before it, any other with the newest and can come back
  function knoepfe(e, dokument) {
    const [neueste, vorher] = dokument.fassungen;
    const textKnopf = e.pdf && !e.datei.endsWith(".pdf") ? knopf(window.Texte.t("Als Text"), () => alsText(e)) : null;
    const vergleich = e === neueste
      ? (vorher ? knopf(window.Texte.t("Vergleich mit vorher"), () => vergleichen(vorher, neueste)) : null)
      : knopf(window.Texte.t("Mit neuester vergleichen"), () => vergleichen(e, neueste));
    return [knopf(window.Texte.t("Ansehen"), () => ansehen(e)), textKnopf, vergleich, e === neueste ? null : zurueckholenKnopf(e, dokument),
      loeschenKnopf(e)];
  }

  function dokumentKarte(dokument) {
    const { oben, gefaltet, faltTitel } = Logik.ansicht(dokument, { nurVerwendet: nurVerwendet && !nurDatei });
    const gefaltetTeil = faltTitel ? el("details", { class: "drafts__older" }, el("summary", {}, faltTitel),
      el("ul", {}, gefaltet.map(e => fassung(e, knoepfe(e, dokument))))) : null;
    return el("article", { class: "karte drafts__doc" }, el("h4", {}, dokument.titel),
      el("ul", {}, oben.map(e => fassung(e, knoepfe(e, dokument)))), gefaltetTeil);
  }

  function zeigeFilter(gruppen) {
    const knoepfe = Logik.filter(gruppen, { nurVerwendet }).map(f => el("button", {
      type: "button", class: "btn btn--sm", "aria-pressed": String(f.art === filterArt),
      onclick: () => { filterArt = f.art; zeige(); },
    }, f.titel, " ", el("span", { class: "num" }, String(f.zahl))));
    $("filter").replaceChildren(...knoepfe);
    $("filter").hidden = Boolean(nurDatei) || gruppen.length < 2;
  }

  let gruppen = [];
  let filterArt = Logik.ALLE;
  const nurDatei = new URLSearchParams(location.search).get("datei") || "";

  // "Nur verwendete" stays across reloads; without storage (private window) it simply starts off
  const NUR_VERWENDETE = "entwuerfe.nurVerwendet";
  function gemerkt() {
    try { return Logik.gespeichert(localStorage.getItem(NUR_VERWENDETE)); } catch { return false; }
  }
  function merken(an) {
    try { localStorage.setItem(NUR_VERWENDETE, Logik.speicherwert(an)); } catch { /* the choice lasts until reload */ }
  }
  let nurVerwendet = gemerkt();
  $("nur-verwendete").checked = nurVerwendet;
  $("nur-verwendete").addEventListener("change", () => {
    nurVerwendet = $("nur-verwendete").checked;
    merken(nurVerwendet);
    zeige();
  });

  function zeige() {
    zeigeFilter(gruppen);
    const sichtbar = Logik.sichtbar(gruppen, { art: filterArt, datei: nurDatei, nurVerwendet: nurVerwendet && !nurDatei });
    $("gruppen").replaceChildren(...sichtbar.map(g => el("section", { class: "drafts__group" },
      el("h3", {}, g.titel), ...g.dokumente.map(dokumentKarte))));
    $("leer").hidden = sichtbar.length > 0;
    $("leer").textContent = nurVerwendet && !nurDatei && gruppen.length ? window.Texte.t("Noch nichts mit einer Bewerbung versendet.")
      : window.Texte.t("Noch keine Entwürfe.");
    $("nur-verwendete").closest("label").hidden = Boolean(nurDatei);
    $("nur-datei").hidden = !nurDatei;
  }

  async function laden() {
    try {
      ({ gruppen } = await holen("/api/entwuerfe"));
      if (!gruppen.some(g => g.art === filterArt)) filterArt = Logik.ALLE;
      zeige();
    } catch (fehler) {
      meldung(window.Texte.t("Laden fehlgeschlagen: {fehler}", { fehler: fehler.message }), "fehler");
    }
  }

  async function versionen() {
    try {
      const daten = await holen("/api/versionen");
      $("versionen-hinweis").textContent = daten.hinweis;
      const karten = daten.versionen.map(v => el("div", { class: "karte" },
        el("strong", {}, v.nachricht), el("div", { class: "leise" }, dotLine([datum(v.datum), v.commit ? `Git ${v.commit.slice(0, 10)}` : ""])),  // kein UI-Text: a commit id
        el("ul", {}, v.dateien.map(d => el("li", {}, d.startsWith("versendet/")
          ? el("a", { href: url("/api/versendet", { datei: d }), target: "_blank", rel: "noopener" }, d) : d)))));
      $("versionen").replaceChildren(...(karten.length ? karten : [el("p", { class: "leer" }, window.Texte.t("Noch nichts versendet."))]));
    } catch (fehler) {
      meldung(window.Texte.t("Versionen nicht lesbar: {fehler}", { fehler: fehler.message }), "fehler");
    }
  }

  laden();
  versionen();
})();
