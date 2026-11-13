"use strict";
// What „Lebenslauf und Dateien“ shows (#264, A9), without DOM so it can be tested (tests/dateien_logik.test.cjs):
// the choice of the CV, certificates and references in one list, the photos.
(function (global) {
  const BYTES_PER_MB = 1000000;
  const BYTES_PER_KB = 1000;
  const CERTIFICATE = "zertifikat";
  const DIPLOMA = "diplom";
  const REFERENCE = "zeugnis";
  // G63: the order of the spec; the ids stay those of the folders (own_files.py), only the labels are new.
  const KINDS = [REFERENCE, DIPLOMA, CERTIFICATE];
  const KIND_LABELS = { [REFERENCE]: "Arbeitszeugnis", [DIPLOMA]: "Diplom", [CERTIFICATE]: "Zertifikat" };
  // A Fähigkeitszeugnis or Maturitätszeugnis is a diploma, so the diploma is asked first. "Master" alone stays out:
  // a Scrum Master is a certificate. The person corrects the rest.
  const DIPLOMA_NAME = /diplom|f(?:ä|ae|a)higkeitszeugnis|(?:^|[^a-zäöü])matur|bachelor|master of|berufsattest|lizentiat|(?:^|[^a-z])(?:efz|eba)(?:[^a-z]|$)/i;
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
    const text = name || "";
    if (DIPLOMA_NAME.test(text)) return DIPLOMA;
    return REFERENCE_NAME.test(text) ? REFERENCE : CERTIFICATE;
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

  // G61: the designs that build a CV on their own, the preset first (register.CV_DESIGNS). Siegel, Raster and
  // Register stay the design of a dossier, chosen per application.
  const DESIGNS = [
    { id: "zweispaltig", name: "Zweispaltig", text: "Foto und Kontakt im Kopf, zwei Spalten. Viel auf wenig Platz." },
    { id: "einspaltig", name: "Einspaltig", text: "Schlicht, alles untereinander. Liest sich auch in Bewerbungsportalen gut." },
  ];
  const PRESET_DESIGN = DESIGNS[0].id;
  const findDesign = id => DESIGNS.find(design => design.id === id) || DESIGNS[0];
  const designName = id => findDesign(id).name;

  /** Body for POST /api/dateien/aussehen, or null when nothing changes. */
  function designToSave(current, chosen) {
    if (!DESIGNS.some(design => design.id === chosen)) {
      throw new Error(`Bitte ${DESIGNS.map(design => design.name).join(" oder ")} wählen.`);
    }
    return chosen === current ? null : { design: chosen };
  }

  function designSaved(id) {
    return `Neue Unterlagen entstehen jetzt im Design ${designName(id)}. Was schon erstellt oder versendet ist, bleibt, wie es ist.`;
  }

  const logic = { KINDS, KIND_LABELS, cvChoice, needsRemoval, variantNote, guessKind, oneList, sizeText, photoSummary,
                  DESIGNS, PRESET_DESIGN, designName, designToSave, designSaved };
  if (typeof module !== "undefined") module.exports = logic;
  else global.DateienLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
