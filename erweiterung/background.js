// Service worker of the extension: starts a search when the person asks for it (popup or page of the app),
// reports the progress to the popup (storage) and to open pages of the app (ports of app-bridge.js).

import { AppConnection, explain } from './lib/app.js';
import { runSearch } from './lib/search.js';
import { followKey, readOpenPage } from './lib/sites.js';
import { adKey } from './lib/page-ad.js';
import { textSet } from './lib/popup-view.js';
import { watchingBar } from './lib/bar-text.js';
import { ALLOWED, BAR_ACTIONS, FORM_ACTIONS, RAV_ACTIONS, WATCH_ACTION, isRavSender, senderKind } from './lib/senders.js';
import { ALL_PAGES, ApplyRun } from './lib/apply.js';
import { RavRun, isRavPage } from './lib/rav.js';
import { showHits } from './lib/app-tab.js';
import { reloadForAppVersion, siteAccessControl } from './lib/reload.js';
import { SearchTabs, currentRun } from './lib/run-state.js';
import { checkCompany, structuredData } from './lib/kununu.js';
import { adQueue, fetchHitAds, fetchMissingAds, isNewStart } from './lib/missing-ads.js';

const LOAD_TIMEOUT_MS = 30000;
const RELOAD_DELAY_MS = 300;
const RELOADED_FOR = 'neu-geladen-fuer';
const ADS_FETCHED_FOR = 'inserate-geholt-fuer';
const appPorts = new Set();
let running = false;
let fetchingAds = false;
const adLoads = adQueue();
let adsCheckedOrigin = null; // the app page whose start was last looked at; a new start comes with a new port
let searchCancelled = false;
let versionChecked = false;
let watchedTab = null; // with „Zuschauen“ (MIN-370): the visible tab of the search
const searchTabs = new SearchTabs();

// Pages of the app that were already open when the extension was loaded get the bridge now, so the setup page
// shows „bereit“ without a reload. app-bridge.js itself checks that the page belongs to the app.
// Only when the extension itself is new: after a Chrome update the pages still have a working bridge.
chrome.runtime.onInstalled.addListener(async ({ reason }) => {
  if (reason !== 'install' && reason !== 'update') return;
  const tabs = await chrome.tabs.query({ url: 'http://127.0.0.1/*' });
  await Promise.allSettled(tabs.map((tab) => chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['app-bridge.js'] })));
});

// Runs inside the portal tab, in the same isolated world as the injected adapters. Must stay self-contained.
async function inPage(portal, method, args) {
  try {
    const adapter = globalThis.bewerbungsbegleiterPortals && globalThis.bewerbungsbegleiterPortals[portal];
    if (!adapter) return { ok: false, fehler: 'Anpassung für das Portal nicht geladen' };
    return { ok: true, value: await adapter[method](...args) };
  } catch (error) {
    return { ok: false, fehler: String((error && error.message) || error), changed: Boolean(error && error.changed) };
  }
}

function waitForLoad(tabId) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error('Die Seite lädt nicht.'));
    }, LOAD_TIMEOUT_MS);
    function listener(id, change) {
      if (id === tabId && change.status === 'complete') {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    }
    chrome.tabs.onUpdated.addListener(listener);
  });
}

