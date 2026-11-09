// Every configured place gets its share of the query limit (#175), with invented places and terms.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { buildQueries } from '../lib/queries.js';

const KEYWORDS = ['Python', 'TypeScript', 'Go', 'Rust', 'Kotlin', 'Swift', 'SQL', 'Linux', 'Docker', 'Kubernetes',
  'Terraform', 'Ansible', 'React', 'Vue', 'Angular'];
const NICHES = ['EdTech', 'GovTech', 'MedTech', 'CleanTech', 'FinTech', 'LegalTech'];
const PLAN = {
  portale: ['jobs.ch', 'jobscout24'], stichworte: KEYWORDS, nischen: NICHES, kantone: ['BE', 'SO'],
  orte: ['Bern', 'Thun', 'Biel', 'Solothurn'], plz: ['3000', '3600', '2500', '4500'], regionen: [],
  max_abfragen: 30, max_alter_tage: 45,
};

/** Keywords searched per place, in the order the queries run. */
function perPlace(queries, key) {
  const found = new Map();
  for (const query of queries.filter((q) => q[key] !== undefined)) {
    found.set(query[key], [...(found.get(query[key]) || []), query.keyword]);
  }
  return found;
}

for (const [portal, field, key] of [['jobs.ch', 'orte', 'place'], ['jobscout24', 'plz', 'postalCode']]) {
  test(`${portal} searches every place with its top keywords in profile order`, () => {
    const { queries } = buildQueries(portal, PLAN);
    const found = perPlace(queries, key);
    assert.deepEqual([...found.keys()].sort(), [...PLAN[field]].sort());
    for (const [place, keywords] of found) {
      assert.ok(keywords.length >= 6, `${place} gets ${keywords.length} keywords`);
      assert.deepEqual(keywords, KEYWORDS.slice(0, keywords.length), `${place} searches the top keywords first`);
    }
  });

  test(`${portal} stays within the query limit and counts the rest`, () => {
    const { queries, skipped } = buildQueries(portal, PLAN);
    const niches = portal === 'jobs.ch' ? NICHES.length : 0;
    assert.equal(queries.length, PLAN.max_abfragen);
    assert.equal(skipped, KEYWORDS.length * PLAN[field].length + niches - PLAN.max_abfragen);
  });
}

test('jobs.ch still searches every niche once without a place', () => {
  const { queries } = buildQueries('jobs.ch', PLAN);
  assert.deepEqual(queries.filter((q) => q.place === undefined).map((q) => q.keyword), NICHES);
});

test('the home still comes first', () => {
  const { queries } = buildQueries('jobscout24', PLAN);
  assert.deepEqual(queries.slice(0, 2).map((q) => [q.keyword, q.postalCode]), [['Python', '3000'], ['TypeScript', '3000']]);
});
