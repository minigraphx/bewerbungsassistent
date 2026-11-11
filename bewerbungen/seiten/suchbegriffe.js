"use strict";
// The view „Suchbegriffe prüfen“ (#210, option B of docs/design/suchbegriffe.md): one card per change with a checkbox,
// the reason of the AI and the evidence of the app, the result as „So sucht die App danach“, revise, take over, undo.
// The page names a change only by its place in the proposal; the app keeps the proposal and writes nothing unticked.
(() => {
  const { holen, senden, el, status, textsatz } = window.App;
  const L = window.SuchbegriffeLogik;
  const $ = id => document.getElementById(id);
  let satz = "stelle-sie";
  let texte = L.texte(satz);
  let vorschlag = null;
  let frueher = [];  // former proposals of this visit, „Vorschlag 1 zeigen“
  let gewaehlt = new Set();
  let abgebrochen = false;

  function meldung(titel, text, knoepfe = []) {
    $("meldung").hidden = false;
    $("meldung-titel").textContent = titel;
    $("meldung-text").textContent = text;
    $("meldung-knoepfe").replaceChildren(...knoepfe);
  }

  const knopf = (text, aktion, klasse = "btn btn--sm") => el("button", { type: "button", class: klasse, onclick: aktion }, text);
  const neuKnopf = () => knopf("Neu vorschlagen", () => holeVorschlag());

  function warten(an) {
    $("warten").hidden = !an;
    $("warten-titel").textContent = texte.warten;
    $("warten-notiz").textContent = texte.wartenNotiz;
  }

  async function holeVorschlag(body = {}) {
    abgebrochen = false;
    $("meldung").hidden = true;
    warten(true);
    try {
      const neu = await senden("/api/suchbegriffe/vorschlag", body);
      if (abgebrochen) return;
      if (vorschlag) frueher = [...frueher, vorschlag];
      zeige(neu);
    } catch (fehler) {
      if (!abgebrochen) meldung("Kein Vorschlag", fehler.message, [knopf("Nochmals versuchen", () => holeVorschlag(body))]);
    } finally {
      warten(false);
    }
  }

  function marke({ begriff, wort, art }) {
    return el("li", { class: `term term--${art}` }, el("span", { class: "term__name" }, begriff), el("span", { class: "term__word" }, wort));
  }

  function beleg(b) {
    const anteil = L.balken(b);
    const alle = el("span", { class: "share__all" });
    const unter = el("span", { class: "share__below" });
    alle.style.width = `${anteil.anteil}%`;
    unter.style.width = `${(anteil.anteil * anteil.unter) / 100}%`;
    return el("div", { class: "change__evidence" },
      el("div", { class: "share", "aria-hidden": "true" }, alle, unter),
      el("p", {}, L.belegSatz(b)),
      L.belegBeispiele(b) ? el("p", { class: "change__examples" }, L.belegBeispiele(b)) : null,
      el("p", {}, el("a", { href: L.belegAdresse(b) }, L.belegLink(b))));
  }

  function karte(a) {
    const id = `aenderung-${a.nummer}`;
    const haken = el("input", { type: "checkbox", id, "aria-describedby": `${id}-grund` });
    haken.checked = gewaehlt.has(a.nummer);
    haken.addEventListener("change", () => waehle(a.nummer, haken.checked));
    return el("div", { class: "change" },
      el("p", { class: "change__area" }, a.bereich_name,
        a.zu_allgemein ? el("span", { class: "term term--flag" }, el("span", { class: "term__word" }, "zu allgemein")) : null),
      el("label", { class: "check", for: id }, haken, el("span", {}, a.satz)),
      el("ul", { class: "terms" }, ...L.marken(a).map(marke)),
      el("p", { class: "change__reason", id: `${id}-grund` }, a.grund),
      a.beleg ? beleg(a.beleg) : null);
  }

  function zeigeEndstand(antwort) {
    const bloecke = L.endstand(vorschlag.jetzt, antwort.endstand).map(b => el("div", {},
      el("h3", {}, b.name),
      el("ul", { class: "terms" }, ...b.begriffe.map(x => marke({ begriff: x.begriff, wort: x.neu ? "neu" : "", art: x.neu ? "new" : "kept" })))));
    $("endstand").replaceChildren(...bloecke);
    $("faellt-weg").textContent = antwort.entfaellt.length ? `Fällt weg: ${antwort.entfaellt.join(", ")}` : "";
    $("grenzen").textContent = antwort.grenzen.zeile;
    $("uebernehmen").textContent = L.hauptknopf(gewaehlt.size, vorschlag.aenderungen.length);
    $("uebernehmen").disabled = Boolean(antwort.grenzen.gesperrt);
    $("uebernehmen-grund").textContent = antwort.grenzen.gesperrt || "";
  }

  function veraltet(text) {
    $("vorschlag").hidden = true;
    meldung("Vorschlag veraltet", text, [neuKnopf()]);
  }

  async function waehle(nummer, an) {
    gewaehlt = new Set([...gewaehlt].filter(n => n !== nummer).concat(an ? [nummer] : []));
    try {
      const antwort = await senden("/api/suchbegriffe/endstand", { vorschlag: vorschlag.vorschlag, gewaehlt: [...gewaehlt] });
      if (antwort.veraltet) veraltet(antwort.meldung);
      else zeigeEndstand(antwort);
    } catch (fehler) {
      status($("status"), fehler.message, "fehler");
    }
  }

  function zeigeKopf(v) {
    $("vorschlag-kopf").textContent = L.kopf(v.aenderungen.length);
    $("runde").hidden = v.runde < 2;
    $("runde").textContent = L.runde(v, satz);
    $("geaendert").hidden = !v.geaendert;
    $("geaendert").textContent = v.geaendert ? `Geändert gegenüber Vorschlag ${v.runde - 1}: ${v.geaendert}` : "";
    $("ihr-hinweis").hidden = !v.hinweis;
    $("ihr-hinweis").textContent = v.hinweis ? `${texte.ihrHinweis}: «${v.hinweis}»` : "";
    const davor = frueher[frueher.length - 1];
    $("frueher").hidden = !davor;
    $("frueher").textContent = davor ? `Vorschlag ${davor.runde} zeigen` : "";
    $("frueher").onclick = () => {
      frueher = [...frueher.slice(0, -1), vorschlag];  // swap, so the newer one can come back the same way
      zeige(davor);
    };
  }

  function zeige(v) {
    vorschlag = v;
    gewaehlt = new Set(v.aenderungen.map(a => a.nummer));
    $("gesehen").textContent = texte.gesehen(v.treffer, v.seit);
    $("anders").hidden = false;
    $("anders-hilfe").textContent = texte.andersHilfe;
    if (!v.aenderungen.length) {
      $("vorschlag").hidden = true;
      meldung(texte.passt, texte.passtNotiz);
      return;
    }
    $("vorschlag").hidden = false;
    zeigeKopf(v);
    $("zusammenfassung").textContent = v.zusammenfassung;
    $("aenderungen").replaceChildren(...v.aenderungen.map(karte));
    $("fuss-satz").textContent = texte.fuss;
    $("fuss").textContent = L.fuss(v);
    zeigeEndstand(v);
    $("vorschlag-kopf").focus();
  }

  async function rueckgaengig(stand) {
    try {
      await senden("/api/suchbegriffe/rueckgaengig", stand);
      status($("status"), L.RUECKGAENGIG_FERTIG, "ok");
    } catch (fehler) {
      status($("status"), fehler.message, "fehler");
    }
  }

  async function uebernehmen() {
    $("uebernehmen").disabled = true;
    try {
      const stand = await senden("/api/suchbegriffe/uebernehmen", { vorschlag: vorschlag.vorschlag, gewaehlt: [...gewaehlt] });
      $("aenderungen-feld").disabled = true;
      $("verwerfen").hidden = true;
      $("uebernehmen-grund").replaceChildren(el("a", { class: "btn btn--sm", href: "/treffer" }, "Jetzt suchen"));
      status($("status"), L.uebernommen(stand.anzahl), "ok",
        { aktion: { text: "Rückgängig machen", ausfuehren: () => rueckgaengig({ vorher: stand.vorher, nachher: stand.nachher }) } });
    } catch (fehler) {
      $("uebernehmen").disabled = false;
      if (fehler.message.startsWith("Vorschlag veraltet")) veraltet(fehler.message);
      else status($("status"), fehler.message, "fehler");
    }
  }

  function verwerfen() {
    $("vorschlag").hidden = true;
    meldung("Verworfen", "Am Suchprofil hat sich nichts geändert.", [neuKnopf()]);
  }

  function anders() {
    const hinweis = $("anders-text").value.trim();
    if (!hinweis) {
      status($("status"), "Bitte schreiben, was anders sein soll.", "fehler");
      $("anders-text").focus();
      return;
    }
    holeVorschlag(vorschlag ? { vorher: vorschlag.vorschlag, hinweis } : {});
  }

  async function einwilligungOffen() {
    try {
      const { einwilligung } = await holen("/api/ki/status");
      return einwilligung && !einwilligung.erteilt ? einwilligung : null;
    } catch {
      return null;  // the proposal route says what is missing
    }
  }

  async function start() {
    satz = await textsatz();
    texte = L.texte(satz);
    const vorab = await holen("/api/suchbegriffe/hinweis").catch(() => ({ verfuegbar: true }));
    if (!vorab.verfuegbar) {
      meldung("Nur bei der Stellensuche", "Suchbegriffe prüfen gibt es vorerst nur bei der Stellensuche.");
      return;
    }
    $("gesehen").textContent = texte.gesehen(vorab.treffer, vorab.seit);
    $("anders-kosten").textContent = vorab.kosten_usd ? L.schaetzung(vorab.kosten_usd) : "";
    const offen = await einwilligungOffen();
    if (!offen) {
      holeVorschlag();
      return;
    }
    meldung("", texte.einwilligung);
    window.Einwilligung.zeile($("einwilligung"), offen, neu => {
      if (neu.einwilligung && !neu.einwilligung.erteilt) return;
      $("einwilligung").hidden = true;
      holeVorschlag();
    });
  }

  $("abbrechen").addEventListener("click", () => {
    abgebrochen = true;
    warten(false);
    meldung("Abgebrochen", "Am Suchprofil hat sich nichts geändert.", [neuKnopf()]);
  });
  $("uebernehmen").addEventListener("click", uebernehmen);
  $("verwerfen").addEventListener("click", verwerfen);
  $("neu-vorschlagen").addEventListener("click", anders);
  start();
})();
