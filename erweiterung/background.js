// Service worker of the extension: starts a search when the person asks for it (popup or page of the app),
// reports the progress to the popup (storage) and to open pages of the app (ports of app-bridge.js).

import { AppConnection, explain } from './lib/app.js';
import { runSearch } from './lib/search.js';
import { adKey } from './lib/page-ad.js';
import { ALLOWED, BAR_ACTIONS, FORM_ACTIONS, senderKind } from './lib/senders.js';
import { ALL_PAGES, ApplyRun } from './lib/apply.js';

const LOAD_TIMEOUT_MS = 30000;
const appPorts = new Set();
let running = false;

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
    const adapter = globalThis.bewerbungsassistentPortals && globalThis.bewerbungsassistentPortals[portal];
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
  async openTab(url) {
    const tab = await chrome.tabs.create({ url, active: false });
    await waitForLoad(tab.id);
    return tab.id;
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
    return chrome.tabs.remove(tabId);
  },
};

async function publish(state) {
  await chrome.storage.session.set({ lauf: state });
  for (const port of appPorts) port.postMessage({ art: 'lauf', lauf: state });
}

async function startSearch() {
  if (running) return { laeuft: true };
  running = true;
  const app = new AppConnection();
  const started = new Date().toISOString();
  await publish({ zustand: 'laeuft', beginn: started, schritt: { phase: 'start' } });
  (async () => {
    try {
      const report = (step) => publish({ zustand: 'laeuft', beginn: started, schritt: step });
      const result = await runSearch({ app, browser: browserTabs, report, sleep: (ms) => new Promise((r) => setTimeout(r, ms)) });
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

async function status() {
  const app = new AppConnection();
  try {
    const hello = await app.hello();
    // Only a running app is asked for the plan: opening the popup should not start it.
    const plan = hello.app ? await app.request('GET', '/api/suche/plan').then((answer) => answer.plan, () => null) : null;
    return { verbunden: true, version: hello.version, app: hello.app, plan };
  } catch (error) {
    return { verbunden: false, fehler: error.message || explain('') };
  } finally {
    app.close();
  }
}

async function openApp() {
  const app = new AppConnection();
  try {
    // A request starts the app if it does not run; afterwards hello knows its address.
    await app.request('GET', '/api/suche/plan').catch(() => null);
    const hello = await app.hello();
    if (!hello.app) throw new Error('Die App läuft nicht.');
    await chrome.tabs.create({ url: `${hello.app}treffer` });
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
  async fill(tabId, documents, values, uploads) {
    return chrome.scripting.executeScript({
      target: { tabId, documentIds: documents.map((d) => d.documentId) },
      func: (v, u) => globalThis.bewerbungsassistentFiller.fill(v, u),
      args: [values, uploads],
    });
  },
  async follow(tabId, documents) {
    const top = documents.find((d) => d.frameId === 0);
    if (!top) return {};
    const [frame] = await chrome.scripting.executeScript({ target: { tabId, documentIds: [top.documentId] }, func: () => globalThis.bewerbungsassistentFiller.follow() });
    return (frame && frame.result) || {};
  },
  async bar(tabId, balken) {
    await chrome.tabs.sendMessage(tabId, { art: 'formular-balken', balken }, { frameId: 0 });
  },
  async end(tabId, text) {
    await chrome.tabs.sendMessage(tabId, { art: 'formular-ende', text }).catch(() => {});
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

chrome.tabs.onUpdated.addListener((tabId, change, tab) => {
  if (change.status === 'complete' && tab.url) applyRun.loaded(tabId, tab.url);
});
chrome.tabs.onRemoved.addListener((tabId) => applyRun.closed(tabId));

function formAction(message, sender) {
  const tabId = sender.tab.id;
  const actions = {
    'formular-stand': () => applyRun.frameReport(tabId, sender.frameId, message.bericht),
    'formular-datei': () => applyRun.file(tabId, message.schluessel),
    'formular-rahmen': () => applyRun.frameLoaded(tabId),
    'formular-hier': () => applyRun.fillHere(tabId),
    'formular-abgeschickt': () => applyRun.sent(tabId),
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
  if (message && (FORM_ACTIONS.has(message.art) || BAR_ACTIONS.has(message.art))) return fromForm(message, sender, reply);
  const actions = {
    'suche-starten': startSearch,
    status,
    'app-oeffnen': openApp,
    'seite-pruefen': (m) => pageAd(m, '/api/seite/pruefen', 'pruefung'),
    'seite-speichern': (m) => pageAd(m, '/api/seite/speichern', 'gespeichert'),
    'bewerben-starten': (m) => applyRun.start(m),
    'bewerben-weiter': () => applyRun.resume(),
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
  });
});
