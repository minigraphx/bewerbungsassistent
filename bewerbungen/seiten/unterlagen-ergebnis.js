"use strict";
// The step «Unterlagen erstellen und prüfen» (#321, option A in docs/design/unterlagen-erstellen.md, G40, G41) without
// DOM: one tile per built document with its pages, how they were balanced (G93) and the link to where it is adapted, the findings with the passed checks counted
// apart, and the short lines for the dossier and the attachments (tests/unterlagen_ergebnis.test.cjs).
(function (global) {
  const W = typeof module !== "undefined" ? require("./unterlagen-wahl.js") : global.UnterlagenWahl;
  const STEP_TITLE = "Unterlagen erstellen und prüfen";
  const DESIGN_NAMES = { siegel: "Siegel", raster: "Raster", register: "Register" };
  const OPEN = "Als PDF öffnen";
  // The CV is made apart and shared by several applications; the click leads to where it is chosen (Andy, 15.11.2026)
  const ADAPT = {
    variant: { text: "Für diese Stelle anpassen", target: "variant" },
    files: { text: "In Lebenslauf und Dateien ändern", target: "files", href: "/dateien" },
    letter: { text: "Anschreiben ändern", target: "letter" },
    dossier: { text: "Dossier gestalten", target: "dossier" },
  };
  // How the page fill changed the setting (lebenslauf/page_fill.change); levels the server does not name stay silent
  const CHANGES = {
    "slightly-tighter": "etwas enger gesetzt",
    tighter: "enger gesetzt",
    tightest: "so eng wie möglich",
    wider: "etwas grosszügiger gesetzt",
  };
  const PARTS = ["letter", "cv"];
  const PART_NAMES = { letter: "Anschreiben", cv: "Lebenslauf" };
  const NEXT_CREATE = `Die App erstellt Lebenslauf und Anschreiben als PDF und prüft sie gleich. Danach stehen sie unter «${STEP_TITLE}» zum Ansehen bereit.`;

  const fileName = file => file.split("/").pop();
  const plural = (count, one, many) => `${count} ${count === 1 ? one : many}`;

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
      .map(part => (art === "dossier" ? `${PART_NAMES[part]} ${CHANGES[changes[part]]}` : CHANGES[changes[part]]));
    return [plural(info.seiten, "Seite", "Seiten"), ...words];
  }

  /** One tile per built document in the order of the choice; nothing is adapted once the application is sent. */
  function tiles(pdfs, choice, { ownCv = false, sent = false, notes = {} } = {}) {
    return W.rahmen(pdfs, choice).map(([art, name]) => ({
      art, name, alt: `${name}, Seite 1`, open: OPEN, adapt: sent ? null : adaptFor(art, ownCv),
      note: pageNote(art, (notes || {})[art]),
    }));
  }

  /** Problems and confirmed breaches stay in view; the checks that passed are only counted (A3). */
  function findingGroups(findings) {
    const all = findings || [];
    const ok = all.filter(f => f.stufe === "ok" && !f.schluessel);
    return {
      shown: all.filter(f => !ok.includes(f)),
      ok,
      okLabel: ok.length ? `${plural(ok.length, "Prüfung", "Prüfungen")} in Ordnung` : "",
    };
  }

  /** One sentence for the status line, so a screen reader hears the result of the check. */
  function announcement(findings) {
    if (!findings) return "";
    const count = level => findings.filter(f => f.stufe === level).length;
    const parts = [
      count("fehler") ? `${count("fehler")} Fehler` : "",
      count("hinweis") ? plural(count("hinweis"), "Hinweis", "Hinweise") : "",
      count("ok") ? `${plural(count("ok"), "Prüfung", "Prüfungen")} in Ordnung` : "",
    ].filter(Boolean);
    return parts.length ? `Geprüft: ${parts.join(", ")}.` : "Geprüft.";
  }

  /** The certificates that go along, as one line; without a saved choice the suggestion counts but is not saved. */
  function attachmentsLine(available, chosen, suggested) {
    if (!available.length) return "Beilagen: noch keine Zertifikate hochgeladen.";
    const files = chosen || suggested;
    if (!files.length) return "Beilagen: keine gewählt.";
    const names = files.map(fileName).join(", ");
    return chosen ? `Beilagen: ${names}` : `Beilagen: ${names} (Vorschlag, noch nicht gespeichert)`;
  }

  function designName(entry) {
    const design = entry.dossier_design || "siegel";
    const own = Object.values(entry.dossier_seiten || {}).some(name => name && name !== design);
    return own ? null : DESIGN_NAMES[design] || DESIGN_NAMES.siegel;
  }

  function designLine(entry) {
    const name = designName(entry);
    return name ? `Design ${name}` : "Design pro Seite";
  }

  /** After creating, the form tiles and the dossier line collapse into this one line (#322, board A3). */
  function formLine(entry) {
    if (W.gewaehlt(entry) !== "dossier") return "Form: Anschreiben und Lebenslauf";
    return `Form: Dossier, ${designName(entry) || "Design pro Seite"}`;
  }

  /** Whether the main file of the chosen form is there: the dossier itself, or one of the two files. */
  const built = (pdfs, choice) => Boolean(choice === "dossier" ? pdfs.dossier : pdfs.lebenslauf || pdfs.anschreiben);

  /** The state of greeting and thanks; an empty text leaves its page out of the dossier (G19). */
  function textsState({ gruss = "", dank = "" }) {
    const greeting = Boolean(gruss.trim());
    const thanks = Boolean(dank.trim());
    if (greeting && thanks) return "Begrüssung und Dank geschrieben";
    if (greeting) return "Begrüssung geschrieben, ohne Dank";
    if (thanks) return "Dank geschrieben, ohne Begrüssung";
    return "Ohne Begrüssung und Dank";
  }

  function nextClarify(errors) {
    return errors === 1
      ? `Die Prüfung hat einen Fehler gefunden. Er steht unter «${STEP_TITLE}».`
      : `Die Prüfung hat ${errors} Fehler gefunden. Sie stehen unter «${STEP_TITLE}».`;
  }

  const logic = { STEP_TITLE, OPEN, NEXT_CREATE, pageNote, tiles, findingGroups, announcement, attachmentsLine, designLine,
    formLine, built, textsState, nextClarify };
  if (typeof module !== "undefined") module.exports = logic;
  else global.UnterlagenErgebnis = logic;
})(typeof window !== "undefined" ? window : globalThis);
