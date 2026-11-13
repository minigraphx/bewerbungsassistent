"use strict";
// Suche einstellen (#263, A4, G57): what the search looks for in four cards plus Erweitert. Everything changes here;
// region, workload, exclusions and the title filter through their own forms (suche-rahmen.js, #286, G64).
(() => {
  const { holen, senden, status, textsatz } = window.App;
  const anzeige = window.SucheAnzeige;
  const logik = window.TrefferLogik;
  const L = window.SuchbegriffeLogik;
  const $ = id => document.getElementById(id);
  const NICHTS = "Nichts angegeben";
  const meldung = (inhalt, stufe) => status($("status"), inhalt, stufe);
  let ladeNummer = 0;

  function zeigeRahmen(daten, rahmen, lehrstelle) {
    $("region-text").textContent = anzeige.regionText(daten.region, lehrstelle) || NICHTS;
    $("pensum-titel").hidden = lehrstelle;
    $("pensum-text").hidden = lehrstelle;
    $("pensum-text").textContent = rahmen.pensum || NICHTS;
    $("karte-nicht").hidden = lehrstelle;
    $("ausschluss-text").textContent = rahmen.ausschluss.join(", ") || NICHTS;
    $("titel-ausschluss-text").textContent = rahmen.titel_ausschluss.join(", ") || NICHTS;
    const filter = anzeige.titelfilterText(rahmen.titel_positiv, rahmen.titel_ausschluss);
    $("titelfilter").hidden = lehrstelle;
    $("titelfilter-text").textContent = filter || window.SucheRahmenLogik.titelfilterLeer;
    window.SucheRahmen.zeige(rahmen, lehrstelle);
  }

  function zeigeAblauf(daten) {
    $("auto-bewerten").checked = daten.einstellungen.auto_bewerten;
    $("zuschauen").checked = daten.einstellungen.zuschauen;
    $("auto-text").textContent = `Neue Treffer nach der Suche automatisch bewerten (höchstens ${daten.grenze} pro Suche)`;
  }

  /** The check of the terms (G45, G15) with its cost; only a job search with hits has it. */
  async function zeigePruefen(lehrstelle) {
    $("pruefen-block").hidden = true;
    if (lehrstelle) return;
    try {
      const [antwort, satz] = await Promise.all([holen("/api/suchbegriffe/hinweis"), textsatz()]);
      const texte = L.texte(satz);
      $("pruefen-block").hidden = !antwort.verfuegbar;
      $("pruefen-kosten").textContent = L.schaetzung(antwort.kosten_usd);
      $("pruefen-satz").textContent = texte.satz;
      $("pruefen-was").textContent = texte.wasGeht;
    } catch {
      /* the check is extra; the terms work without it */
    }
  }

  async function lade() {
    const nummer = ++ladeNummer;
    try {
      const [daten, rahmen] = await Promise.all([holen("/api/suche/liste"), holen("/api/suche/rahmen")]);
      if (nummer !== ladeNummer) return;  // a newer load is on its way
      const lehrstelle = daten.art === "lehrstelle";
      $("ohne-profil").hidden = !daten.sperrgrund;
      $("ohne-profil-text").textContent = daten.sperrgrund || "";
      $("angebot-wahl").hidden = !lehrstelle;
      $("angebot").value = logik.wahlAus(daten.angebote || []);
      window.Suchbegriffe.zeige(daten.art, daten.gesuchte_berufe || [], daten.gesuchte_schluessel || []);
      window.PortalWahl.zeige(daten.portale_wahl || [], lade);
      zeigeRahmen(daten, rahmen, lehrstelle);
      zeigeAblauf(daten);
      zeigePruefen(lehrstelle);
      $("zusammenfassung").textContent = anzeige.zusammenfassung({
        begriffe: daten.gesuchte_berufe || [], region: daten.region, portale: (daten.portale || []).length, lehrstelle,
      });
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
      meldung(`Gesucht wird: ${logik.sucheText(angebote).replace(/ suchen$/, "")}.`, "ok");
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