const browserTabs = {
  async openTab(url, watching) {
    const tab = await chrome.tabs.create({ url, active: watching });
    if (watching) watchedTab = tab.id;
    searchTabs.opened(tab.id);
    try {
      await waitForLoad(tab.id);
    } catch (error) {
      if (watchedTab === tab.id) watchedTab = null;
      searchTabs.closedBySearch(tab.id);
      await chrome.tabs.remove(tab.id).catch(() => {});
      throw error;
    }
    return tab.id;
  },
  /** Only a note to the person: the search goes on if it cannot be shown. */
  async showWatching(tabId, portal) {
    try {
      await chrome.scripting.executeScript({ target: { tabId }, files: ['form/bar.js'] });
      const { textsatz } = await chrome.storage.local.get('textsatz');
      await chrome.tabs.sendMessage(tabId, { art: 'formular-balken', balken: { ...watchingBar(textsatz, portal), knoepfe: ['suche_abbrechen'] } }, { frameId: 0 });
    } catch {
      // the page is just changing; the next page shows it again
    }
  },
  async navigate(tabId, url) {
    const loaded = waitForLoad(tabId);
    await chrome.tabs.update(tabId, { url });
    await loaded;
  },
  async inject(tabId, files) {
    await chrome.scripting.executeScript({ target: { tabId }, files });
  },
  async run(tabId, portal, method, args) {
    const [result] = await chrome.scripting.executeScript({ target: { tabId }, func: inPage, args: [portal, method, args] });
    return (result && result.result) || { ok: false, fehler: 'Keine Antwort aus dem Tab' };
  },
  closeTab(tabId) {
    if (watchedTab === tabId) watchedTab = null; // closed by the search itself, that is no cancelling
    searchTabs.closedBySearch(tabId);
    return chrome.tabs.remove(tabId);
  },
  async readOpen(tabId) {
    const [result] = await chrome.scripting.executeScript({ target: { tabId }, func: readOpenPage });
    return (result && result.result) || { title: '', text: '', links: [], wall: '' };
  },
  hasAllPages: () => chrome.permissions.contains(ALL_PAGES),
  askAllPages: () => openPermissionForSearch(),
};

const OWN_KEY_SEEN = 'eigener-schluessel-gesehen';
/** The access to all pages for further sites (MIN-348); see followKey. */
const siteAccess = {
  remember: () => chrome.storage.local.set({ [OWN_KEY_SEEN]: true }),
  remembered: async () => Boolean((await chrome.storage.local.get(OWN_KEY_SEEN))[OWN_KEY_SEEN]),
  ...siteAccessControl({
    has: () => chrome.permissions.contains(ALL_PAGES),
    remove: () => chrome.permissions.remove(ALL_PAGES),
    forget: () => chrome.storage.local.remove(OWN_KEY_SEEN),
    busy: isBusy,
    restart: restartSoon,
  }),
};

/** A search, a list of open forms, a run waiting for access or the entries for the Job-Room: a reload would lose them. */
async function isBusy() {
  if (running || fetchingAds || adLoads.busy()) return true;
  const session = await chrome.storage.session.get([FORMS_KEY, RAV_KEY, PENDING_KEY]);
  return Object.keys(session[FORMS_KEY] || {}).length > 0 || Boolean(session[RAV_KEY]) || Boolean(session[PENDING_KEY]);
}

/** After the answer to the page is out; onInstalled gives open pages of the app a new bridge. */
function restartSoon() {
  setTimeout(() => chrome.runtime.reload(), RELOAD_DELAY_MS);
}

/** Only a package from a store has an update_url; the store updates that one itself. */
function followAppVersion(hello) {
  const manifest = chrome.runtime.getManifest();
  return reloadForAppVersion({
    appVersion: hello.version,
    appRunning: Boolean(hello.app),
    ownVersion: manifest.version,
    unpacked: !manifest.update_url,
    busy: isBusy,
    tried: async () => (await chrome.storage.local.get(RELOADED_FOR))[RELOADED_FOR] || null,
    remember: (version) => chrome.storage.local.set({ [RELOADED_FOR]: version }),
    restart: restartSoon,
  });
}

async function openPermissionForSearch() {
  await siteAccess.remember();
  const url = chrome.runtime.getURL('erlauben.html?fuer=suche');
  const [open] = await chrome.tabs.query({ url });
  if (open) await chrome.tabs.update(open.id, { active: true }); // one search after the other must not pile up tabs
  else await chrome.tabs.create({ url });
  return { geoeffnet: true };
}

async function publish(state) {
  await chrome.storage.session.set({ lauf: state });
  for (const port of appPorts) send(port, { art: 'lauf', lauf: state });
}

/** A page that went away in between must not stop the run's reports to the others. */
function send(port, message) {
  try {
    port.postMessage(message);
  } catch {
    appPorts.delete(port);
  }
}

/** The run as pages see it: what a stopped worker left as running is over. */
async function runNow() {
  const { lauf } = await chrome.storage.session.get('lauf');
  return currentRun(lauf, running);
}

