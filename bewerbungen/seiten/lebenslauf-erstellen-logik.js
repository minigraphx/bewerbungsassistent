"use strict";
// „Lebenslauf erstellen“ on the page of an application (G17, #118): which stations, in which order, and the design,
// apart from each other. Every change returns a new state. No DOM (tests/lebenslauf_erstellen.test.cjs).
(function (global) {
  // G61: the designs that build a CV alone (register.CV_DESIGNS); Siegel, Raster and Register stay the dossier's.
  const DESIGNS = [
    { id: "zweispaltig", name: "Zweispaltig", text: "Foto und Kontakt im Kopf, zwei Spalten." },
    { id: "einspaltig", name: "Einspaltig", text: "Schlicht, alles untereinander." },
  ];
  const NOTHING_CHOSEN = "Bitte mindestens eine Station wählen.";

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
    return { stand: answer.stand, sections, design: answer.design };
  }

  const changeSection = (state, name, change) =>
    ({ ...state, sections: state.sections.map(section => (section.name === name ? change(section) : section)) });

  function toggle(state, name, index) {
    return changeSection(state, name, section => {
      const picked = new Set(section.chosen);
      if (picked.has(index)) picked.delete(index);
      else picked.add(index);
      return withChosen(section, picked);
    });
  }

  /** One place up (-1) or down (+1); at the edge it stays. */
  function move(state, name, index, step) {
    return changeSection(state, name, section => {
      const from = section.order.indexOf(index);
      const to = from + step;
      if (from < 0 || to < 0 || to >= section.order.length) return section;
      const order = [...section.order];
      [order[from], order[to]] = [order[to], order[from]];
      return withChosen({ ...section, order }, new Set(section.chosen));
    });
  }

  function canMove(state, name, index) {
    const section = state.sections.find(part => part.name === name);
    const place = section ? section.order.indexOf(index) : -1;
    return { up: place > 0, down: place >= 0 && place < section.order.length - 1 };
  }

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

  const logic = { DESIGNS, start, toggle, move, canMove, choose, request, savedText };
  if (typeof module !== "undefined") module.exports = logic;
  else global.LebenslaufErstellenLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
