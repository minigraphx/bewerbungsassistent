// Service worker of the extension: starts a search when the person asks for it (popup or page of the app),
// reports the progress to the popup (storage) and to open pages of the app (ports of app-bridge.js).

import { AppConnection, explain } from './lib/app.js';
import { runSearch } from './lib/search.js';
import { ALLOWED, senderKind } from './lib/senders.js';

const LOAD_TIMEOUT_MS = 30000;
const appPorts = new Set();
let running = false;

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
    return { verbunden: true, version: hello.version, app: hello.app };
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

chrome.runtime.onMessage.addListener((message, sender, reply) => {
  const actions = { 'suche-starten': startSearch, status, 'app-oeffnen': openApp };
  const action = message && actions[message.art];
  if (!action) return false;
  trusted(sender)
    .then((kind) => {
      if (!kind || !ALLOWED[kind].has(message.art)) throw new Error('Nur die App und das Popup dürfen die Suche starten.');
      return action();
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
