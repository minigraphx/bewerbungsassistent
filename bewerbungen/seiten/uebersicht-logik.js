"use strict";
// The overview after the design (MIN-369): what comes next for each application, which ones are still running,
// and what „Das steht an“ shows first. No DOM, so it can be tested (tests/uebersicht_logik.test.cjs).
// `grund` is why the app cannot open the form yet (/api/bewerben/auswahl, null = ready), `ravGrund` why it cannot
// be entered in the Job-Room (/api/rav/auswahl, null = can be entered, undefined = no RAV).
(function (global) {
  const LAUFEND = ["Gemerkt", "Bewerben", "Beworben", "Gespräch"];
  const NACHFRAGEN_NACH_TAGEN = 14;
  const OHNE_LEBENSLAUF = "Lebenslauf-PDF fehlt";  // apply.NO_CV starts so
  const OHNE_LINK = "Kein Link zum Formular";      // apply.NO_LINK starts so
  const OHNE_FREIGABE = "Anschreiben noch nicht freigegeben";  // apply.NOT_APPROVED starts so
  // The order of what to do: an interview first, then sending, then what is missing, then the RAV, then deciding.
  const RANG = { gespraech: 0, abschicken: 1, freigeben: 1, unterlagen: 2, link: 2, offen: 2, rav: 3, entscheiden: 4, warten: 5, fertig: 6 };
  const GRUPPE_AB = 2;  // from two of a kind, one line does them together

  function plusTage(iso, tage) {
    const tag = new Date(`${iso}T12:00:00Z`);
    tag.setUTCDate(tag.getUTCDate() + tage);
    return tag.toISOString().slice(0, 10);
  }

  function datum(iso) {
    if (!iso) return "";
    const [j, m, t] = iso.split("-");
    return `${t}.${m}.${j}`;
  }

  const laufend = b => LAUFEND.includes(b.status);

  /** { art, frist?, zusatz?, grund? } — art is one of RANG; frist an ISO date that orders and shows in the list. */
  function naechsterSchritt(b, { grund, ravGrund } = {}) {
    const ravOffen = ravGrund === null;
    switch (b.status) {
      case "Gemerkt":
        return { art: "entscheiden", frist: b.frist };
      case "Bewerben":
        if (grund === null) return { art: "abschicken", frist: b.frist };
        if (typeof grund === "string" && grund.startsWith(OHNE_LEBENSLAUF)) return { art: "unterlagen", frist: b.frist };
        if (typeof grund === "string" && grund.startsWith(OHNE_LINK)) return { art: "link", frist: b.frist };
        if (typeof grund === "string" && grund.startsWith(OHNE_FREIGABE)) return { art: "freigeben", frist: b.frist };
        return { art: "offen", frist: b.frist, grund: grund || "" };
      case "Beworben":
        if (ravOffen) return { art: "rav" };
        return { art: "warten", zusatz: b.beworben_am ? plusTage(b.beworben_am, NACHFRAGEN_NACH_TAGEN) : "" };
      case "Gespräch":
        return { art: "gespraech", frist: b.gespraech_am };
      default:
        return ravOffen ? { art: "rav" } : { art: "fertig" };
    }
  }

  function vergleiche(a, b) {
    return RANG[a.schritt.art] - RANG[b.schritt.art]
      || (a.schritt.frist || "9999").localeCompare(b.schritt.frist || "9999")
      || (b.bewerbung.eingetragen_am || "").localeCompare(a.bewerbung.eingetragen_am || "");
  }

  /** Every application with its next step, in the order of the list: what to do first, the closest date first. */
  function mitSchritten(alle, gruende = new Map(), ravGruende = new Map()) {
    return alle.map(bewerbung => ({
      bewerbung,
      schritt: naechsterSchritt(bewerbung, { grund: gruende.get(bewerbung.id), ravGrund: ravGruende.get(bewerbung.id) }),
    })).sort(vergleiche);
  }

  /** Laufend, Abgeschlossen or Alle, with the search over company, position and note. */
  function gefiltert(zeilen, ansicht, suche) {
    const wort = (suche || "").trim().toLowerCase();
    return zeilen.filter(({ bewerbung: b, schritt }) =>
      (ansicht === "alle" || (ansicht === "abgeschlossen") === (!laufend(b) && schritt.art !== "rav"))
      && (!wort || `${b.firma} ${b.stelle} ${b.notiz || ""}`.toLowerCase().includes(wort)));
  }

  // Sorting by a column (MIN-404). A value of null means nothing to compare: it stays at the bottom in both directions.
  const VERLAUF = ["Gemerkt", "Bewerben", "Beworben", "Gespräch", "Zusage", "Absage", "Zurückgezogen", "Verworfen"];
  const position = wert => (wert < 0 ? null : wert);
  const SPALTEN = {
    stelle: z => z.bewerbung.stelle || null,
    stand: z => position(VERLAUF.indexOf(z.bewerbung.status)),
    note: z => (typeof z.bewerbung.passung === "number" ? z.bewerbung.passung : null),
    schritt: z => RANG[z.schritt.art] ?? null,
    frist: z => z.schritt.frist || null,
  };
  const ZUERST_ABSTEIGEND = ["note"];  // the best grade first
  const GEGENTEIL = { auf: "ab", ab: "auf" };

  function vergleicheWerte(a, b) {
    return typeof a === "number" ? a - b : a.localeCompare(b, "de", { sensitivity: "base" });
  }

  /** A copy of the rows by the chosen column; without one, or with equal values, the order of the app stays. */
  function sortiert(zeilen, sortierung) {
    const wert = sortierung && SPALTEN[sortierung.spalte];
    if (!wert) return zeilen;
    const zeichen = sortierung.richtung === "ab" ? -1 : 1;
    return [...zeilen].sort((a, b) => {
      const [x, y] = [wert(a), wert(b)];
      if (x === null || y === null) return (x === null) - (y === null);
      return zeichen * vergleicheWerte(x, y);
    });
  }

  /** What a click on a column heading does: first direction, the other one, back to the order of the app. */
  function naechsteSortierung(aktuell, spalte) {
    const erste = ZUERST_ABSTEIGEND.includes(spalte) ? "ab" : "auf";
    if (aktuell?.spalte !== spalte) return { spalte, richtung: erste };
    return aktuell.richtung === erste ? { spalte, richtung: GEGENTEIL[erste] } : null;
  }

  /** A sorting from the browser's storage, if it is one this page knows. */
  function gueltigeSortierung(wert) {
    return wert && Object.hasOwn(SPALTEN, wert.spalte ?? "") && Object.hasOwn(GEGENTEIL, wert.richtung ?? "")
      ? { spalte: wert.spalte, richtung: wert.richtung } : null;
  }

  /** „Abgeschlossen: 1 Zusage, 5 Absagen, 1 zurückgezogen.“ — counts per status of what the view „Abgeschlossen“ shows. */
  function abgeschlossenZaehlen(zeilen) {
    const zahl = {};
    for (const { bewerbung: b } of gefiltert(zeilen, "abgeschlossen", "")) zahl[b.status] = (zahl[b.status] || 0) + 1;
    return zahl;
  }

  /**
   * What „Das steht an“ shows: the first thing to do as the big card, the next few below. Two or more
   * applications that are ready to send (or to enter in the Job-Room) become one item, so they open together.
   * Items: { art, eintraege: [{bewerbung, schritt}] } — one entry, or several for a group.
   */
  function stehtAn(zeilen, hoechstens = 4) {
    const zuTun = zeilen.filter(z => !["warten", "fertig"].includes(z.schritt.art));
    const gruppen = [];
    const einzeln = [];
    for (const art of ["abschicken", "rav"]) {
      const gleiche = zuTun.filter(z => z.schritt.art === art);
      if (gleiche.length >= GRUPPE_AB) gruppen.push({ art, eintraege: gleiche });
    }
    const gruppiert = new Set(gruppen.map(g => g.art));
    for (const z of zuTun) if (!gruppiert.has(z.schritt.art)) einzeln.push({ art: z.schritt.art, eintraege: [z] });
    const alle = [...gruppen, ...einzeln].sort((a, b) => vergleiche(a.eintraege[0], b.eintraege[0]));
    return alle.slice(0, hoechstens);
  }

  const logik = { LAUFEND, NACHFRAGEN_NACH_TAGEN, datum, plusTage, laufend, naechsterSchritt, mitSchritten, gefiltert, sortiert, naechsteSortierung, gueltigeSortierung, abgeschlossenZaehlen, stehtAn };
  if (typeof module !== "undefined") module.exports = logik;
  else global.UebersichtLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
