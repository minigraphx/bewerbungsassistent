// The run over the tabs of forms (MIN-346), with the app and the browser replaced.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';
import { ApplyRun, MAX_AI_ROUNDS, describeReport, hostOf, mergeReports, sameSite } from '../lib/apply.js';
import { ALLOWED, BAR_ACTIONS, FORM_ACTIONS, senderKind } from '../lib/senders.js';

const READY = { id: 'a', firma: 'Muster', stelle: 'X', link: 'https://firma.ch/stelle' };

function setup({ permission = true, start = { bereit: [READY], abgelehnt: [], doppelt: [] }, report = { felder: 5, gefuellt: 4, offen: 1, einwilligungen: 1, anmeldung: false, hinweise: [] }, followed = {} } = {}) {
  const log = [];
  let forms = {};
  let nextTab = 10;
  let waiting = null;
  const current = { url: 'https://firma.ch/' };
  const answers = {
    '/api/bewerben/start': () => start,
    '/api/bewerben/stand': () => ({}),
    '/api/bewerben/daten': () => ({ werte: { email: 'a@example.ch' }, dateien: [] }),
    '/api/bewerben/abgeschickt': () => ({ stand: 'abgeschickt', hinweise: [] }),
    '/api/bewerben/datei': ({ teil }) => ({ name: 'a.pdf', typ: 'application/pdf', teile: 3, daten: `T${teil}` }),
  };
  const run = new ApplyRun({
    ask: async (method, path, data) => {
      log.push([path, data]);
      return answers[path](data);
    },
    tabs: {
      blank: async () => { log.push(['blank']); return nextTab++; },
      navigate: async (tabId, url) => { log.push(['navigate', tabId, url]); },
      activate: async (tabId) => { log.push(['activate', tabId]); },
      url: async () => current.url,
      inject: async () => { log.push(['inject']); return [{ frameId: 0, documentId: 'D' }]; },
      fill: async (tabId, documents, values, uploads, ki) => { log.push(['fill', documents, ki]); return [{ frameId: 0, result: report }]; },
      follow: async (tabId, documents) => { log.push(['follow', documents]); return followed; },
      bar: async (tabId, balken) => { log.push(['bar', balken]); },
      end: async (tabId, text) => { log.push(['end', text]); },
      permissionPage: async () => { log.push(['permissionPage']); },
    },
    store: { get: async () => forms, set: async (next) => { forms = next; } },
    pending: { get: async () => waiting, set: async (next) => { waiting = next; } },
    hasPermission: async () => permission,
    sleep: async () => {},
  });
  return { run, log, current, answers, forms: () => forms, seen: (name) => log.filter((e) => e[0] === name) };
}

test('hosts only of web pages', () => {
  assert.equal(hostOf('https://a.ch/x'), 'a.ch');
  assert.equal(hostOf('about:blank'), null);
  assert.equal(hostOf('chrome://settings'), null);
  assert.equal(hostOf('kaputt'), null);
});

test('the same site is the host and its subdomains, nothing wider', () => {
  assert.ok(sameSite('www.firma.ch', 'firma.ch'));
  assert.ok(sameSite('jobs.firma.ch', 'firma.ch'));
  assert.ok(sameSite('www.firma.ch', 'jobs.firma.ch'));
  assert.ok(!sameSite('firma.ch', 'firma2.ch'));
  assert.ok(!sameSite('notfirma.ch', 'firma.ch'));
  assert.ok(!sameSite('jobs.firma.ch', 'apply.firma.ch'));
  assert.ok(!sameSite('a.co.uk', 'b.co.uk'));
});

test('the frames of a tab count together', () => {
  const merged = mergeReports({ 0: { felder: 2, gefuellt: 1, offen: 1, hinweise: ['x'] }, 5: { felder: 3, gefuellt: 3, einwilligungen: 1, hinweise: ['x', 'y'] } });
  assert.deepEqual(merged, { felder: 5, gefuellt: 4, offen: 1, einwilligungen: 1, entwuerfe: 0, ki: 0, anmeldung: false, hinweise: ['x', 'y'] });
});

