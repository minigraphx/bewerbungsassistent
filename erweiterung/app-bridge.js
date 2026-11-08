// Content script on 127.0.0.1: only on pages of the app (meta tag), it shows that the extension is there and
// passes "start search" from the page to the extension and the progress back to the page.
(function () {
  if (!document.querySelector('meta[name="bewerbungsbegleiter"]')) return;
  // Also injected when the extension is installed, and the manifest may add it again: only one may answer the page.
  // A script of an earlier installation no longer counts, it has lost its connection.
  if (globalThis.bewerbungsbegleiterBridgeAlive?.()) return;
  globalThis.bewerbungsbegleiterBridgeAlive = () => Boolean(chrome.runtime?.id);
  const version = chrome.runtime.getManifest().version;
  const toPage = (message) => window.postMessage({ quelle: 'bewerbungsbegleiter-erweiterung', version, ...message }, location.origin);

  document.documentElement.dataset.bewerbungsbegleiterErweiterung = version;
  // The stores add update_url. Only a hand-loaded extension can be told to reload when the app brings another version.
  if (!chrome.runtime.getManifest().update_url) document.documentElement.dataset.bewerbungsbegleiterEntpackt = 'true';
  toPage({ art: 'da' });

  const NOT_REACHED = 'Die Erweiterung antwortet nicht. Bitte die Seite neu laden.';

  // The browser stops an idle service worker and with it this port; a new worker knows only ports made after it
  // started. So the port is made again before the next message, and the worker sends the current run on connect.
  let port = null;
  function connect() {
    if (port) return;
    try {
      port = chrome.runtime.connect({ name: 'app-seite' });
    } catch {
      return; // the extension was reloaded: the message below fails as well and tells the page
    }
    const own = port;
    own.onMessage.addListener((message) => toPage(message));
    own.onDisconnect.addListener(() => {
      if (port === own) port = null;
    });
  }
  connect();

  function ask(message) {
    connect();
    Promise.resolve()
      .then(() => chrome.runtime.sendMessage(message))
      .catch(() => ({ fehler: NOT_REACHED }))
      .then((answer) => toPage({ art: 'antwort', frage: message.art, antwort: answer || { fehler: NOT_REACHED } }));
  }

  window.addEventListener('message', (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const data = event.data;
    if (!data || data.quelle !== 'bewerbungsbegleiter-seite') return;
    if (['zugriff-erlauben', 'zugriff-abgeben', 'suche-starten', 'status'].includes(data.art)) ask({ art: data.art });
    if (data.art === 'rav-starten') ask({ art: data.art, ids: data.ids });
    if (data.art === 'bewerben-starten') ask({ art: data.art, ids: data.ids, bestaetigt: data.bestaetigt });
  });
})();
