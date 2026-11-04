// Adapters for apprenticeships (MIN-365): names of professions, and results read from small stand-ins for the pages.
// Selectors and page shapes were checked against the live portals in a background tab of a real browser.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';

const require = createRequire(import.meta.url);
const common = require('../portals/common.js');
const lena = require('../portals/lena.js');
const yousty = require('../portals/yousty.js');

const label = (option) => option.label;
const words = (name) => [...common.professionWords(name)].sort();

test('name in the profile and name on the portal give the same words', () => {
  for (const [ours, theirs] of [
    ['Fachfrau Gesundheit EFZ', 'Fachmann/-frau Gesundheit EFZ'],
    ['Fachmann Betreuung EFZ, Fachrichtung Kinder', 'Fachmann/-frau Betreuung (Kinder) EFZ'],
    ['Assistentin Gesundheit und Soziales EBA', 'Assistent/-in Gesundheit und Soziales EBA'],
    ['Assistentin Gesundheit und Soziales EBA', 'Assistent/in Gesundheit und Soziales EBA'],
    ['Kauffrau EFZ', 'Kaufmann/-frau EFZ'],
    ['Informatikerin EFZ', 'Informatiker/in EFZ'],
    ['Coiffeuse EFZ', 'Coiffeur/-euse EFZ'],
    ['Köchin EFZ', 'Koch/Köchin EFZ'],
  ]) {
    assert.deepEqual(words(ours), words(theirs), ours);
  }
});

const YOUSTY_LABELS = [
  { label: 'Fachmann/-frau Betreuung (FaBe) EFZ', id: 'plain' },
  { label: 'Fachmann/-frau Betreuung (FaBe) EFZ Generalistische Ausbildung', id: 'general' },
  { label: 'Fachmann/-frau Betreuung (FaBe) EFZ Kinder', id: 'children' },
  { label: 'Fachmann/-frau Gesundheit (FaGe) EFZ', id: 'health' },
  { label: 'Fachmann/-frau Bewegungs- und Gesundheitsförderung EFZ', id: 'movement' },
];

test('the plain profession wins over its specialisations, a named specialisation is found', () => {
  assert.equal(common.bestProfession('Fachfrau Betreuung EFZ', YOUSTY_LABELS, label).id, 'plain');
  assert.equal(common.bestProfession('Fachfrau Betreuung EFZ, Fachrichtung Kinder', YOUSTY_LABELS, label).id, 'children');
  assert.equal(common.bestProfession('Fachfrau Gesundheit EFZ', YOUSTY_LABELS, label).id, 'health');
});

test('a profession the portal does not have stays without a match', () => {
  assert.equal(common.bestProfession('Bootbauerin EFZ', YOUSTY_LABELS, label), null);
  assert.equal(common.bestProfession('', YOUSTY_LABELS, label), null);
});

/** Stand-in for a page element: selector → element(s), as far as the adapters ask. */
function element({ text = '', attributes = {}, one = {}, all = {}, className = '' } = {}) {
  return {
    textContent: text,
    className,
    getAttribute: (name) => attributes[name] ?? null,
    querySelector: (selector) => one[selector] ?? null,
    querySelectorAll: (selector) => all[selector] ?? [],
  };
}

function youstyCard({ id = '8690204', chips = ['2027verfügbar', '2028verfügbar', 'Schnupperlehreverfügbar'] } = {}) {
  return element({
    one: {
      'a[href*="/lehrstellen/profile/"]': element({ attributes: { href: `/de-CH/lehrstellen/profile/${id}-fage-bern?x=1` } }),
      '.title': element({ text: 'Fachmann/-frau Gesundheit (FaGe) EFZ' }),
    },
    all: {
      '.availability.available': chips.map((text) => element({ text })),
      '.company-info strong': [element({ text: 'Spital Muster' }), element({ text: 'Bern' })],
    },
  });
}

const QUERY = { keyword: 'Fachfrau Gesundheit EFZ', years: [2027], place: 'Bern', radius: 25 };

test('yousty result as hit, with the wanted years only', () => {
  assert.deepEqual(yousty.toHit(youstyCard(), QUERY), {
    portal: 'yousty', portal_id: '8690204', stelle: 'Fachmann/-frau Gesundheit (FaGe) EFZ', firma: 'Spital Muster', ort: 'Bern',
    link: 'https://www.yousty.ch/de-CH/lehrstellen/profile/8690204-fage-bern', art: 'Lehrstelle',
    beruf: 'Fachfrau Gesundheit EFZ', lehrbeginn: '2027',
  });
  assert.equal(yousty.toHit(youstyCard(), { ...QUERY, years: [] }).lehrbeginn, '2027, 2028');
});

