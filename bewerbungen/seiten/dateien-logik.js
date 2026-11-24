"use strict";
// What „Lebenslauf und Dateien“ shows (#264, A9), without DOM so it can be tested (tests/dateien_logik.test.cjs):
// the choice of the CV, certificates and references in one list, the photos and whether the CV shows one. Labels and
// sentences come in the app language through Texte (#430), each read when used; the ids of kinds and designs stay.
(function (global) {
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const BYTES_PER_MB = 1000000;
  const BYTES_PER_KB = 1000;
  const CERTIFICATE = "zertifikat";
  const DIPLOMA = "diplom";
  const REFERENCE = "zeugnis";
  // G63: the order of the spec; the ids stay those of the folders (own_files.py), only the labels are new. A school
  // report is a Zeugnis as much as a work reference, so the label names neither (#292).
  const KINDS = [REFERENCE, DIPLOMA, CERTIFICATE];
  const KIND_LABELS = {
    get [REFERENCE]() { return Texte.t("Zeugnis"); }, get [DIPLOMA]() { return Texte.t("Diplom"); },
    get [CERTIFICATE]() { return Texte.t("Zertifikat"); },
  };
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
    return count === 1 ? Texte.t("1 Bewerbung hat eine eigene Variante, dort gilt sie.")
      : Texte.t("{anzahl} Bewerbungen haben eine eigene Variante, dort gilt sie.", { anzahl: count });
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
    if (bytes >= BYTES_PER_MB) return Texte.t("{zahl} MB", { zahl: (bytes / BYTES_PER_MB).toFixed(1) });
    return Texte.t("{zahl} KB", { zahl: Math.max(1, Math.round(bytes / BYTES_PER_KB)) });
  }

  // Whole sentences per count, so each language words one photo and several in its own way
  function photoSummary(photos, shown = true) {
    if (!photos.length) return Texte.t("Noch kein Foto. Ein Foto ist freiwillig.");
    const anzahl = photos.length;
    if (!shown) {
      return anzahl === 1 ? Texte.t("1 Foto. Neue Unterlagen entstehen ohne Foto.")
        : Texte.t("{anzahl} Fotos. Neue Unterlagen entstehen ohne Foto.", { anzahl });
    }
    return anzahl === 1 ? Texte.t("1 Foto, es wird verwendet.")
      : Texte.t("{anzahl} Fotos, das umrandete wird verwendet.", { anzahl });
  }

  /** „Im Lebenslauf zeigen“ (G62): there once a photo exists, on unless the person turned it off. */
  function photoSwitch(photos, shown) {
    return { visible: photos.length > 0, checked: shown !== false };
  }

  // G61: the designs that build a CV on their own, the preset first (register.CV_DESIGNS). Siegel, Raster and
  // Register stay the design of a dossier, chosen per application.
  const DESIGNS = [
    { id: "zweispaltig", get name() { return Texte.t("Zweispaltig"); },
      get text() { return Texte.t("Foto und Kontakt im Kopf, zwei Spalten. Viel auf wenig Platz."); } },
    { id: "einspaltig", get name() { return Texte.t("Einspaltig"); },
      get text() { return Texte.t("Schlicht, alles untereinander. Liest sich auch in Bewerbungsportalen gut."); } },
  ];
  const PRESET_DESIGN = DESIGNS[0].id;
  const findDesign = id => DESIGNS.find(design => design.id === id) || DESIGNS[0];
  const designName = id => findDesign(id).name;

  /** Body for POST /api/dateien/aussehen, or null when nothing changes. */
  function designToSave(current, chosen) {
    if (!DESIGNS.some(design => design.id === chosen)) {
      const [erstes, zweites] = DESIGNS.map(design => design.name);
      throw new Error(Texte.t("Bitte {erstes} oder {zweites} wählen.", { erstes, zweites }));
    }
    return chosen === current ? null : { design: chosen };
  }

  function designSaved(id) {
    return Texte.t("Neue Unterlagen entstehen jetzt im Design {design}. Was schon erstellt oder versendet ist, bleibt, wie es ist.",
                   { design: designName(id) });
  }

  // DIPLOMA_NAME and REFERENCE_NAME are also the guess on „Meine Angaben“ (G84, onboarding/src/kindguess.js).
  const logic = { KINDS, KIND_LABELS, DIPLOMA_NAME, REFERENCE_NAME, cvChoice, needsRemoval, variantNote, guessKind, oneList, sizeText, photoSummary,
                  photoSwitch, DESIGNS, PRESET_DESIGN, designName, designToSave, designSaved };
  if (typeof module !== "undefined") module.exports = logic;
  else global.DateienLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
