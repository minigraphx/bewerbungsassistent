"use strict";
// The application page after the design (MIN-369): six steps from the ad to recording it, and what comes next.
// From /api/bewerbung (`daten`), the findings of /api/pruefung (`befunde`, null until checked), whether the AI is
// set up and whether the person reports to an RAV. No DOM, so it can be tested (tests/bewerbung_logik.test.cjs).
// Approving a letter is not stored: the letter step is done once a letter exists; it is read as PDF when checking.
(function (global) {
  const SCHRITTE = ["stelle", "lebenslauf", "anschreiben", "pruefen", "abschicken", "festhalten"];

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
  /** Both files are built and, with a dossier chosen (G40), the dossier too. */
  function gebaut(daten) {
    const pdfs = daten.pdfs || {};
    return Boolean(pdfs.lebenslauf && pdfs.anschreiben && (daten.bewerbung.unterlagen !== "dossier" || pdfs.dossier));
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
        meta: (daten.stellentext || "").trim() ? (b.eingetragen_am ? `erfasst ${datum(b.eingetragen_am).slice(0, 6)}` : "Inserat da") : gesendet ? "" : "Inserat fehlt",
      },
      lebenslauf: {
        erledigt: gesendet || Boolean(b.variante) || !variantenDa || Boolean(daten.eigener_lebenslauf),
        meta: b.variante ? `Variante ${b.variante}` : daten.eigener_lebenslauf ? "eigenes PDF" : variantenDa ? "Variante wählen" : "ganzer Lebenslauf",
      },
      anschreiben: {
        erledigt: gesendet || Boolean(daten.eigenes_anschreiben) || (Boolean(daten.hat_anschreiben) && !offeneFreigabe(daten)),
        meta: daten.eigenes_anschreiben ? "eigenes PDF" : !daten.hat_anschreiben ? (gesendet ? "" : "fehlt noch")
          : offeneFreigabe(daten) ? "lesen und freigeben" : daten.anschreiben_freigabe?.freigegeben ? "freigegeben" : "vorhanden",
      },
      pruefen: {
        erledigt: gesendet || (fertig && befunde !== null && fehler(befunde) === 0),
        meta: !fertig ? (gesendet ? "" : "PDFs erstellen") : befunde === null ? "wird geprüft" : fehler(befunde)
          ? `${fehler(befunde)} Fehler` : hinweise(befunde)
            ? `${hinweise(befunde)} ${hinweise(befunde) === 1 ? "Hinweis" : "Hinweise"}` : "in Ordnung",
      },
      abschicken: {
        erledigt: gesendet,
        meta: gesendet ? `am ${datum(b.beworben_am || b.versand?.datum)}` : du ? "machst du selbst" : "machen Sie selbst",
      },
      festhalten: {
        erledigt: Boolean(b.versand) && (!rav || Boolean(b.rav_eingetragen_am)),
        meta: !b.versand ? "" : rav && !b.rav_eingetragen_am ? "Job-Room offen" : "festgehalten",
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
        return { art: befunde === null ? "pruefen" : "klaeren", ziel: "s-pruefen" };
      case "abschicken": return { art: b.formular_link || b.link ? "formular" : "versand", ziel: "s-abschicken" };
      case "festhalten":
        if (b.versand) return { art: "jobroom", ziel: "s-festhalten" };
        return { art: b.beworben_am ? "nachtragen" : "versand", ziel: "s-abschicken" };
      default:
        if (b.status === "Gespräch") return { art: "gespraech", ziel: "s-festhalten" };
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
    const punkte = [
      [b.eingetragen_am, "Erfasst"],
      [b.beworben_am, "Beworben"],
      [b.versand?.datum, b.versand ? `Versand erfasst (${b.versand.art})` : ""],
      [b.rav_eingetragen_am, "Im Job-Room eingetragen"],
      [b.gespraech_am, "Gespräch"],
      [b.absage_am, "Absage"],
    ].filter(([wann, was]) => wann && was);
    return punkte.sort((x, y) => x[0].localeCompare(y[0])).map(([wann, was]) => ({ datum: wann, text: was }));
  }

  /** „Erneut prüfen“ only once there is a check to repeat (#222); null means not checked since the last change. */
  function erneutPruefen(befunde) {
    return Array.isArray(befunde);
  }

  const logik = { SCHRITTE, datum, versendet, offeneFreigabe, schritte, aktueller, naechster, beenden, verlauf, erneutPruefen };
  if (typeof module !== "undefined") module.exports = logik;
  else global.BewerbungLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
