"use strict";
// Exclusion reasons the AI proposes from dismissed hits on Suche einstellen (#319, G86), without DOM: the words of the
// box. Counts, costs and the hits a proposal rests on come from the app (routes_ai_exclusions.py); the AI only names
// the reason, and the app has checked each of its hits. Texts in the app language through Texte (#425); the value the
// AI named and the place and category the app sends are data here.
(global => {
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const TITEL = "titel_ausschluss";

  /** Whether the box shows its empty state instead of the button; then nothing goes to the AI. */
  const zuWenige = stand => !(stand.anzahl >= stand.mindestens);

  // The sets take the page's Texte as `Texte`, so the scanner reads each key.
  const einleitung = (stand, satz, Texte) => Texte.text("einstellen.ki-ausschluesse", satz, { anzahl: stand.anzahl });
  const wasGeht = (satz, Texte) => Texte.text("einstellen.ki-ausschluesse-was", satz);

  function bisher(anzahl) {
    if (!anzahl) return Texte.t("Keine verworfenen Stellen, die das Suchprofil noch nicht ausschliesst.");
    return anzahl === 1 ? Texte.t("Erst 1 verworfene Stelle, die das Suchprofil noch nicht ausschliesst.")
      : Texte.t("Erst {anzahl} verworfene Stellen, die das Suchprofil noch nicht ausschliesst.", { anzahl });
  }

  function leer(stand, satz, Texte) {
    return `${bisher(stand.anzahl)} ${Texte.text("einstellen.ki-ausschluesse-leer", satz, { mindestens: stand.mindestens })}`;
  }

  /**
   * What the box shows: its intro with button and the line about the AI, or its empty state. Adopting can drop the
   * count below the minimum while proposals are still shown below; then they keep their own intro and the line.
   */
  function ansicht(stand, offen, satz, Texte) {
    if (!zuWenige(stand)) return { satz: einleitung(stand, satz, Texte), start: true, was: true };
    if (offen) {
      return { satz: Texte.text("einstellen.ki-ausschluesse-rest", satz, { mindestens: stand.mindestens }), start: false, was: true };
    }
    return { satz: leer(stand, satz, Texte), start: false, was: false };
  }

  const gleich = wert => String(wert).trim().toLowerCase();

  /** Whether the profile has the proposal's entry now, as `vorhanden` of the overview names it; case does not count. */
  const steht = (vorschlag, vorhanden) => (vorhanden[vorschlag.art] || []).some(w => gleich(w) === gleich(vorschlag.wert));

  /**
   * How a proposal shown follows the profile after another card changed it: `angezeigt` is what the card shows
   * ("offen", "uebernommen", "schon", "zurueck"). Gives the new state with its text, or null if the card is right.
   */
  function abgleich(vorschlag, vorhanden, angezeigt) {
    const daAngezeigt = angezeigt === "uebernommen" || angezeigt === "schon";
    const da = steht(vorschlag, vorhanden);
    if (da && !daAngezeigt) return { angezeigt: "schon", text: schonDa(vorschlag) };
    if (!da && daAngezeigt) return { angezeigt: "zurueck", text: zurueck(vorschlag) };
    return null;
  }

  /**
   * The cost before the run, worded like every one-request line (G44, G46, G80, #334): over the credit it names what is
   * left; the button stays (#319). `trefferLogik` is TrefferLogik.
   */
  const kosten = (stand, trefferLogik) => trefferLogik.costLine(stand).text;

  // The app keeps only proposals that rest on at least two hits (exclusion_reasons.MIN_HITS).
  const stuetze = vorschlag => Texte.t("Aus {anzahl} verworfenen Stellen:", { anzahl: vorschlag.treffer.length });

  function trefferZeile(treffer) {
    const mehr = [treffer.firma, treffer.ort, treffer.pensum].filter(Boolean).join(", ");
    return mehr ? `${treffer.stelle} – ${mehr}` : treffer.stelle;
  }

  // A title word needs no category: „Im Titel“ says it.
  const wo = vorschlag => (vorschlag.art === TITEL ? Texte.t("Kommt unter «{ort}»", { ort: vorschlag.ort })
    : Texte.t("{kategorie}, kommt unter «{ort}»", { kategorie: vorschlag.kategorie, ort: vorschlag.ort }));
  const knopfLabel = vorschlag => Texte.t("«{wert}» übernehmen", { wert: vorschlag.wert });
  const ab = art => (art === TITEL ? Texte.t("Gilt ab der nächsten Suche.") : Texte.t("Gilt ab der nächsten Einschätzung."));
  const uebernommen = vorschlag => Texte.t("«{wert}» steht jetzt unter «{ort}». {ab}",
    { wert: vorschlag.wert, ort: vorschlag.ort, ab: ab(vorschlag.art) });
  const zurueck = vorschlag => Texte.t("«{wert}» steht nicht mehr unter «{ort}».", { wert: vorschlag.wert, ort: vorschlag.ort });
  const schonDa = vorschlag => Texte.t("«{wert}» steht schon unter «{ort}».", { wert: vorschlag.wert, ort: vorschlag.ort });

  const nichtGeladen = fehler => Texte.t("Ausschlüsse von der KI lassen sich gerade nicht anbieten. {fehler}", { fehler });
  const nichtUebernommen = fehler => Texte.t("Nicht übernommen. {fehler}", { fehler });
  const nichtZurueck = fehler => Texte.t("Nicht zurückgenommen. {fehler}", { fehler });

  /** The count of the proposals; „ihn“ for one and „einen“ for several are two sets, so each language words its own. */
  function fertig(anzahl, satz, Texte) {
    if (!anzahl) return Texte.t("Die KI hat keinen gemeinsamen Grund gefunden. Am Suchprofil hat sich nichts geändert.");
    const zahl = anzahl === 1 ? Texte.t("1 Vorschlag.") : Texte.t("{anzahl} Vorschläge.", { anzahl });
    const rest = anzahl === 1 ? Texte.text("einstellen.ki-ausschluesse-fertig-eins", satz)
      : Texte.text("einstellen.ki-ausschluesse-fertig", satz);
    return `${zahl} ${rest}`;  // two sentences, each in the app language
  }

  const logik = { TITEL, get KNOPF() { return Texte.t("Übernehmen"); }, get NEU_FRAGEN() { return Texte.t("Neu vorschlagen lassen"); },
    get RUECKGAENGIG() { return Texte.t("Rückgängig"); },
    get DENKT() { return Texte.t("Die KI sucht nach gemeinsamen Gründen, das dauert einen Moment …"); },
    nichtGeladen, nichtUebernommen, nichtZurueck, zuWenige, einleitung, wasGeht, leer, ansicht, steht, abgleich, kosten,
    stuetze, trefferZeile, wo, knopfLabel, uebernommen, zurueck, schonDa, fertig };
  if (typeof module !== "undefined") module.exports = logik;
  else global.KiAusschluesseLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
