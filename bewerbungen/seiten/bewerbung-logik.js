"use strict";
// The application page after the design (MIN-369): six steps from the ad to recording it, and what comes next.
// From /api/bewerbung (`daten`), the findings of /api/pruefung (`befunde`, null until checked), whether the AI is
// set up and whether the person reports to an RAV. No DOM, so it can be tested (tests/bewerbung_logik.test.cjs).
// Approving a letter is not stored: the letter step is done once a letter exists; it is read as PDF when checking.
(function (global) {
  // Loaded before this file on the page; required in the tests. Texts in the app language through Texte (#426).
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const SCHRITTE = ["stelle", "lebenslauf", "anschreiben", "pruefen", "abschicken", "festhalten"];
  // The kinds of dispatch as stored (register.JOBROOM_ART) and how the history words them; an unknown kind shows as stored.
  const ART_NAMEN = {
    "elektronisch": () => Texte.t("elektronisch"), "schriftlich": () => Texte.t("schriftlich"),
    "persönlich": () => Texte.t("persönlich"), "telefonisch": () => Texte.t("telefonisch"),
  };

  function datum(iso) {
    if (!iso) return "";
    const [j, m, t] = iso.split("-");
    return `${t}.${m}.${j}`;
  }

  const versendet = b => Boolean(b.versand || b.beworben_am);
  /** A draft that counts and still waits for the person's approval (letter_approval.py). */
  const offeneFreigabe = daten => Boolean(daten.anschreiben_freigabe?.noetig && !daten.anschreiben_freigabe?.freigegeben);
  const fehler = befunde => (befunde || []).filter(b => b.stufe === "fehler").length;
  const hinweise = befunde => (befunde || []).filter(b => b.stufe === "hinweis").length;
  /** Layout breaches the person has not confirmed yet (G52): until then no form opens. */
  const offen = befunde => (befunde || []).filter(b => b.schluessel && !b.bestaetigt).length;
  /** A CV over its limit (G92): cut or allowed three pages, never confirmed as it is. */
  const zuLang = befunde => (befunde || []).some(b => b.kuerzen && !b.bestaetigt);
  const bestaetigen = () => Texte.t("So lassen");
  // G94: a letter over one page leads to the step Anschreiben, where its longest paragraph carries a visible label
  const cutInLetter = () => Texte.t("Im Anschreiben kürzen");
  const letterOver = befunde => (befunde || []).find(b => b.letter_cut && !b.bestaetigt) || null;

  /** The place of the paragraph the step Anschreiben marks, while a letter over one page is neither cut nor confirmed. */
  function longestParagraph(befunde) {
    const place = letterOver(befunde)?.letter_cut.paragraph;
    return Number.isInteger(place) ? place : null;
  }
  /**
   * A letter over one page (G94) or a CV over its limit with no cut left (#330) left as it is stays a hint, so the line
   * matches «1 Hinweis» above it.
   */
  const KEPT_OVER = {
    anschreiben: {
      none: werte => Texte.t("Anschreiben: {seiten} Seiten. Bestätigt: so lassen.", werte),
      one: werte => Texte.t("Anschreiben: {seiten} Seiten, etwa 1 Zeile zu viel. Bestätigt: so lassen.", werte),
      many: werte => Texte.t("Anschreiben: {seiten} Seiten, etwa {zeilen} Zeilen zu viel. Bestätigt: so lassen.", werte),
    },
    lebenslauf: {
      none: werte => Texte.t("Lebenslauf: {seiten} Seiten. Bestätigt: so lassen.", werte),
      one: werte => Texte.t("Lebenslauf: {seiten} Seiten, etwa 1 Zeile zu viel. Bestätigt: so lassen.", werte),
      many: werte => Texte.t("Lebenslauf: {seiten} Seiten, etwa {zeilen} Zeilen zu viel. Bestätigt: so lassen.", werte),
    },
  };
  function keptOver(document, { pages, lines }) {
    const say = KEPT_OVER[document][lines > 1 ? "many" : lines === 1 ? "one" : "none"];
    return say({ seiten: pages, zeilen: lines });
  }
  /** Both files are built and, with a dossier chosen (G40), the dossier too. */
  function gebaut(daten) {
    const pdfs = daten.pdfs || {};
    return Boolean(pdfs.lebenslauf && pdfs.anschreiben && (daten.bewerbung.unterlagen !== "dossier" || pdfs.dossier));
  }

  function pruefenMeta(befunde) {
    const anzahl = fehler(befunde) || offen(befunde) || hinweise(befunde);
    if (fehler(befunde)) return anzahl === 1 ? Texte.t("1 Fehler") : Texte.t("{anzahl} Fehler", { anzahl });
    if (zuLang(befunde)) return Texte.t("Lebenslauf zu lang");
    if (offen(befunde)) {
      return anzahl === 1 ? Texte.t("1 Meldung bestätigen") : Texte.t("{anzahl} Meldungen bestätigen", { anzahl });
    }
    if (hinweise(befunde)) return anzahl === 1 ? Texte.t("1 Hinweis") : Texte.t("{anzahl} Hinweise", { anzahl });
    return Texte.t("in Ordnung");
  }

  /**
   * One finding of the check as a line: { text, stufe, knopf } — knopf confirms a layout breach (G52). A CV over its
   * limit brings `kuerzen` instead, the cuts to tick (G92, kuerzen.js); a letter over one page also offers
   * `cutInLetter`, before «So lassen» (G94). A CV over its limit with no cut left waits on «So lassen» alone, as a
   * `decision` (#330).
   */
  function befundZeile(b) {
    if (b.kuerzen && !b.bestaetigt) return { text: b.text, stufe: b.stufe, knopf: null, kuerzen: b.kuerzen };
    if (b.letter_cut && !b.bestaetigt) return { text: b.text, stufe: b.stufe, knopf: bestaetigen(), cutInLetter: cutInLetter() };
    if (b.letter_cut) return { text: keptOver("anschreiben", b.letter_cut), stufe: "hinweis", knopf: null };
    if (b.cv_over && !b.bestaetigt) return { text: b.text, stufe: b.stufe, knopf: bestaetigen(), decision: true };
    if (b.cv_over) return { text: keptOver("lebenslauf", b.cv_over), stufe: "hinweis", knopf: null };
    if (b.schluessel && b.bestaetigt) {
      return { text: Texte.t("{text} Bestätigt: so lassen.", { text: b.text }), stufe: "ok", knopf: null };
    }
    return { text: b.text, stufe: b.stufe, knopf: b.schluessel ? bestaetigen() : null };
  }

  /** For each step: { id, erledigt, meta } — meta is the short line under the step. */
  function schritte(daten, { befunde = null, rav = false, du = false } = {}) {
    const b = daten.bewerbung;
    const gesendet = versendet(b);
    const fertig = gebaut(daten);
    const variantenDa = (daten.varianten || []).length > 0;
    const stand = {
      stelle: {
        erledigt: Boolean((daten.stellentext || "").trim()) || gesendet,
        meta: (daten.stellentext || "").trim()
          ? (b.eingetragen_am ? Texte.t("erfasst {datum}", { datum: datum(b.eingetragen_am).slice(0, 6) }) : Texte.t("Inserat da"))
          : gesendet ? "" : Texte.t("Inserat fehlt"),
      },
      lebenslauf: {
        erledigt: gesendet || Boolean(b.variante) || !variantenDa || Boolean(daten.eigener_lebenslauf),
        meta: b.variante ? Texte.t("Variante {name}", { name: b.variante }) : daten.eigener_lebenslauf ? Texte.t("eigenes PDF")
          : variantenDa ? Texte.t("Variante wählen") : Texte.t("ganzer Lebenslauf"),
      },
      anschreiben: {
        erledigt: gesendet || Boolean(daten.eigenes_anschreiben) || (Boolean(daten.hat_anschreiben) && !offeneFreigabe(daten)),
        meta: daten.eigenes_anschreiben ? Texte.t("eigenes PDF") : !daten.hat_anschreiben ? (gesendet ? "" : Texte.t("fehlt noch"))
          : offeneFreigabe(daten) ? Texte.t("lesen und freigeben")
            : daten.anschreiben_freigabe?.freigegeben ? Texte.t("freigegeben") : Texte.t("vorhanden"),
      },
      pruefen: {
        erledigt: gesendet || (fertig && befunde !== null && fehler(befunde) === 0 && offen(befunde) === 0),
        meta: !fertig ? (gesendet ? "" : Texte.t("PDFs erstellen")) : befunde === null ? Texte.t("wird geprüft") : pruefenMeta(befunde),
      },
      abschicken: {
        erledigt: gesendet,
        meta: gesendet ? Texte.t("am {datum}", { datum: datum(b.beworben_am || b.versand?.datum) })
          : du ? Texte.t("machst du selbst") : Texte.t("machen Sie selbst"),
      },
      festhalten: {
        erledigt: Boolean(b.versand) && (!rav || Boolean(b.rav_eingetragen_am)),
        meta: !b.versand ? "" : rav && !b.rav_eingetragen_am ? Texte.t("Job-Room offen") : Texte.t("festgehalten"),
      },
    };
    return SCHRITTE.map(id => ({ id, ...stand[id] }));
  }

  /** The step to show as current: the first one not done; null when all are. */
  function aktueller(liste) {
    return liste.find(s => !s.erledigt)?.id || null;
  }

  /**
   * What the card „Nächster Schritt“ says: { art, ziel } — art names the case, ziel the section to go to.
   * Once everything is done, the status decides (interview, waiting, finished).
   */
  function naechster(daten, { befunde = null, rav = false, ki = false } = {}) {
    const b = daten.bewerbung;
    const liste = schritte(daten, { befunde, rav });
    switch (aktueller(liste)) {
      case "stelle": return { art: "inserat", ziel: "s-stelle" };
      case "lebenslauf": return { art: "variante", ziel: "s-lebenslauf" };
      case "anschreiben":
        if (daten.hat_anschreiben) return { art: "freigeben", ziel: "s-anschreiben" };
        return { art: ki ? "entwerfen" : "eigenes", ziel: "s-anschreiben" };
      case "pruefen":
        if (!gebaut(daten)) return { art: "erstellen", ziel: "s-pruefen" };
        if (befunde === null) return { art: "pruefen", ziel: "s-pruefen" };
        if (fehler(befunde)) return { art: "klaeren", ziel: "s-pruefen" };
        return { art: zuLang(befunde) ? "kuerzen" : "bestaetigen", ziel: "s-pruefen" };
      case "abschicken": return { art: b.formular_link || b.link ? "formular" : "versand", ziel: "s-abschicken" };
      case "festhalten":
        if (b.versand) return { art: "jobroom", ziel: "s-festhalten" };
        return { art: b.beworben_am ? "nachtragen" : "versand", ziel: "s-abschicken" };
      default:
        if (b.status === "Gespräch" || (b.status === "Beworben" && b.gespraech_am)) return { art: "gespraech", ziel: "s-festhalten" };
        if (b.status === "Absage") return { art: "absage", ziel: "s-festhalten" };
        if (b.status === "Zusage") return { art: "zusage", ziel: "s-festhalten" };
        return { art: "warten", ziel: "s-festhalten" };
    }
  }

  // G29: ending an application never depends on the deadline, the person decides when it is over.
  const ENDE = {
    Gemerkt: "Verworfen", Bewerben: "Verworfen",
    Beworben: "Zurückgezogen", Gespräch: "Zurückgezogen",
  };

  /** The stage that ends the application from its current one: { stand } or null once it is over. */
  function beenden(b) {
    const stand = ENDE[b.status];
    return stand ? { stand } : null;
  }

  /** Dates of the application as a short history, oldest first. */
  function verlauf(b) {
    const art = b.versand ? (ART_NAMEN[b.versand.art] ? ART_NAMEN[b.versand.art]() : b.versand.art) : "";
    const punkte = [
      [b.eingetragen_am, Texte.t("Erfasst")],
      [b.beworben_am, Texte.t("Beworben")],
      [b.versand?.datum, b.versand ? Texte.t("Versand erfasst ({art})", { art }) : ""],
      [b.rav_eingetragen_am, Texte.t("Im Job-Room eingetragen")],
      [b.gespraech_am, Texte.t("Gespräch")],
      [b.absage_am, Texte.t("Absage")],
    ].filter(([wann, was]) => wann && was);
    return punkte.sort((x, y) => x[0].localeCompare(y[0])).map(([wann, was]) => ({ datum: wann, text: was }));
  }

  /** „Erneut prüfen“ only once there is a check to repeat (#222); null means not checked since the last change. */
  function erneutPruefen(befunde) {
    return Array.isArray(befunde);
  }

  const logik = { SCHRITTE, get LONGEST_LABEL() { return Texte.t("Längster Absatz"); }, datum, versendet, offeneFreigabe, schritte, aktueller, naechster, beenden, verlauf,
    erneutPruefen, befundZeile, longestParagraph };
  if (typeof module !== "undefined") module.exports = logik;
  else global.BewerbungLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
