"use strict";
// Exclusion reasons the AI proposes from dismissed hits on Suche einstellen (#319, G86), without DOM: the words of the
// box. Counts, costs and the hits a proposal rests on come from the app (routes_ai_exclusions.py); the AI only names
// the reason, and the app has checked each of its hits.
(global => {
  const TITEL = "titel_ausschluss";
  const KNOPF = "Übernehmen";
  const FRAGEN = "Gründe vorschlagen lassen";
  const NEU_FRAGEN = "Neu vorschlagen lassen";
  const RUECKGAENGIG = "Rückgängig";
  const WAS_GEHT = "Nur Titel, Firma, Ort und Pensum der verworfenen Stellen. Kein Lebenslauf, kein Suchprofil, "
    + "nichts über die Person.";
  const DENKT = "Die KI sucht nach gemeinsamen Gründen, das dauert einen Moment …";
  const NICHT_GELADEN = "Ausschlüsse von der KI lassen sich gerade nicht anbieten.";
  const NICHT_GESPEICHERT = "Nicht übernommen.";
  const NICHT_ZURUECK = "Nicht zurückgenommen.";

  const stellen = n => `${n} ${n === 1 ? "verworfene Stelle" : "verworfene Stellen"}`;

  /** Whether the box shows its empty state instead of the button; then nothing goes to the AI. */
  const zuWenige = stand => !(stand.anzahl >= stand.mindestens);

  const einleitung = (stand, satz, texte) => texte.text("einstellen.ki-ausschluesse", satz, { anzahl: stand.anzahl });

  function leer(stand, satz, texte) {
    const bisher = stand.anzahl ? `Erst ${stellen(stand.anzahl)}.` : "Noch keine verworfenen Stellen.";
    return `${bisher} ${texte.text("einstellen.ki-ausschluesse-leer", satz, { mindestens: stand.mindestens })}`;
  }

  /** The cost before the run, worded like „Alle prüfen“ (G44, G46, G80); `trefferLogik` is TrefferLogik. */
  const kosten = (stand, trefferLogik) => trefferLogik.estimateLine(stand);

  // The app keeps only proposals that rest on at least two hits (exclusion_reasons.MIN_HITS).
  const stuetze = vorschlag => `Aus ${vorschlag.treffer.length} verworfenen Stellen:`;

  function trefferZeile(treffer) {
    const mehr = [treffer.firma, treffer.ort, treffer.pensum].filter(Boolean).join(", ");
    return mehr ? `${treffer.stelle} – ${mehr}` : treffer.stelle;
  }

  const wo = vorschlag => `${vorschlag.kategorie}, kommt unter «${vorschlag.ort}»`;
  const knopfLabel = vorschlag => `«${vorschlag.wert}» übernehmen`;
  const ab = art => (art === TITEL ? "Gilt ab der nächsten Suche." : "Gilt ab der nächsten Einschätzung.");
  const uebernommen = vorschlag => `«${vorschlag.wert}» steht jetzt unter «${vorschlag.ort}». ${ab(vorschlag.art)}`;
  const zurueck = vorschlag => `«${vorschlag.wert}» steht nicht mehr unter «${vorschlag.ort}».`;

  function fertig(anzahl, satz, texte) {
    if (!anzahl) return "Die KI hat keinen gemeinsamen Grund gefunden. Am Suchprofil hat sich nichts geändert.";
    const wie = anzahl === 1 ? "1 Vorschlag." : `${anzahl} Vorschläge.`;
    return `${wie} ${texte.text("einstellen.ki-ausschluesse-fertig", satz, { welchen: anzahl === 1 ? "ihn" : "einen" })}`;
  }

  const logik = { TITEL, KNOPF, FRAGEN, NEU_FRAGEN, RUECKGAENGIG, WAS_GEHT, DENKT, NICHT_GELADEN, NICHT_GESPEICHERT,
    NICHT_ZURUECK, zuWenige, einleitung, leer, kosten, stuetze, trefferZeile, wo, knopfLabel, uebernommen, zurueck,
    fertig };
  if (typeof module !== "undefined") module.exports = logik;
  else global.KiAusschluesseLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