test('the bar says what is open', () => {
  const view = describeReport({ felder: 18, gefuellt: 14, offen: 3, einwilligungen: 1, anmeldung: false, hinweise: [] });
  assert.match(view.text, /14 Felder ausgefüllt, 3 offen, 1 Einwilligung bitte selbst prüfen/);
  assert.ok(view.knoepfe.includes('abgeschickt'));
  assert.match(describeReport({ felder: 1, gefuellt: 1, offen: 0 }).text, /1 Feld ausgefüllt/);
});

test('a login stops it, without the button for sending', () => {
  const view = describeReport({ felder: 0, anmeldung: true });
  assert.match(view.text, /Anmeldung/);
  assert.ok(view.aufmerksamkeit && !view.knoepfe.includes('abgeschickt'));
});

test('tells the app about a new form before the form can ask for files', async () => {
  const { run, log } = setup();

  await run.start({ ids: ['a'] });

  const position = (found) => log.findIndex(found);
  assert.ok(position((e) => e[0] === '/api/bewerben/stand') < position((e) => e[0] === 'navigate'));
});

test('opens the tab of a checked application and then fills it', async () => {
  const { run, log, forms, seen } = setup();

  assert.deepEqual(await run.start({ ids: ['a'] }), { geoeffnet: 1 });
  assert.deepEqual(seen('navigate'), [['navigate', 10, READY.link]]);
  assert.deepEqual(log.find((e) => e[0] === '/api/bewerben/stand')[1], { id: 'a', stand: 'geoeffnet' });

  await run.loaded(10, 'https://firma.ch/stelle');

  assert.equal(seen('fill').length, 1);
  assert.deepEqual(forms()[10].hosts, ['firma.ch']);
  assert.ok(log.some((e) => e[0] === '/api/bewerben/stand' && e[1].stand === 'ausgefuellt'));
  assert.match(seen('bar')[0][1].text, /4 Felder ausgefüllt/);
});

test('the answer to a refused run is passed on and nothing opens', async () => {
  const { run, seen } = setup({ start: { bereit: [], abgelehnt: [{ id: 'a', grund: 'x' }], doppelt: [] } });

  const answer = await run.start({ ids: ['a'] });

  assert.equal(answer.abgelehnt.length, 1);
  assert.equal(seen('blank').length, 0);
});

test('without the permission it asks first and goes on afterwards', async () => {
  const context = setup({ permission: false });

  assert.deepEqual(await context.run.start({ ids: ['a'], bestaetigt: true }), { berechtigung: true });
  assert.equal(context.seen('permissionPage').length, 1);
  assert.equal(context.seen('blank').length, 0);

  context.run.hasPermission = async () => true;
  assert.deepEqual(await context.run.resume(), { geoeffnet: 1 });
  assert.equal(context.seen('blank').length, 1);
  await assert.rejects(context.run.resume());
});

test('an application that is open already gets its tab back', async () => {
  const { run, seen } = setup();
  await run.start({ ids: ['a'] });

  await run.start({ ids: ['a'] });

  assert.equal(seen('blank').length, 1);
  assert.deepEqual(seen('activate'), [['activate', 10]]);
});

test('a second start while one runs opens nothing more', async () => {
  const { run, seen } = setup();

  const answers = await Promise.all([run.start({ ids: ['a'] }), run.start({ ids: ['a'] })]);

  assert.deepEqual(answers, [{ geoeffnet: 1 }, { laeuft: true }]);
  assert.equal(seen('blank').length, 1);
});

test('the bridge in the page of the app answers once, also when injected twice', () => {
  const code = readFileSync(new URL('../app-bridge.js', import.meta.url), 'utf8');
  const listeners = [];
  const context = {
    document: { querySelector: () => ({}), documentElement: { dataset: {} } },
    window: { addEventListener: (type) => listeners.push(type), postMessage: () => {} },
    location: { origin: 'http://127.0.0.1:1' },
    chrome: {
      runtime: { id: 'x', getManifest: () => ({ version: '1' }), connect: () => ({ onMessage: { addListener: () => {} } }) },
    },
  };
  context.globalThis = context;
  const run = () => vm.runInNewContext(code, context);

  run();
  run();
  assert.deepEqual(listeners, ['message']);

  context.chrome.runtime.id = undefined; // the extension was reloaded: the old script no longer counts
  run();
  assert.deepEqual(listeners, ['message', 'message']);
});