async function startSearch() {
  if (running) return { laeuft: true };
  running = true;
  searchCancelled = false;
  searchTabs.clear();
  const app = new AppConnection();
  const started = new Date().toISOString();
  await publish({ zustand: 'laeuft', beginn: started, schritt: { phase: 'start' } });
  (async () => {
    try {
      const report = (step) => publish({ zustand: 'laeuft', beginn: started, schritt: step });
      const result = await runSearch({ app, browser: browserTabs, access: siteAccess, report, sleep: (ms) => new Promise((r) => setTimeout(r, ms)), cancelled: () => searchCancelled });
      await publish({ zustand: 'fertig', beginn: started, ende: new Date().toISOString(), ergebnis: result });
    } catch (error) {
      await publish({ zustand: 'fehler', beginn: started, fehler: error.message });
    } finally {
      app.close();
      running = false;
    }
  })();
  return { gestartet: true };
}

/** The popup's „Suche abbrechen“: the run stops after its current step, like the button in a watched tab. */
async function stopSearch() {
  if (running) searchCancelled = true;
  return { abgebrochen: running };
}

async function status() {
  const lauf = await runNow();
  const app = new AppConnection();
  try {
    const hello = await app.hello();
    // Only a running app is asked for the plan: opening the popup should not start it.
    const plan = hello.app ? await app.request('GET', '/api/suche/plan').then((answer) => answer.plan, () => null) : null;
    await followKey(plan, siteAccess);
    // The page that asks for access has no plan of its own: it speaks like the app from the last known plan.
    if (plan) await chrome.storage.local.set({ textsatz: textSet(plan) });
    // Staying on the old version is no reason to report the connection as lost.
    await followAppVersion(hello).catch(() => false);
    return { verbunden: true, version: hello.version, app: hello.app, plan, lauf };
  } catch (error) {
    return { verbunden: false, fehler: error.message || explain(''), lauf };
  } finally {
    app.close();
  }
}

const adTabs = {
  async openTab(url) {
    const tab = await chrome.tabs.create({ url, active: false });
    try {
      await waitForLoad(tab.id);
    } catch (error) {
      await chrome.tabs.remove(tab.id).catch(() => {});
      throw error;
    }
    return tab.id;
  },
  inject: browserTabs.inject,
  run: browserTabs.run,
  closeTab: (tabId) => chrome.tabs.remove(tabId),
};

/**
 * Missing ad texts (G37, #275): once per start of the app, the first time one of its pages connects. A search that
 * runs is left alone; the app hands out each job once per start, so a second page asking gets nothing.
 */
