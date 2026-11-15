"use strict";
// A point under „Was fehlt oder unsicher ist“ taken over as an exclusion (#224, G83), without DOM: the words of the
// button, the form and the feedback in the point. What the app proposes comes from routes_adopt_exclusion.py, never
// from the AI.
(global => {
  const TITEL = "titel_ausschluss";
  const INSERAT = "ausschluss";
  const ARTEN = [
    { art: TITEL, text: "Im Titel", hinweis: "Ein Titel mit diesem Wort kommt bei der nächsten Suche nicht mehr in die Liste." },
    { art: INSERAT, text: "Im Inserat", hinweis: "Solche Stellen kommen weiter in die Liste. "
      + "Die KI liest es bei jeder weiteren Einschätzung als Ausschluss mit." },
  ];
  const SEITE = "Suche einstellen";
  const KNOPF = "Künftig nicht zeigen";
  const AUSGESCHLOSSEN = "Ausgeschlossen";
  const WO = "Wo eintragen?";
  const FELD = "Was nicht vorkommen soll";
  const EINTRAGEN = "Eintragen";
  const ABBRECHEN = "Abbrechen";
  const RUECKGAENGIG = "Rückgängig";
  const NICHT_GELADEN = "Der Vorschlag liess sich nicht laden.";
  const NICHT_GESPEICHERT = "Nicht gespeichert.";
  const NICHT_ZURUECK = "Nicht zurückgenommen.";
  const STAND_FEHLT = "Ob ein Punkt schon ausgeschlossen ist, liess sich nicht prüfen.";

  const ort = art => (ARTEN.find(a => a.art === art) || ARTEN[1]).text;
  const hinweis = art => (ARTEN.find(a => a.art === art) || ARTEN[1]).hinweis;
  const knopfLabel = punkt => `${KNOPF}: ${punkt}`;
  /** The intro of the form; `karte` is the card's title from texte.js (einstellen.nicht) in the person's address. */
  const frage = (karte, du) => `Die App trägt den Eintrag unten auf «${SEITE}» unter «${karte}» ein. `
    + (du ? "Du kannst ihn vorher ändern." : "Sie können ihn vorher ändern.");
  const ab = art => (art === TITEL ? "Gilt ab der nächsten Suche." : "Gilt ab der nächsten Einschätzung.");
  const uebernommen = (art, wert) => `«${wert}» steht jetzt auf «${SEITE}» unter «${ort(art)}». ${ab(art)}`;
  const zurueck = (art, wert) => `«${wert}» steht nicht mehr auf «${SEITE}» unter «${ort(art)}».`;

  const logik = { TITEL, INSERAT, ARTEN, KNOPF, AUSGESCHLOSSEN, WO, FELD, EINTRAGEN, ABBRECHEN, RUECKGAENGIG,
    NICHT_GELADEN, NICHT_GESPEICHERT, NICHT_ZURUECK, STAND_FEHLT, ort, hinweis, knopfLabel, frage, uebernommen, zurueck };
  if (typeof module !== "undefined") module.exports = logik;
  else global.HakenAusschlussLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