test('tabs outside the list are left alone', async () => {
  const { run, seen } = setup();

  await run.loaded(99, 'https://firma.ch/');

  assert.equal(seen('inject').length, 0);
});

test('a redirect on the first load counts, a new address later needs the person', async () => {
  const { run, forms, seen } = setup();
  await run.start({ ids: ['a'] });
  await run.loaded(10, 'https://ats.example/form');
  assert.deepEqual(forms()[10].hosts, ['ats.example']);
  assert.equal(seen('fill').length, 1);

  await run.loaded(10, 'https://webmail.example/inbox');

  assert.equal(seen('fill').length, 1);
  assert.match(seen('bar').at(-1)[1].text, /Neue Adresse: webmail\.example/);
  assert.ok(seen('bar').at(-1)[1].knoepfe.includes('hier'));

  await run.fillHere(10);

  assert.equal(seen('fill').length, 2);
  assert.deepEqual(forms()[10].hosts, ['ats.example', 'webmail.example']);
});

test('the next page of the same address fills without asking', async () => {
  const { run, seen } = setup();
  await run.start({ ids: ['a'] });
  await run.loaded(10, 'https://firma.ch/schritt1');

  await run.loaded(10, 'https://firma.ch/schritt2');

  assert.equal(seen('fill').length, 2);
});

const NO_FORM = { felder: 0, gefuellt: 0, offen: 0, einwilligungen: 0, anmeldung: false, hinweise: [] };

test('follows the link of the ad once; a new address behind it waits for the person', async () => {
  const { run, forms, seen } = setup({ report: NO_FORM, followed: { url: 'https://ats.example/form' } });
  await run.start({ ids: ['a'] });

  await run.loaded(10, 'https://firma.ch/stelle');

  assert.equal(seen('follow').length, 1);
  assert.deepEqual(seen('navigate').at(-1), ['navigate', 10, 'https://ats.example/form']);
  assert.ok(!forms()[10].hosts.includes('ats.example'));
  const fills = seen('fill').length;

  await run.loaded(10, 'https://ats.example/form');

  assert.equal(seen('fill').length, fills);
  assert.match(seen('bar').at(-1)[1].text, /Neue Adresse: ats\.example/);
  await assert.rejects(run.file(10, 'lebenslauf'));

  await run.fillHere(10);

  assert.equal(seen('fill').length, fills + 1);
  assert.equal(seen('follow').length, 1);
});

test('values go only to the documents that were checked', async () => {
  const { run, seen } = setup();
  await run.start({ ids: ['a'] });

  await run.loaded(10, 'https://firma.ch/');

  assert.deepEqual(seen('fill')[0][1], [{ frameId: 0, documentId: 'D' }]);
});

test('a subdomain of the known site fills without asking', async () => {
  const { run, seen } = setup();
  await run.start({ ids: ['a'] });
  await run.loaded(10, 'https://www.firma.ch/');

  await run.loaded(10, 'https://jobs.firma.ch/form');

  assert.equal(seen('fill').length, 2);
});

test('a frame built later gets its turn, on a known address only', async () => {
  const { run, current, seen } = setup();
  await run.start({ ids: ['a'] });
  await run.loaded(10, 'https://firma.ch/');
  assert.equal(seen('fill').length, 1);

  await run.frameLoaded(10);
  assert.equal(seen('fill').length, 2);

  current.url = 'https://evil.example/';
  await run.frameLoaded(10);
  assert.equal(seen('fill').length, 2);

  await run.frameLoaded(99);
  assert.equal(seen('fill').length, 2);
});

