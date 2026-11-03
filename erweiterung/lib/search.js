// One search run: plan from the app, per portal a background tab, result lists, screening by the app,
// full texts of the new hits, hits to the app, summary. Only started by the person (popup or app page).

import { ADAPTERS, buildQueries, chunks, hitKey } from './queries.js';

export const DELAY_MS = 600; // between requests to a portal, to stay gentle
export const SEND_SIZE = 10;
const SCREEN_SIZE = 200;
const COMMON = 'portals/common.js';

function changedText(portal, message) {
  return `Die Seite von ${portal} hat sich verändert (${message}). Die Suche dort braucht ein Update der Erweiterung.`;
}

async function listAll(portal, plan, tab, deps) {
  const found = new Map();
  let problem = '';
  const { queries, skipped } = buildQueries(portal, plan);
  if (skipped) {
    problem = `${portal}: ${skipped} Suchen ausgelassen (höchstens ${queries.length}). Im Suchprofil weniger Stichworte oder Orte angeben.`;
  }
  for (const query of queries) {
    for (let page = 1; page <= plan.max_seiten; page += 1) {
      deps.report({ portal, phase: 'suche', stichwort: query.keyword, seite: page, gefunden: found.size });
      const result = await deps.browser.run(tab, portal, 'list', [query, page]);
      await deps.sleep(DELAY_MS);
      if (!result.ok) {
        if (result.changed) throw Object.assign(new Error(result.fehler), { changed: true });
        problem = [problem, `${portal}: ${result.fehler}`].filter(Boolean).join(' ');
        break;
      }
      for (const hit of result.value.hits) found.set(hitKey(hit), hit);
      if (!result.value.more) break;
    }
  }
  return { found, problem };
}

async function screen(found, app) {
  const wanted = [];
  for (const part of chunks([...found.values()], SCREEN_SIZE)) {
    const answer = await app.request('POST', '/api/suche/sichten', { treffer: part });
    wanted.push(...answer.holen);
  }
  return wanted.filter((key) => found.has(key)).map((key) => found.get(key));
}

/**
 * Full texts, then the hits to the app. An ad that did not load (e.g. too many requests) is not sent, so the
 * next search tries again; an ad whose page has no readable text is sent without text.
 */
async function sendWithTexts(portal, hits, tab, deps) {
  let added = 0;
  let missing = 0;
  let failed = 0;
  let done = 0;
  for (const part of chunks(hits, SEND_SIZE)) {
    const full = [];
    for (const hit of part) {
      deps.report({ portal, phase: 'texte', fertig: done, von: hits.length });
      done += 1;
      const result = await deps.browser.run(tab, portal, 'details', [hit]);
      await deps.sleep(DELAY_MS);
      if (!result.ok) {
        if (result.changed) throw Object.assign(new Error(result.fehler), { changed: true });
        failed += 1;
        continue;
      }
      if (!result.value.text) missing += 1;
      full.push({ ...hit, text: result.value.text || '' });
    }
    if (full.length) {
      const answer = await deps.app.request('POST', '/api/suche/treffer', { treffer: full });
      added += answer.neu;
    }
  }
  return { added, missing, failed };
}

/** Search one portal; problems end up in the summary instead of stopping the run. */
export async function searchPortal(portal, plan, deps) {
  const summary = { treffer: 0, neu: 0, problem: '' };
  const adapter = ADAPTERS[portal];
  if (!adapter) return { ...summary, problem: `${portal}: unbekanntes Portal` };
  let tab = null;
  try {
    tab = await deps.browser.openTab(adapter.start);
    await deps.browser.inject(tab, [COMMON, adapter.file]);
    const { found, problem } = await listAll(portal, plan, tab, deps);
    const wanted = await screen(found, deps.app);
    const { added, missing, failed } = await sendWithTexts(portal, wanted, tab, deps);
    const notes = [
      problem,
      missing ? `${missing} Inserate ohne lesbaren Text.` : '',
      failed ? `${failed} Inserate nicht geladen, sie kommen bei der nächsten Suche wieder.` : '',
    ];
    return { treffer: found.size, neu: added, problem: notes.filter(Boolean).join(' ') };
  } catch (error) {
    return { ...summary, problem: error.changed ? changedText(portal, error.message) : `${portal}: ${error.message}` };
  } finally {
    if (tab !== null) await deps.browser.closeTab(tab).catch(() => {});
  }
}

/** The whole run. Errors before the first portal (no app, no search profile) are thrown. */
export async function runSearch(deps) {
  const { plan } = await deps.app.request('GET', '/api/suche/plan');
  const portals = {};
  for (const portal of plan.portale) {
    portals[portal] = await searchPortal(portal, plan, deps);
  }
  await deps.app.request('POST', '/api/suche/abschluss', { portale: portals });
  return { portale: portals, hinweise: plan.hinweise || [] };
}
