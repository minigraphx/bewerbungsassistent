// Content script on 127.0.0.1: only on pages of the app (meta tag), it shows that the extension is there and
// passes "start search" from the page to the extension and the progress back to the page.
(function () {
  if (!document.querySelector('meta[name="bewerbungsassistent"]')) return;
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
  });
})();