test('a failure on a page the tab has left stays silent', async () => {
  const { run, current, seen } = setup();
  await run.start({ ids: ['a'] });
  run.tabs.inject = async () => { throw new Error('Frame gone'); };
  current.url = 'https://other.example/';

  await run.loaded(10, 'https://firma.ch/');

  assert.equal(seen('bar').length, 0);
});

test('the state reaches the app, or is tried again with the next report', async () => {
  const context = setup();
  await context.run.start({ ids: ['a'] });
  context.answers['/api/bewerben/stand'] = () => { throw new Error('weg'); };
  await context.run.loaded(10, 'https://firma.ch/');
  assert.equal(context.forms()[10].ausgefuellt, false);

  context.answers['/api/bewerben/stand'] = () => ({});
  await context.run.frameReport(10, 3, { felder: 3, gefuellt: 3 });

  assert.equal(context.forms()[10].ausgefuellt, true);
});

test('a link to something else than the web is not followed', async () => {
  const { run, seen } = setup({ report: NO_FORM, followed: { url: 'file:///etc/passwd' } });
  await run.start({ ids: ['a'] });

  await run.loaded(10, 'https://firma.ch/stelle');

  assert.equal(seen('navigate').length, 1);
  assert.match(seen('bar').at(-1)[1].text, /kein Formular/);
});

test('without a form and a link it tells the person', async () => {
  const { run, seen } = setup({ report: NO_FORM });
  await run.start({ ids: ['a'] });

  await run.loaded(10, 'https://firma.ch/stelle');

  const bar = seen('bar').at(-1)[1];
  assert.match(bar.text, /kein Formular/);
  assert.ok(bar.aufmerksamkeit);
});

test('a login is not followed away from', async () => {
  const { run, seen } = setup({ report: { ...NO_FORM, anmeldung: true } });
  await run.start({ ids: ['a'] });

  await run.loaded(10, 'https://firma.ch/login');

  assert.equal(seen('follow').length, 0);
  assert.match(seen('bar').at(-1)[1].text, /Anmeldung/);
});

test('a later step of the form reports and updates the bar', async () => {
  const { run, seen } = setup();
  await run.start({ ids: ['a'] });
  await run.loaded(10, 'https://firma.ch/');

  await run.frameReport(10, 7, { felder: 4, gefuellt: 4, offen: 0 });

  assert.match(seen('bar').at(-1)[1].text, /8 Felder ausgefüllt/);
});

test('reports at the same time do not overwrite each other', async () => {
  const { run, forms } = setup();
  await run.start({ ids: ['a'] });
  await run.loaded(10, 'https://firma.ch/');

  await Promise.all([1, 2, 3, 4].map((frame) => run.frameReport(10, frame, { felder: 1 })));

  assert.equal(Object.keys(forms()[10].frames).length, 5);
});

test('a file comes in parts and only for the application of the tab', async () => {
  const { run, log } = setup();
  await run.start({ ids: ['a'] });

  const file = await run.file(10, 'lebenslauf');

  assert.deepEqual(file, { name: 'a.pdf', typ: 'application/pdf', daten: 'T0T1T2' });
  assert.ok(log.filter((e) => e[0] === '/api/bewerben/datei').every((e) => e[1].id === 'a'));
  await assert.rejects(run.file(99, 'lebenslauf'));
});

test('a dispatch is recorded only when the person says so, and ends the tab', async () => {
  const { run, log, forms, seen } = setup();
  await run.start({ ids: ['a'] });
  await run.loaded(10, 'https://firma.ch/');
  assert.ok(!log.some((e) => e[0] === '/api/bewerben/abgeschickt'));

  await run.sent(10);

  assert.deepEqual(log.find((e) => e[0] === '/api/bewerben/abgeschickt')[1], { id: 'a' });
  assert.deepEqual(forms(), {});
  assert.match(seen('end')[0][1], /Versand erfasst/);
});

test('a failed dispatch stays visible and the tab stays in the list', async () => {
  const { run, forms, seen } = setup();
  await run.start({ ids: ['a'] });
  run.ask = async () => { throw new Error('Lebenslauf-PDF fehlt'); };

  await run.sent(10);

  assert.ok(forms()[10]);
  assert.equal(seen('bar').at(-1)[1].fehler, true);
});

