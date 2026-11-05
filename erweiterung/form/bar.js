// The bar at the edge of the tab of a form (MIN-346, MIN-347), only in the top frame: the state, the colours, and the buttons
// that are the person's decision. In a closed shadow root, so the page cannot reach them; the host element keeps its
// look with important inline styles. A click only counts when a person made it on a bar that can be seen.
(function () {
  'use strict';
  if (globalThis.bewerbungsassistentBar || window !== window.top) return;
  const END_WAIT_MS = 6000;
  const IN_THE_DIALOG = 'Dateien von dort ins Formular ziehen. Oder im Datei-Dialog: Mac ⇧⌘G und Pfad einfügen, Windows Pfad ins Feld „Dateiname“.';
  const ATTENTION = '⚠ ';
  const STYLE = `
    :host { all: initial; }
    .bar { position: fixed; left: 0; right: 0; bottom: 0; z-index: 2147483647; display: flex; flex-wrap: wrap; gap: 8px 12px;
      align-items: center; padding: 10px 14px; background: #1f2933; color: #fff; font: 14px/1.4 system-ui, sans-serif;
      box-shadow: 0 -2px 8px rgba(0,0,0,.35); }
    .bar.oben { top: 0; bottom: auto; }
    .text { flex: 1 1 280px; }
    .fehler { color: #ffb4a8; }
    ul { margin: 4px 0 0; padding-left: 18px; }
    .farben { display: flex; gap: 10px; font-size: 12px; }
    .farben i { display: inline-block; width: 10px; height: 10px; margin-right: 4px; border-radius: 2px; }
    button { font: inherit; padding: 4px 10px; border-radius: 4px; border: 1px solid #9aa5b1; background: transparent; color: #fff; cursor: pointer; }
    button.haupt { background: #fff; color: #1f2933; border-color: #fff; font-weight: 600; }
    .pfad { flex: 1 1 100%; display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: center; font-size: 13px; }
    .pfad code { font: 12px ui-monospace, monospace; word-break: break-all; user-select: all; }
    .pfad small { flex: 1 1 100%; color: #cbd2d9; }
  `;
  const HOST_STYLE = [['all', 'initial'], ['display', 'block'], ['opacity', '1'], ['visibility', 'visible']];
  const LEGEND = [['#2e7d32', 'ausgefüllt'], ['#ef6c00', 'offen'], ['#c62828', 'selbst bestätigen'], ['#1565c0', 'von der KI, bitte prüfen']];
  const BUTTONS = {
    hier: ['Hier ausfüllen', 'formular-hier', 'haupt'],
    ordner: ['Dateien im Ordner zeigen', 'formular-ordner', ''],
    abgeschickt: ['Abgeschickt? Ja', 'formular-abgeschickt', 'haupt'],
    stoppen: ['Nicht mehr ausfüllen', 'formular-stoppen', ''],
    suche_abbrechen: ['Suche abbrechen', 'suche-abbrechen', ''],
    rav_ja: ['Eingetragen? Ja', 'rav-eingetragen', ''],
    rav_ueberspringen: ['Überspringen', 'rav-ueberspringen', ''],
    rav_stoppen: ['Stoppen', 'rav-stoppen', ''],
    rav_formular: ['Zum Formular', 'rav-zum-formular', 'haupt'],
  };

  let host = null;
  let root = null;
  let atTop = false;

  function element(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  }

  function send(art, id) {
    chrome.runtime.sendMessage({ art, id }).catch(() => { /* the extension was reloaded */ });
  }

  function barVisible() {
    const style = getComputedStyle(host);
    return style.opacity === '1' && style.visibility === 'visible' && style.display !== 'none';
  }

  /** `id` says which entry the bar is about while it is shown: a late click cannot hit another one (MIN-347). */
  function button([text, art, className], id) {
    const el = element('button', className, text);
    el.type = 'button';
    el.addEventListener('click', (event) => { if (event.isTrusted && barVisible()) send(art, id); });
    return el;
  }

  function folderLine(path) {
    const line = element('div', 'pfad');
    const copy = element('button', '', 'Pfad kopieren');
    copy.type = 'button';
    copy.addEventListener('click', async (event) => {
      if (!event.isTrusted || !barVisible()) return;
      try {
        await navigator.clipboard.writeText(path);
        copy.textContent = 'Kopiert';
      } catch {
        copy.textContent = 'Bitte von Hand markieren'; // a page can forbid the clipboard
      }
    });
    line.append(element('code', '', path), copy, element('small', '', IN_THE_DIALOG));
    return line;
  }

  function moveButton(bar) {
    const el = element('button', '', '↕');
    el.type = 'button';
    el.title = 'Balken oben oder unten zeigen';
    el.addEventListener('click', () => {
      atTop = !atTop;
      bar.classList.toggle('oben', atTop);
    });
    return el;
  }

  function legend(kind) {
    const box = element('div', 'farben');
    for (const [color, text] of kind === 'rav' ? LEGEND.slice(0, 2) : LEGEND) {
      const item = element('span');
      const swatch = element('i');
      swatch.style.background = color;
      item.append(swatch, text);
      box.append(item);
    }
    return box;
  }

  function ensureRoot() {
    if (host && host.isConnected) return root;
    host = document.createElement('div');
    for (const [name, value] of HOST_STYLE) host.style.setProperty(name, value, 'important');
    root = host.attachShadow({ mode: 'closed' });
    document.documentElement.append(host);
    return root;
  }

  function setTitleMark(on) {
    const marked = document.title.startsWith(ATTENTION);
    if (on && !marked) document.title = ATTENTION + document.title;
    if (!on && marked) document.title = document.title.slice(ATTENTION.length);
  }

  function show(balken) {
    const bar = element('div', atTop ? 'bar oben' : 'bar');
    const text = element('div', balken.fehler ? 'text fehler' : 'text', balken.text);
    if (balken.hinweise && balken.hinweise.length) {
      const list = element('ul');
      list.append(...balken.hinweise.map((hint) => element('li', '', hint)));
      text.append(list);
    }
    const style = element('style');
    style.textContent = STYLE;
    bar.append(text);
    if (balken.farben) bar.append(legend(balken.farben));
    bar.append(...(balken.knoepfe || []).map((key) => button(BUTTONS[key], balken.id)), moveButton(bar));
    if (balken.pfad) bar.append(folderLine(balken.pfad)); // the root is closed: the page does not learn the path
    ensureRoot().replaceChildren(style, bar);
    setTitleMark(Boolean(balken.aufmerksamkeit));
  }

  function end(text) {
    show({ text });
    setTimeout(() => {
      if (host) host.remove();
      host = null;
    }, END_WAIT_MS);
  }

  globalThis.bewerbungsassistentBar = { show };
  chrome.runtime.onMessage.addListener((message) => {
    if (message && message.art === 'formular-balken') show(message.balken);
    if (message && message.art === 'formular-ende') end(message.text);
  });
})();
