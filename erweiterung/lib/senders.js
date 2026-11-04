// Who may talk to the service worker: the popup of the extension and the page of the running app.
// The content script runs on every port of 127.0.0.1 (match patterns ignore the port), so a page there is
// only trusted when its origin is the address the app itself reports over Native Messaging.

/** What the popup and the app page may ask for. */
export const ALLOWED = {
  popup: new Set(['suche-starten', 'status', 'app-oeffnen', 'seite-pruefen', 'seite-speichern']),
  app: new Set(['suche-starten', 'status', 'bewerben-starten']),
  erlauben: new Set(['bewerben-weiter']),
};

/** What a form in a tab of a run may ask for (MIN-346); the buttons of the bar only from the top frame. */
export const FORM_ACTIONS = new Set(['formular-stand', 'formular-datei', 'formular-rahmen', 'formular-ki']);
export const BAR_ACTIONS = new Set(['formular-hier', 'formular-abgeschickt', 'formular-stoppen']);

function origin(url) {
  try {
    return new URL(url).origin;
  } catch {
    return null;
  }
}

/**
 * 'popup', 'erlauben' or 'app' for a trusted sender, otherwise null.
 * @param {{id?: string, url?: string, tab?: object}} sender  as chrome.runtime passes it
 * @param {string} extensionId
 * @param {string|null} appUrl  address of the running app, from `hallo`
 * @returns {'popup'|'erlauben'|'app'|null}
 */
export function senderKind(sender, extensionId, appUrl) {
  if (!sender || sender.id !== extensionId || !sender.url) return null;
  if (!sender.tab && sender.url.startsWith(`chrome-extension://${extensionId}/`)) return 'popup';
  if (sender.tab && sender.url === `chrome-extension://${extensionId}/erlauben.html`) return 'erlauben';
  if (sender.tab && appUrl && origin(sender.url) === origin(appUrl)) return 'app';
  return null;
}
