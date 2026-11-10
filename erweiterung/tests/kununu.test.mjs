// Reading kununu on the person's click (G35, #189): score and number of reviews from schema.org AggregateRating,
// candidates from a search page, nothing from a page without that data. Invented saved pages in tests/fixtures.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { checkCompany, companyLink, interpret, searchUrl, structuredData } from '../lib/kununu.js';

const LINK = 'https://www.kununu.com/ch/muster-industrie';

/** A saved page as structuredData returns it from the tab: its address and the texts of its JSON-LD blocks. */
function page(file, url) {
  const html = readFileSync(new URL(`./fixtures/${file}`, import.meta.url), 'utf8');
  const structured = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  return { url, structured };
}

const companyPage = (wert) => ({ url: LINK, structured: [JSON.stringify({ '@type': 'Organization', name: 'Muster AG', aggregateRating: wert })] });

test('the search goes to kununu.com with nothing but the company name', () => {
  assert.equal(searchUrl('Muster Industrie AG'), 'https://www.kununu.com/ch/search?q=Muster%20Industrie%20AG');
  assert.equal(searchUrl('Müller & Söhne', 'de'), 'https://www.kununu.com/de/search?q=M%C3%BCller%20%26%20S%C3%B6hne');
});

test('only a company page on kununu.com counts as a link', () => {
  assert.equal(companyLink('https://www.kununu.com/ch/muster-industrie?utm=x#top'), LINK);
  assert.equal(companyLink('https://www.kununu.com/de/muster-industrie/kommentare'), 'https://www.kununu.com/de/muster-industrie/kommentare');
  for (const other of ['https://www.kununu.com/ch/search?q=x', 'https://www.kununu.com/at/muster', 'http://www.kununu.com/ch/muster',
    'https://kununu.com.example.ch/ch/muster', 'https://www.example.ch/ch/muster', 'javascript:alert(1)', '', null]) {
    assert.equal(companyLink(other), null, other);
  }
});

test('a company page gives score and number of reviews', () => {
  assert.deepEqual(interpret(page('kununu-firma.html', LINK)), { art: 'firma', zustand: 'gefunden', wert: 3.8, bewertungen: 214, link: LINK });
});

test('a company page without a rating has no reviews yet', () => {
  const url = 'https://www.kununu.com/ch/kleinwerk-muster';
  assert.deepEqual(interpret(page('kununu-firma-ohne-bewertungen.html', url)), { art: 'firma', zustand: 'keine', link: url });
  assert.equal(interpret(companyPage({ ratingValue: 4, reviewCount: 0 })).zustand, 'keine');
});

test('the rating may come as numbers, with a comma, as ratingCount or as an EmployerAggregateRating', () => {
  assert.equal(interpret(companyPage({ ratingValue: 4.2, ratingCount: 12 })).wert, 4.2);
  assert.equal(interpret(companyPage({ ratingValue: '4,2', reviewCount: '1’312' })).bewertungen, 1312);
  const employer = { url: LINK, structured: [JSON.stringify({ '@type': 'EmployerAggregateRating', ratingValue: '3.1', ratingCount: '57',
    itemReviewed: { '@type': 'Organization', name: 'Muster AG' } })] };
  assert.deepEqual(interpret(employer), { art: 'firma', zustand: 'gefunden', wert: 3.1, bewertungen: 57, link: LINK });
});

test('a rating on another scale or out of range is not read, not converted', () => {
  assert.equal(interpret(companyPage({ ratingValue: '8', bestRating: '10', reviewCount: '20' })), null);
  assert.equal(interpret(companyPage({ ratingValue: '5.4', reviewCount: '20' })), null);
  assert.equal(interpret(companyPage({ ratingValue: 'gut', reviewCount: '20' })), null);
});

test('a search page lists its companies on kununu as candidates', () => {
  const url = searchUrl('Beispiel Holding');
  assert.deepEqual(interpret(page('kununu-suche-mehrere.html', url)), { art: 'suche', kandidaten: [
    { name: 'Beispiel Holding AG', link: 'https://www.kununu.com/ch/beispiel-holding', ort: 'Zürich', bewertungen: 41 },
    { name: 'Beispiel Holding Services GmbH', link: 'https://www.kununu.com/ch/beispiel-holding-services', ort: 'Basel' },
    { name: 'Beispiel Holding Schweiz', link: 'https://www.kununu.com/ch/beispiel-holding-schweiz' },
  ] });
  assert.deepEqual(interpret(page('kununu-suche-keine.html', searchUrl('Testlogistik'))), { art: 'suche', kandidaten: [] });
});

test('a verification page, broken data or no data at all gives nothing', () => {
  assert.equal(interpret(page('kununu-pruefung.html', LINK)), null);
  assert.equal(interpret(page('kununu-pruefung.html', searchUrl('Muster'))), null);
  assert.equal(interpret({ url: LINK, structured: ['{kein json'] }), null);
  assert.equal(interpret({ url: 'https://www.example.ch/', structured: page('kununu-firma.html', LINK).structured }), null);
  assert.equal(interpret(null), null);
});

/** A fake tab: each address gives a saved page; it remembers what was opened. */
function tab(pages) {
  const opened = [];
  const open = async (url) => {
    opened.push(url);
    const [file, finalUrl] = pages[url] || ['kununu-pruefung.html', url];
    return page(file, finalUrl || url);
  };
  return { open, opened };
}

