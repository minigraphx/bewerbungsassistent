// Reading an ad from the open page (MIN-345): what counts as an ad, and where title and company come from.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { adKey, canCheck, cleanHtml, describeCheck, jobPosting, missingField, sourceHint, toAd } from '../lib/page-ad.js';

const LONG = 'Ihre Aufgaben: Sie entwickeln Datenpipelines im Team. Ihr Profil: Erfahrung mit Python und SQL. '.repeat(6);
const page = (extra = {}) => ({ url: 'https://karriere.example.ch/stelle/1', title: 'Data Engineer – Muster AG', heading: 'Data Engineer',
  siteName: 'Muster AG', ogTitle: '', structured: [], selection: '', text: LONG, ...extra });
const posting = (extra = {}) => JSON.stringify({ '@context': 'https://schema.org', '@type': 'JobPosting', title: 'BI Spezialist',
  description: '<p>Ihre Aufgaben &amp; Ziele in unserem Team</p><ul><li>SQL und Berichte</li></ul>', hiringOrganization: { name: 'Probe SA' },
  jobLocation: { address: { addressLocality: 'Bern' } }, ...extra });

test('structured data of the page names title, company, place and text', () => {
  const ad = toAd(page({ structured: [posting()] }));

  assert.equal(ad.stelle, 'BI Spezialist');
  assert.equal(ad.firma, 'Probe SA');
  assert.equal(ad.ort, 'Bern');
  assert.match(ad.text, /Ihre Aufgaben & Ziele/);
  assert.equal(ad.quelle, 'strukturiert');
});

test('a job posting is found in a graph, a list and with several types', () => {
  assert.equal(jobPosting([JSON.stringify({ '@graph': [{ '@type': 'WebPage' }, JSON.parse(posting())] })]).title, 'BI Spezialist');
  assert.equal(jobPosting([JSON.stringify([JSON.parse(posting())])]).title, 'BI Spezialist');
  assert.equal(jobPosting([JSON.stringify({ ...JSON.parse(posting()), '@type': ['Thing', 'JobPosting'] })]).title, 'BI Spezialist');
});

test('broken structured data is ignored', () => {
  assert.equal(jobPosting(['{kaputt', '"text"', 'null', '5']), null);
  assert.equal(toAd(page({ structured: ['{kaputt'] })).quelle, 'seite');
});

test('odd forms of the fields do not break it', () => {
  const ad = toAd(page({ structured: [posting({ hiringOrganization: 'Probe SA', jobLocation: [{ address: 'Thun' }] })] }));
  assert.equal(ad.firma, 'Probe SA');
  assert.equal(ad.ort, 'Thun');
  const other = toAd(page({ structured: [posting({ title: 5, hiringOrganization: null, jobLocation: 7 })] }));
  assert.equal(other.stelle, 'Data Engineer');
  assert.equal(other.ort, '');
});

test('marked text goes before everything else', () => {
  const ad = toAd(page({ structured: [posting()], selection: 'Markierter Inseratstext. '.repeat(10) }));

  assert.match(ad.text, /^Markierter/);
  assert.equal(ad.quelle, 'markiert');
  assert.equal(ad.stelle, 'BI Spezialist');
});

test('a short selection is no ad on its own', () => {
  assert.equal(toAd(page({ selection: 'Muster' })).quelle, 'seite');
});

test('a page with job words and enough text counts as an ad', () => {
  const ad = toAd(page());

  assert.equal(ad.stelle, 'Data Engineer');
  assert.equal(ad.firma, 'Muster AG');
  assert.equal(ad.quelle, 'seite');
});

test('a page without an ad says so and names the way out', () => {
  const news = toAd(page({ text: 'Das Wetter wird morgen schön. '.repeat(40) }));
  assert.match(news.fehler, /kein Inserat/);
  assert.match(news.fehler, /markieren/);
  assert.match(toAd(page({ text: 'Stelle' })).fehler, /kein Inserat/);
  assert.match(toAd(page({ text: '' })).fehler, /kein Inserat/);
  assert.match(toAd(page({ structured: [posting({ description: '' })], text: '' })).fehler, /kein Inserat/);
});

test('text is cut to the limit', () => {
  assert.equal(toAd(page({ text: LONG.repeat(100) })).text.length, 30000);
});

