// Forms in tabs (MIN-346): the extension opens what the person chose in the app, fills it, reports the state and
// records a dispatch only after the person pressed the button. Tab, app and storage come from outside, for the tests.

export const ALL_PAGES = { origins: ['<all_urls>'] };
const FOLLOW_WAIT_MS = 1500;
const MAX_PARTS = 60;
const NO_FORM = 'Hier ist kein Formular zu finden. Bitte das Formular selbst öffnen, es wird dann ausgefüllt. Schon abgeschickt? Dann unten bestätigen.';
const LOGIN = 'Hier braucht es eine Anmeldung oder ein Konto: Das bleibt bei Ihnen. Danach geht das Ausfüllen weiter.';
const GOES_ON = 'Ausfüllen beendet. Die eingetragenen Werte bleiben im Formular.';

export function hostOf(url) {
  try {
    const { protocol, hostname } = new URL(url);
    return protocol === 'http:' || protocol === 'https:' ? hostname : null;
  } catch {
    return null;
  }
}

/** The same site: „www.firma.ch“, „firma.ch“ and „jobs.firma.ch“. Nothing wider: „co.uk“ is not one site. */
export function sameSite(host, other) {
  const a = host.replace(/^www\./, '');
  const b = other.replace(/^www\./, '');
  return a === b || a.endsWith(`.${b}`) || b.endsWith(`.${a}`);
}

/** All frames of a tab together. */
export function mergeReports(frames) {
  const reports = Object.values(frames || {});
  const sum = (key) => reports.reduce((total, r) => total + (Number(r[key]) || 0), 0);
  return {
    felder: sum('felder'), gefuellt: sum('gefuellt'), offen: sum('offen'), einwilligungen: sum('einwilligungen'),
    anmeldung: reports.some((r) => r.anmeldung),
    hinweise: [...new Set(reports.flatMap((r) => (Array.isArray(r.hinweise) ? r.hinweise : [])))],
  };
}

function plural(count, one, many) {
  return `${count} ${count === 1 ? one : many}`;
}

/** The text of the bar: „14 Felder ausgefüllt, 3 offen, 1 Einwilligung bitte selbst prüfen“. */
export function describeReport(merged) {
  if (merged.anmeldung) return { text: LOGIN, aufmerksamkeit: true, knoepfe: ['stoppen'] };
  if (!merged.felder) return { text: NO_FORM, aufmerksamkeit: true, knoepfe: ['abgeschickt', 'stoppen'] };
  const parts = [`${plural(merged.gefuellt, 'Feld', 'Felder')} ausgefüllt`, `${merged.offen} offen`];
  if (merged.einwilligungen) parts.push(`${plural(merged.einwilligungen, 'Einwilligung', 'Einwilligungen')} bitte selbst prüfen`);
  return { text: `${parts.join(', ')}. Abschicken bleibt bei Ihnen.`, hinweise: merged.hinweise, farben: true,
           knoepfe: ['abgeschickt', 'stoppen'] };
}

export class ApplyRun {
  /**
   * @param {object} deps
   * @param {(method: string, path: string, data?: object) => Promise<any>} deps.ask  request to the app
   * @param {object} deps.tabs  blank, navigate, activate, url, inject, fill, follow, bar, end, permissionPage
   * @param {{get: () => Promise<object>, set: (forms: object) => Promise<void>}} deps.store  tabs of this run
   * @param {{get: () => Promise<object|null>, set: (request: object|null) => Promise<void>}} deps.pending  a run waiting for the access
   * @param {() => Promise<boolean>} deps.hasPermission
   * @param {(ms: number) => Promise<void>} deps.sleep
   */
  constructor({ ask, tabs, store, pending, hasPermission, sleep }) {
    Object.assign(this, { ask, tabs, store, pending, hasPermission, sleep });
    this.queue = Promise.resolve();
    this.starting = false;
  }

  /** Changes of the list one after the other, so answers of several frames do not overwrite each other. */
  change(fn) {
    const step = this.queue.then(async () => {
      const forms = await this.store.get();
      const { next, result } = fn(forms);
      if (next !== forms) await this.store.set(next);
      return result;
    });
    this.queue = step.catch(() => {});
    return step;
  }

