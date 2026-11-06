// Entering work efforts in Job-Room (MIN-347): the mapping onto the real form, and the run over one tab.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import { FORM_URL, RavRun, isRavPage } from '../lib/rav.js';
import { ALLOWED, RAV_ACTIONS, isRavSender } from '../lib/senders.js';

const require = createRequire(import.meta.url);
const { isSavedTitle, plan } = require('../form/rav-fields.js');

const text = (control, label = control) => ({ control, type: 'text', label, filled: false });
const tick = (type, label, control = '') => ({ control, type, label, filled: false });

/** The form as it was read on 4.11.2026; labels as in the public language files of Job-Room. */
function form(labels = {}) {
  const l = {
    electronic: 'Elektronisch', letter: 'Brieflich', personal: 'Persönlich', phone: 'Telefonisch', no: 'Nein', yes: 'Ja',
    full: 'Vollzeit', part: 'Teilzeit', open: 'Noch offen', employed: 'Anstellung', rejected: 'Absage', postal: 'PLZ / Ort', ...labels,
  };
  return [
    text('date', 'Datum'),
    tick('checkbox', l.electronic), tick('checkbox', l.letter), tick('checkbox', l.personal), tick('checkbox', l.phone),
    text('companyName', 'Unternehmen'), text('street', 'Strasse'), text('houseNumber', 'Nr.'), text('postOfficeBoxNumber', 'Postfach-Nr.'),
    { control: 'countryIsoCode', type: 'select-one', label: 'Land', filled: true },
    { control: '', type: 'text', label: l.postal, combobox: true, filled: false },
    text('contactPerson', 'Kontaktperson'), text('email', 'E-Mail'), text('url', 'Link zum Online-Formular'),
    { control: 'phone', type: 'tel', label: 'Telefonnummer', filled: false }, text('occupation', 'Stellenbezeichnung'),
    tick('radio', l.no, 'appliedThroughRav'), tick('radio', l.yes, 'appliedThroughRav'),
    tick('radio', l.full, 'workload'), tick('radio', l.part, 'workload'),
    tick('checkbox', 'Vorstellungsgespräch', 'interview'),
    tick('radio', l.open), tick('radio', l.employed), tick('radio', l.rejected),
  ];
}

const VALUES = {
  date: '20.10.2026', channel: 'electronic', company: 'Muster AG', occupation: 'Entwickler', email: 'a@example.org',
  workload: 'full', through_rav: false, result: 'open', interview: false,
};

function applied(fields, found) {
  return Object.fromEntries(found.actions.map((a) => [`${fields[a.index].control || ''}:${fields[a.index].label}`, a.value ?? 'click']));
}

test('an electronic application fills what is known and ticks only its own choices', () => {
  const fields = form();
  const found = plan(fields, VALUES);
  assert.equal(found.changed, false);
  assert.deepEqual(applied(fields, found), {
    'date:Datum': '20.10.2026', 'companyName:Unternehmen': 'Muster AG', 'email:E-Mail': 'a@example.org',
    'occupation:Stellenbezeichnung': 'Entwickler', ':Elektronisch': 'click', 'appliedThroughRav:Nein': 'click',
    'workload:Vollzeit': 'click', ':Noch offen': 'click',
  });
  assert.deepEqual(found.hints, []);
});

test('the same form in French and Italian', () => {
  const french = form({ electronic: 'Par voie électronique', letter: 'Par lettre', personal: 'Contact personnel', phone: 'Par téléphone',
    no: 'Non', yes: 'Oui', full: 'A plein temps', part: 'A temps partiel', open: 'En suspens', employed: 'Engagement', rejected: 'Réponse négative', postal: 'NPA / lieu' });
  assert.equal(plan(french, VALUES).changed, false);
  const italian = form({ electronic: 'Per via elettronica', letter: 'Per lettera', personal: 'Di persona', phone: 'Telefonicamente',
    no: 'No', yes: 'Sì', full: 'Tempo pieno', part: 'Tempo parziale', open: 'In sospeso', employed: 'Assunzione', rejected: 'Non assunzione', postal: 'NPA / luogo' });
  assert.equal(plan(italian, VALUES).changed, false);
});

