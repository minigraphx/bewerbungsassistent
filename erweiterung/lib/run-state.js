// What the service worker knows about a search run, so that a page of the app never waits for a run that is over (#142).

export const INTERRUPTED = 'Die Suche wurde unterbrochen. Was schon gefunden war, ist da.';

/**
 * The run as pages should see it. The browser may stop an idle worker and start a new one, which has no run: a stored
 * „laeuft“ from before is then over, not running.
 * @param {object|null|undefined} stored the last published state (storage.session „lauf“)
 * @param {boolean} running whether this worker runs a search
 * @returns {object|null}
 */
export function currentRun(stored, running) {
  if (!stored) return null;
  if (stored.zustand === 'laeuft' && !running) return { ...stored, zustand: 'fehler', fehler: INTERRUPTED };
  return stored;
}

/** The tabs a search opened. Closing one of them by hand stops the search, whether it is watched or not. */
export class SearchTabs {
  #open = new Set();

  opened(tabId) {
    this.#open.add(tabId);
  }

  /** The search closes its own tab: no cancelling. */
  closedBySearch(tabId) {
    this.#open.delete(tabId);
  }

  /** @returns {boolean} true when the person closed a tab of the search */
  removed(tabId) {
    return this.#open.delete(tabId);
  }

  clear() {
    this.#open.clear();
  }
}
