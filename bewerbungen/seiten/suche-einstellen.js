"use strict";
// Suche einstellen (#263, A4, G57): what the search looks for in four cards plus Erweitert. Everything changes here;
// region, workload, exclusions and the title filter through their own forms (suche-rahmen.js, #286, G64).
(() => {
  const { holen, senden, status, textsatz, el } = window.App;
  const anzeige = window.SucheAnzeige;
  const logik = window.TrefferLogik;
  const L = window.SuchbegriffeLogik;
  const $ = id => document.getElementById(id);
  const NICHTS = "Nichts angegeben";
  const meldung = (inhalt, stufe) => status($("status"), inhalt, stufe);
  let ladeNummer = 0;

  function zeigeRahmen(daten, rahmen, lehrstelle, ausgeschlossen, satz) {
    $("region-text").textContent = anzeige.regionText(daten.region, lehrstelle) || NICHTS;
    const nischen = anzeige.nischenText(daten.region, lehrstelle, satz === "stelle-du");  // G111
    $("nischen-titel").hidden = !nischen;
    $("nischen-text").hidden = !nischen;
    $("nischen-text").textContent = nischen;
    $("pensum-titel").hidden = lehrstelle;
    $("pensum-text").hidden = lehrstelle;
    $("pensum-text").textContent = rahmen.pensum || NICHTS;
    // Excluded companies (#226, G65) hold for apprenticeships too; the exclusions of the profile only for jobs.
    for (const teil of $("karte-nicht").querySelectorAll(".nur-stelle")) teil.hidden = lehrstelle;
    $("firmen-ausgeschlossen-text").textContent = ausgeschlossen.map(firma => firma.name).join(", ") || NICHTS;
    $("ausschluss-text").textContent = rahmen.ausschluss.join(", ") || NICHTS;
    $("titel-ausschluss-text").textContent = rahmen.titel_ausschluss.join(", ") || NICHTS;
    $("titelfilter").hidden = lehrstelle;
    window.TitelfilterBeispiele.begriffe(rahmen.titel_positiv, rahmen.titel_ausschluss);
    window.SucheRahmen.zeige(rahmen, lehrstelle, ausgeschlossen, (daten.region && daten.region.nischen) || 0);
  }

  /** G105: a «Nur» line with an unknown portal, or a term whose portals are all switched off, under the list. */
  function zeigePortalHinweise(hinweise) {
    const liste = $("suchliste-portale-hinweise");
    liste.replaceChildren(...hinweise.map(text => el("li", { class: "notice notice--warning" }, el("p", { class: "notice__body" }, text))));
    liste.hidden = !hinweise.length;
  }

  function zeigeAblauf(daten) {
    $("auto-bewerten").checked = daten.einstellungen.auto_bewerten;
    $("zuschauen").checked = daten.einstellungen.zuschauen;
    $("auto-text").textContent = `Neue Treffer nach der Suche automatisch bewerten (höchstens ${daten.grenze} pro Suche)`;
  }

  /**
   * The cost of the check beside its link, worded like „Alle prüfen“ (#329); `fehler`: the estimate failed. Opening the
   * check sends the text at once, so a used-up credit locks the link.
   */
  function zeigeKosten(schaetzung, fehler) {
    const zeile = fehler ? { text: logik.estimateFailedText(fehler.message), usedUp: false } : logik.costLine(schaetzung);
    $("pruefen-kosten").replaceChildren(...(zeile.usedUp ? window.Texte.withCodeRequestLink(zeile.text, el) : [zeile.text]));
    L.lockCheckLink($("pruefen-knopf"), zeile.usedUp);
  }

  /** The check of the terms (G45, G15) with its cost; only a job search has it. */
  async function zeigePruefen(lehrstelle, nummer) {
    $("pruefen-block").hidden = true;
    if (lehrstelle) return;
    let schaetzung = null;
    let fehler = null;
    try {
      schaetzung = await holen("/api/suchbegriffe/schaetzung");
    } catch (grund) {
      fehler = grund;  // the box stays and says why the estimate is missing
    }
    const satz = await textsatz().catch(() => undefined);
    if (nummer !== ladeNummer || (schaetzung && !schaetzung.verfuegbar)) return;
    const texte = L.texte(satz);
    $("pruefen-satz").textContent = texte.satz;
    $("pruefen-was").textContent = texte.wasGeht;
    zeigeKosten(schaetzung, fehler);
    $("pruefen-block").hidden = false;
  }

  /** What each term and place brought (G103); on its own, so the rest of the page does not wait for it. */
  async function zeigeErtrag(nummer) {
    try {
      const ertrag = await holen("/api/suche/ertrag");
      if (nummer !== ladeNummer) return;
      window.SucheErtrag.zeige(ertrag, await textsatz());
      window.TitelfilterBeispiele.beispiele(ertrag.titelfilter);
    } catch (fehler) {
      meldung(`Was die Suche bringt, liess sich nicht laden: ${fehler.message}`, "fehler");
    }
  }

  async function lade() {
    const nummer = ++ladeNummer;
    try {
      const [daten, rahmen, firmen, satz] = await Promise.all([holen("/api/suche/liste"), holen("/api/suche/rahmen"),
        holen("/api/firmen/ausgeschlossen"), textsatz()]);
      if (nummer !== ladeNummer) return;  // a newer load is on its way
      const lehrstelle = daten.art === "lehrstelle";
      $("ohne-profil").hidden = !daten.sperrgrund;
      $("ohne-profil-text").textContent = daten.sperrgrund || "";
      $("angebot-wahl").hidden = !lehrstelle;
      $("angebot").value = logik.wahlAus(daten.angebote || []);
      window.Suchliste.portale(daten.begriff_portale);
      window.Suchliste.pflicht(daten.begriff_pflicht);
      zeigePortalHinweise(daten.portal_hinweise || []);
      window.Suchbegriffe.zeige(daten.art, daten.gesuchte_berufe || [], daten.gesuchte_schluessel || [], daten.begriff_laenge);
      window.PortalWahl.zeige(daten.portale_wahl || [], lade);
      zeigeRahmen(daten, rahmen, lehrstelle, firmen.firmen, satz);
      zeigeAblauf(daten);
      zeigePruefen(lehrstelle, nummer);
      zeigeErtrag(nummer);
      window.DoppeltGesucht.lade();
      window.OrteHinweise.lade();
      $("zusammenfassung").replaceChildren(...window.DotLine.render(anzeige.zusammenfassung({
        begriffe: daten.gesuchte_berufe || [], region: daten.region, portale: (daten.portale || []).length, lehrstelle,
      }), el));
    } catch (fehler) {
      meldung(fehler.message, "fehler");
    }
  }

  function schalter(id, feld) {
    $(id).addEventListener("change", event => {
      senden("/api/suche/einstellungen", { [feld]: event.target.checked })
        .catch(fehler => { event.target.checked = !event.target.checked; meldung(fehler.message, "fehler"); });
    });
  }

  async function textAnsehen() {
    try {
      const { text } = await holen("/api/suchbegriffe/text");
      $("ki-text-inhalt").textContent = text;
      $("ki-text").showModal();
      $("ki-text-schliessen").focus();
    } catch (fehler) {
      meldung(fehler.message, "fehler");
    }
  }

  $("angebot").addEventListener("change", async () => {
    try {
      const { angebote } = await senden("/api/suche/angebot", { wahl: $("angebot").value });
      meldung(logik.gesuchtText(angebote), "ok");
    } catch (fehler) {
      meldung(fehler.message, "fehler");
      lade();
    }
  });
  schalter("auto-bewerten", "auto_bewerten");
  schalter("zuschauen", "zuschauen");
  $("ki-text-ansehen").addEventListener("click", textAnsehen);
  $("ki-text-schliessen").addEventListener("click", () => $("ki-text").close());
  document.addEventListener("suchprofil-geaendert", lade);
  textsatz().then(satz => window.Texte.anwenden(document, satz)).finally(lade);
})();
