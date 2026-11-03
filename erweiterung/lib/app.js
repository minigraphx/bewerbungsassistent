// Connection to the app over Native Messaging: one port per search, answers matched by id.

export const HOST = 'bewerbungsassistent';
const MISSING = /not found|nicht gefunden|forbidden|exited|beendet/i;
export const APP_MISSING =
  'Die App Bewerbungsassistent wurde nicht gefunden. Bitte die App installieren und einmal starten; '
  + 'sie meldet sich dabei beim Browser an.';

/** Readable message for an error of the browser's Native Messaging. */
export function explain(message) {
  return MISSING.test(message || '') ? APP_MISSING : `Verbindung zur App unterbrochen (${message || 'unbekannt'}).`;
}

export class AppConnection {
  constructor(runtime = chrome.runtime) {
    this.runtime = runtime;
    this.port = null;
    this.next = 1;
    this.pending = new Map();
  }

  open() {
    if (this.port) return;
    this.port = this.runtime.connectNative(HOST);
    this.port.onMessage.addListener((reply) => {
      const waiting = this.pending.get(reply && reply.id);
      if (!waiting) return;
      this.pending.delete(reply.id);
      if (reply.ok) waiting.resolve(reply.daten);
      else waiting.reject(new Error(reply.fehler || 'Fehler in der App'));
    });
    this.port.onDisconnect.addListener(() => {
      const error = new Error(explain(this.runtime.lastError && this.runtime.lastError.message));
      this.port = null;
      for (const waiting of this.pending.values()) waiting.reject(error);
      this.pending.clear();
    });
  }

  send(message) {
    this.open();
    const id = this.next++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.port.postMessage({ ...message, id });
    });
  }

  hello() {
    return this.send({ art: 'hallo' });
  }

  request(method, path, data) {
    return this.send({ art: 'anfrage', methode: method, pfad: path, daten: data });
  }

  close() {
    if (this.port) this.port.disconnect();
    this.port = null;
  }
}