test('yousty: other years, trial apprenticeships and school offers are no hits', () => {
  assert.equal(yousty.toHit(youstyCard({ chips: ['2028verfügbar'] }), QUERY), null);
  assert.equal(yousty.toHit(youstyCard({ chips: ['Schnupperlehreverfügbar'] }), { ...QUERY, years: [] }), null);
  assert.equal(yousty.toHit(element({ one: { '.title': element({ text: 'Handelsschule' }) } }), QUERY), null);
});

function youstyDoc({ body, cards = [], links = [] }) {
  return { body: { textContent: body }, querySelectorAll: (s) => (s === '.result' ? cards : s === 'a' ? links : []) };
}

test('yousty: without a count the other offers on the page are not taken for hits', () => {
  // The words „Keine Lehrstelle“ are part of every result page, the count only of those with hits.
  const none = youstyDoc({ body: 'Keine Lehrstelle gefunden', cards: [youstyCard()] });
  assert.deepEqual(yousty.parseList(none, QUERY, 1), { hits: [], more: false });
  const some = youstyDoc({ body: '25 Lehrstellen gefunden. Keine Lehrstelle …', cards: [youstyCard()], links: [element({ text: 'nächste ›' })] });
  const list = yousty.parseList(some, QUERY, 1);
  assert.equal(list.hits.length, 1);
  assert.equal(list.more, true);
});

test('yousty: later pages have no count; an unknown page is a changed portal', () => {
  assert.equal(yousty.parseList(youstyDoc({ body: 'Seite 2', cards: [youstyCard()] }), QUERY, 2).hits.length, 1);
  assert.throws(() => yousty.parseList(youstyDoc({ body: 'Etwas anderes' }), QUERY, 1), (error) => error.changed === true);
  assert.throws(() => yousty.parseList(youstyDoc({ body: '3 Lehrstellen gefunden' }), QUERY, 1), (error) => error.changed === true);
});

test('yousty address: place with radius, or canton in the path; one year as filter', () => {
  const near = new URL(yousty.searchUrl(QUERY, '33481-fage', 2), 'https://www.yousty.ch');
  assert.equal(near.pathname, '/de-CH/lehrstellen');
  assert.deepEqual(Object.fromEntries(near.searchParams), { place: 'Bern', job: '33481-fage', distance: '25', year: '2027', page: '2' });
  const canton = new URL(yousty.searchUrl({ keyword: 'x', years: [2027, 2028], canton: 'SO' }, '33481-fage', 1), 'https://www.yousty.ch');
  assert.equal(canton.pathname, '/de-CH/lehrstellen/SO/33481-fage');
  assert.equal(canton.search, '');
});

test('yousty text comes from the structured data of the page', () => {
  const script = (content) => element({ text: content });
  const doc = { querySelectorAll: () => [script('kein JSON'), script('{"@type":"Organization"}'), script('{"@type":"JobPosting","description":"Deine Lehre &amp; mehr"}')] };
  assert.deepEqual(yousty.parseDetails(doc), { text: 'Deine Lehre & mehr' });
  assert.deepEqual(yousty.parseDetails({ querySelectorAll: () => [] }), { text: '' });
});

function lenaCard({ id = '3709234', title = 'Fachmann/-frau Gesundheit EFZ (2027)' } = {}) {
  const company = element({ text: 'Spital Muster' });
  return element({
    text: `Spital Muster ${title} Biel/Bienne (BE) Ausbildungsort auf Karte anzeigen Sprache Deutsch Bemerkung Bitte (FR) beachten`,
    one: {
      'a[href*="/lehrstellen/"]': element({ attributes: { href: `https://www.berufsberatung.ch/de/lehrstellen/${id}` } }),
      '.search-result-title': element({ text: title }),
      '.search-result-sup-title, .text-overline-small': company,
    },
  });
}

test('LENA result as hit: year out of the title, place from the card', () => {
  assert.deepEqual(lena.toHit(lenaCard(), QUERY), {
    portal: 'LENA', portal_id: '3709234', stelle: 'Fachmann/-frau Gesundheit EFZ', firma: 'Spital Muster', ort: 'Biel/Bienne (BE)',
    link: 'https://www.berufsberatung.ch/de/lehrstellen/3709234', art: 'Lehrstelle', beruf: 'Fachfrau Gesundheit EFZ', lehrbeginn: '2027',
  });
});

test('LENA: other years are no hits, and cards of an unknown form are a changed portal', () => {
  assert.equal(lena.toHit(lenaCard({ title: 'Fachmann/-frau Gesundheit EFZ (2028)' }), QUERY), null);
  const root = (cards) => ({ querySelectorAll: (s) => (s === '.search-result' ? cards : []) });
  assert.deepEqual(lena.parseList(root([lenaCard({ title: 'X EFZ (2028)' })]), QUERY), { hits: [], more: false });
  assert.throws(() => lena.parseList(root([element()]), { ...QUERY, years: [] }), (error) => error.changed === true);
  assert.deepEqual(lena.parseList(root([]), QUERY), { hits: [], more: false });
});