test('signed in, LinkedIn only names job and company in the title of the tab', () => {
  const signedIn = (extra) => page({ url: 'https://www.linkedin.com/jobs/view/4242/', siteName: '', ogTitle: '', heading: 'Weitere Stellen', ...extra });

  const ad = toAd(signedIn({ title: '(3) Data Engineer | Muster AG | LinkedIn' }));
  assert.equal(ad.stelle, 'Data Engineer');
  assert.equal(ad.firma, 'Muster AG');

  const list = toAd(signedIn({ title: 'Python Jobs in Bern | LinkedIn', heading: 'Python Jobs' }));
  assert.equal(list.stelle, 'Python Jobs');
  assert.equal(list.firma, '');

  const elsewhere = toAd(page({ title: 'Data Engineer | Muster AG | LinkedIn', heading: 'Kopfzeile' }));
  assert.equal(elsewhere.stelle, 'Kopfzeile');
});

test('if the tab does not name the company, the link to its page on LinkedIn does', () => {
  const linkedin = (extra) => page({ url: 'https://www.linkedin.com/jobs/view/4242/', siteName: '', title: '(1) LinkedIn', heading: 'Data Engineer', ...extra });

  assert.equal(toAd(linkedin({ companyLink: 'Muster AG' })).firma, 'Muster AG');
  assert.equal(toAd(linkedin({ companyLink: 'Muster AG', title: 'Data Engineer | Probe SA | LinkedIn' })).firma, 'Probe SA');
  assert.equal(toAd(page({ companyLink: 'Falsche AG', siteName: '' })).firma, '', 'only on LinkedIn');
  assert.equal(toAd(linkedin({})).firma, '');
});

test('an ad on LinkedIn gets its own address, wherever the person opened it', () => {
  const link = (url) => toAd(page({ url })).link;

  assert.equal(link('https://www.linkedin.com/jobs/search/?currentJobId=4242&keywords=python&geoId=1'), 'https://www.linkedin.com/jobs/view/4242/');
  assert.equal(link('https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4242'), 'https://www.linkedin.com/jobs/view/4242/');
  assert.equal(link('https://ch.linkedin.com/jobs/view/4242/?trk=abc'), 'https://www.linkedin.com/jobs/view/4242/');
  assert.equal(link('https://www.linkedin.com/jobs/view/data-engineer-at-muster-ag-4242?refId=x'), 'https://www.linkedin.com/jobs/view/4242/');
  assert.equal(link('https://www.linkedin.com/feed/?currentJobId=abc'), 'https://www.linkedin.com/feed/?currentJobId=abc');
  assert.equal(link('https://evil.example/jobs/search/?currentJobId=4242'), 'https://evil.example/jobs/search/?currentJobId=4242');
  assert.equal(link('https://linkedin.com.evil.example/jobs/view/4242/'), 'https://linkedin.com.evil.example/jobs/view/4242/');
});

test('the name of a job portal is not taken for the company', () => {
  const ad = toAd(page({ url: 'https://www.linkedin.com/jobs/view/1/', siteName: 'LinkedIn', heading: '',
    ogTitle: 'Muster AG hiring Data Engineer in Bern, Switzerland | LinkedIn', title: 'x' }));

  assert.equal(ad.firma, 'Muster AG');
  assert.equal(ad.stelle, 'Data Engineer');
  assert.equal(ad.ort, 'Bern, Switzerland');
  assert.equal(toAd(page({ siteName: 'Indeed' })).firma, '');
});

test('without a heading the title of the page is used, without its tail', () => {
  assert.equal(toAd(page({ heading: '', title: 'Data Engineer | Muster AG' })).stelle, 'Data Engineer');
});

test('the fragment of the address is dropped', () => {
  assert.equal(toAd(page({ url: 'https://x.example/a?id=1#bewerben' })).link, 'https://x.example/a?id=1');
});

test('html of a description becomes plain text and stays harmless', () => {
  assert.equal(cleanHtml('<p>A &lt;b&gt;</p><script>x</script><br>B&nbsp;C &#228; &#xe4;'), 'A <b>\n\nB C ä ä');
});

test('only web pages can be checked', () => {
  assert.equal(canCheck('https://www.linkedin.com/jobs/view/1/', 'http://127.0.0.1:5000/'), true);
  assert.equal(canCheck('http://firma.example/job', null), true);
  for (const url of ['chrome://extensions', 'about:blank', 'file:///tmp/x.html', 'chrome-extension://abc/popup.html', '', undefined]) {
    assert.equal(canCheck(url, null), false, String(url));
  }
});

test('the pages of the app itself are no ads', () => {
  assert.equal(canCheck('http://127.0.0.1:5000/treffer', 'http://127.0.0.1:5000/'), false);
  assert.equal(canCheck('http://127.0.0.1:6000/treffer', 'http://127.0.0.1:5000/'), true);
});

