"use strict";
// The page Firmen (G35, #188, docs/design/firmen.md): what state a company is in at kununu, the numbers as the
// page shows them, filters and sorting. No DOM, so it can be tested (tests/firmen_logik.test.cjs).
// A row comes from /api/firmen: { schluessel, name, ort, treffer: [{zustand}], bewerbungen: [{status}], kununu, suche }.
(function (global) {
  const WENIGE_UNTER = 10;       // under 10 reviews the value says little (Andy, 9.11.2026)
  const VERALTET_NACH_TAGEN = 90;
  const ABGESCHLOSSEN = ["Absage", "Zusage", "Verworfen", "Zurückgezogen"];
  const FILTER = ["alle", "neu", "bewerbung", "klaeren"];
  const ZU_KLAEREN = ["mehrere", "nicht_gefunden", "fehler"];
  const MIT_WERT = ["gefunden", "wenige"];
  // Sorting by kununu: values first, then the rest in this order; those without a value stay below in both directions.
  const RANG_OHNE_WERT = { keine: 0, mehrere: 1, nicht_gefunden: 2, fehler: 3, zugeordnet: 4, ungeprueft: 5 };
  const SPALTEN = { firma: "aufsteigend", kununu: "absteigend", verknuepft: "absteigend", geprueft: "absteigend" };
  const STANDARD_SORTIERUNG = { spalte: "verknuepft", richtung: "absteigend" };

  /** ungeprueft, zugeordnet, gefunden, wenige, keine, mehrere, nicht_gefunden or fehler. */
  function zustand(firma) {
    const k = firma.kununu;
    if (!k) return "ungeprueft";
    if (k.zustand !== "gefunden") return k.zustand;
    if (!k.bewertungen || typeof k.wert !== "number") return "keine";
    return k.bewertungen < WENIGE_UNTER ? "wenige" : "gefunden";
  }

  function tageZwischen(von, bis) {
    return Math.round((Date.parse(`${bis}T12:00:00Z`) - Date.parse(`${von}T12:00:00Z`)) / 86400000);
  }

  /** A value older than 90 days stays, with its date as „Stand“ and „Neu prüfen“. */
  function veraltet(firma, heute) {
    const am = firma.kununu?.geprueft_am;
    return Boolean(am) && ["gefunden", "wenige", "keine"].includes(zustand(firma)) && tageZwischen(am, heute) > VERALTET_NACH_TAGEN;
  }

  const wert = zahl => Number(zahl).toFixed(1);
  const anzahl = zahl => String(Math.round(zahl)).replace(/\B(?=(\d{3})+(?!\d))/g, "’");
  const prozent = zahl => `${Math.round(zahl)} %`;
  const datum = iso => (iso ? `${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(0, 4)}` : "");
  const bewertungen = zahl => `${anzahl(zahl)} ${zahl === 1 ? "Bewertung" : "Bewertungen"}`;
  /** Where the value comes from: the site of kununu, and whether the person entered it by hand (#189). */
  function seite(k) {
    const ort = k?.seite === "de" ? "kununu.com/de" : "kununu.com/ch";
    if (!k?.von_hand) return ort;
    return k.link ? `${ort}, von Hand eingetragen` : "von Hand eingetragen";
  }

  /** „3 Treffer, 2 neu“, „1 Treffer, verworfen“ or „“. */
  function trefferText(treffer) {
    if (!treffer.length) return "";
    const neu = treffer.filter(t => t.zustand === "neu").length;
    const zusatz = neu ? `${neu} neu` : treffer.every(t => t.zustand === "verworfen") ? "verworfen" : "";
    return [`${treffer.length} Treffer`, zusatz].filter(Boolean).join(", ");
  }

  const neueTreffer = firma => firma.treffer.filter(t => t.zustand === "neu").length;
  const offeneBewerbungen = firma => firma.bewerbungen.filter(b => !ABGESCHLOSSEN.includes(b.status)).length;

  function passt(firma, filter) {
    if (filter === "neu") return neueTreffer(firma) > 0;
    if (filter === "bewerbung") return offeneBewerbungen(firma) > 0;
    if (filter === "klaeren") return ZU_KLAEREN.includes(zustand(firma));
    return true;
  }

  function gueltigerFilter(filter) {
    return FILTER.includes(filter) ? filter : "alle";
  }

  /** The companies of a filter whose name contains the search, in any case. */
  function gefiltert(firmen, filter, suche = "") {
    const gesucht = suche.trim().toLocaleLowerCase("de");
    return firmen.filter(f => passt(f, gueltigerFilter(filter)) && (!gesucht || f.name.toLocaleLowerCase("de").includes(gesucht)));
  }

  function zaehlen(firmen) {
    return Object.fromEntries(FILTER.map(filter => [filter, firmen.filter(f => passt(f, filter)).length]));
  }

  const nachName = (a, b) => a.name.localeCompare(b.name, "de");

  function vergleich(spalte) {
    if (spalte === "firma") return nachName;
    if (spalte === "geprueft") return (a, b) => (a.kununu?.geprueft_am || "").localeCompare(b.kununu?.geprueft_am || "");
    // Companies with new hits first, then by all hits and applications together
    return (a, b) => (neueTreffer(a) - neueTreffer(b)) || (a.treffer.length + a.bewerbungen.length - b.treffer.length - b.bewerbungen.length);
  }

  function kununuGruppe(firma) {
    const z = zustand(firma);
    return z === "gefunden" ? 0 : z === "wenige" ? 1 : 2 + RANG_OHNE_WERT[z];
  }

  /** Sorted by kununu: enough reviews by value, then few reviews by value, then without a value, in both directions. */
  function nachKununu(firmen, richtung) {
    const vorzeichen = richtung === "aufsteigend" ? 1 : -1;
    return [...firmen].sort((a, b) => {
      const gruppe = kununuGruppe(a) - kununuGruppe(b);
      if (gruppe) return gruppe;
      return kununuGruppe(a) < 2 ? vorzeichen * (a.kununu.wert - b.kununu.wert) || nachName(a, b) : nachName(a, b);
    });
  }

  function sortiert(firmen, sortierung = STANDARD_SORTIERUNG) {
    const { spalte, richtung } = gueltigeSortierung(sortierung);
    if (spalte === "kununu") return nachKununu(firmen, richtung);
    const vorzeichen = richtung === "aufsteigend" ? 1 : -1;
    const vergleiche = vergleich(spalte);
    return [...firmen].sort((a, b) => vorzeichen * vergleiche(a, b) || nachName(a, b));
  }

  function gueltigeSortierung(sortierung) {
    const spalte = SPALTEN[sortierung?.spalte] ? sortierung.spalte : STANDARD_SORTIERUNG.spalte;
    const richtung = ["aufsteigend", "absteigend"].includes(sortierung?.richtung) ? sortierung.richtung : SPALTEN[spalte];
    return { spalte, richtung };
  }

  /** A click on a header: the same column turns round, another one starts in its own direction. */
  function naechsteSortierung(aktuell, spalte) {
    const jetzt = gueltigeSortierung(aktuell);
    if (jetzt.spalte !== spalte) return gueltigeSortierung({ spalte });
    return { spalte, richtung: jetzt.richtung === "aufsteigend" ? "absteigend" : "aufsteigend" };
  }

  /** Where „Prüfen“ and „Bei kununu suchen“ go: the assigned page if there is one, else the search on kununu.com/ch. */
  function pruefenLink(firma) {
    return firma.kununu?.link || firma.suche;
  }

  /** The line under the title: how many companies, how many found, when last checked. */
  function zusammenfassung(firmen) {
    const gefunden = firmen.filter(f => ["gefunden", "wenige", "keine"].includes(zustand(f))).length;
    const daten = firmen.map(f => f.kununu?.geprueft_am).filter(Boolean).sort();
    return { anzahl: firmen.length, gefunden, zuletzt: daten.length ? daten[daten.length - 1] : "" };
  }

  // „Prüfen“ through the extension (#189).
  const NICHT_GELESEN = "Der Tab bleibt offen; der Wert lässt sich von Hand eintragen.";
  const WERT_FALSCH = "Der Wert muss eine Zahl von 1 bis 5 sein.";
  const ANZAHL_FALSCH = "Die Anzahl Bewertungen muss eine ganze Zahl ab 0 sein.";

  /** What the page says after a check; null when the extension is missing and kununu only opened in a tab. */
  function pruefErgebnis(antwort, name) {
    if (antwort?.geoeffnet) return null;
    if (!antwort || antwort.fehler) return { text: antwort?.fehler || "Die Erweiterung antwortet nicht.", stufe: "warning", vonHand: false };
    if (!antwort.gelesen) return { text: `Bei kununu liess sich für ${name} kein Wert lesen. ${NICHT_GELESEN}`, stufe: "warning", vonHand: true };
    const k = antwort.kununu || {};
    const texte = {
      gefunden: () => `${name}: kununu ${wert(k.wert)} von 5, ${bewertungen(k.bewertungen)}.`,
      keine: () => `${name}: bei kununu noch keine Bewertungen.`,
      nicht_gefunden: () => `${name}: bei kununu nicht gefunden.`,
      mehrere: () => `${name}: mehrere Treffer bei kununu. Bitte den passenden wählen.`,
    };
    return { text: (texte[k.zustand] || texte.nicht_gefunden)(), stufe: "success", vonHand: false };
  }

  /** Score and count as the person typed them, or the field that is wrong and why. */
  function vonHandWerte(wertText, anzahlText) {
    const zahl = String(wertText ?? "").trim().replace(",", ".");
    const anzahlRoh = String(anzahlText ?? "").trim().replace(/[’'\s]/g, "");
    const wertZahl = /^\d+(\.\d+)?$/.test(zahl) ? Number(zahl) : NaN;
    if (!(wertZahl >= 1 && wertZahl <= 5)) return { fehler: WERT_FALSCH, feld: "wert" };
    if (!/^\d+$/.test(anzahlRoh)) return { fehler: ANZAHL_FALSCH, feld: "bewertungen" };
    return { wert: wertZahl, bewertungen: Number(anzahlRoh) };
  }

  const logik = { pruefErgebnis, vonHandWerte, WENIGE_UNTER, VERALTET_NACH_TAGEN, FILTER, MIT_WERT, STANDARD_SORTIERUNG, zustand, veraltet, wert, anzahl,
                  prozent, datum, bewertungen, seite, trefferText, gefiltert, zaehlen, sortiert, gueltigerFilter,
                  gueltigeSortierung, naechsteSortierung, pruefenLink, zusammenfassung };
  if (typeof module !== "undefined") module.exports = logik;
  else global.FirmenLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