test('a form that changed fills nothing and says so', () => {
  for (const drop of ['date', 'occupation', 'workload', 'appliedThroughRav']) {
    const found = plan(form().filter((f) => f.control !== drop), VALUES);
    assert.equal(found.changed, true, drop);
    assert.deepEqual(found.actions, []);
  }
  assert.equal(plan(form({ electronic: 'Online' }), VALUES).changed, true);
  assert.equal(plan(form({ rejected: 'Negativ' }), VALUES).changed, true);
  assert.equal(plan(form().filter((f) => f.control !== 'email'), VALUES).changed, true, 'a value without its field');
  assert.equal(plan(form().filter((f) => f.control !== 'email'), { ...VALUES, email: undefined, url: 'https://a.ch' }).changed, false);
});

test('what is there stays', () => {
  const fields = form().map((f) => (f.control === 'companyName' ? { ...f, filled: true } : f));
  assert.ok(!('companyName:Unternehmen' in applied(fields, plan(fields, VALUES))));
  const ticked = form().map((f) => (f.label === 'Elektronisch' ? { ...f, filled: true } : f));
  assert.ok(!(':Elektronisch' in applied(ticked, plan(ticked, VALUES))));
});

test('a letter gets the address; the place is typed but chosen by the person', () => {
  const fields = form();
  const found = plan(fields, { ...VALUES, channel: 'letter', email: undefined, street: 'Musterweg', house_number: '12', po_box: '77', postal_city: '3000 Bern' });
  const done = applied(fields, found);
  assert.equal(done['street:Strasse'], 'Musterweg');
  assert.equal(done['houseNumber:Nr.'], '12');
  assert.equal(done['postOfficeBoxNumber:Postfach-Nr.'], '77');
  assert.equal(done[':PLZ / Ort'], '3000 Bern');
  assert.equal(done[':Brieflich'], 'click');
  assert.ok(found.open.includes(fields.findIndex((f) => f.combobox)));
  assert.match(found.hints.join(), /PLZ \/ Ort/);
});

test('a letter without an address, an electronic one without a way to reach it', () => {
  const letter = plan(form(), { ...VALUES, channel: 'letter', email: undefined });
  assert.match(letter.hints.join(), /Adresse/);
  const fields = form();
  const electronic = plan(fields, { ...VALUES, email: undefined });
  assert.match(electronic.hints.join(), /E-Mail oder/);
  assert.ok(electronic.open.includes(fields.findIndex((f) => f.control === 'email')));
});

test('unknown workload stays open, marked on both choices', () => {
  const fields = form();
  const found = plan(fields, { ...VALUES, workload: undefined });
  assert.ok(!('workload:Vollzeit' in applied(fields, found)) && !('workload:Teilzeit' in applied(fields, found)));
  assert.deepEqual(found.open, fields.flatMap((f, i) => (f.control === 'workload' ? [i] : [])));
  assert.match(found.hints.join(), /Pensum/);
});

test('result, interview and assignment', () => {
  const fields = form();
  const found = plan(fields, { ...VALUES, result: 'rejected', interview: true, through_rav: true });
  const done = applied(fields, found);
  assert.equal(done[':Absage'], 'click');
  assert.equal(done['interview:Vorstellungsgespräch'], 'click');
  assert.equal(done['appliedThroughRav:Ja'], 'click');
  assert.ok(!('appliedThroughRav:Nein' in done));
  assert.match(found.hints.join(), /Absagegrund/);
  assert.equal(applied(fields, plan(fields, { ...VALUES, result: 'employed' }))[':Anstellung'], 'click');
});

test('labels may carry a mark for required fields', () => {
  const fields = form({ electronic: ' Elektronisch * ' });
  assert.equal(plan(fields, VALUES).changed, false);
});

test('the message after saving is recognised in four languages, and only that', () => {
  for (const title of ['Arbeitsbemühung gespeichert', 'Recherche d’emploi sauvegardée', "Recherche d'emploi sauvegardée",
    'Sforzo personale intrapreso per trovare lavoro salvato', 'Efforts to find work saved', '  Arbeitsbemühung   gespeichert\n×  ']) {
    assert.ok(isSavedTitle(title), title);
  }
  assert.ok(!isSavedTitle('Arbeitsbemühung konnte nicht gespeichert werden'));
  assert.ok(!isSavedTitle(''));
});

// The run

const READY = [{ id: 'a', firma: 'Muster AG', stelle: 'Entwickler' }, { id: 'b', firma: 'Beispiel GmbH', stelle: 'Analyst' }];