test('LENA: what is typed into the search form', () => {
  assert.deepEqual(lena.searchTerms('Fachfrau Betreuung EFZ, Fachrichtung Kinder'), ['Fachfrau Betreuung EFZ Kinder', 'Fachfrau Betreuung Kinder']);
  assert.deepEqual(lena.searchTerms('Fachfrau Gesundheit'), ['Fachfrau Gesundheit']);
});

test('LENA: a place must match exactly, a postal code takes the first suggestion', () => {
  const found = [{ value: 'allmendingen_b__bern-be-ch', label: 'Allmendingen b. Bern' }, { value: 'bern-be-ch', label: 'Bern' }];
  assert.equal(lena.pickPlace(found, 'Bern').value, 'bern-be-ch');
  assert.equal(lena.pickPlace(found, 'bern').value, 'bern-be-ch');
  assert.equal(lena.pickPlace(found.slice(0, 1), 'Bern'), null);
  assert.equal(lena.pickPlace(found.slice(1), '3012').value, 'bern-be-ch');
});

test('the adapters load side by side and register under the name of the plan', () => {
  assert.deepEqual(Object.keys(globalThis.bewerbungsassistentPortals).sort(), ['LENA', 'yousty']);
});

const TRIAL = { ...QUERY, trial: true, years: [] };

test('yousty trial: own id and address, so it stays apart from the apprenticeship of the same profile', () => {
  const hit = yousty.toHit(youstyCard({ chips: [] }), TRIAL);

  assert.equal(hit.art, 'Schnupperlehre');
  assert.equal(hit.portal_id, 'schnupperlehre-8690204');
  assert.equal(hit.link, 'https://www.yousty.ch/de-CH/lehrstellen/profile/8690204-fage-bern#schnupperlehre');
  assert.equal(hit.lehrbeginn, undefined);
  assert.notEqual(hit.portal_id, yousty.toHit(youstyCard(), QUERY).portal_id);
});

test('yousty trial: own list with its own words, also for no result', () => {
  const none = youstyDoc({ body: 'Keine Schnupperlehre gefunden', cards: [youstyCard({ chips: [] })] });
  assert.deepEqual(yousty.parseList(none, TRIAL, 1), { hits: [], more: false });
  const some = youstyDoc({ body: '35 Schnupperlehren gefunden', cards: [youstyCard({ chips: [] })] });
  assert.equal(yousty.parseList(some, TRIAL, 1).hits[0].art, 'Schnupperlehre');
  assert.throws(() => yousty.parseList(youstyDoc({ body: '3 Lehrstellen gefunden' }), TRIAL, 1), (error) => error.changed === true);
});

test('yousty trial address: place or canton on the own list, without a year', () => {
  const near = new URL(yousty.searchUrl({ ...TRIAL, years: [2027] }, '1712-x', 1), 'https://www.yousty.ch');
  assert.equal(near.pathname, '/de-CH/schnupperlehren');
  assert.equal(near.searchParams.get('place'), 'Bern');
  assert.equal(near.searchParams.get('job'), '1712-x');
  assert.equal(near.searchParams.get('year'), null);
  const { place, radius, ...withoutPlace } = TRIAL;
  const canton = new URL(yousty.searchUrl({ ...withoutPlace, canton: 'BE' }, '1712-x', 1), 'https://www.yousty.ch');
  assert.equal(canton.pathname, '/de-CH/schnupperlehren/BE/1712-x');
});

test('LENA trial: address card as hit, with the link of the trial page', () => {
  const card = element({
    text: 'Muster AG Abdichter/-in EFZ Bern (BE) Adresse',
    one: {
      'a[href*="/schnupperlehren/"]': element({ attributes: { href: '/de/schnupperlehren/123' } }),
      '.search-result-title': element({ text: 'Abdichter/-in EFZ' }),
      '.search-result-sup-title, .text-overline-small': element({ text: 'Muster AG' }),
    },
  });

  const hit = lena.toHit(card, TRIAL);

  assert.equal(hit.art, 'Schnupperlehre');
  assert.equal(hit.portal_id, 'schnupperlehre-123');
  assert.equal(hit.link, 'https://www.berufsberatung.ch/de/schnupperlehren/123');
  assert.equal(hit.ort, 'Bern (BE)');
  assert.equal(hit.firma, 'Muster AG');
});

test('LENA: the search path follows the query', () => {
  assert.equal(lena.searchPath(TRIAL), '/de/suche/schnupperadressen');
  assert.equal(lena.searchPath(QUERY), '/de/suche/lehrstellen');
});

test('profession words follow the same cases as the app', () => {
  const cases = JSON.parse(fs.readFileSync(new URL('./profession_words.json', import.meta.url), 'utf8'));
  for (const [name, expected] of cases) assert.deepEqual(words(name), [...expected].sort(), name);
});