test('stopping and closing take the tab out of the list', async () => {
  const { run, forms, seen } = setup();
  await run.start({ ids: ['a'] });

  await run.stop(10);
  assert.deepEqual(forms(), {});
  assert.equal(seen('end').length, 1);

  await run.start({ ids: ['a'] });
  await run.closed(11);
  assert.deepEqual(forms(), {});
});

test('the app fails while filling: the bar says so', async () => {
  const { run, seen } = setup();
  await run.start({ ids: ['a'] });
  run.ask = async () => { throw new Error('Die App antwortet nicht.'); };

  await run.loaded(10, 'https://firma.ch/');

  assert.equal(seen('bar').at(-1)[1].text, 'Die App antwortet nicht.');
});

test('only the page of the app starts a run, and only the permission page goes on', () => {
  const id = 'abc';
  const page = senderKind({ id, url: `chrome-extension://${id}/erlauben.html`, tab: { id: 1 } }, id, null);
  assert.equal(page, 'erlauben');
  assert.ok(ALLOWED.erlauben.has('bewerben-weiter') && !ALLOWED.erlauben.has('bewerben-starten'));
  assert.ok(ALLOWED.app.has('bewerben-starten') && !ALLOWED.popup.has('bewerben-starten'));
  assert.equal(senderKind({ id, url: `chrome-extension://${id}/popup.html`, tab: { id: 1 } }, id, null), null);
  assert.equal(senderKind({ id, url: 'https://firma.ch/', tab: { id: 1 } }, id, 'http://127.0.0.1:5000/'), null);
  for (const action of [...FORM_ACTIONS, ...BAR_ACTIONS]) {
    assert.ok(!ALLOWED.app.has(action) && !ALLOWED.popup.has(action), action);
  }
});

const unclear = (ref, label) => ({ ref, art: 'unklar', label, name: '', hinweis: '' });

async function withForm(helpAnswers) {
  const setup_ = setup();
  const { run, log } = setup_;
  await run.start({ ids: ['a'] });
  const forms = await run.store.get();
  const tabId = Number(Object.keys(forms)[0]);
  const original = run.ask;
  const asked = [];
  run.ask = async (method, path, data) => {
    if (path !== '/api/bewerben/felder') return original(method, path, data);
    asked.push(data);
    const reply = helpAnswers.shift();
    if (reply instanceof Error) throw reply;
    return reply;
  };
  return { run, tabId, asked, log };
}

test('help for fields asks the app for this application', async () => {
  const { run, tabId, asked } = await withForm([{ zuordnung: { f1: 'city' }, entwuerfe: { f2: 'Ein Entwurf.' }, hinweise: [] }]);

  const answer = await run.assist(tabId, [unclear('f1', 'Wohngemeinde'), { ...unclear('f2', 'Warum?'), art: 'frage' }]);

  assert.deepEqual(answer, { zuordnung: { f1: 'city' }, entwuerfe: { f2: 'Ein Entwurf.' }, hinweise: [] });
  assert.equal(asked[0].id, 'a');
  assert.equal(asked[0].felder.length, 2);
});

test('a field asked before is answered without another call, under its new reference', async () => {
  const { run, tabId, asked } = await withForm([{ zuordnung: { f1: 'city' }, entwuerfe: {}, hinweise: [] }]);

  await run.assist(tabId, [unclear('f1', 'Wohngemeinde'), unclear('f2', 'Rätsel')]);
  const again = await run.assist(tabId, [unclear('f9', 'Wohngemeinde'), unclear('f8', 'Rätsel')]);

  assert.equal(asked.length, 1);
  assert.deepEqual(again.zuordnung, { f9: 'city' });
});