  updateTab(tabId, fn) {
    return this.change((forms) => {
      const entry = forms[tabId];
      if (!entry) return { next: forms, result: null };
      const updated = fn(entry);
      return { next: { ...forms, [tabId]: updated }, result: updated };
    });
  }

  removeTab(tabId) {
    return this.change((forms) => {
      const { [tabId]: entry, ...rest } = forms;
      return { next: entry ? rest : forms, result: entry || null };
    });
  }

  async entry(tabId) {
    return (await this.store.get())[tabId] || null;
  }

  /** The choice in the app: the app checks it, and only its own links are opened. */
  async start(request) {
    if (this.starting) return { laeuft: true };
    this.starting = true;
    try {
      return await this.startChecked(request);
    } finally {
      this.starting = false;
    }
  }

  async startChecked({ ids, bestaetigt }) {
    const answer = await this.ask('POST', '/api/bewerben/start', { ids, bestaetigt: bestaetigt === true });
    if (!answer.bereit.length) return answer;
    if (!(await this.hasPermission())) {
      await this.pending.set({ ids, bestaetigt }); // the question can outlast the service worker
      await this.tabs.permissionPage();
      return { berechtigung: true };
    }
    for (const [position, application] of answer.bereit.entries()) await this.open(application, position === 0);
    return { geoeffnet: answer.bereit.length };
  }

  async resume() {
    const waiting = await this.pending.get();
    await this.pending.set(null);
    if (!waiting) throw new Error('Bitte in der App nochmals auf „Bewerben“ klicken.');
    return this.start(waiting);
  }

  async open(application, active) {
    const forms = await this.store.get();
    const known = Object.entries(forms).find(([, entry]) => entry.id === application.id);
    if (known) {
      await this.tabs.activate(Number(known[0]));
      return;
    }
    // First the empty tab: then the list knows it before the form has loaded.
    const tabId = await this.tabs.blank(active);
    const entry = { id: application.id, firma: application.firma, hosts: [], frames: {}, gefolgt: false, ausgefuellt: false };
    await this.change((current) => ({ next: { ...current, [tabId]: entry }, result: null }));
    await this.tabs.navigate(tabId, application.link);
    await this.ask('POST', '/api/bewerben/stand', { id: application.id, stand: 'geoeffnet' });
  }

  /** A page of a listed tab has loaded. On a new address the person decides first: tabs can be used for anything. */
  async loaded(tabId, url) {
    const host = hostOf(url);
    if (!host) return;
    const entry = await this.updateTab(tabId, (current) => {
      const known = !current.hosts.length || current.hosts.some((h) => sameSite(h, host));
      return { ...current, frames: {}, hosts: known ? [...new Set([...current.hosts, host])] : current.hosts,
               fremd: known ? null : host };
    });
    if (!entry) return;
    try {
      const documents = await this.tabs.inject(tabId);
      if (entry.fremd) await this.tabs.bar(tabId, { text: `Neue Adresse: ${host}. Hier auch ausfüllen?`, knoepfe: ['hier', 'abgeschickt', 'stoppen'] });
      else await this.fill(tabId, entry, documents, true);
    } catch (error) {
      await this.reportFailure(tabId, host, error);
    }
  }

  /** A failure on a page the tab has left says nothing: the next page has its own turn. */
  async reportFailure(tabId, host, error) {
    const current = await this.tabs.url(tabId).catch(() => null);
    if (hostOf(current) === host) await this.showError(tabId, error);
  }

  async fillHere(tabId) {
    const entry = await this.updateTab(tabId, (current) => ({
      ...current, hosts: current.fremd ? [...new Set([...current.hosts, current.fremd])] : current.hosts, fremd: null,
    }));
    if (!entry) return;
    try {
      await this.fill(tabId, entry, await this.tabs.inject(tabId), false);
    } catch (error) {
      await this.showError(tabId, error);
    }
  }

  /** A frame was built after the page had loaded: same check of the address, then only the new frames have work. */
  async frameLoaded(tabId) {
    const entry = await this.entry(tabId);
    if (!entry || entry.fremd) return;
    const host = hostOf(await this.tabs.url(tabId));
    if (!host || !entry.hosts.includes(host)) return;
    try {
      await this.fill(tabId, entry, await this.tabs.inject(tabId), false);
    } catch (error) {
      await this.reportFailure(tabId, host, error);
    }
  }

