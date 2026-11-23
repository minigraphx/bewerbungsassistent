"use strict";
// A point under „Was fehlt oder unsicher ist“ taken over as an exclusion (#224, G83), without DOM: the words of the
// button, the form and the feedback in the point. What the app proposes comes from routes_adopt_exclusion.py, never
// from the AI. Texts in the app language through Texte.t (#422): the words are read when they are shown, never when
// the script loads, so the language of the page decides.
(global => {
  const TITEL = "titel_ausschluss";
  const INSERAT = "ausschluss";
  const Texte = { t: (deutsch, werte) => (typeof module !== "undefined" ? require("./texte.js") : global.Texte).t(deutsch, werte) };

  const arten = () => [
    { art: TITEL, text: Texte.t("Im Titel"),
      hinweis: Texte.t("Ein Titel mit diesem Wort kommt bei der nächsten Suche nicht mehr in die Liste.") },
    { art: INSERAT, text: Texte.t("Im Inserat"),
      hinweis: Texte.t("Solche Stellen kommen weiter in die Liste. Die KI liest es bei jeder weiteren Einschätzung als Ausschluss mit.") },
  ];
  const seite = () => Texte.t("Suche einstellen");
  const knopf = () => Texte.t("Künftig nicht zeigen");

  const art = name => arten().find(a => a.art === name) || arten()[1];
  const ort = name => art(name).text;
  const hinweis = name => art(name).hinweis;
  const knopfLabel = punkt => Texte.t("Künftig nicht zeigen: {punkt}", { punkt });
  /** The intro of the form; `karte` is the card's title from texte.js (einstellen.nicht) in the person's address. */
  const frage = (karte, du) => (du
    ? Texte.t("Die App trägt den Eintrag unten auf «{seite}» unter «{karte}» ein. Du kannst ihn vorher ändern.", { seite: seite(), karte })
    : Texte.t("Die App trägt den Eintrag unten auf «{seite}» unter «{karte}» ein. Sie können ihn vorher ändern.", { seite: seite(), karte }));
  const ab = name => (name === TITEL ? Texte.t("Gilt ab der nächsten Suche.") : Texte.t("Gilt ab der nächsten Einschätzung."));
  const uebernommen = (name, wert) =>
    Texte.t("«{wert}» steht jetzt auf «{seite}» unter «{ort}». {ab}", { wert, seite: seite(), ort: ort(name), ab: ab(name) });
  const zurueck = (name, wert) =>
    Texte.t("«{wert}» steht nicht mehr auf «{seite}» unter «{ort}».", { wert, seite: seite(), ort: ort(name) });

  const logik = {
    TITEL, INSERAT,
    get ARTEN() { return arten(); },
    get KNOPF() { return knopf(); },
    get AUSGESCHLOSSEN() { return Texte.t("Ausgeschlossen"); },
    get WO() { return Texte.t("Wo eintragen?"); },
    get FELD() { return Texte.t("Was nicht vorkommen soll"); },
    get EINTRAGEN() { return Texte.t("Eintragen"); },
    get ABBRECHEN() { return Texte.t("Abbrechen"); },
    get RUECKGAENGIG() { return Texte.t("Rückgängig"); },
    get NICHT_GELADEN() { return Texte.t("Der Vorschlag liess sich nicht laden."); },
    get NICHT_GESPEICHERT() { return Texte.t("Nicht gespeichert."); },
    get NICHT_ZURUECK() { return Texte.t("Nicht zurückgenommen."); },
    get STAND_FEHLT() { return Texte.t("Ob ein Punkt schon ausgeschlossen ist, liess sich nicht prüfen."); },
    ort, hinweis, knopfLabel, frage, uebernommen, zurueck,
  };
  if (typeof module !== "undefined") module.exports = logik;
  else global.HakenAusschlussLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