async function fetchAdsAtStart(pageUrl) {
  const origin = pageUrl ? new URL(pageUrl).origin : null;
  if (running || fetchingAds || origin === adsCheckedOrigin) return;
  adsCheckedOrigin = origin;
  fetchingAds = true;
  const app = new AppConnection();
  try {
    const hello = await app.hello();
    const last = (await chrome.storage.session.get(ADS_FETCHED_FOR))[ADS_FETCHED_FOR] || null;
    if (!isNewStart(hello, last)) return;
    await chrome.storage.session.set({ [ADS_FETCHED_FOR]: hello.einstieg });
    await adLoads.run(() => fetchMissingAds({ app, browser: adTabs, sleep }));
  } finally {
    fetchingAds = false;
    app.close();
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** „Alle prüfen“ (#209): the texts of these hits before the AI rates them, after any loading that already runs. */
function fetchAdsForHits(message) {
  return adLoads.run(async () => {
    const app = new AppConnection();
    try {
      return await fetchHitAds(message, { app, browser: adTabs, sleep, searching: () => running });
    } finally {
      app.close();
    }
  });
}

/** A page of the app is open, so the app runs: it may have just replaced the folder. Once per life of this worker. */
function checkVersionOnce() {
  if (versionChecked) return;
  versionChecked = true;
  const app = new AppConnection();
  app.hello().then(followAppVersion).catch(() => {}).finally(() => app.close()); // popup and setup page will tell
}

async function openApp() {
  const app = new AppConnection();
  try {
    // A request starts the app if it does not run; afterwards hello knows its address.
    await app.request('GET', '/api/suche/plan').catch(() => null);
    const hello = await app.hello();
    if (!hello.app) throw new Error('Die App läuft nicht.');
    await showHits(hello.app, chrome, hello.einstieg);
    return { ok: true };
  } finally {
    app.close();
  }
}

/** Address of the running app as it reports itself; asked again when a page does not match the last one. */
async function appUrl(pageUrl) {
  const { app } = await chrome.storage.session.get('app');
  if (app && pageUrl && pageUrl.startsWith(app)) return app;
  const connection = new AppConnection();
  try {
    const hello = await connection.hello();
    await chrome.storage.session.set({ app: hello.app || null });
    return hello.app || null;
  } catch {
    return null;
  } finally {
    connection.close();
  }
}

/** 'popup', 'app' or null; a page on 127.0.0.1 counts only when it is the running app. */
async function trusted(sender) {
  const kind = senderKind(sender, chrome.runtime.id, null);
  if (kind || !sender || !sender.tab) return kind;
  return senderKind(sender, chrome.runtime.id, await appUrl(sender.url));
}

/** Check or save the ad the popup read from the open tab; the result stays for the popup when it is opened again. */
async function pageAd(message, path, kept) {
  const ad = message.anzeige;
  if (!ad || typeof ad !== 'object' || typeof ad.text !== 'string') throw new Error('Das Inserat fehlt.');
  const app = new AppConnection();
  try {
    const answer = await app.request('POST', path, ad);
    const { seite } = await chrome.storage.session.get('seite');
    const key = adKey(ad);
    const earlier = seite && seite.key === key ? seite : { key };
    await chrome.storage.session.set({ seite: { ...earlier, [kept]: answer } });
    return answer;
  } finally {
    app.close();
  }
}

async function askApp(method, path, data) {
  const app = new AppConnection();
  try {
    return await app.request(method, path, data);
  } finally {
    app.close();
  }
}

let kununuBusy = false;

/**
 * „Prüfen“ on the page Firmen (G35, #189): one company at a time, in a tab in the background. What was read goes to
 * the app; a page that could not be read comes to the front, so the person sees it and can enter the value by hand.
 */
async function checkKununu(message) {
  if (kununuBusy) throw new Error('Es läuft schon eine Prüfung bei kununu.');
  if (typeof message.firma !== 'string' || !message.firma) throw new Error('Die Firma fehlt.');
  kununuBusy = true;
  let tabId = null;
  try {
    tabId = (await chrome.tabs.create({ url: 'about:blank', active: false })).id;
    const open = async (url) => {
      const loaded = waitForLoad(tabId);
      await chrome.tabs.update(tabId, { url });
      await loaded;
      const [result] = await chrome.scripting.executeScript({ target: { tabId }, func: structuredData });
      return (result && result.result) || { url, structured: [] };
    };
    const reading = await checkCompany({ name: message.name, link: message.link }, open);
    if (!reading) {
      await chrome.tabs.update(tabId, { active: true });
      tabId = null;
      return { gelesen: false };
    }
    return { gelesen: true, kununu: await askApp('POST', '/api/firmen/kununu', { firma: message.firma, ...reading }) };
  } finally {
    kununuBusy = false;
    if (tabId !== null) chrome.tabs.remove(tabId).catch(() => {});
  }
}

const FILLER_FILES = ['form/fields.js', 'form/filler.js', 'form/bar.js'];

// Only tabs of the list get these scripts, in all their frames: application systems often sit in embedded frames.
const formTabs = {
  async blank(active) {
    return (await chrome.tabs.create({ url: 'about:blank', active })).id;
  },
  async navigate(tabId, url) {
    await chrome.tabs.update(tabId, { url });
  },
  async activate(tabId) {
    await chrome.tabs.update(tabId, { active: true });
  },
  async url(tabId) {
    return (await chrome.tabs.get(tabId)).url;
  },
  /** The documents that have the scripts now; later steps go to these only, not to whatever the tab shows by then. */
  async inject(tabId) {
    const results = await chrome.scripting.executeScript({ target: { tabId, allFrames: true }, files: FILLER_FILES });
    return results.map(({ frameId, documentId }) => ({ frameId, documentId }));
  },
  async fill(tabId, documents, values, uploads, ai) {
    return chrome.scripting.executeScript({
      target: { tabId, documentIds: documents.map((d) => d.documentId) },
      func: (v, u, a) => globalThis.bewerbungsbegleiterFiller.fill(v, u, a),
      args: [values, uploads, ai],
    });
  },
  async follow(tabId, documents) {
    const top = documents.find((d) => d.frameId === 0);
    if (!top) return {};
    const [frame] = await chrome.scripting.executeScript({ target: { tabId, documentIds: [top.documentId] }, func: () => globalThis.bewerbungsbegleiterFiller.follow() });
    return (frame && frame.result) || {};
  },
  async bar(tabId, balken) {
    await chrome.tabs.sendMessage(tabId, { art: 'formular-balken', balken }, { frameId: 0 });
  },
  async end(tabId, balken) {
    await chrome.tabs.sendMessage(tabId, { art: 'formular-ende', balken }).catch(() => {});
  },
  async permissionPage() {
    await chrome.tabs.create({ url: chrome.runtime.getURL('erlauben.html') });
  },
};

const FORMS_KEY = 'formulare';
const PENDING_KEY = 'formulare-wartend';
const applyRun = new ApplyRun({
  ask: askApp,
  tabs: formTabs,
  store: {
    get: async () => (await chrome.storage.session.get(FORMS_KEY))[FORMS_KEY] || {},
    set: (forms) => chrome.storage.session.set({ [FORMS_KEY]: forms }),
  },
  pending: {
    get: async () => (await chrome.storage.session.get(PENDING_KEY))[PENDING_KEY] || null,
    set: (request) => chrome.storage.session.set({ [PENDING_KEY]: request }),
  },
  hasPermission: () => chrome.permissions.contains(ALL_PAGES),
  sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
});

const RAV_FILES = ['form/bar.js', 'form/rav-fields.js', 'form/rav-filler.js'];
const RAV_KEY = 'rav-lauf';
const ravRun = new RavRun({
  ask: askApp,
  tabs: {
    blank: () => formTabs.blank(true),
    navigate: formTabs.navigate,
    activate: formTabs.activate,
    exists: (tabId) => chrome.tabs.get(tabId).then(() => true, () => false),
    // Pinned to the document that was checked: the page may redirect to a login in between.
    async inject(tabId) {
      const [{ documentId, result }] = await chrome.scripting.executeScript({ target: { tabId }, func: () => location.href });
      if (isRavPage(result)) await chrome.scripting.executeScript({ target: { tabId, documentIds: [documentId] }, files: RAV_FILES });
    },
    bar: formTabs.bar,
    end: formTabs.end,
  },
  store: {
    get: async () => (await chrome.storage.session.get(RAV_KEY))[RAV_KEY] || null,
    set: (run) => chrome.storage.session.set({ [RAV_KEY]: run }),
  },
  sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
});

chrome.tabs.onUpdated.addListener((tabId, change, tab) => {
  if (change.status !== 'complete' || !tab.url) return;
  applyRun.loaded(tabId, tab.url);
  ravRun.loaded(tabId, tab.url).catch(() => { /* the tab went away while loading */ });
});
chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabId === watchedTab) watchedTab = null;
  if (searchTabs.removed(tabId) && running) searchCancelled = true;
  applyRun.closed(tabId);
  ravRun.closed(tabId);
});