  /** The values go only to the documents that were checked: a page that leaves meanwhile gets nothing. */
  async fill(tabId, entry, documents, mayFollow) {
    const { werte, dateien } = await this.ask('GET', '/api/bewerben/daten', { id: entry.id });
    const results = await this.tabs.fill(tabId, documents, werte, dateien);
    const frames = Object.fromEntries(results.filter((r) => r.result).map((r) => [r.frameId, r.result]));
    const updated = await this.updateTab(tabId, (current) => ({ ...current, frames: { ...current.frames, ...frames } }));
    if (!updated) return;
    if (mayFollow && await this.followIfNoForm(tabId, updated, documents)) return;
    await this.publish(tabId);
  }

  /** Only the ad? Follow „Jetzt bewerben“ once, if the page has not built its form by then. The page names the link, so a
   * new address behind it waits for the person like any other. */
  async followIfNoForm(tabId, entry, documents) {
    const merged = mergeReports(entry.frames);
    if (entry.gefolgt || merged.felder || merged.anmeldung) return false;
    await this.sleep(FOLLOW_WAIT_MS);
    const current = await this.entry(tabId);
    if (!current || mergeReports(current.frames).felder) return false;
    const target = await this.tabs.follow(tabId, documents);
    await this.updateTab(tabId, (e) => ({ ...e, gefolgt: true }));
    if (target.url && hostOf(target.url)) {
      await this.tabs.navigate(tabId, target.url);
      return true;
    }
    return Boolean(target.geklickt);
  }

  /** A frame found something new, e.g. the next step of a form. */
  async frameReport(tabId, frameId, bericht) {
    if (!bericht || typeof bericht !== 'object') return;
    const entry = await this.updateTab(tabId, (current) => ({ ...current, frames: { ...current.frames, [frameId]: bericht } }));
    if (entry) await this.publish(tabId);
  }

  async publish(tabId) {
    const entry = await this.entry(tabId);
    if (!entry) return;
    const merged = mergeReports(entry.frames);
    if (merged.gefuellt && !entry.ausgefuellt) {
      // Not reached the app? The next report tries again.
      const reached = await this.ask('POST', '/api/bewerben/stand', { id: entry.id, stand: 'ausgefuellt' }).then(() => true, () => false);
      if (reached) await this.updateTab(tabId, (current) => ({ ...current, ausgefuellt: true }));
    }
    await this.tabs.bar(tabId, describeReport(merged));
  }

  /** A file of the application of this tab, whole: the extension asks for it in parts below the host's limit. */
  async file(tabId, key) {
    const entry = await this.entry(tabId);
    if (!entry || entry.fremd) throw new Error('Dieser Tab gehört nicht mehr zum Bewerben.');
    const part = (teil) => this.ask('GET', '/api/bewerben/datei', { id: entry.id, schluessel: key, teil: String(teil) });
    const first = await part(0);
    if (first.teile > MAX_PARTS) throw new Error('Die Datei ist zu gross.');
    let daten = first.daten;
    for (let teil = 1; teil < first.teile; teil += 1) daten += (await part(teil)).daten;
    return { name: first.name, typ: first.typ, daten };
  }

  /** The person said it is sent. */
  async sent(tabId) {
    const entry = await this.entry(tabId);
    if (!entry) return;
    try {
      const answer = await this.ask('POST', '/api/bewerben/abgeschickt', { id: entry.id });
      await this.removeTab(tabId);
      const notes = answer.hinweise && answer.hinweise.length ? ` ${answer.hinweise.join(' ')}` : '';
      await this.tabs.end(tabId, `Versand erfasst.${notes}`);
    } catch (error) {
      await this.showError(tabId, error);
    }
  }

  async stop(tabId) {
    if (await this.removeTab(tabId)) await this.tabs.end(tabId, GOES_ON);
  }

  async closed(tabId) {
    await this.removeTab(tabId);
  }

  async showError(tabId, error) {
    await this.tabs.bar(tabId, { text: error.message, fehler: true, aufmerksamkeit: true, knoepfe: ['stoppen'] }).catch(() => {});
  }
}