test('one company found on kununu.com/ch is opened and read', async () => {
  const { open, opened } = tab({ [searchUrl('Muster Industrie AG')]: ['kununu-suche-eine.html'], [LINK]: ['kununu-firma.html'] });
  assert.deepEqual(await checkCompany({ name: 'Muster Industrie AG' }, open),
    { zustand: 'gefunden', wert: 3.8, bewertungen: 214, link: LINK });
  assert.deepEqual(opened, [searchUrl('Muster Industrie AG'), LINK]);
});

test('an assigned page is read directly, without a search', async () => {
  const { open, opened } = tab({ [LINK]: ['kununu-firma.html'] });
  assert.equal((await checkCompany({ name: 'Muster Industrie AG', link: LINK }, open)).wert, 3.8);
  assert.deepEqual(opened, [LINK]);
});

test('several companies go to the person to choose, even when one name fits exactly', async () => {
  const { open, opened } = tab({ [searchUrl('Beispiel Holding AG')]: ['kununu-suche-mehrere.html'] });
  const reading = await checkCompany({ name: 'Beispiel Holding AG' }, open);
  assert.equal(reading.zustand, 'mehrere');
  assert.equal(reading.kandidaten.length, 3);
  assert.deepEqual(opened, [searchUrl('Beispiel Holding AG')]);
});

test('kununu.com/de is searched only when kununu.com/ch finds nothing', async () => {
  const de = 'https://www.kununu.com/de/muster-industrie';
  const { open, opened } = tab({ [searchUrl('Muster Industrie AG')]: ['kununu-suche-keine.html'],
    [searchUrl('Muster Industrie AG', 'de')]: ['kununu-suche-eine.html'],
    [LINK]: ['kununu-firma.html', de] });
  // The search on /de lists the /ch address here; what counts is the page the tab ends up on.
  const reading = await checkCompany({ name: 'Muster Industrie AG' }, open);
  assert.equal(reading.link, de);
  assert.deepEqual(opened, [searchUrl('Muster Industrie AG'), searchUrl('Muster Industrie AG', 'de'), LINK]);
});

test('nothing on either site means not found', async () => {
  const { open } = tab({ [searchUrl('Testlogistik GmbH')]: ['kununu-suche-keine.html'],
    [searchUrl('Testlogistik GmbH', 'de')]: ['kununu-suche-keine.html'] });
  assert.deepEqual(await checkCompany({ name: 'Testlogistik GmbH' }, open), { zustand: 'nicht_gefunden' });
});

test('a verification page stops the check: nothing is read and nothing else is opened', async () => {
  const { open, opened } = tab({});
  assert.equal(await checkCompany({ name: 'Muster Industrie AG' }, open), null);
  assert.deepEqual(opened, [searchUrl('Muster Industrie AG')]);

  const second = tab({ [searchUrl('Muster Industrie AG')]: ['kununu-suche-eine.html'] });
  assert.equal(await checkCompany({ name: 'Muster Industrie AG' }, second.open), null);
});

test('a link that is not a kununu company page is never opened', async () => {
  const { open, opened } = tab({ [searchUrl('Muster Industrie AG')]: ['kununu-suche-keine.html'],
    [searchUrl('Muster Industrie AG', 'de')]: ['kununu-suche-keine.html'] });
  await checkCompany({ name: 'Muster Industrie AG', link: 'https://www.example.ch/muster' }, open);
  assert.ok(opened.every((url) => url.startsWith('https://www.kununu.com/')), opened.join(' '));
});

test('a company without a name is not searched', async () => {
  const { open, opened } = tab({});
  await assert.rejects(checkCompany({ name: '  ' }, open), /Firmenname/);
  assert.deepEqual(opened, []);
});

test('the reader in the tab returns the address and at most a few JSON-LD blocks, each cut to a size', () => {
  const blocks = Array.from({ length: 30 }, (_, i) => ({ textContent: i === 0 ? 'x'.repeat(300000) : `{"n":${i}}` }));
  globalThis.document = { querySelectorAll: (selector) => (selector === 'script[type="application/ld+json"]' ? blocks : []) };
  globalThis.location = { href: LINK };
  try {
    const read = structuredData();
    assert.equal(read.url, LINK);
    assert.equal(read.structured.length, 20);
    assert.equal(read.structured[0].length, 200000);
  } finally {
    delete globalThis.document;
    delete globalThis.location;
  }
});

test('only the page of the app starts a check, and the extension may read kununu.com and nothing else of kununu', async () => {
  const { ALLOWED } = await import('../lib/senders.js');
  assert.ok(ALLOWED.app.has('kununu-pruefen'));
  assert.ok(!ALLOWED.popup.has('kununu-pruefen') && !ALLOWED.erlauben.has('kununu-pruefen'));
  const manifest = JSON.parse(readFileSync(new URL('../manifest.json', import.meta.url)));
  assert.deepEqual(manifest.host_permissions.filter((host) => host.includes('kununu')), ['https://www.kununu.com/*']);
  const bridge = readFileSync(new URL('../app-bridge.js', import.meta.url), 'utf8');
  assert.match(bridge, /'kununu-pruefen'/);
});