test('only the new fields of a page cost a call', async () => {
  const { run, tabId, asked } = await withForm([
    { zuordnung: { f1: 'city' }, entwuerfe: {}, hinweise: [] },
    { zuordnung: { f4: 'notice' }, entwuerfe: {}, hinweise: [] },
  ]);

  await run.assist(tabId, [unclear('f1', 'Wohngemeinde')]);
  const second = await run.assist(tabId, [unclear('f3', 'Wohngemeinde'), unclear('f4', 'Frist')]);

  assert.deepEqual(asked[1].felder.map((f) => f.ref), ['f4']);
  assert.deepEqual(second.zuordnung, { f3: 'city', f4: 'notice' });
});

test('after a failing step the unanswered fields can be asked again', async () => {
  const { run, tabId, asked } = await withForm([
    { zuordnung: {}, entwuerfe: {}, hinweise: ['Überlastet'], wiederholen: true },
    { zuordnung: { f1: 'city' }, entwuerfe: {}, hinweise: [] },
  ]);

  const first = await run.assist(tabId, [unclear('f1', 'Wohngemeinde')]);
  const second = await run.assist(tabId, [unclear('f1', 'Wohngemeinde')]);

  assert.deepEqual(first.hinweise, ['Überlastet']);
  assert.deepEqual(second.zuordnung, { f1: 'city' });
  assert.deepEqual(second.hinweise, []);
  assert.equal(asked.length, 2);
});

test('a note about the page does not cost another call, and stays after a reload', async () => {
  const { run, tabId, asked } = await withForm([{ zuordnung: {}, entwuerfe: {}, hinweise: ['Auffällige Zeilen'], wiederholen: false }]);

  const first = await run.assist(tabId, [unclear('f1', 'Rätsel')]);
  const again = await run.assist(tabId, [unclear('f7', 'Rätsel')]);

  assert.deepEqual(first.hinweise, ['Auffällige Zeilen']);
  assert.deepEqual(again.hinweise, ['Auffällige Zeilen']);
  assert.equal(asked.length, 1);
});

test('a tab has a limit of calls, so a page cannot run up costs', async () => {
  const replies = Array.from({ length: 30 }, () => ({ zuordnung: {}, entwuerfe: {}, hinweise: [] }));
  const { run, tabId, asked } = await withForm(replies);

  let last;
  for (let n = 0; n < 30; n += 1) last = await run.assist(tabId, [unclear(`f${n}`, `Feld ${n}`)]);

  assert.equal(asked.length, MAX_AI_ROUNDS);
  assert.equal(last.hinweise.length, 1);
  assert.deepEqual(last.zuordnung, {});
});

test('no help on a tab that left the list or waits for the person on a new address', async () => {
  const { run, tabId, asked } = await withForm([]);
  await run.updateTab(tabId, (entry) => ({ ...entry, fremd: 'andere.ch' }));

  await assert.rejects(run.assist(tabId, [unclear('f1', 'x')]));
  await assert.rejects(run.assist(999, [unclear('f1', 'x')]));
  await assert.rejects(run.assist(tabId, 'kein Array'));
  assert.equal(asked.length, 0);
});

test('the bar counts drafts and says when the AI is at work', () => {
  const merged = mergeReports({ 0: { felder: 5, gefuellt: 3, offen: 1, einwilligungen: 0, entwuerfe: 2, ki: 1 } });

  assert.equal(merged.entwuerfe, 2);
  assert.match(describeReport(merged).text, /2 Textentwürfe bitte prüfen/);
  assert.match(describeReport(merged).text, /KI/);
  assert.doesNotMatch(describeReport({ ...merged, ki: 0 }).text, /KI/);
});

test('whether the AI may help comes from the app and goes to the frame', async () => {
  const { run, log } = setup({});
  const original = run.ask;
  run.ask = async (method, path, data) => (path === '/api/bewerben/daten' ? { werte: {}, dateien: [], ki: true } : original(method, path, data));
  await run.start({ ids: ['a'] });
  const tabId = Number(Object.keys(await run.store.get())[0]);

  await run.loaded(tabId, 'https://firma.ch/form');

  assert.equal(log.find(([step]) => step === 'fill').at(-1), true);
});

test('the frame may ask for help', () => {
  assert.ok(FORM_ACTIONS.has('formular-ki'));
});