function setup({ start = { bereit: READY, abgelehnt: [] } } = {}) {
  const log = [];
  let state = null;
  const answers = {
    '/api/rav/start': () => start,
    '/api/rav/angaben': ({ id }) => ({ werte: { company: id } }),
    '/api/rav/eingetragen': () => ({ rav_eingetragen_am: '2026-10-26' }),
  };
  const run = new RavRun({
    ask: async (method, path, data) => { log.push(['ask', path, data]); return answers[path](data); },
    tabs: {
      blank: async () => { log.push(['blank']); return 7; },
      navigate: async (tabId, url) => { log.push(['navigate', tabId, url]); },
      activate: async (tabId) => { log.push(['activate', tabId]); },
      exists: async () => true,
      inject: async (tabId) => { log.push(['inject', tabId]); },
      bar: async (tabId, balken) => { log.push(['bar', { ...balken, text: [balken.titel, balken.text].filter(Boolean).join(' ') }]); },
      end: async (tabId, balken) => { log.push(['end', [balken.titel, balken.text].join(' ')]); },
    },
    store: { get: async () => state, set: async (next) => { state = next; } },
    sleep: async () => {},
  });
  const seen = (name) => log.filter((e) => e[0] === name);
  return { run, log, answers, seen, state: () => state, lastBar: () => seen('bar').at(-1)[1], asked: (path) => log.filter((e) => e[0] === 'ask' && e[1] === path) };
}

const PAGE = 'https://www.job-room.ch/work-efforts/create';

test('only Job-Room itself counts as the page', () => {
  assert.ok(isRavPage(PAGE));
  assert.ok(!isRavPage('http://www.job-room.ch/work-efforts/create'));
  assert.ok(!isRavPage('https://www.job-room.ch.example.org/'));
  assert.ok(!isRavPage('https://login.example.org/?x=www.job-room.ch'));
  assert.ok(!isRavPage('kaputt'));
  assert.ok(!isRavPage(undefined));
});

test('start opens one tab on the form', async () => {
  const t = setup();
  assert.deepEqual(await t.run.start({ ids: ['a', 'b'] }), { geoeffnet: 2 });
  assert.equal(t.seen('blank').length, 1);
  assert.deepEqual(t.seen('navigate'), [['navigate', 7, FORM_URL]]);
  assert.deepEqual(t.state().open.map((e) => e.id), ['a', 'b']);
});

test('start reports what is refused and opens nothing', async () => {
  const t = setup({ start: { bereit: [READY[1]], abgelehnt: [{ id: 'a', firma: 'Muster AG', grund: 'Schon im RAV eingetragen.' }] } });
  const answer = await t.run.start({ ids: ['a', 'b'] });
  assert.equal(answer.abgelehnt.length, 1);
  assert.equal(t.seen('blank').length, 0);
  assert.equal(t.state(), null);
});

test('a second start brings the running tab forward', async () => {
  const t = setup();
  await t.run.start({ ids: ['a'] });
  const answer = await t.run.start({ ids: ['b'] });
  assert.match(answer.fehler, /läuft schon/);
  assert.deepEqual(t.seen('activate'), [['activate', 7]]);
  assert.equal(t.seen('blank').length, 1);
});

test('a start after the tab vanished begins anew', async () => {
  const t = setup();
  await t.run.start({ ids: ['a'] });
  t.run.tabs.exists = async () => false;
  assert.deepEqual(await t.run.start({ ids: ['b'] }), { geoeffnet: 2 });
});

test('start needs a list of ids', async () => {
  const t = setup();
  await assert.rejects(t.run.start({ ids: 'a' }));
  await assert.rejects(t.run.start({}));
});

test('scripts go only into the tab of the run and only on Job-Room', async () => {
  const t = setup();
  await t.run.loaded(7, PAGE);
  assert.equal(t.seen('inject').length, 0, 'no run yet');
  await t.run.start({ ids: ['a'] });
  await t.run.loaded(8, PAGE);
  await t.run.loaded(7, 'https://login.example.org/');
  assert.equal(t.seen('inject').length, 0);
  await t.run.loaded(7, PAGE);
  assert.deepEqual(t.seen('inject'), [['inject', 7]]);
});

test('another load of the same page keeps the bar: only a new script says it waits', async () => {
  const t = setup();
  await t.run.start({ ids: ['a'] });
  await t.run.report(7, { id: 'a', hinweise: ['Pensum selbst wählen.'], geaendert: false });
  await t.run.loaded(7, PAGE);
  assert.deepEqual(t.lastBar().hinweise, ['Pensum selbst wählen.']);
  await t.run.waiting(7);
  assert.deepEqual(t.lastBar().knoepfe, ['rav_stoppen']);
  await assert.rejects(t.run.waiting(8));
});

