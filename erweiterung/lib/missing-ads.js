// Ad texts the app is missing (G37, #275): at a new start of the app, saved jobs and hits without text get it from
// their portal, one tab per portal in the background. Only portals with their own adapter allow automatic loading;
// the app names the others. The texts go to the app only, never to the AI.

import { ADAPTERS, chunks } from './queries.js';
import { DELAY_MS } from './search.js';

export const LIST_PATH = '/api/inserate/holen';
export const LOAD_PATH = '/api/inserate/texte';
const SEND_SIZE = 10;
const COMMON = 'portals/common.js';

/** A running app whose entry address (new token per start) differs from the last one this run was made for. */
export function isNewStart(hello, last) {
  return Boolean(hello && hello.app && hello.einstieg) && hello.einstieg !== last;
}

function byPortal(jobs) {
  const groups = new Map();
  for (const job of jobs) {
    if (!job || !ADAPTERS[job.portal]) continue;
    groups.set(job.portal, [...(groups.get(job.portal) || []), job]);
  }
  return groups;
}

const failure = (job, reason) => ({ art: job.art, id: job.id, text: '', fehler: String(reason || 'unbekannter Fehler') });

async function loadOne(tab, portal, job, deps) {
  const result = await deps.browser.run(tab, portal, 'details', [{ portal, portal_id: job.portal_id, link: job.link }]);
  await deps.sleep(DELAY_MS);
  return result.ok ? { art: job.art, id: job.id, text: (result.value && result.value.text) || '' } : failure(job, result.fehler);
}

/** The texts of one portal; a portal that does not open gives its reason to each of its jobs. */
async function loadPortal(portal, jobs, deps) {
  const results = [];
  let tab = null;
  try {
    tab = await deps.browser.openTab(ADAPTERS[portal].start, false);
    await deps.browser.inject(tab, [COMMON, ADAPTERS[portal].file]);
    for (const job of jobs) results.push(await loadOne(tab, portal, job, deps));
  } catch (error) {
    results.push(...jobs.slice(results.length).map((job) => failure(job, error.message)));
  } finally {
    if (tab !== null) await deps.browser.closeTab(tab).catch(() => {});
  }
  return results;
}

/** Asks the app what it is missing, loads it and hands back texts and reasons. */
export async function fetchMissingAds(deps) {
  const answer = await deps.app.request('POST', LIST_PATH, {});
  const jobs = Array.isArray(answer && answer.laden) ? answer.laden : [];
  let loaded = 0;
  let failed = 0;
  for (const [portal, list] of byPortal(jobs)) {
    const results = await loadPortal(portal, list, deps);
    loaded += results.filter((r) => r.text).length;
    failed += results.filter((r) => !r.text).length;
    for (const part of chunks(results, SEND_SIZE)) await deps.app.request('POST', LOAD_PATH, { texte: part });
  }
  return { geladen: loaded, fehlgeschlagen: failed };
}
