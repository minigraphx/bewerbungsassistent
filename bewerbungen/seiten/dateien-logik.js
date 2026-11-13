"use strict";
// What „Lebenslauf und Dateien“ shows (#264, A9), without DOM so it can be tested (tests/dateien_logik.test.cjs):
// the choice of the CV, certificates and references in one list, the photos.
(function (global) {
  const BYTES_PER_MB = 1000000;
  const BYTES_PER_KB = 1000;
  const CERTIFICATE = "zertifikat";
  const REFERENCE = "zeugnis";
  const KINDS = [CERTIFICATE, REFERENCE];
  const KIND_LABELS = { [CERTIFICATE]: "Zertifikat oder Diplom", [REFERENCE]: "Zeugnis" };
  // A reference says so in its name more often than a certificate does; the person corrects the rest.
  const REFERENCE_NAME = /zeugnis|referenz|arbeitsbest[aä]tigung|reference|testimonial/i;

  /** Which card is chosen: an own PDF counts as long as it is there; without one, the person may be about to add it. */
  function cvChoice({ ownPdf = false, wantsOwn = false } = {}) {
    return ownPdf || wantsOwn ? "eigen" : "app";
  }

  /** Going back to the CV of the app means removing the own PDF, so the page asks first. */
  function needsRemoval({ ownPdf = false, chosen } = {}) {
    return ownPdf && chosen === "app";
  }

  function variantNote(count) {
    if (!count) return "";
    return count === 1 ? "1 Bewerbung hat eine eigene Variante, dort gilt sie."
      : `${count} Bewerbungen haben eine eigene Variante, dort gilt sie.`;
  }

  function guessKind(name) {
    return REFERENCE_NAME.test(name || "") ? REFERENCE : CERTIFICATE;
  }

  /** Certificates and references from GET /api/dateien as one list by name; the CV has its own card. */
  function oneList(found) {
    const rows = KINDS.flatMap(kind => (found[kind] || []).map(file => ({ ...file, art: kind })));
    return rows.sort((a, b) => a.name.localeCompare(b.name, "de"));
  }

  function sizeText(bytes) {
    if (bytes >= BYTES_PER_MB) return `${(bytes / BYTES_PER_MB).toFixed(1)} MB`;
    return `${Math.max(1, Math.round(bytes / BYTES_PER_KB))} KB`;
  }

  function photoSummary(photos) {
    if (!photos.length) return "Noch kein Foto. Ein Foto ist freiwillig.";
    if (photos.length === 1) return "1 Foto, es wird verwendet.";
    return `${photos.length} Fotos, das umrandete wird verwendet.`;
  }

  const logic = { KINDS, KIND_LABELS, cvChoice, needsRemoval, variantNote, guessKind, oneList, sizeText, photoSummary };
  if (typeof module !== "undefined") module.exports = logic;
  else global.DateienLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
