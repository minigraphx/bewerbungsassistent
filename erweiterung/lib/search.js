// One search run: plan from the app, per portal a background tab, result lists, screening by the app,
// full texts of the new hits, hits to the app, summary. Only started by the person (popup or app page).

import { ADAPTERS, buildQueries, chunks, hitKey } from './queries.js';
import { followKey, searchSites } from './sites.js';
import { CANCELLED, screen, stopIfCancelled } from './steps.js';

export const DELAY_MS = 600; // between requests to a portal, to stay gentle
export const SEND_SIZE = 10;
const COMMON = 'portals/common.js';

/** The scripts of the portal, and with „Zuschauen“ the message that the browser is being steered (again after each page). */
async function loadPortal(portal, plan, tab, deps) {
  await deps.browser.inject(tab, [COMMON, ADAPTERS[portal].file]);
  if (plan.zuschauen) await deps.browser.showWatching(tab, portal);
}

function changedText(portal, message) {
  return `Die Seite von ${portal} hat sich verändert (${message}). Die Suche dort braucht ein Update der Erweiterung.`;
}

/** For portals that fill their list in the page: the tab goes to the list of this query, adapters loaded anew. */
async function openResults(portal, plan, query, tab, deps) {
  const target = await deps.browser.run(tab, portal, 'searchUrl', [query]);
  if (!target.ok) return target;
  await deps.browser.navigate(tab, target.value);
  await loadPortal(portal, plan, tab, deps);
  return target;
}

async function listAll(portal, plan, tab, deps) {
  const found = new Map();
  let problem = '';
  const { queries, skipped } = buildQueries(portal, plan);
  if (skipped) {
    problem = `${portal}: ${skipped} Suchen ausgelassen (höchstens ${queries.length}). Im Suchprofil weniger Stichworte oder Orte angeben.`;
  }
  for (const query of queries) {
    if (ADAPTERS[portal].opensPages) {
      stopIfCancelled(deps);
      const opened = await openResults(portal, plan, query, tab, deps);
      await deps.sleep(DELAY_MS);
      if (!opened.ok) {
        if (opened.changed) throw Object.assign(new Error(opened.fehler), { changed: true });
        problem = [problem, `${portal}: ${opened.fehler}`].filter(Boolean).join(' ');
        continue;
      }
    }
    for (let page = 1; page <= plan.max_seiten; page += 1) {
      stopIfCancelled(deps);
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
      stopIfCancelled(deps);
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
    tab = await deps.browser.openTab(adapter.start, Boolean(plan.zuschauen));
    await loadPortal(portal, plan, tab, deps);
    const { found, problem } = await listAll(portal, plan, tab, deps);
    const wanted = await screen(found, deps.app);
    const limit = plan.max_texte || wanted.length;
    const later = Math.max(0, wanted.length - limit);
    const { added, missing, failed } = await sendWithTexts(portal, wanted.slice(0, limit), tab, deps);
    const notes = [
      problem,
      later ? `${later} weitere neue Inserate kommen bei der nächsten Suche dran.` : '',
      missing ? `${missing} Inserate ohne lesbaren Text.` : '',
      failed ? `${failed} Inserate nicht geladen, sie kommen bei der nächsten Suche wieder.` : '',
    ];
    return { treffer: found.size, neu: added, problem: notes.filter(Boolean).join(' ') };
  } catch (error) {
    // Closing the tab is a way to cancel too: then the error is only about the tab being gone.
    if (error.cancelled || deps.cancelled?.()) return { ...summary, problem: `${portal}: ${CANCELLED}` };
    return { ...summary, problem: error.changed ? changedText(portal, error.message) : `${portal}: ${error.message}` };
  } finally {
    if (tab !== null) await deps.browser.closeTab(tab).catch(() => {});
  }
}

/** The whole run. Errors before the first portal (no app, no search profile) are thrown. */
export async function runSearch(deps) {
  const { plan } = await deps.app.request('GET', '/api/suche/plan');
  if (deps.access) await followKey(plan, deps.access);
  const portals = {};
  for (const portal of plan.portale) {
    if (deps.cancelled?.()) break;
    portals[portal] = await searchPortal(portal, plan, deps);
  }
  const all = { ...portals, ...(deps.cancelled?.() ? {} : await searchSites(plan, deps)) };
  await deps.app.request('POST', '/api/suche/abschluss', { portale: all });
  return { portale: all, hinweise: plan.hinweise || [], abgebrochen: Boolean(deps.cancelled?.()) };
}
