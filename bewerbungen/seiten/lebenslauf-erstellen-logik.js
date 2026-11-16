"use strict";
// „Lebenslauf erstellen“ on the page of an application (G17, #118): which stations, in which order, and the design,
// apart from each other. Every change returns a new state. No DOM (tests/lebenslauf_erstellen.test.cjs).
// The AI's suggestion (#293, G75) is applied on top of the stations as Meine Angaben gives them; the person's own
// changes are replayed after it, so undoing one recommendation brings back exactly its changes and keeps the rest
// (tests/lebenslauf_vorschlaege.test.cjs).
(function (global) {
  // G61: the designs that build a CV alone (register.CV_DESIGNS); Siegel, Raster and Register stay the dossier's.
  const DESIGNS = [
    { id: "zweispaltig", name: "Zweispaltig", text: "Foto und Kontakt im Kopf, zwei Spalten." },
    { id: "einspaltig", name: "Einspaltig", text: "Schlicht, alles untereinander." },
  ];
  const NOTHING_CHOSEN = "Bitte mindestens eine Station wählen.";
  // Keys of texte.js: the box speaks Sie or du and names a Lehrstelle.
  const APPLIED_LINE = "lebenslauf.ki-angewendet";
  const OFFERS = {
    aus: { line: "lebenslauf.ki-aus", button: "lebenslauf.ki-einschalten", action: "einrichten" },
    ohne_inserat: { line: "lebenslauf.ki-ohne-inserat", button: "lebenslauf.ki-zum-stellentext", action: "stellentext" },
    gespeichert: { line: "lebenslauf.ki-gespeichert", button: "lebenslauf.ki-neu", action: "vorschlagen" },
    bereit: { line: "lebenslauf.ki-bereit", button: "lebenslauf.ki-holen", action: "vorschlagen" },
  };

  const withChosen = (section, picked) => ({ ...section, chosen: section.order.filter(index => picked.has(index)) });

  /** The state from GET /api/lebenslauf/erstellen: the stations in the order shown, chosen ones first. */
  function start(answer) {
    const sections = answer.abschnitte.map(part => ({
      name: part.abschnitt,
      title: part.titel,
      stations: part.stationen,
      order: part.stationen.map(station => station.index),
      chosen: part.stationen.filter(station => station.gewaehlt).map(station => station.index),
    }));
    return { stand: answer.stand, sections, base: sections, design: answer.design, summaryBase: answer.kurzprofil,
             recommendations: [], manual: [] };
  }

  const changeSection = (sections, name, change) =>
    sections.map(section => (section.name === name ? change(section) : section));

  function pick(sections, { name, index, chosen }) {
    return changeSection(sections, name, section => {
      const picked = new Set(section.chosen);
      if (chosen) picked.add(index);
      else picked.delete(index);
      return withChosen(section, picked);
    });
  }

  function swap(sections, { name, index, step }) {
    return changeSection(sections, name, section => {
      const from = section.order.indexOf(index);
      const to = from + step;
      if (from < 0 || to < 0 || to >= section.order.length) return section;
      const order = [...section.order];
      [order[from], order[to]] = [order[to], order[from]];
      return withChosen({ ...section, order }, new Set(section.chosen));
    });
  }

  /** The active recommendations: their stations left out, the ones they move up first, in their order. */
  function recommended(sections, recommendations) {
    const active = recommendations.filter(r => r.on);
    const out = active.flatMap(r => r.weglassen);
    const up = active.flatMap(r => r.voran);
    return sections.map(section => {
      const first = up.filter(ref => ref.abschnitt === section.name && section.order.includes(ref.index))
        .map(ref => ref.index);
      const order = [...first, ...section.order.filter(index => !first.includes(index))];
      const gone = new Set(out.filter(ref => ref.abschnitt === section.name).map(ref => ref.index));
      return withChosen({ ...section, order }, new Set(section.chosen.filter(index => !gone.has(index))));
    });
  }

  function computed(state) {
    const sections = state.manual.reduce((current, step) => (step.kind === "pick" ? pick(current, step) : swap(current, step)),
      recommended(state.base, state.recommendations));
    return { ...state, sections };
  }

  function toggle(state, name, index) {
    const section = state.sections.find(part => part.name === name);
    const chosen = !(section && section.chosen.includes(index));
    return computed({ ...state, manual: [...state.manual, { kind: "pick", name, index, chosen }] });
  }

  /** One place up (-1) or down (+1); at the edge it stays. */
  function move(state, name, index, step) {
    return computed({ ...state, manual: [...state.manual, { kind: "move", name, index, step }] });
  }

  function canMove(state, name, index) {
    const section = state.sections.find(part => part.name === name);
    const place = section ? section.order.indexOf(index) : -1;
    return { up: place > 0, down: place >= 0 && place < section.order.length - 1 };
  }

  /** The suggestion of POST /api/lebenslauf/erstellen/vorschlag, every recommendation applied. */
  function suggest(state, answer) {
    return computed({ ...state, recommendations: answer.empfehlungen.map(r => ({ ...r, on: true })) });
  }

  function setRecommendation(state, number, on) {
    return computed({ ...state, recommendations: state.recommendations.map(r => (r.nummer === number ? { ...r, on } : r)) });
  }

  /** The summary the recommendations give; the one of Meine Angaben when none changes it. */
  function summary(state) {
    const own = state.recommendations.find(r => r.on && typeof r.kurzprofil === "string");
    return own ? own.kurzprofil : state.summaryBase;
  }

  /**
   * Whether opening the panel asks the AI at once. Never (G95, Andy on 16.11.2026): the person first sees the text
   * that would go and what it costs (G15), and only „Vorschläge holen“ sends it. The single place that decides.
   */
  const autoSuggest = () => false;

  /**
   * The line beside the button from GET …/schaetzung, worded by `estimateLine` (TrefferLogik, as „Alle prüfen“).
   * Over the credit it names what is left instead of what stays; `usedUp` locks the button.
   */
  function costLine(estimate, estimateLine) {
    const credit = typeof estimate.guthaben === "number" ? estimate.guthaben : null;
    const usedUp = credit !== null && credit <= 0;
    if (credit === null || usedUp || estimate.kosten <= credit) return { text: estimateLine(estimate), usedUp };
    const about = estimateLine({ ...estimate, guthaben: null });
    const left = `${estimate.waehrung} ${credit.toFixed(2)}`;
    return { text: `${about} Im Guthaben sind noch ${left}, das reicht vielleicht nicht.`, usedUp };
  }

  const estimateFailedText = reason => `Die Schätzung fehlt: ${reason}`;

  /** What the box offers when the suggestion is not applied on opening: line, button and what the button does. */
  function aiOffer(answer) {
    if (answer.ki === "bereit") return answer.eigene_variante ? OFFERS.gespeichert : OFFERS.bereit;
    return OFFERS[answer.ki] || OFFERS.aus;
  }

  /** The announcement after a suggestion; `cost` is the server's charged text, empty for a repeat from its cache. */
  function suggestedText(count, cost = "") {
    const said = count ? `Vorschlag der KI angewendet: ${count} ${count === 1 ? "Empfehlung" : "Empfehlungen"}.`
      : "Die KI schlägt für diese Stelle nichts anderes vor.";
    return cost ? `${said} ${cost}` : said;
  }

  const recommendationText = (recommendation, on) => `${on ? "Wieder angewendet" : "Zurückgenommen"}: ${recommendation.was}.`;

  function choose(state, design) {
    if (!DESIGNS.some(choice => choice.id === design)) {
      throw new Error(`Bitte ${DESIGNS.map(choice => choice.name).join(" oder ")} wählen.`);
    }
    return { ...state, design };
  }

  /** Body for POST /api/lebenslauf/erstellen; the texts come from the fields as they are when saving. */
  function request(state, { id, berufsbezeichnung, kurzprofil, bezeichnung }) {
    if (!state.sections.some(section => section.chosen.length)) throw new Error(NOTHING_CHOSEN);
    const stationen = Object.fromEntries(state.sections.map(section => [section.name, [...section.chosen]]));
    return { id, stand: state.stand, stationen, design: state.design, berufsbezeichnung, kurzprofil, bezeichnung };
  }

  function savedText({ variante, gebaut, hinweis }) {
    if (hinweis) return hinweis;
    const name = `«${variante.beschreibung || variante.id}»`;
    return gebaut ? `Gespeichert als ${name} und als PDF erstellt. Er gilt jetzt für diese Bewerbung.`
      : `Gespeichert als ${name}. Er gilt jetzt für diese Bewerbung.`;
  }

  const logic = { DESIGNS, start, toggle, move, canMove, choose, request, savedText, suggest, setRecommendation, summary,
                  autoSuggest, APPLIED_LINE, aiOffer, costLine, estimateFailedText, suggestedText, recommendationText };
  if (typeof module !== "undefined") module.exports = logic;
  else global.LebenslaufErstellenLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