function ravAction(message, tabId) {
  const actions = {
    'rav-wartet': () => ravRun.waiting(tabId),
    'rav-daten': () => ravRun.values(tabId),
    'rav-stand': () => ravRun.report(tabId, message),
    'rav-gespeichert': () => ravRun.entered(tabId, message.id),
    'rav-kein-formular': () => ravRun.noForm(tabId),
    'rav-eingetragen': () => ravRun.entered(tabId, message.id),
    'rav-ueberspringen': () => ravRun.skip(tabId, message.id),
    'rav-stoppen': () => ravRun.stop(tabId),
    'rav-zum-formular': () => ravRun.toForm(tabId),
  };
  return actions[message.art]();
}

/** Messages of the script in the Job-Room tab; the run itself checks that the tab is its own. */
function fromRav(message, sender, reply) {
  Promise.resolve().then(() => {
    if (!isRavSender(sender, chrome.runtime.id)) throw new Error('Dieser Tab gehört nicht zum Eintragen im RAV.');
    return ravAction(message, sender.tab.id);
  }).then((answer) => reply(answer || {}), (error) => reply({ fehler: error.message }));
  return true;
}

function formAction(message, sender) {
  const tabId = sender.tab.id;
  const actions = {
    'formular-stand': () => applyRun.frameReport(tabId, sender.frameId, message.bericht),
    'formular-datei': () => applyRun.file(tabId, message.schluessel),
    'formular-rahmen': () => applyRun.frameLoaded(tabId),
    'formular-ki': () => applyRun.assist(tabId, message.felder),
    'formular-hier': () => applyRun.fillHere(tabId),
    'formular-abgeschickt': () => applyRun.sent(tabId),
    'formular-ordner': () => applyRun.openFolder(tabId),
    'formular-stoppen': () => applyRun.stop(tabId),
  };
  return actions[message.art]();
}

