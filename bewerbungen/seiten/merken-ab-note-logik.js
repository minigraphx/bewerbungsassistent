"use strict";
// „Alle ab Note … merken“ on Stellen (#214, A3): the grades to choose from and what the page says. No DOM, so it can be tested.
// Texts in the app language through Texte.t (#422); a count that can be 1 has its own text, so no language says
// «1 résultats», while German stays as it was.
(function (global) {
  /** Swiss grades in half steps; below 3 a hit hardly fits, so the list starts there. */
  const NOTEN = [3, 3.5, 4, 4.5, 5, 5.5, 6];
  const VORGABE = 4.5;  // A3: from 4.5 a job fits well

  const Texte = { t: (deutsch, werte) => (typeof module !== "undefined" ? require("./texte.js") : global.Texte).t(deutsch, werte) };
  const notenText = note => String(note);

  /** A stored or chosen grade from the list, else the default. */
  function gueltigeNote(wert) {
    const zahl = Number(wert);
    return NOTEN.includes(zahl) ? zahl : VORGABE;
  }

  const knopfText = note => Texte.t("Alle ab Note {note} merken", { note: notenText(note) });

  /** The question before saving: how many and which hits, and what stays as it is. */
  function bestaetigung(vorschau) {
    const werte = { anzahl: vorschau.anzahl, note: notenText(vorschau.note) };
    const eins = vorschau.anzahl === 1;
    return {
      titel: eins ? Texte.t("1 Treffer ab Note {note} merken?", werte) : Texte.t("{anzahl} Treffer ab Note {note} merken?", werte),
      einleitung: eins ? Texte.t("Dieser Treffer kommt unter Bewerbungen:") : Texte.t("Diese Treffer kommen unter Bewerbungen:"),
      // each row as the parts of a «·» line (#342)
      zeilen: vorschau.treffer.map(t => [`${t.stelle}${t.firma ? `, ${t.firma}` : ""}`, Texte.t("Note {note}", { note: notenText(t.note) })]),
      nachsatz: Texte.t("Treffer ohne Note und solche, die schon gemerkt oder verworfen sind, bleiben, wie sie sind."),
      ok: eins ? Texte.t("1 Treffer merken") : Texte.t("{anzahl} Treffer merken", werte),
    };
  }

  const keinerText = note => Texte.t("Keine neuen Treffer mit Note {note} oder besser.", { note: notenText(note) });

  /** The message after saving; a hit that changed since the question is named as left alone. */
  function ergebnisText(antwort) {
    const gemerkt = antwort.gemerkt.length;
    const erste = gemerkt === 1 ? Texte.t("1 Treffer gemerkt. Er steht jetzt unter Bewerbungen.")
      : Texte.t("{anzahl} Treffer gemerkt. Sie stehen jetzt unter Bewerbungen.", { anzahl: gemerkt });
    const uebrig = antwort.uebersprungen.length;
    if (!uebrig) return erste;
    const zweite = uebrig === 1
      ? Texte.t("1 Treffer hat sich inzwischen geändert und bleibt, wie er ist.")
      : Texte.t("{anzahl} Treffer haben sich inzwischen geändert und bleiben, wie sie sind.", { anzahl: uebrig });
    return `${erste} ${zweite}`;
  }

  /** A failed step says what did not work before the reason the app gives. */
  function fehlerText(schritt, note, grund) {
    const werte = { note: notenText(note), grund };
    return schritt === "merken" ? Texte.t("Die Treffer ab Note {note} liessen sich nicht merken: {grund}", werte)
      : Texte.t("Die Treffer ab Note {note} liessen sich nicht laden: {grund}", werte);
  }

  const logik = { NOTEN, VORGABE, gueltigeNote, knopfText, bestaetigung, keinerText, ergebnisText, fehlerText };
  if (typeof module !== "undefined") module.exports = logik;
  else global.MerkenAbNoteLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
