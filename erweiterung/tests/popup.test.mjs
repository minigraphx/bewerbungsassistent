// What the popup shows (MIN-369): text set, last search, portals of a running search, rating of the open page.
import test from 'node:test';
import assert from 'node:assert/strict';
import { lastSearch, noteWord, portalRows, ratingView, textSet, words } from '../lib/popup-view.js';
import { permissionText } from '../lib/permission-text.js';

const PLAN = { art: 'stelle', portale: ['jobs.ch', 'job-room', 'jobscout24'], weitere_seiten: [{ portal: 'karriere.muster-ag.ch' }] };

test('the text set follows the choice of the setup', () => {
  assert.equal(textSet({ art: 'lehrstelle', anrede: 'sie' }), 'lehrstelle-du');
  assert.equal(textSet({ art: 'stelle', anrede: 'du' }), 'stelle-du');
  assert.equal(textSet({ art: 'stelle' }), 'stelle-sie');
  assert.equal(textSet(null), 'stelle-sie');
  assert.match(words('stelle-du').keepBrowsing, /^Du kannst/);
  assert.equal(words('lehrstelle-du').save, 'Lehrstelle speichern');
  assert.equal(words('unbekannt').title, 'Stellen suchen');
});

test('the last search says when and how many new hits', () => {
  const now = new Date(2026, 10, 6, 14, 0);
  const run = { zustand: 'fertig', ende: new Date(2026, 10, 6, 8, 12).toISOString(),
    ergebnis: { portale: { 'jobs.ch': { neu: 8 }, 'job-room': { neu: 4 } } } };
  assert.deepEqual(lastSearch(run, now), { text: 'Letzte Suche heute, 08:12 · 12 neue Treffer', problem: false });
  const yesterday = { ...run, ende: new Date(2026, 10, 5, 17, 3).toISOString(), ergebnis: { portale: { a: { neu: 1 } }, abgebrochen: true } };
  assert.equal(lastSearch(yesterday, now).text, 'Letzte Suche gestern, 17:03 (abgebrochen) · 1 neuer Treffer');
  assert.match(lastSearch({ ...run, ende: new Date(2026, 9, 30, 9, 0).toISOString() }, now).text, /^Letzte Suche am 30\.10\.2026, 09:00/);
  assert.deepEqual(lastSearch({ zustand: 'fehler', fehler: 'App fehlt' }, now), { text: 'App fehlt', problem: true });
  assert.equal(lastSearch({ zustand: 'laeuft' }, now).text, '');
  assert.equal(lastSearch(null, now).text, '');
});

test('while a search runs, portals before the current one are done and later ones wait', () => {
  const run = { zustand: 'laeuft', schritt: { phase: 'suche', portal: 'job-room', seite: 2 } };
  assert.deepEqual(portalRows(PLAN, run), [
    { name: 'jobs.ch', state: 'done', text: 'fertig' },
    { name: 'job-room', state: 'current', text: 'Seite 2' },
    { name: 'jobscout24', state: 'waiting', text: 'wartet' },
    { name: 'karriere.muster-ag.ch', state: 'waiting', text: 'wartet' },
  ]);
  const reading = portalRows(PLAN, { zustand: 'laeuft', schritt: { phase: 'texte', portal: 'jobs.ch', fertig: 3, von: 9 } });
  assert.equal(reading[0].text, 'liest Inserate, 3 von 9');
  assert.ok(portalRows(PLAN, { zustand: 'laeuft' }).every((row) => row.state === 'waiting'));
  assert.deepEqual(portalRows(null, run), [{ name: 'job-room', state: 'current', text: 'Seite 2' }]);
  assert.deepEqual(portalRows(PLAN, { zustand: 'fertig' }), []);
});

test('the rating shows the note with its word and what fits or is missing', () => {
  const view = ratingView({ note: 5, passt: ['Einkauf', 'SAP MM'], haken: ['Englisch verhandlungssicher'] }, false);
  assert.deepEqual(view.notes.map((n) => [n.text, n.filled, n.half, n.word]), [['5', 5, false, 'passt gut']]);
  assert.equal(view.notes[0].label, 'Note 5 von 6, passt gut');
  assert.equal(view.text, 'Passt: Einkauf, SAP MM. Fehlt: Englisch verhandlungssicher.');
  const apprenticeship = ratingView({ note: 4.5, beruf_note: 5.5, unsicher: 'kurzes Inserat' }, true);
  assert.deepEqual(apprenticeship.notes.map((n) => n.label), ['Beruf: Note 5.5 von 6, passt sehr gut', 'Lehrstelle: Note 4.5 von 6, passt gut']);
  assert.equal(apprenticeship.notes[1].half, true);
  assert.equal(apprenticeship.unsure, 'Note unsicher: kurzes Inserat');
  assert.equal(noteWord(3.5), 'passt wenig');
  assert.equal(noteWord(4), 'passt knapp');
});

test('the page that asks for access speaks like the app and promises only what holds', () => {
  const forms = permissionText('formulare', 'stelle-sie');
  assert.match(forms.text, /Ihre Erlaubnis/);
  assert.deepEqual(forms.never, ['etwas abschicken', 'Einwilligungen bestätigen', 'sich anmelden oder Passwörter lesen']);
  assert.match(permissionText('formulare', 'lehrstelle-du').foot, /kannst du/);
  assert.match(permissionText('suche', 'lehrstelle-du').text, /Lehrstellen finden/);
  const jobDu = permissionText('suche', 'stelle-du');
  assert.match(jobDu.text, /deine Erlaubnis/);
  assert.match(jobDu.text, /dort Stellen finden/);
  assert.match(jobDu.does[0], /^Stellenanzeigen auf deinen Seiten/);
  assert.match(permissionText('suche', undefined).question, /Ihren weiteren Seiten/);
});
