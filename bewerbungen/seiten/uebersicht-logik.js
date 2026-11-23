"use strict";
// The overview after the design (MIN-369): what comes next for each application, the views by stage (#165),
// and what „Das steht an“ shows first. No DOM, so it can be tested (tests/uebersicht_logik.test.cjs).
// `grund` is why the app cannot open the form yet (/api/bewerben/auswahl, null = ready), `ravGrund` why it cannot
// be entered in the Job-Room (/api/rav/auswahl, null = can be entered, undefined = no RAV).
(function (global) {
  // The views by stage (#165). They go by the status only: a rejection still to enter in the Job-Room is finished,
  // and „Das steht an“ shows that entry anyway.
  const STAENDE = {
    gemerkt: ["Gemerkt", "Bewerben"],
    beworben: ["Beworben", "Gespräch"],
    abgeschlossen: ["Absage", "Zusage", "Verworfen", "Zurückgezogen"],
  };
  const ANSICHTEN = [...Object.keys(STAENDE), "alle"];
  const STANDARD_ANSICHT = "beworben";
  const FRUEHERE_ANSICHT = { laufend: "beworben" };  // stored before #165
  const NACHFRAGEN_NACH_TAGEN = 14;
  // The German start of apply's reasons, only compared, never shown (the step's own words come from schrittText).
  const OHNE_LEBENSLAUF = "Lebenslauf-PDF fehlt";  // kein UI-Text: apply.NO_CV starts so
  const OHNE_LINK = "Kein Link zum Formular";      // kein UI-Text: apply.NO_LINK starts so
  const OHNE_FREIGABE = "Anschreiben noch nicht freigegeben";  // kein UI-Text: apply.NOT_APPROVED starts so
  // Loaded before this file on every page; required in the tests. Texts in the app language through Texte.t (#417).
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
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

  /**
   * { art, frist?, zusatz?, grund? } — art is one of RANG; frist an ISO date that orders and shows in the list; zusatz,
   * for a sent application, the date to follow up from, also while the Job-Room entry is still open (#269).
   */
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
      case "Beworben": {
        // An interview date counts before the stage says Gespräch (#268); an open Job-Room entry still comes first.
        if (b.gespraech_am && !ravOffen) return { art: "gespraech", frist: b.gespraech_am };
        const nachfragen = b.beworben_am ? plusTage(b.beworben_am, NACHFRAGEN_NACH_TAGEN) : "";
        return { art: ravOffen ? "rav" : "warten", zusatz: nachfragen };
      }
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

  /** Gemerkt, Beworben, Abgeschlossen or Alle, with the search over company, position and note. */
  function gefiltert(zeilen, ansicht, suche) {
    const wort = (suche || "").trim().toLowerCase();
    const staende = STAENDE[ansicht];
    return zeilen.filter(({ bewerbung: b }) =>
      (ansicht === "alle" || (staende || []).includes(b.status))
      && (!wort || `${b.firma} ${b.stelle} ${b.notiz || ""}`.toLowerCase().includes(wort)));
  }

  /** How many applications each view shows without a search: { gemerkt, beworben, abgeschlossen, alle }. */
  function ansichtenZaehlen(zeilen) {
    return Object.fromEntries(ANSICHTEN.map(name => [name, gefiltert(zeilen, name, "").length]));
  }

  /** A view from the browser's storage: a known one, the former „Laufend“ as Beworben, else the default. */
  function gueltigeAnsicht(wert) {
    if (typeof wert !== "string") return STANDARD_ANSICHT;
    if (Object.hasOwn(FRUEHERE_ANSICHT, wert)) return FRUEHERE_ANSICHT[wert];
    return ANSICHTEN.includes(wert) ? wert : STANDARD_ANSICHT;
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
    erfasst: z => z.bewerbung.eingetragen_am || null,  // ISO, so the alphabet is the calendar (#168)
  };
  const ZUERST_ABSTEIGEND = ["note", "erfasst"];  // the best grade and the newest entry first
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

  // The finished stages, one definition for the view „Abgeschlossen“ and the tab of Stellen (#373), with the words
  // of the line „Abgeschlossen: …“ for one and for more.
  const ABGESCHLOSSEN = STAENDE.abgeschlossen;
  // Per finished stage the count with its word, for one and for more, in the app language (#417).
  function zusage(anzahl) {
    const Texte = texts();
    return anzahl === 1 ? Texte.t("{anzahl} Zusage", { anzahl }) : Texte.t("{anzahl} Zusagen", { anzahl });
  }
  function absage(anzahl) {
    const Texte = texts();
    return anzahl === 1 ? Texte.t("{anzahl} Absage", { anzahl }) : Texte.t("{anzahl} Absagen", { anzahl });
  }
  function verworfen(anzahl) {
    const Texte = texts();
    return Texte.t("{anzahl} verworfen", { anzahl });
  }
  function zurueckgezogen(anzahl) {
    const Texte = texts();
    return Texte.t("{anzahl} zurückgezogen", { anzahl });
  }
  const ABGESCHLOSSEN_WORT = { Zusage: zusage, Absage: absage, Verworfen: verworfen, "Zurückgezogen": zurueckgezogen };

  /** „3 Absagen“: a count with the word of its stage, as the line „Abgeschlossen: …“ names it. */
  function abgeschlossenTeil(status, anzahl) {
    const wort = ABGESCHLOSSEN_WORT[status];
    return wort ? wort(anzahl) : `${anzahl} ${status}`;
  }

  /**
   * What „Das steht an“ shows: the first thing to do as the big card, the next few below. Two or more
   * applications that are ready to send (or to enter in the Job-Room, or saved to decide) become one item.
   * Items: { art, eintraege: [{bewerbung, schritt}] } — one entry, or several for a group.
   */
  function stehtAn(zeilen, hoechstens = 4) {
    const zuTun = zeilen.filter(z => !["warten", "fertig"].includes(z.schritt.art));
    const gruppen = [];
    const einzeln = [];
    for (const art of ["abschicken", "rav", "entscheiden"]) {  // saved jobs together are the pass of G38
      const gleiche = zuTun.filter(z => z.schritt.art === art);
      if (gleiche.length >= GRUPPE_AB) gruppen.push({ art, eintraege: gleiche });
    }
    const gruppiert = new Set(gruppen.map(g => g.art));
    for (const z of zuTun) if (!gruppiert.has(z.schritt.art)) einzeln.push({ art: z.schritt.art, eintraege: [z] });
    const alle = [...gruppen, ...einzeln].sort((a, b) => vergleiche(a.eintraege[0], b.eintraege[0]));
    return alle.slice(0, hoechstens);
  }

  /**
   * What a step is called, in the list of Bewerbungen and on Heute: { titel, zusatz }. `anzahl` is how many a grouped
   * item stands for; `t(key, values)` gives the text of texte.js in the form of the person.
   */
  function schrittText(schritt, anzahl, t) {
    const Texte = texts();
    switch (schritt.art) {
      case "abschicken": return anzahl > 1
        ? { titel: Texte.t("{anzahl} Bewerbungen abschicken", { anzahl }), zusatz: Texte.t("Formulare sind bereit") }
        : { titel: Texte.t("Abschicken"), zusatz: Texte.t("Formular ist bereit") };
      case "freigeben": return { titel: Texte.t("Anschreiben lesen und freigeben"), zusatz: Texte.t("Entwurf ist fertig") };
      case "unterlagen": return { titel: Texte.t("Unterlagen erstellen"), zusatz: Texte.t("Lebenslauf-PDF fehlt") };
      case "link": return { titel: Texte.t("Link zum Formular eintragen"), zusatz: Texte.t("dann füllt die Erweiterung es aus") };
      case "offen": return { titel: schritt.grund || Texte.t("Bewerbung öffnen"), zusatz: "" };
      case "rav": return anzahl > 1
        ? { titel: Texte.t("{anzahl} Bewerbungen im Job-Room eintragen", { anzahl }), zusatz: Texte.t("fürs RAV") }
        : { titel: Texte.t("Im Job-Room eintragen"), zusatz: Texte.t("fürs RAV") };
      case "gespraech": return schritt.frist ? { titel: t("bewerbung.gespraech"), zusatz: datum(schritt.frist) }
        : { titel: t("heute.gespraech.termin"), zusatz: "" };
      case "entscheiden": return anzahl > 1
        ? { titel: Texte.t("Gemerkte Stellen in einem Durchgang bewerten"), zusatz: t("heute.durchgang.unter") }
        : { titel: Texte.t("Entscheiden"), zusatz: Texte.t("bewerben oder verwerfen") };
      case "warten": return { titel: Texte.t("Antwort abwarten"),
                              zusatz: schritt.zusatz ? Texte.t("nachfragen ab {datum}", { datum: datum(schritt.zusatz) }) : "" };
      default: return { titel: "", zusatz: "" };
    }
  }

  // Changing the stage of several applications at once (#170). A selection is a Set of ids; every change
  // returns a new one. Only the selected rows the view shows count, so a hidden row is never changed by surprise.
  // The views by name, as their tabs show them, in the app language (#417).
  function viewLabel(view) {
    const Texte = texts();
    return { gemerkt: Texte.t("Gemerkt"), beworben: Texte.t("Beworben"), abgeschlossen: Texte.t("Abgeschlossen") }[view];
  }
  const shownIds = rows => rows.map(z => z.bewerbung.id);
  function applications(count) {
    const Texte = texts();
    return count === 1 ? Texte.t("1 Bewerbung") : Texte.t("{anzahl} Bewerbungen", { anzahl: count });
  }

  function toggleOne(selected, id) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  }

  /** Select all in the view; when all of them are selected already, it takes them out again. */
  function toggleAll(selected, rows) {
    const ids = shownIds(rows);
    if (selectionState(selected, rows) === "all") return new Set([...selected].filter(id => !ids.includes(id)));
    return new Set([...selected, ...ids]);
  }

  /** "none", "some" or "all" of the rows the view shows: the state of the checkbox „Alle“. */
  function selectionState(selected, rows) {
    const taken = selectedIds(selected, rows).length;
    if (taken === 0) return "none";
    return taken === rows.length ? "all" : "some";
  }

  /** The ids a change applies to: selected and shown, in the order of the list. */
  function selectedIds(selected, rows) {
    return shownIds(rows).filter(id => selected.has(id));
  }

  /** Without the ids that are no longer in the register, e.g. after Claude changed it. */
  function keepKnown(selected, rows) {
    const known = new Set(shownIds(rows));
    return new Set([...selected].filter(id => known.has(id)));
  }

  /** The bar to change the stage shows only once a row is ticked (#222, UX finding 15), as in mail programs. */
  function showBulkBar(count) {
    return count > 0;
  }

  function selectionLabel(count) {
    const Texte = texts();
    return count === 0 ? Texte.t("Keine ausgewählt") : Texte.t("{anzahl} ausgewählt", { anzahl: count });
  }

  function stageQuestion(count, stageName) {
    const Texte = texts();
    return Texte.t("{bewerbungen} auf „{stand}“ setzen?", { bewerbungen: applications(count), stand: stageName });
  }

  function viewOfStage(stage) {
    return Object.keys(STAENDE).find(view => STAENDE[view].includes(stage)) || "alle";
  }

  /** The status line after the change; it says where the rows went when they left the view. */
  function stageDone(count, stage, stageName, view) {
    const Texte = texts();
    const words = { bewerbungen: applications(count), stand: stageName };
    const target = viewOfStage(stage);
    if (view === "alle" || target === view || !viewLabel(target)) return Texte.t("{bewerbungen} auf „{stand}“ gesetzt.", words);
    const moved = { ...words, ansicht: viewLabel(target) };
    return count === 1
      ? Texte.t("{bewerbungen} auf „{stand}“ gesetzt. Sie steht jetzt unter „{ansicht}“.", moved)
      : Texte.t("{bewerbungen} auf „{stand}“ gesetzt. Sie stehen jetzt unter „{ansicht}“.", moved);
  }

  const logik = { ANSICHTEN, STANDARD_ANSICHT, NACHFRAGEN_NACH_TAGEN, ABGESCHLOSSEN, ABGESCHLOSSEN_WORT, datum, plusTage, naechsterSchritt,
                  mitSchritten, gefiltert, ansichtenZaehlen, gueltigeAnsicht, sortiert, naechsteSortierung, gueltigeSortierung,
                  abgeschlossenZaehlen, abgeschlossenTeil, stehtAn,
                  toggleOne, toggleAll, selectionState, selectedIds, keepKnown, showBulkBar, selectionLabel, stageQuestion, viewOfStage,
                  stageDone, schrittText };
  if (typeof module !== "undefined") module.exports = logik;
  else global.UebersichtLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
