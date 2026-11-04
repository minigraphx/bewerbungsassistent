// Content script on 127.0.0.1: only on pages of the app (meta tag), it shows that the extension is there and
// passes "start search" from the page to the extension and the progress back to the page.
(function () {
  if (!document.querySelector('meta[name="bewerbungsassistent"]')) return;
  // Also injected when the extension is installed, and the manifest may add it again: only one may answer the page.
  // A script of an earlier installation no longer counts, it has lost its connection.
  if (globalThis.bewerbungsassistentBridgeAlive?.()) return;
  globalThis.bewerbungsassistentBridgeAlive = () => Boolean(chrome.runtime?.id);
  const version = chrome.runtime.getManifest().version;
  const toPage = (message) => window.postMessage({ quelle: 'bewerbungsassistent-erweiterung', version, ...message }, location.origin);

  document.documentElement.dataset.bewerbungsassistentErweiterung = version;
  toPage({ art: 'da' });

  const port = chrome.runtime.connect({ name: 'app-seite' });
  port.onMessage.addListener((message) => toPage(message));

  window.addEventListener('message', (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const data = event.data;
    if (!data || data.quelle !== 'bewerbungsassistent-seite') return;
    if (data.art === 'suche-starten' || data.art === 'status') {
      chrome.runtime.sendMessage({ art: data.art }).then((answer) => toPage({ art: 'antwort', frage: data.art, antwort: answer }));
    }
    if (data.art === 'rav-starten') {
      chrome.runtime.sendMessage({ art: data.art, ids: data.ids })
        .then((answer) => toPage({ art: 'antwort', frage: data.art, antwort: answer }));
    }
    if (data.art === 'bewerben-starten') {
      chrome.runtime.sendMessage({ art: data.art, ids: data.ids, bestaetigt: data.bestaetigt })
        .then((answer) => toPage({ art: 'antwort', frage: data.art, antwort: answer }));
    }
  });
})();