test('a page that cannot be injected does not break the run', async () => {
  const t = setup();
  await t.run.start({ ids: ['a'] });
  t.run.tabs.inject = async () => { throw new Error('Cannot access'); };
  await t.run.loaded(7, PAGE);
  assert.equal(t.state().open.length, 2);
});

test('the values are those of the entry at the front of the queue, for its tab only', async () => {
  const t = setup();
  await t.run.start({ ids: ['a', 'b'] });
  assert.deepEqual(await t.run.values(7), { id: 'a', werte: { company: 'a' } });
  await assert.rejects(t.run.values(8));
  assert.deepEqual(t.asked('/api/rav/angaben').at(-1)[2], { id: 'a' });
});

test('values the app refuses show in the bar and the next can be taken', async () => {
  const t = setup();
  await t.run.start({ ids: ['a'] });
  t.answers['/api/rav/angaben'] = () => { throw new Error('Schon im RAV eingetragen.'); };
  const answer = await t.run.values(7);
  assert.equal(answer.fehler, 'Schon im RAV eingetragen.');
  assert.equal(t.lastBar().fehler, true);
  assert.deepEqual(t.lastBar().knoepfe, ['rav_ueberspringen', 'rav_stoppen']);
});

test('after filling, the bar says the person saves, and offers the way out', async () => {
  const t = setup();
  await t.run.start({ ids: ['a', 'b'] });
  await t.run.report(7, { id: 'a', hinweise: ['Pensum selbst wählen.'], geaendert: false });
  const bar = t.lastBar();
  assert.match(bar.text, /1 von 2/);
  assert.match(bar.text, /Muster AG/);
  assert.match(bar.text, /Speichern/);
  assert.deepEqual(bar.hinweise, ['Pensum selbst wählen.']);
  assert.deepEqual(bar.knoepfe, ['rav_ja', 'rav_formular', 'rav_ueberspringen', 'rav_stoppen']);
  assert.equal(bar.id, 'a', 'the buttons say which entry they mean');
  assert.equal(bar.farben, 'rav');
  assert.equal(bar.aufmerksamkeit, true);
});

test('a changed form is reported in words, and nothing was filled', async () => {
  const t = setup();
  await t.run.start({ ids: ['a'] });
  await t.run.report(7, { id: 'a', hinweise: [], geaendert: true });
  const bar = t.lastBar();
  assert.equal(bar.fehler, true);
  assert.match(bar.text, /anders aus/);
  assert.deepEqual(bar.knoepfe, ['rav_ja', 'rav_formular', 'rav_ueberspringen', 'rav_stoppen']);
});

test('a report about another entry changes nothing', async () => {
  const t = setup();
  await t.run.start({ ids: ['a', 'b'] });
  await t.run.report(7, { id: 'b', hinweise: [], geaendert: false });
  assert.equal(t.seen('bar').length, 0);
});

test('saving marks the entry, then the next form opens; the last one ends the run', async () => {
  const t = setup();
  await t.run.start({ ids: ['a', 'b'] });
  await t.run.entered(7, 'a');
  assert.deepEqual(t.asked('/api/rav/eingetragen'), [['ask', '/api/rav/eingetragen', { id: 'a' }]]);
  assert.deepEqual(t.state().open.map((e) => e.id), ['b']);
  assert.equal(t.seen('navigate').length, 2);
  assert.match(t.lastBar().text, /Beispiel GmbH/);
  await t.run.entered(7, 'b');
  assert.equal(t.state(), null);
  assert.match(t.seen('end')[0][1], /2 eingetragen/);
  assert.equal(t.seen('navigate').length, 2, 'the last form stays open');
});

test('a late or repeated message about an entry marks nothing twice', async () => {
  const t = setup();
  await t.run.start({ ids: ['a', 'b'] });
  await t.run.entered(7, 'a');
  await t.run.entered(7, 'a');
  assert.equal(t.asked('/api/rav/eingetragen').length, 1);
  assert.deepEqual(t.state().open.map((e) => e.id), ['b']);
});

test('messages from another tab are refused', async () => {
  const t = setup();
  await t.run.start({ ids: ['a'] });
  await assert.rejects(t.run.entered(8, 'a'));
  await assert.rejects(t.run.skip(8, 'a'));
  await assert.rejects(t.run.stop(8));
  assert.equal(t.state().open.length, 2);
});