/** Messages of the scripts in a form: only from a tab of the list, and the bar only exists in the top frame. */
function fromForm(message, sender, reply) {
  const known = sender.id === chrome.runtime.id && sender.tab && applyRun.entry(sender.tab.id);
  Promise.resolve(known).then((entry) => {
    if (!entry || (BAR_ACTIONS.has(message.art) && sender.frameId !== 0)) throw new Error('Dieser Tab gehört nicht zum Bewerben.');
    return formAction(message, sender);
  }).then((answer) => reply(answer || {}), (error) => reply({ fehler: error.message }));
  return true;
}

chrome.runtime.onMessage.addListener((message, sender, reply) => {
  if (message && RAV_ACTIONS.has(message.art)) return fromRav(message, sender, reply);
  if (message && message.art === WATCH_ACTION) {
    if (sender.id === chrome.runtime.id && sender.tab && sender.tab.id === watchedTab) searchCancelled = true;
    return false;
  }
  if (message && (FORM_ACTIONS.has(message.art) || BAR_ACTIONS.has(message.art))) return fromForm(message, sender, reply);
  const actions = {
    'suche-starten': startSearch,
    'suche-stoppen': stopSearch,
    status,
    'app-oeffnen': openApp,
    'seite-pruefen': (m) => pageAd(m, '/api/seite/pruefen', 'pruefung'),
    'seite-speichern': (m) => pageAd(m, '/api/seite/speichern', 'gespeichert'),
    'bewerben-starten': (m) => applyRun.start(m),
    'bewerben-weiter': () => applyRun.resume(),
    'rav-starten': (m) => ravRun.start(m),
    'zugriff-erlauben': () => openPermissionForSearch(),
    'zugriff-abgeben': () => siteAccess.release(),
    'kununu-pruefen': checkKununu,
    'inserate-holen': fetchAdsForHits,
  };
  const action = message && actions[message.art];
  if (!action) return false;
  trusted(sender)
    .then((kind) => {
      if (!kind || !ALLOWED[kind].has(message.art)) throw new Error('Nur die App und das Popup dürfen die Suche starten.');
      return action(message);
    })
    .then(reply, (error) => reply({ fehler: error.message }));
  return true; // answer comes later
});

chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== 'app-seite') {
    port.disconnect();
    return;
  }
  trusted(port.sender).then((kind) => {
    if (kind !== 'app') {
      port.disconnect();
      return;
    }
    appPorts.add(port);
    port.onDisconnect.addListener(() => appPorts.delete(port));
    // A page that connects during a run has missed its start; how a run ended it asks with „status“ when it waits.
    runNow().then((lauf) => { if (lauf && lauf.zustand === 'laeuft') send(port, { art: 'lauf', lauf }); });
    checkVersionOnce();
    fetchAdsAtStart(port.sender && port.sender.url).catch(() => {}); // what was not loaded the app names itself
  });
});
