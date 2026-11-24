"use strict";
// The dialog «Dossier gestalten» (#322, board A2 of docs/design/unterlagen-erstellen.md) without DOM: when «Abbrechen»
// asks first, what the page says after «Übernehmen», and where Tab wraps (tests/dossier_dialog.test.cjs).
// Texts in the app language through Texte (#429); the page's Texte is found when a text is made.
(function (global) {
  const texte = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  const Texte = { t: deutsch => texte().t(deutsch) };
  const saved = () => Texte.t("Dossier übernommen. Mit «Unterlagen erstellen» entsteht es neu.");
  // One sentence per case, so French and English can say one page or two
  const LEFT_OUT = {
    gruss: () => Texte.t("Ohne Begrüssung entfällt die Seite dazu."),
    dank: () => Texte.t("Ohne Dank entfällt die Seite dazu."),
    beide: () => Texte.t("Ohne Begrüssung und Dank entfällt die Seite dazu."),
  };

  /** Typed texts are work; a design is one click to choose again, so only texts make «Abbrechen» ask. */
  const cancelAction = textsChanged => (textsChanged ? "ask" : "close");

  /** An empty text leaves its page out of the dossier (G19); the message says so. `texts` is null when unchanged. */
  function savedMessage(designChanged, texts) {
    if (!designChanged && !texts) return "";
    if (!texts) return saved();
    const noGreeting = !texts.gruss.trim();
    const noThanks = !texts.dank.trim();
    if (!noGreeting && !noThanks) return saved();
    const leftOut = noGreeting && noThanks ? LEFT_OUT.beide : noGreeting ? LEFT_OUT.gruss : LEFT_OUT.dank;
    return `${saved()} ${leftOut()}`;
  }

  /**
   * The index to focus when Tab leaves the last control or Shift+Tab the first, so the focus stays in the dialog;
   * -1 lets the browser move on. `index` is -1 when the dialog itself has the focus.
   */
  function wrapIndex(index, count, backwards) {
    if (!count) return -1;
    if (index === -1) return backwards ? count - 1 : 0;
    if (backwards) return index === 0 ? count - 1 : -1;
    return index === count - 1 ? 0 : -1;
  }

  const logic = { cancelAction, savedMessage, wrapIndex };
  if (typeof module !== "undefined") module.exports = logic;
  else global.DossierDialogLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
