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
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const bewertungen = zahl => (zahl === 1 ? Texte.t("1 Bewertung") : Texte.t("{anzahl} Bewertungen", { anzahl: anzahl(zahl) }));
  /** Where the value comes from: the site of kununu, and whether the person entered it by hand (#189). */
  function seite(k) {
    const ort = k?.seite === "de" ? "kununu.com/de" : "kununu.com/ch";
    if (!k?.von_hand) return ort;
    return k.link ? Texte.t("{seite}, von Hand eingetragen", { seite: ort }) : Texte.t("von Hand eingetragen");
  }

  /** „3 Treffer, 2 neu“, „1 Treffer, verworfen“ or „“. */
  function trefferText(treffer) {
    if (!treffer.length) return "";
    const Texte = texts();
    const neu = treffer.filter(t => t.zustand === "neu").length;
    const alle = treffer.length;
    if (neu) return [alle === 1 ? Texte.t("1 Treffer") : Texte.t("{anzahl} Treffer", { anzahl: alle }),
      neu === 1 ? Texte.t("1 neu") : Texte.t("{anzahl} neu", { anzahl: neu })].join(", ");
    if (treffer.every(t => t.zustand === "verworfen")) {
      return alle === 1 ? Texte.t("1 Treffer, verworfen") : Texte.t("{anzahl} Treffer, verworfen", { anzahl: alle });
    }
    return alle === 1 ? Texte.t("1 Treffer") : Texte.t("{anzahl} Treffer", { anzahl: alle });
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

  // „Prüfen“ through the extension (#189). The sentence for a page elsewhere is its own text (#421): the German one
  // was built by replacing „von Hand“, which a translation does not contain.
  function nichtGelesen(wo) {
    const Texte = texts();
    return wo ? Texte.t("Der Tab bleibt offen; der Wert lässt sich unter {wo} von Hand eintragen.", { wo })
      : Texte.t("Der Tab bleibt offen; der Wert lässt sich von Hand eintragen.");
  }
  const wertFalsch = () => Texte.t("Der Wert muss eine Zahl von 1 bis 5 sein.");
  const anzahlFalsch = () => Texte.t("Die Anzahl Bewertungen muss eine ganze Zahl ab 0 sein.");

  /** What the page says after a check; null when the extension is missing and kununu only opened in a tab.
   *  `wo` names the page for entering a value by hand when the check ran elsewhere (Stellen suchen). */
  function pruefErgebnis(antwort, name, { wo = "" } = {}) {
    if (antwort?.geoeffnet) return null;
    const Texte = texts();
    if (!antwort || antwort.fehler) return { text: antwort?.fehler || Texte.t("Die Erweiterung antwortet nicht."), stufe: "warning", vonHand: false };
    if (!antwort.gelesen) {
      return { text: Texte.t("Bei kununu liess sich für {name} kein Wert lesen. {weiter}", { name, weiter: nichtGelesen(wo) }),
               stufe: "warning", vonHand: true };
    }
    const k = antwort.kununu || {};
    const texte = {
      gefunden: () => Texte.t("{name}: kununu {wert} von 5, {bewertungen}.", { name, wert: wert(k.wert), bewertungen: bewertungen(k.bewertungen) }),
      keine: () => Texte.t("{name}: bei kununu noch keine Bewertungen.", { name }),
      nicht_gefunden: () => Texte.t("{name}: bei kununu nicht gefunden.", { name }),
      mehrere: () => Texte.t("{name}: mehrere Treffer bei kununu. Bitte den passenden wählen.", { name }),
    };
    return { text: (texte[k.zustand] || texte.nicht_gefunden)(), stufe: "success", vonHand: false };
  }

  /** Whether a check is due: never checked, page assigned, last check failed, or the value is out of date. Both pages
   *  offer „Prüfen“ by this rule; Stellen suchen names it „Jetzt prüfen“, „Nochmals prüfen“ or „Neu prüfen“. */
  function pruefungFaellig(firma, heute) {
    return ["ungeprueft", "zugeordnet", "fehler"].includes(zustand(firma)) || veraltet(firma, heute);
  }

  /** Whether „Von Hand eintragen“ shows. A check that cannot read stores nothing, so the company keeps its state: every
   *  company with a check due or without a value gets it, also on a fresh page after a check on Stellen suchen. */
  function vonHandAnbieten(firma, heute, nichtGelesen = new Set()) {
    return pruefungFaellig(firma, heute) || !MIT_WERT.includes(zustand(firma)) || nichtGelesen.has(firma.schluessel);
  }

  /** Score and count as the person typed them, or the field that is wrong and why. */
  function vonHandWerte(wertText, anzahlText) {
    const zahl = String(wertText ?? "").trim().replace(",", ".");
    const anzahlRoh = String(anzahlText ?? "").trim().replace(/[’'\s]/g, "");
    const wertZahl = /^\d+(\.\d+)?$/.test(zahl) ? Number(zahl) : NaN;
    if (!(wertZahl >= 1 && wertZahl <= 5)) return { fehler: wertFalsch(), feld: "wert" };
    if (!/^\d+$/.test(anzahlRoh)) return { fehler: anzahlFalsch(), feld: "bewertungen" };
    return { wert: wertZahl, bewertungen: Number(anzahlRoh) };
  }

  // Stellen suchen (#190): the badge after the company name and the company line in the detail column.

  /** Hit id → its company, from the hits each row of /api/firmen lists. */
  function nachTreffer(firmen) {
    return new Map(firmen.flatMap(firma => firma.treffer.map(t => [t.id, firma])));
  }

  /** The badge in a hit row, or null: text only (the row is a button), its full wording read with the button's name. */
  function marke(firma) {
    if (!firma) return null;
    const Texte = texts();
    const z = zustand(firma);
    const k = firma.kununu;
    const werte = { wert: wert(k?.wert), bewertungen: bewertungen(k?.bewertungen) };
    if (z === "gefunden") {
      return { text: Texte.t("kununu {wert} von 5", werte), vorlesen: Texte.t("kununu {wert} von 5, {bewertungen}", werte), art: "wert" };
    }
    if (z === "wenige") {
      return { text: Texte.t("kununu {wert} von 5, wenige Bewertungen", werte),
               vorlesen: Texte.t("kununu {wert} von 5, nur {bewertungen}", werte), art: "wenige" };
    }
    if (z === "mehrere") return { text: Texte.t("kununu: wählen"), vorlesen: Texte.t("kununu: passende Firma wählen"), art: "leise" };
    if (z === "nicht_gefunden") return { text: Texte.t("nicht bei kununu"), vorlesen: Texte.t("bei kununu nicht gefunden"), art: "leise" };
    return null;
  }

  function angabenMitWert(firma, z, lehrstelle) {
    const Texte = texts();
    const k = firma.kununu;
    const lernende = lehrstelle && k.lernende?.bewertungen && typeof k.lernende.wert === "number"
      ? Texte.t("Lernende: {wert} von 5, {bewertungen}", { wert: wert(k.lernende.wert), bewertungen: bewertungen(k.lernende.bewertungen) }) : "";
    const empfehlung = z === "gefunden" && typeof k.empfehlung === "number"
      ? Texte.t("{prozent} empfehlen", { prozent: prozent(k.empfehlung) }) : "";
    const anzahlText = z === "wenige" ? Texte.t("Nur {bewertungen}, wenig aussagekräftig.", { bewertungen: bewertungen(k.bewertungen) })
      : bewertungen(k.bewertungen);
    return [anzahlText, empfehlung, lernende, seite(k)].filter(Boolean);
  }

  function zeilenAktionen(firma, z, heute) {
    const Texte = texts();
    const link = firma.kununu?.link;
    const ansehen = link ? [{ art: "ansehen", text: Texte.t("Bei kununu ansehen"), href: link }] : [];
    const pruefen = text => [{ art: "pruefen", text, href: pruefenLink(firma) }];
    if (z === "ungeprueft") return pruefen(Texte.t("Jetzt prüfen"));
    if (z === "zugeordnet") return [...pruefen(Texte.t("Prüfen")), ...ansehen];
    if (z === "fehler") return pruefen(Texte.t("Nochmals prüfen"));
    if (z === "nicht_gefunden") return [{ art: "suchen", text: Texte.t("Bei kununu suchen"), href: firma.suche }];
    if (z === "mehrere") return [];
    return [...(pruefungFaellig(firma, heute) ? pruefen(Texte.t("Neu prüfen")) : []), ...ansehen];
  }

  /** The sentence of the detail column for a company without a value to show, or "". */
  function zeilenSatz(z, lehrstelle) {
    const Texte = texts();
    const saetze = {
      ungeprueft: () => Texte.t("Noch nicht bei kununu geprüft."),
      zugeordnet: () => Texte.t("Seite zugeordnet, noch nicht geprüft."),
      keine: () => Texte.t("Noch keine Bewertungen."),
      fehler: () => Texte.t("Nicht geprüft. kununu war nicht erreichbar. Bitte später nochmals prüfen."),
      nicht_gefunden: () => Texte.t("Bei kununu nicht gefunden."),
      mehrere: () => (lehrstelle ? Texte.t("Mehrere Lehrbetriebe bei kununu.") : Texte.t("Mehrere Firmen bei kununu.")),
    };
    return Object.hasOwn(saetze, z) ? saetze[z]() : "";
  }

  /** What the detail column says about the company of a hit; links open kununu in a new tab. */
  function firmenZeile(firma, heute, { lehrstelle = false } = {}) {
    const Texte = texts();
    const z = zustand(firma);
    const k = firma.kununu || {};
    const mitWert = MIT_WERT.includes(z);
    const geprueft = k.geprueft_am && z !== "zugeordnet"
      ? (veraltet(firma, heute) ? Texte.t("Stand {datum}", { datum: datum(k.geprueft_am) })
        : Texte.t("Geprüft am {datum}", { datum: datum(k.geprueft_am) })) : "";
    return { titel: Texte.t("{firma} bei kununu", { firma: firma.name }), zustand: z, wert: mitWert ? wert(k.wert) : null,
             wenige: z === "wenige", angaben: mitWert ? angabenMitWert(firma, z, lehrstelle) : [], datum: geprueft,
             satz: zeilenSatz(z, lehrstelle), aktionen: zeilenAktionen(firma, z, heute) };
  }

  const logik = { pruefErgebnis, vonHandWerte, vonHandAnbieten, pruefungFaellig, WENIGE_UNTER, VERALTET_NACH_TAGEN, FILTER, MIT_WERT, STANDARD_SORTIERUNG, zustand, veraltet, wert, anzahl,
                  prozent, datum, bewertungen, seite, trefferText, gefiltert, zaehlen, sortiert, gueltigerFilter,
                  gueltigeSortierung, naechsteSortierung, pruefenLink, zusammenfassung, nachTreffer, marke, firmenZeile };
  if (typeof module !== "undefined") module.exports = logik;
  else global.FirmenLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
