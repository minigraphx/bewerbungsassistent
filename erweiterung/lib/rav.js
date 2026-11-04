// The run that enters applications in Job-Room (MIN-347): one tab, one entry after the other. The person logs in and
// saves; this only opens the form, hands over the values and moves on. Kept in the session storage, because the
// service worker does not stay alive between two entries. What is entered here never goes to the AI.

export const RAV_HOST = 'www.job-room.ch';
export const FORM_URL = `https://${RAV_HOST}/work-efforts/create`;
const NEXT_WAIT_MS = 1500;
const WAITING = 'Warte auf das Formular der Arbeitsbemühungen …';
const NO_FORM = 'Hier ist kein Formular für die Arbeitsbemühungen zu sehen. Bitte bei Job-Room anmelden, falls nötig, und danach „Zum Formular“ drücken. Erscheint es auch dann nicht, hat sich der Job-Room geändert: bitte von Hand eintragen.';
const CHANGED = 'Das Formular im Job-Room sieht anders aus als erwartet, darum wurde nichts ausgefüllt. Bitte von Hand eintragen und selbst speichern, oder überspringen.';
const SAVE_YOURSELF = 'Bitte prüfen und selbst auf „Speichern“ drücken; damit geht der Eintrag ans RAV.';
const NOT_RECORDED = 'Der Eintrag ist im Job-Room gespeichert, aber in der App nicht vermerkt:';
const RUNNING = 'Es läuft schon ein Durchgang fürs RAV; der Tab ist jetzt vorn.';
const NOT_THIS_TAB = 'Dieser Tab gehört nicht zum Eintragen im RAV.';
const NO_CHOICE = 'Bitte zuerst Bewerbungen ankreuzen.';

export function isRavPage(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' && parsed.hostname === RAV_HOST;
  } catch {
    return false;
  }
}

export class RavRun {
  constructor({ ask, tabs, store, sleep }) {
    this.ask = ask;
    this.tabs = tabs;
    this.store = store;
    this.sleep = sleep;
    this.chain = Promise.resolve();
  }

  /** One step at a time: the tab, the bar and the app may all speak at once. */
  change(step) {
    const result = this.chain.then(step);
    this.chain = result.catch(() => {});
    return result;
  }

  async mine(tabId) {
    const run = await this.store.get();
    if (!run || run.tabId !== tabId) throw new Error(NOT_THIS_TAB);
    return run;
  }

  async bar(tabId, balken) {
    await this.tabs.bar(tabId, balken).catch(() => { /* the page is just changing; the script reports again */ });
  }

  start({ ids }) {
    return this.change(async () => {
      if (!Array.isArray(ids) || !ids.length) throw new Error(NO_CHOICE);
      const earlier = await this.store.get();
      if (earlier && await this.tabs.exists(earlier.tabId)) {
        await this.tabs.activate(earlier.tabId);
        return { fehler: RUNNING };
      }
      const { bereit, abgelehnt } = await this.ask('POST', '/api/rav/start', { ids });
      if (abgelehnt.length) return { abgelehnt };
      const tabId = await this.tabs.blank();
      await this.store.set({ tabId, open: bereit, total: bereit.length, entered: 0, skipped: 0 });
      await this.tabs.navigate(tabId, FORM_URL);
      return { geoeffnet: bereit.length };
    });
  }

  /** The tab finished loading a page; a login elsewhere gets no script. */
  loaded(tabId, url) {
    return this.change(async () => {
      const run = await this.store.get();
      if (!run || run.tabId !== tabId || !isRavPage(url)) return;
      try {
        await this.tabs.inject(tabId);
      } catch {
        // an error page of the browser, or the page moved on: nothing to fill, the person sees it
      }
    });
  }

  /** From a script just started in a new document; a document that stays keeps its bar and hints. */
  waiting(tabId) {
    return this.change(async () => {
      await this.mine(tabId);
      await this.bar(tabId, { text: WAITING, knoepfe: ['rav_stoppen'] });
    });
  }

  values(tabId) {
    return this.change(async () => {
      const run = await this.mine(tabId);
      const entry = run.open[0];
      try {
        const { werte } = await this.ask('GET', '/api/rav/angaben', { id: entry.id });
        return { id: entry.id, werte };
      } catch (error) {
        await this.bar(tabId, { id: entry.id, text: `${entry.firma}: ${error.message}`, fehler: true, knoepfe: ['rav_ueberspringen', 'rav_stoppen'] });
        return { fehler: error.message };
      }
    });
  }

  report(tabId, { id, hinweise, geaendert }) {
    return this.change(async () => {
      const run = await this.mine(tabId);
      const entry = run.open[0];
      if (entry.id !== id) return;
      const position = run.total - run.open.length + 1;
      const name = `Eintrag ${position} von ${run.total}: ${entry.firma}, ${entry.stelle}.`;
      const buttons = ['rav_ja', 'rav_ueberspringen', 'rav_stoppen'];
      if (geaendert) await this.bar(tabId, { id, text: `${name} ${CHANGED}`, fehler: true, knoepfe: buttons, aufmerksamkeit: true });
      else await this.bar(tabId, { id, text: `${name} ${SAVE_YOURSELF}`, hinweise, knoepfe: buttons, farben: 'rav', aufmerksamkeit: true });
    });
  }

  noForm(tabId) {
    return this.change(async () => {
      await this.mine(tabId);
      await this.bar(tabId, { text: NO_FORM, knoepfe: ['rav_formular', 'rav_stoppen'], aufmerksamkeit: true });
    });
  }

  toForm(tabId) {
    return this.change(async () => {
      await this.mine(tabId);
      await this.tabs.navigate(tabId, FORM_URL);
    });
  }

  /**
   * The message of Job-Room or the button of the bar, always about one entry: a second click may wait in line behind
   * the first, and must not hit the next entry, which the person has not even seen.
   */
  entered(tabId, id) {
    return this.change(async () => {
      const run = await this.mine(tabId);
      const entry = run.open[0];
      if (entry.id !== id) return;
      try {
        await this.ask('POST', '/api/rav/eingetragen', { id: entry.id });
      } catch (error) {
        await this.bar(tabId, { id, text: `${NOT_RECORDED} ${error.message}`, fehler: true, knoepfe: ['rav_ja', 'rav_ueberspringen', 'rav_stoppen'] });
        return;
      }
      await this.advance({ ...run, open: run.open.slice(1), entered: run.entered + 1 }, `Vermerkt: ${entry.firma}.`);
    });
  }

  skip(tabId, id) {
    return this.change(async () => {
      const run = await this.mine(tabId);
      if (run.open[0].id !== id) return;
      await this.advance({ ...run, open: run.open.slice(1), skipped: run.skipped + 1 }, `Übersprungen: ${run.open[0].firma}.`);
    });
  }

  stop(tabId) {
    return this.change(async () => this.finish(await this.mine(tabId)));
  }

  closed(tabId) {
    return this.change(async () => {
      const run = await this.store.get();
      if (run && run.tabId === tabId) await this.store.set(null);
    });
  }

  async advance(run, done) {
    if (!run.open.length) {
      await this.finish(run);
      return;
    }
    await this.store.set(run);
    await this.bar(run.tabId, { text: `${done} Weiter mit ${run.open[0].firma} …` });
    await this.sleep(NEXT_WAIT_MS);
    await this.tabs.navigate(run.tabId, FORM_URL);
  }

  async finish(run) {
    await this.store.set(null);
    await this.tabs.end(run.tabId, `Fertig: ${run.entered} eingetragen, ${run.skipped} übersprungen. Die Übersicht in der App zeigt es.`);
  }
}
