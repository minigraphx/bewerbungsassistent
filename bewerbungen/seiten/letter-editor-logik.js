"use strict";
// The letter editor without DOM (G94, #332): how many lines a paragraph takes, which one is longest, the goal line
// while the check found the letter over one page, whether anything changed and what goes to the server. The number of
// characters per line comes from the server (letter_edit.CHARS_PER_LINE); this file never owns it.
// Texts in the app language through Texte (#429); the page's Texte is found when a text is made.
(function (global) {
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };

  const folded = text => String(text ?? "").trim().split(/\s+/).filter(Boolean).join(" ");
  const lines = count => (count === 1 ? Texte.t("1 Zeile") : Texte.t("{anzahl} Zeilen", { anzahl: count }));

  /** About how many lines the build needs for `text`; 0 for an empty field. */
  function lineCount(text, charsPerLine) {
    const length = [...folded(text)].length;
    return length ? Math.ceil(length / charsPerLine) : 0;
  }

  function lineHint(text, charsPerLine) {
    const count = lineCount(text, charsPerLine);
    return count ? Texte.t("etwa {zeilen}", { zeilen: lines(count) }) : Texte.t("Leer: fällt beim Speichern weg.");
  }

  /** The place of the longest paragraph by characters, the first on a tie; -1 without any. */
  function longestIndex(paragraphs) {
    return paragraphs.reduce((best, text, place) =>
      (best < 0 || [...folded(text)].length > [...folded(paragraphs[best])].length ? place : best), -1);
  }

  const totalLines = (paragraphs, charsPerLine) => paragraphs.reduce((sum, text) => sum + lineCount(text, charsPerLine), 0);

  /**
   * The line at the top of the paragraphs while the check found the letter over one page (`cut` is its letter_cut):
   * what it found, then the lines saved since the editor opened (`baseline`), if any.
   */
  function goalLine(cut, baseline, now) {
    if (!cut) return "";
    const found = cut.lines > 0 ? Texte.t("Die Prüfung fand etwa {zeilen} zu viel.", { zeilen: lines(cut.lines) })
      : Texte.t("Die Prüfung fand: Das Anschreiben ist länger als eine Seite.");
    const saved = baseline - now;
    if (saved <= 0) return found;
    const values = { gefunden: found, zeilen: lines(saved) };
    return cut.lines > 0 && saved >= cut.lines
      ? Texte.t("{gefunden} Bisher etwa {zeilen} weniger; ob es reicht, zeigt erst «Unterlagen erstellen».", values)
      : Texte.t("{gefunden} Bisher etwa {zeilen} weniger.", values);
  }

  /** The paragraphs as the build reads the fields: each line trimmed, split at blank lines, white space folded. */
  function paragraphsOf(fields) {
    return fields.flatMap(field => String(field ?? "").replace(/\r\n/g, "\n").split("\n").map(line => line.trim())
      .join("\n").split("\n\n").map(folded).filter(Boolean));
  }

  const same = (a, b) => a.length === b.length && a.every((value, place) => value === b[place]);

  /** Whether the letter would change; white space alone does not count. */
  function isDirty(loaded, values) {
    return ["betreff", "anrede", "gruss"].some(key => folded(loaded[key]) !== folded(values[key]))
      || !same(paragraphsOf(loaded.absaetze), paragraphsOf(values.absaetze));
  }

  const isEmpty = values => paragraphsOf(values.absaetze).length === 0;

  /** What the route takes: fields trimmed, empty paragraphs dropped, the fingerprint of the file as loaded. */
  function payload(values, fingerprint) {
    return { betreff: values.betreff.trim(), anrede: values.anrede.trim(),
             absaetze: values.absaetze.map(text => text.trim()).filter(Boolean), gruss: values.gruss.trim(),
             fingerabdruck: fingerprint };
  }

  /** The field that takes the focus after the one at `place` was removed, `left` fields remaining. */
  const focusAfterRemove = (place, left) => Math.min(place, left - 1);

  const refusedText = reason => Texte.t("Nicht gespeichert: {grund}. Der Text bleibt hier.",
                                        { grund: String(reason).replace(/\.\s*$/, "") });

  /** conflict: the file changed (409); unreachable: no answer at all; refused: the server named a reason. */
  function failure(error) {
    if (error && error.status === 409) return "conflict";
    return error && typeof error.status === "number" ? "refused" : "unreachable";
  }

  const logik = { lineCount, lineHint, longestIndex, totalLines, goalLine, paragraphsOf, isDirty, isEmpty, payload,
                  focusAfterRemove, refusedText, failure };
  if (typeof module !== "undefined") module.exports = logik;
  else global.LetterEditorLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