test('a second click on the bar does not hit the next entry', async () => {
  const t = setup();
  await t.run.start({ ids: ['a', 'b'] });
  await Promise.all([t.run.entered(7, 'a'), t.run.entered(7, 'a')]);
  assert.equal(t.asked('/api/rav/eingetragen').length, 1);
  assert.deepEqual(t.state().open.map((e) => e.id), ['b']);
  assert.equal(t.state().entered, 1);
});

test('a second click on skip does not drop the next entry', async () => {
  const t = setup();
  await t.run.start({ ids: ['a', 'b'] });
  await Promise.all([t.run.skip(7, 'a'), t.run.skip(7, 'a')]);
  assert.deepEqual(t.state().open.map((e) => e.id), ['b']);
  assert.equal(t.state().skipped, 1);
});

test('a click without an entry marks nothing', async () => {
  const t = setup();
  await t.run.start({ ids: ['a'] });
  await t.run.entered(7);
  await t.run.skip(7);
  assert.equal(t.asked('/api/rav/eingetragen').length, 0);
  assert.equal(t.state().open.length, 2);
});

test('when the app cannot record it, the entry stays and the bar says so', async () => {
  const t = setup();
  await t.run.start({ ids: ['a'] });
  t.answers['/api/rav/eingetragen'] = () => { throw new Error('Die App läuft nicht.'); };
  await t.run.entered(7, 'a');
  assert.equal(t.state().open.length, 2);
  assert.equal(t.lastBar().fehler, true);
  assert.match(t.lastBar().text, /nicht vermerkt/);
  assert.ok(t.lastBar().knoepfe.includes('rav_ja'));
  assert.equal(t.seen('end').length, 0);
});

test('skipping marks nothing', async () => {
  const t = setup();
  await t.run.start({ ids: ['a', 'b'] });
  await t.run.skip(7, 'a');
  assert.equal(t.asked('/api/rav/eingetragen').length, 0);
  assert.deepEqual(t.state().open.map((e) => e.id), ['b']);
  await t.run.skip(7, 'b');
  assert.match(t.seen('end')[0][1], /2 übersprungen/);
});

test('without a form the bar asks to log in and offers the way back', async () => {
  const t = setup();
  await t.run.start({ ids: ['a'] });
  await t.run.noForm(7);
  assert.match(t.lastBar().text, /anmelden/);
  assert.deepEqual(t.lastBar().knoepfe, ['rav_formular', 'rav_stoppen']);
  await t.run.toForm(7);
  assert.deepEqual(t.seen('navigate').at(-1), ['navigate', 7, FORM_URL]);
});

test('stopping ends the run and leaves the tab', async () => {
  const t = setup();
  await t.run.start({ ids: ['a', 'b'] });
  await t.run.stop(7);
  assert.equal(t.state(), null);
  assert.equal(t.seen('end').length, 1);
  assert.deepEqual(await t.run.values(7).catch(() => 'refused'), 'refused');
});

test('closing the tab ends the run; another tab closing does not', async () => {
  const t = setup();
  await t.run.start({ ids: ['a'] });
  await t.run.closed(8);
  assert.ok(t.state());
  await t.run.closed(7);
  assert.equal(t.state(), null);
});

// Who may ask

test('only the app starts a run, only the script on Job-Room talks to it', () => {
  assert.ok(ALLOWED.app.has('rav-starten'));
  assert.ok(!ALLOWED.popup.has('rav-starten'));
  for (const action of ['rav-wartet', 'rav-daten', 'rav-stand', 'rav-gespeichert', 'rav-kein-formular', 'rav-eingetragen', 'rav-ueberspringen', 'rav-stoppen', 'rav-zum-formular']) {
    assert.ok(RAV_ACTIONS.has(action), action);
  }
  const good = { id: 'x', tab: { id: 7 }, frameId: 0, url: PAGE };
  assert.ok(isRavSender(good, 'x'));
  assert.ok(!isRavSender({ ...good, id: 'y' }, 'x'));
  assert.ok(!isRavSender({ ...good, frameId: 3 }, 'x'));
  assert.ok(!isRavSender({ ...good, url: 'https://firma.ch/' }, 'x'));
  assert.ok(!isRavSender({ ...good, tab: undefined }, 'x'));
  assert.ok(!isRavSender(null, 'x'));
});

test('nothing on the way to Job-Room knows the AI or the save button', () => {
  for (const file of ['lib/rav.js', 'form/rav-fields.js', 'form/rav-filler.js']) {
    const source = readFileSync(new URL(`../${file}`, import.meta.url), 'utf8');
    assert.ok(!/formular-ki|\/felder|\.submit\(|requestSubmit/.test(source), file);
  }
});
