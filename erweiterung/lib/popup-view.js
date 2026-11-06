// What the popup shows (MIN-369): the words of the text set, the last search, the portals of a running search and the
// rating of the open page. No DOM; tested in tests/popup.test.mjs.

/** The text set follows the setup of the app: an apprenticeship is always du, a job Sie unless du was chosen. */
export function textSet(plan) {
  if (plan && plan.art === 'lehrstelle') return 'lehrstelle-du';
  return plan && plan.anrede === 'du' ? 'stelle-du' : 'stelle-sie';
}

const WORDS = {
  'stelle-sie': {
    title: 'Stellen suchen',
    keepBrowsing: 'Sie können den Browser weiter benutzen. Der Tab der Suche bleibt offen.',
    noAd: 'Auf dieser Seite ist keine Stellenanzeige erkannt.',
    save: 'Stelle speichern',
    appMissing: 'Starten Sie den Bewerbungsbegleiter auf diesem Computer. Danach verbindet sich die Erweiterung von selbst.',
  },
  'stelle-du': {
    title: 'Stellen suchen',
    keepBrowsing: 'Du kannst den Browser weiter benutzen. Der Tab der Suche bleibt offen.',
    noAd: 'Auf dieser Seite ist keine Stellenanzeige erkannt.',
    save: 'Stelle speichern',
    appMissing: 'Starte den Bewerbungsbegleiter auf diesem Computer. Danach verbindet sich die Erweiterung von selbst.',
  },
  'lehrstelle-du': {
    title: 'Lehrstellen suchen',
    keepBrowsing: 'Du kannst den Browser weiter benutzen. Der Tab der Suche bleibt offen.',
    noAd: 'Auf dieser Seite ist keine Lehrstelle erkannt.',
    save: 'Lehrstelle speichern',
    appMissing: 'Starte den Bewerbungsbegleiter auf diesem Computer. Danach verbindet sich die Erweiterung von selbst.',
  },
};

/** @param {string} set  from textSet */
export function words(set) {
  return WORDS[set] || WORDS['stelle-sie'];
}

const MINUTE_MS = 60000;
const DAY_MS = 24 * 60 * MINUTE_MS;

function dayWord(date, now) {
  const start = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((start(now) - start(date)) / DAY_MS);
  if (days === 0) return 'heute';
  if (days === 1) return 'gestern';
  return `am ${date.toLocaleDateString('de-CH', { day: '2-digit', month: '2-digit', year: 'numeric' })}`;
}

const newHits = (n) => (n === 1 ? '1 neuer Treffer' : `${n} neue Treffer`);

/**
 * The line under „Stellen suchen“ after a run: „Letzte Suche heute, 08:12 · 12 neue Treffer“. Empty without a finished run.
 * @param {{zustand: string, ende?: string, beginn?: string, ergebnis?: object, fehler?: string}|null} run
 */
export function lastSearch(run, now = new Date()) {
  if (!run) return { text: '', problem: false };
  if (run.zustand === 'fehler') return { text: run.fehler || 'Die letzte Suche ist abgebrochen.', problem: true };
  if (run.zustand !== 'fertig') return { text: '', problem: false };
  const when = new Date(run.ende || run.beginn);
  const time = when.toLocaleTimeString('de-CH', { hour: '2-digit', minute: '2-digit' });
  const fresh = Object.values((run.ergebnis && run.ergebnis.portale) || {}).reduce((sum, p) => sum + (p.neu || 0), 0);
  const stopped = run.ergebnis && run.ergebnis.abgebrochen ? ' (abgebrochen)' : '';
  return { text: `Letzte Suche ${dayWord(when, now)}, ${time}${stopped} · ${newHits(fresh)}`, problem: false };
}

function currentText(step) {
  if (step.phase === 'suche') return `Seite ${step.seite}`;
  if (step.phase === 'texte') return `liest Inserate, ${step.fertig} von ${step.von}`;
  return 'startet';
}

/** The portals of the plan in their order; further sites at the end, as the search runs them. */
export function planPortals(plan) {
  if (!plan) return [];
  return [...(plan.portale || []), ...(plan.weitere_seiten || []).map((site) => site.portal)];
}

/**
 * One row per portal while a search runs: the portals before the current one are done, the ones after it wait.
 * Without a plan (the app did not answer) only the current portal is known.
 * @returns {Array<{name: string, state: 'done'|'current'|'waiting', text: string}>}
 */
export function portalRows(plan, run) {
  if (!run || run.zustand !== 'laeuft') return [];
  const step = run.schritt || { phase: 'start' };
  const names = planPortals(plan);
  if (step.portal && !names.includes(step.portal)) names.push(step.portal);
  const current = step.portal ? names.indexOf(step.portal) : -1;
  return names.map((name, index) => {
    if (index < current) return { name, state: 'done', text: 'fertig' };
    if (index === current) return { name, state: 'current', text: currentText(step) };
    return { name, state: 'waiting', text: 'wartet' };
  });
}

export function noteWord(note) {
  if (note >= 5.5) return 'passt sehr gut';
  if (note >= 4.5) return 'passt gut';
  if (note >= 4) return 'passt knapp';
  return 'passt wenig';
}

const SCALE = 6;

function note(value, name) {
  const number = Number(value);
  return {
    name, text: String(number), filled: Math.max(0, Math.min(SCALE, Math.floor(number))), half: number % 1 >= 0.5,
    word: noteWord(number), label: `${name ? `${name}: ` : ''}Note ${number} von ${SCALE}, ${noteWord(number)}`,
  };
}

const listText = (label, items) => (items && items.length ? `${label}: ${items.join(', ')}.` : '');

/**
 * The rating of the open page as in the design: note(s) with boxes and word, what fits and what is missing.
 * @param {{note: number, beruf_note?: number, passt?: string[], haken?: string[], neue_luecken?: string[], unsicher?: string}} rating
 * @param {boolean} apprenticeship
 */
export function ratingView(rating, apprenticeship) {
  const notes = apprenticeship && rating.beruf_note
    ? [note(rating.beruf_note, 'Beruf'), note(rating.note, 'Lehrstelle')]
    : [note(rating.note, '')];
  const missing = [...(rating.haken || []), ...(rating.neue_luecken || [])];
  return {
    notes,
    text: [listText('Passt', rating.passt), listText('Fehlt', missing)].filter(Boolean).join(' '),
    unsure: rating.unsicher ? `Note unsicher: ${rating.unsicher}` : '',
  };
}
