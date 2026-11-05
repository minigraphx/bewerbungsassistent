// What belongs where in the Job-Room form for work efforts (MIN-347). Pure logic without the page, for the content
// script and the tests. Built after the form as it was on 4.11.2026; labels from the public language files of Job-Room.
(function (root) {
  'use strict';

  const TEXT_FIELDS = {
    date: 'date', companyName: 'company', contactPerson: 'contact_person', email: 'email', url: 'url', phone: 'phone',
    occupation: 'occupation', street: 'street', houseNumber: 'house_number', postOfficeBoxNumber: 'po_box',
  };
  const REQUIRED_TEXT = ['date', 'companyName', 'occupation'];
  const CHANNELS = {
    electronic: ['elektronisch', 'par voie électronique', 'per via elettronica'],
    letter: ['brieflich', 'par lettre', 'per lettera'],
    personal: ['persönlich', 'contact personnel', 'di persona'],
    phone: ['telefonisch', 'par téléphone', 'telefonicamente'],
  };
  const THROUGH_RAV = { yes: ['ja', 'oui', 'sì', 'si', 'yes'], no: ['nein', 'non', 'no'] };
  const WORKLOADS = {
    full: ['vollzeit', 'a plein temps', 'à plein temps', 'tempo pieno'],
    part: ['teilzeit', 'a temps partiel', 'à temps partiel', 'tempo parziale'],
  };
  const RESULTS = {
    open: ['noch offen', 'en suspens', 'in sospeso'],
    employed: ['anstellung', 'engagement', 'assunzione'],
    rejected: ['absage', 'réponse négative', 'non assunzione'],
  };
  const SAVED_TITLES = ['arbeitsbemühung gespeichert', "recherche d'emploi sauvegardée",
    'sforzo personale intrapreso per trovare lavoro salvato', 'efforts to find work saved'];
  const NEEDS_ADDRESS = new Set(['letter', 'personal']);
  const ADDRESS_VALUES = ['street', 'po_box', 'postal_city'];
  const WORKLOAD_CONTROL = 'workload';
  const THROUGH_RAV_CONTROL = 'appliedThroughRav';
  const INTERVIEW_CONTROL = 'interview';

  const HINT_POSTAL = 'PLZ / Ort bitte aus der Liste wählen.';
  const HINT_ADDRESS = 'Für diese Art von Bewerbung gehört die Adresse der Firma dazu: bitte ergänzen.';
  const HINT_REACH = 'Für eine elektronische Bewerbung braucht es E-Mail oder Link: bitte ergänzen.';
  const HINT_WORKLOAD = 'Pensum bitte selbst wählen.';
  const HINT_REASON = 'Falls nach dem Absagegrund gefragt wird: bitte selbst wählen.';

  function normal(text) {
    return String(text || '').replace(/[’`]/g, "'").replace(/[*:]/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
  }

  function isSavedTitle(text) {
    const found = normal(text);
    return SAVED_TITLES.some((title) => found.includes(title));
  }

  /** Position of the only field of this kind with one of the labels, or -1. */
  function choiceAt(fields, control, type, labels) {
    return fields.findIndex((f) => (f.control || '') === control && f.type === type && labels.includes(normal(f.label)));
  }

  function textAt(fields, control) {
    return fields.findIndex((f) => f.control === control);
  }

  /** Every group the form must have; a missing label means the form is no longer the one this was built for. */
  function locate(fields) {
    const group = (control, type, table) => Object.fromEntries(
      Object.entries(table).map(([key, labels]) => [key, choiceAt(fields, control, type, labels)]));
    return {
      channels: group('', 'checkbox', CHANNELS),
      through: group(THROUGH_RAV_CONTROL, 'radio', THROUGH_RAV),
      workload: group(WORKLOAD_CONTROL, 'radio', WORKLOADS),
      results: group('', 'radio', RESULTS),
      interview: textAt(fields, INTERVIEW_CONTROL),
      postal: fields.findIndex((f) => f.combobox),
    };
  }

  function hasChanged(fields, spots, values) {
    const groups = [spots.channels, spots.through, spots.workload, spots.results];
    const groupMissing = groups.some((group) => Object.values(group).includes(-1));
    const required = REQUIRED_TEXT.some((control) => textAt(fields, control) < 0);
    const withoutField = Object.entries(TEXT_FIELDS).some(([control, key]) => values[key] && textAt(fields, control) < 0);
    return groupMissing || required || withoutField || spots.interview < 0 || (Boolean(values.postal_city) && spots.postal < 0);
  }

  function textActions(fields, values) {
    return Object.entries(TEXT_FIELDS)
      .map(([control, key]) => ({ index: textAt(fields, control), kind: 'text', value: values[key] }))
      .filter((action) => action.value && !fields[action.index].filled);
  }

  function clickActions(fields, spots, values) {
    const wanted = [
      spots.channels[values.channel],
      spots.through[values.through_rav ? 'yes' : 'no'],
      values.workload ? spots.workload[values.workload] : -1,
      spots.results[values.result],
      values.interview ? spots.interview : -1,
    ];
    return wanted.filter((index) => index >= 0 && !fields[index].filled).map((index) => ({ index, kind: 'click' }));
  }

  /** What the person still has to look at: positions to mark and sentences for the bar. */
  function openItems(fields, spots, values) {
    const open = [];
    const hints = [];
    if (values.postal_city) {
      open.push(spots.postal);
      hints.push(HINT_POSTAL);
    }
    if (NEEDS_ADDRESS.has(values.channel) && !ADDRESS_VALUES.some((key) => values[key])) hints.push(HINT_ADDRESS);
    if (values.channel === 'electronic' && !values.email && !values.url) {
      open.push(textAt(fields, 'email'), textAt(fields, 'url'));
      hints.push(HINT_REACH);
    }
    if (!values.workload) {
      open.push(...Object.values(spots.workload));
      hints.push(HINT_WORKLOAD);
    }
    if (values.result === 'rejected') hints.push(HINT_REASON);
    return { open: open.filter((index) => index >= 0), hints };
  }

  /**
   * @param {{control?: string, type: string, label: string, combobox?: boolean, filled: boolean}[]} fields  of the form, in page order
   * @param {object} values  from the app
   * @returns {{changed: boolean, actions: {index: number, kind: 'text'|'click', value?: string}[], open: number[], hints: string[]}}
   */
  function plan(fields, values) {
    const spots = locate(fields);
    if (hasChanged(fields, spots, values)) return { changed: true, actions: [], open: [], hints: [] };
    const postal = values.postal_city && !fields[spots.postal].filled ? [{ index: spots.postal, kind: 'text', value: values.postal_city }] : [];
    return { changed: false, actions: [...textActions(fields, values), ...postal, ...clickActions(fields, spots, values)], ...openItems(fields, spots, values) };
  }

  const api = { isSavedTitle, plan };
  root.bewerbungsbegleiterRavFields = api;
  if (typeof module !== 'undefined') module.exports = api;
})(globalThis);
