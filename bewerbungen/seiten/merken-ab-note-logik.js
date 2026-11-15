"use strict";
// „Alle ab Note … merken“ on Stellen (#214, A3): the grades to choose from and what the page says. No DOM, so it can be tested.
(function (global) {
  /** Swiss grades in half steps; below 3 a hit hardly fits, so the list starts there. */
  const NOTEN = [3, 3.5, 4, 4.5, 5, 5.5, 6];
  const VORGABE = 4.5;  // A3: from 4.5 a job fits well

  const notenText = note => String(note);
  const treffer = anzahl => (anzahl === 1 ? "1 Treffer" : `${anzahl} Treffer`);

  /** A stored or chosen grade from the list, else the default. */
  function gueltigeNote(wert) {
    const zahl = Number(wert);
    return NOTEN.includes(zahl) ? zahl : VORGABE;
  }

  const knopfText = note => `Alle ab Note ${notenText(note)} merken`;

  /** The question before saving: how many and which hits, and what stays as it is. */
  function bestaetigung(vorschau) {
    const note = notenText(vorschau.note);
    return {
      titel: `${treffer(vorschau.anzahl)} ab Note ${note} merken?`,
      einleitung: vorschau.anzahl === 1 ? "Dieser Treffer kommt unter Gemerkt:" : "Diese Treffer kommen unter Gemerkt:",
      zeilen: vorschau.treffer.map(t => `${t.stelle}${t.firma ? `, ${t.firma}` : ""} · Note ${notenText(t.note)}`),
      nachsatz: "Treffer ohne Note und solche, die schon gemerkt oder verworfen sind, bleiben, wie sie sind.",
      ok: `${treffer(vorschau.anzahl)} merken`,
    };
  }

  const keinerText = note => `Keine neuen Treffer mit Note ${notenText(note)} oder besser.`;

  /** The message after saving; a hit that changed since the question is named as left alone. */
  function ergebnisText(antwort) {
    const gemerkt = antwort.gemerkt.length;
    const erste = gemerkt === 1 ? "1 Treffer gemerkt." : `${gemerkt} Treffer gemerkt.`;
    const uebrig = antwort.uebersprungen.length;
    if (!uebrig) return erste;
    const zweite = uebrig === 1
      ? "1 Treffer hat sich inzwischen geändert und bleibt, wie er ist."
      : `${uebrig} Treffer haben sich inzwischen geändert und bleiben, wie sie sind.`;
    return `${erste} ${zweite}`;
  }

  const SCHRITTE = { fragen: "laden", merken: "merken" };

  /** A failed step says what did not work before the reason the app gives. */
  const fehlerText = (schritt, note, grund) =>
    `Die Treffer ab Note ${notenText(note)} liessen sich nicht ${SCHRITTE[schritt]}: ${grund}`;

  const logik = { NOTEN, VORGABE, gueltigeNote, knopfText, bestaetigung, keinerText, ergebnisText, fehlerText };
  if (typeof module !== "undefined") module.exports = logik;
  else global.MerkenAbNoteLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
