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

  // G77: photo, colour and mark of this CV. Names and colours of marks are the dossier's (zeichen-logik.js); without
  // a choice each CV design keeps its own colour, as its theme draws it, and has no mark. Looked up when used, as
  // the page loads zeichen-logik.js after this file.
  const FITTING = "passend";
  const LOGO = "logo";
  const OWN_COLOURS = { zweispaltig: "#38495d", einspaltig: "#2f5d4a" };
  const NO_OFFER = { foto_vorhanden: false, initialen: "", logo: false };
  const marks = () => (typeof module !== "undefined" ? require("./zeichen-logik.js") : global.ZeichenLogik);

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
    const state = { stand: answer.stand, sections, base: sections, design: answer.design, summaryBase: answer.kurzprofil,
                    recommendations: [], manual: [], look: answer.aussehen || null,
                    lookOffer: answer.aussehen_angebot || NO_OFFER };
    // A mark stored earlier that cannot be drawn any more (the logo is gone) starts as none
    const stored = state.look && markChoices(state).find(choice => choice.id === state.look.zeichen);
    const drawable = state.look && (!stored || stored.locked) ? { ...state, look: { ...state.look, zeichen: FITTING } } : state;
    return withOfferedColour(drawable);
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
    return withOfferedColour({ ...state, design });
  }

  /**
   * The marks to choose, each with its sentence (`note`, none for „none“ and the logo) and the reason it cannot be
   * chosen or null. `name` of „none“ and the logo, and the logo's reason, are keys of texte.js; the other names,
   * sentences and reasons are the dossier's words.
   */
  function markChoices(state) {
    const Z = marks();
    const initials = [...(state.lookOffer.initialen || "")];
    return [
      { id: FITTING, name: "lebenslauf.zeichen-ohne", note: null, locked: null },
      ...Z.VARIANTEN.filter(v => v.wert !== Z.PASSEND).map(v => ({
        id: v.wert, name: v.name, note: v.satz,
        locked: v.wert === "verschraenkt" && initials.length !== 2 ? Z.NUR_ZWEI : null })),
      { id: LOGO, name: "lebenslauf.zeichen-logo", note: null,
        locked: state.lookOffer.logo ? null : "lebenslauf.logo-fehlt" },
    ];
  }

  const rgb = hex => [1, 3, 5].map(at => parseInt(hex.slice(at, at + 2), 16));
  const distance = (one, two) => rgb(one).reduce((sum, part, at) => sum + (part - rgb(two)[at]) ** 2, 0);

  /** The dossier swatch the design's own colour is, or comes nearest to: offered once, as „Passend zum Design“. */
  function ownSwatch(design) {
    const own = OWN_COLOURS[design] || OWN_COLOURS.zweispaltig;
    return marks().FARBEN.reduce((best, swatch) => (distance(swatch.farbe, own) < distance(best.farbe, own) ? swatch : best));
  }

  /** The colours: the design's own (its name a key of texte.js, `note` its swatch), then the other swatches. */
  function accentChoices(state) {
    const own = ownSwatch(state.design);
    return [{ id: FITTING, name: "lebenslauf.farbe-passend", colour: OWN_COLOURS[state.design] || OWN_COLOURS.zweispaltig,
              note: own.name },
            ...marks().FARBEN.filter(swatch => swatch !== own)
              .map(swatch => ({ id: swatch.farbe, name: swatch.name, colour: swatch.farbe }))];
  }

  /** A colour the design now offers as its own (stored, or kept from the other design) becomes „Passend zum Design“. */
  function withOfferedColour(state) {
    if (!state.look || accentChoices(state).some(choice => choice.id === state.look.akzent)) return state;
    return { ...state, look: { ...state.look, akzent: FITTING } };
  }

  /** Change one part of the look: {foto}, {zeichen} or {akzent}; what the panel does not offer is refused. */
  function setLook(state, change) {
    if ("zeichen" in change) {
      const found = markChoices(state).find(choice => choice.id === change.zeichen);
      if (!found) throw new Error("Dieses Zeichen gibt es nicht.");
      if (found.locked) throw new Error("Für dieses Zeichen fehlt noch etwas, etwa ein Logo.");
    }
    if ("akzent" in change && !accentChoices(state).some(choice => choice.id === change.akzent)) {
      throw new Error("Diese Farbe steht nicht zur Wahl.");
    }
    if ("foto" in change && typeof change.foto !== "boolean") throw new Error("Bitte mit oder ohne Foto wählen.");
    return { ...state, look: { ...state.look, ...change } };
  }

  /**
   * Whether „Mit Foto“ can be ticked, and if not, the key of texte.js that says why. A blocked box shows no tick;
   * the choice itself stays in the look, so it comes back with a design that shows a photo.
   */
  function photoChoice(state) {
    if (!state.lookOffer.foto_vorhanden) return { available: false, checked: false, reason: "lebenslauf.foto-fehlt" };
    if (state.design === "einspaltig") return { available: false, checked: false, reason: "lebenslauf.foto-einspaltig" };
    return { available: true, checked: Boolean(state.look && state.look.foto), reason: null };
  }

  /**
   * The two parts of the line beside „Farbe und Zeichen ändern“, joined by the page with dot-line.js (#342); `say`
   * turns keys of texte.js into words.
   */
  function lookParts(state, say) {
    const look = state.look || { zeichen: FITTING, akzent: FITTING };
    const markChoice = markChoices(state).find(choice => choice.id === look.zeichen) || markChoices(state)[0];
    const colour = accentChoices(state).find(choice => choice.id === look.akzent) || accentChoices(state)[0];
    const markPart = markChoice.id === FITTING ? say(markChoice.name) : `Zeichen: ${say(markChoice.name)}`;
    return [markPart, `Farbe: ${colour.id === FITTING ? say("lebenslauf.farbe-passend-zeile") : say(colour.name)}`];
  }

  /** Body for POST /api/lebenslauf/erstellen; the texts come from the fields as they are when saving. */
  function request(state, { id, berufsbezeichnung, kurzprofil, bezeichnung }) {
    if (!state.sections.some(section => section.chosen.length)) throw new Error(NOTHING_CHOSEN);
    const stationen = Object.fromEntries(state.sections.map(section => [section.name, [...section.chosen]]));
    return { id, stand: state.stand, stationen, design: state.design, berufsbezeichnung, kurzprofil, bezeichnung,
             ...(state.look ? { aussehen: { ...state.look } } : {}) };
  }

  function savedText({ variante, gebaut, hinweis }) {
    if (hinweis) return hinweis;
    const name = `«${variante.beschreibung || variante.id}»`;
    return gebaut ? `Gespeichert als ${name} und als PDF erstellt. Er gilt jetzt für diese Bewerbung.`
      : `Gespeichert als ${name}. Er gilt jetzt für diese Bewerbung.`;
  }

  const logic = { DESIGNS, NOTHING_CHOSEN, start, toggle, move, canMove, choose, request, savedText, suggest, setRecommendation, summary,
                  autoSuggest, APPLIED_LINE, aiOffer, suggestedText, recommendationText,
                  markChoices, accentChoices, setLook, photoChoice, lookParts };
  if (typeof module !== "undefined") module.exports = logic;
  else global.LebenslaufErstellenLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
