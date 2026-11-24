"use strict";
// The step «Unterlagen erstellen und prüfen» (#321, option A in docs/design/unterlagen-erstellen.md, G40, G41) without
// DOM: one tile per built document with its pages, how they were balanced (G93) and the link to where it is adapted, the findings with the passed checks counted
// apart, and the short lines for the dossier and the attachments (tests/unterlagen_ergebnis.test.cjs).
(function (global) {
  const W = typeof module !== "undefined" ? require("./unterlagen-wahl.js") : global.UnterlagenWahl;
  // Texts in the app language through Texte (#428); the page's Texte is found when a text is made.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const stepTitle = () => Texte.t("Unterlagen erstellen und prüfen");
  const DESIGN_NAMES = { siegel: () => Texte.t("Siegel"), raster: () => Texte.t("Raster"), register: () => Texte.t("Register") };
  const DESIGN_LINES = {
    siegel: () => Texte.t("Design Siegel"), raster: () => Texte.t("Design Raster"), register: () => Texte.t("Design Register"),
  };
  // The CV is made apart and shared by several applications; the click leads to where it is chosen (Andy, 15.11.2026)
  const ADAPT = {
    variant: { get text() { return Texte.t("Für diese Stelle anpassen"); }, target: "variant" },
    files: { get text() { return Texte.t("In Lebenslauf und Dateien ändern"); }, target: "files", href: "/dateien" },
    letter: { get text() { return Texte.t("Anschreiben ändern"); }, target: "letter" },
    dossier: { get text() { return Texte.t("Dossier gestalten"); }, target: "dossier" },
  };
  // How the page fill changed the setting (lebenslauf/page_fill.change); levels the server does not name stay silent
  const CHANGES = {
    "slightly-tighter": () => Texte.t("etwas enger gesetzt"),
    tighter: () => Texte.t("enger gesetzt"),
    tightest: () => Texte.t("so eng wie möglich"),
    wider: () => Texte.t("etwas grosszügiger gesetzt"),
  };
  const PARTS = ["letter", "cv"];
  // The dossier names the part before how it was set; each language joins the two in its own way.
  const PART_CHANGES = {
    letter: wie => Texte.t("Anschreiben {wie}", { wie }),
    cv: wie => Texte.t("Lebenslauf {wie}", { wie }),
  };

  const fileName = file => file.split("/").pop();
  const pagesText = count => (count === 1 ? Texte.t("1 Seite") : Texte.t("{anzahl} Seiten", { anzahl: count }));
  const passedText = count => (count === 1 ? Texte.t("1 Prüfung in Ordnung")
    : Texte.t("{anzahl} Prüfungen in Ordnung", { anzahl: count }));

  function adaptFor(art, ownCv) {
    if (art === "lebenslauf") return ownCv ? ADAPT.files : ADAPT.variant;
    return art === "anschreiben" ? ADAPT.letter : ADAPT.dossier;
  }

  /**
   * The pages and, only where the app changed the setting, how (G93): `info` is `{seiten, ausgleich}` from the server,
   * `ausgleich` names the change per part. The dossier names the part, in the order of its pages.
   */
  function pageNote(art, info) {
    if (!info || !Number.isInteger(info.seiten)) return [];
    const changes = info.ausgleich || {};
    const words = PARTS.filter(part => CHANGES[changes[part]])
      .map(part => (art === "dossier" ? PART_CHANGES[part](CHANGES[changes[part]]()) : CHANGES[changes[part]]()));
    return [pagesText(info.seiten), ...words];
  }

  /** One tile per built document in the order of the choice; nothing is adapted once the application is sent. */
  function tiles(pdfs, choice, { ownCv = false, sent = false, notes = {} } = {}) {
    return W.rahmen(pdfs, choice).map(([art, name]) => ({
      art, name, alt: Texte.t("{name}, Seite 1", { name }), open: Texte.t("Als PDF öffnen"),
      adapt: sent ? null : adaptFor(art, ownCv), note: pageNote(art, (notes || {})[art]),
    }));
  }

  /** Problems and confirmed breaches stay in view; the checks that passed are only counted (A3). */
  function findingGroups(findings) {
    const all = findings || [];
    const ok = all.filter(f => f.stufe === "ok" && !f.schluessel);
    return {
      shown: all.filter(f => !ok.includes(f)),
      ok,
      okLabel: ok.length ? passedText(ok.length) : "",
    };
  }

  /** One sentence for the status line, so a screen reader hears the result of the check. */
  function announcement(findings) {
    if (!findings) return "";
    const count = level => findings.filter(f => f.stufe === level).length;
    const errors = count("fehler");
    const notes = count("hinweis");
    const parts = [
      errors === 1 ? Texte.t("1 Fehler") : errors ? Texte.t("{anzahl} Fehler", { anzahl: errors }) : "",
      notes === 1 ? Texte.t("1 Hinweis") : notes ? Texte.t("{anzahl} Hinweise", { anzahl: notes }) : "",
      count("ok") ? passedText(count("ok")) : "",
    ].filter(Boolean);
    return parts.length ? Texte.t("Geprüft: {teile}.", { teile: parts.join(", ") }) : Texte.t("Geprüft.");
  }

  /** The certificates that go along, as one line; without a saved choice the suggestion counts but is not saved. */
  function attachmentsLine(available, chosen, suggested) {
    if (!available.length) return Texte.t("Beilagen: noch keine Zertifikate hochgeladen.");
    const files = chosen || suggested;
    if (!files.length) return Texte.t("Beilagen: keine gewählt.");
    const names = files.map(fileName).join(", ");
    return chosen ? Texte.t("Beilagen: {namen}", { namen: names })
      : Texte.t("Beilagen: {namen} (Vorschlag, noch nicht gespeichert)", { namen: names });
  }

  /** The id of the one design of all pages, or null with a design per page. */
  function designOf(entry) {
    const design = entry.dossier_design || "siegel";
    const own = Object.values(entry.dossier_seiten || {}).some(name => name && name !== design);
    if (own) return null;
    return DESIGN_NAMES[design] ? design : "siegel";
  }

  function designLine(entry) {
    const design = designOf(entry);
    return design ? DESIGN_LINES[design]() : Texte.t("Design pro Seite");
  }

  /** After creating, the form tiles and the dossier line collapse into this one line (#322, board A3). */
  function formLine(entry) {
    if (W.gewaehlt(entry) !== "dossier") return Texte.t("Form: Anschreiben und Lebenslauf");
    const design = designOf(entry);
    return Texte.t("Form: Dossier, {design}", { design: design ? DESIGN_NAMES[design]() : Texte.t("Design pro Seite") });
  }

  /** Whether the main file of the chosen form is there: the dossier itself, or one of the two files. */
  const built = (pdfs, choice) => Boolean(choice === "dossier" ? pdfs.dossier : pdfs.lebenslauf || pdfs.anschreiben);

  /** The state of greeting and thanks; an empty text leaves its page out of the dossier (G19). */
  function textsState({ gruss = "", dank = "" }) {
    const greeting = Boolean(gruss.trim());
    const thanks = Boolean(dank.trim());
    if (greeting && thanks) return Texte.t("Begrüssung und Dank geschrieben");
    if (greeting) return Texte.t("Begrüssung geschrieben, ohne Dank");
    if (thanks) return Texte.t("Dank geschrieben, ohne Begrüssung");
    return Texte.t("Ohne Begrüssung und Dank");
  }

  function nextClarify(errors) {
    return errors === 1
      ? Texte.t("Die Prüfung hat einen Fehler gefunden. Er steht unter «{schritt}».", { schritt: stepTitle() })
      : Texte.t("Die Prüfung hat {anzahl} Fehler gefunden. Sie stehen unter «{schritt}».", { anzahl: errors, schritt: stepTitle() });
  }

  const nextCreate = () => Texte.t("Die App erstellt Lebenslauf und Anschreiben als PDF und prüft sie gleich. Danach stehen sie unter «{schritt}» zum Ansehen bereit.",
    { schritt: stepTitle() });

  // Read when shown, so they follow the language of the page.
  const logic = { get STEP_TITLE() { return stepTitle(); }, get OPEN() { return Texte.t("Als PDF öffnen"); },
    get NEXT_CREATE() { return nextCreate(); }, pageNote, tiles, findingGroups, announcement, attachmentsLine, designLine,
    formLine, built, textsState, nextClarify };
  if (typeof module !== "undefined") module.exports = logic;
  else global.UnterlagenErgebnis = logic;
})(typeof window !== "undefined" ? window : globalThis);
