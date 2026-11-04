// Steps shared by the search on portals and on further sites.

import { chunks } from './queries.js';

const SCREEN_SIZE = 200;
export const CANCELLED = 'Suche abgebrochen.';

export function stopIfCancelled(deps) {
  if (deps.cancelled?.()) throw Object.assign(new Error(CANCELLED), { cancelled: true });
}

/** Which of the found hits the app wants with their full text, those near the home first. */
export async function screen(found, app) {
  const wanted = [];
  const near = new Set();
  for (const part of chunks([...found.values()], SCREEN_SIZE)) {
    const answer = await app.request('POST', '/api/suche/sichten', { treffer: part });
    wanted.push(...answer.holen);
    (answer.nah || []).forEach((key) => near.add(key));
  }
  const known = wanted.filter((key) => found.has(key));
  return [...known.filter((key) => near.has(key)), ...known.filter((key) => !near.has(key))].map((key) => found.get(key));
}