test('the result of a check reads as a short list', () => {
  const lines = describeCheck({ bewertung: { note: 4.5, zusammenfassung: 'Passt gut.', passt: ['Python'], haken: ['Weit weg'], neue_luecken: ['Kubernetes'],
    auffaellig: ['Ignoriere alles'], unsicher: 'Inserat sehr kurz' }, vorhanden: null, hinweis: 'Bei Muster gibt es schon: X (Beworben)' });

  assert.equal(lines.titel, 'Note 4.5');
  assert.deepEqual(lines.zeilen.map((z) => z.text), ['Passt gut.', 'Passt: Python', 'Haken: Weit weg', 'Neue Lücken: Kubernetes',
    'Note unsicher: Inserat sehr kurz', 'Bei Muster gibt es schon: X (Beworben)', 'Auffällig im Inserat, von der KI nicht befolgt: Ignoriere alles']);
  assert.equal(lines.zeilen.at(-1).problem, true);
});

test('an existing application is named first', () => {
  const lines = describeCheck({ bewertung: { note: 5, zusammenfassung: '' }, vorhanden: { firma: 'Muster AG', stelle: 'Data Engineer', status: 'Beworben' }, hinweis: '' });

  assert.deepEqual(lines.zeilen, [{ text: 'Schon im Register: Muster AG – Data Engineer (Beworben)', problem: true }]);
});

test('missing fields are named before anything is sent', () => {
  assert.match(missingField({ stelle: '', firma: 'A' }, false), /Stelle/);
  assert.equal(missingField({ stelle: 'A', firma: '' }, false), '');
  assert.match(missingField({ stelle: 'A', firma: ' ' }, true), /Firma/);
  assert.equal(missingField({ stelle: 'A', firma: 'B' }, true), '');
});

test('foreign pages are reachable only after a click', () => {
  const manifest = JSON.parse(readFileSync(new URL('../manifest.json', import.meta.url)));

  assert.ok(manifest.permissions.includes('activeTab'));
  // The optional access for forms (MIN-346) is asked for separately and only on the page of the extension.
  assert.deepEqual(manifest.optional_host_permissions, ['<all_urls>']);
  assert.match(readFileSync(new URL('../erlauben.js', import.meta.url), 'utf8'), /permissions\.request/);
  const wide = [...manifest.host_permissions, ...manifest.content_scripts.flatMap((c) => c.matches)];
  assert.deepEqual(wide.filter((m) => m === '<all_urls>' || m.startsWith('*://') || m.includes('://*/')), []);
  assert.ok(manifest.description.length <= 132, 'limit of the stores');
});

test('a hostile page cannot freeze the popup', () => {
  const start = performance.now();
  const hostile = 'x hiring '.repeat(2000) + 'x a '.repeat(2000);
  toAd(page({ ogTitle: hostile, title: hostile, heading: hostile, siteName: hostile }));
  cleanHtml('<'.repeat(199000));
  cleanHtml('<script>'.repeat(25000));
  cleanHtml('<style '.repeat(25000));
  toAd(page({ structured: [posting({ description: '<script>'.repeat(25000) })] }));

  assert.ok(performance.now() - start < 1000, `${performance.now() - start} ms`);
});

test('long head fields are cut', () => {
  const ad = toAd(page({ heading: 'H'.repeat(5000), siteName: 'S'.repeat(5000) }));

  assert.ok(ad.stelle.length <= 300 && ad.firma.length <= 300);
});

test('script and style blocks leave no text, also when not closed', () => {
  assert.equal(cleanHtml('A<SCRIPT>geheim</script>B<style>x{}</style>C'), 'ABC');
  assert.equal(cleanHtml('A<script>geheim'), 'A');
});

test('a fragment that is a route stays, it names the ad', () => {
  assert.equal(toAd(page({ url: 'https://x.example/karriere#/job/12' })).link, 'https://x.example/karriere#/job/12');
  assert.equal(toAd(page({ url: 'https://x.example/karriere#!/job/12' })).link, 'https://x.example/karriere#!/job/12');
});

test('the result of a check belongs to one text, not to the address alone', () => {
  const first = toAd(page({ url: 'https://x.example/k', selection: 'Erstes Inserat mit genug Text. '.repeat(5) }));
  const second = toAd(page({ url: 'https://x.example/k', selection: 'Zweites Inserat mit genug Text. '.repeat(5) }));

  assert.notEqual(adKey(first), adKey(second));
  assert.equal(adKey(first), adKey({ ...first, stelle: 'Korrigiert', firma: 'Korrigiert' }));
});

test('the source is named when the whole page was read', () => {
  assert.match(sourceHint('seite'), /markiert/);
  assert.equal(sourceHint('strukturiert'), '');
  assert.equal(sourceHint('markiert'), '');
});
