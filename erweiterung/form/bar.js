// The bar at the edge of the tab of a form (MIN-346, MIN-347; design Erweiterung-Leisten, MIN-369), only in the top
// frame: the state, the colours of the marks, and the buttons that are the person's decision. In a closed shadow root, so
// the page cannot reach them; the host element keeps its look with important inline styles. A click only counts when a
// person made it on a bar that can be seen. The bar takes its own room at the edge of the page, so it covers no field;
// it is always dark, also in a dark system setting.
(function () {
  'use strict';
  if (globalThis.bewerbungsbegleiterBar || window !== window.top) return;
  const IN_THE_DIALOG = 'Oder die Dateien von dort ins Formular ziehen. Im Dateidialog hilft auch: Mac ⇧⌘G und Pfad einfügen, Windows Pfad ins Feld „Dateiname“.';
  const ATTENTION = '⚠ ';
  const STYLE = `
    :host { all: initial; }
    .bar { position: fixed; left: 0; right: 0; bottom: 0; z-index: 2147483647; box-sizing: border-box; display: flex; flex-wrap: wrap;
      gap: 12px 24px; align-items: center; justify-content: space-between; padding: 14px 16px; background: #27333f; color: #ffffff;
      font: 400 14px/20px "DM Sans", system-ui, -apple-system, "Segoe UI", sans-serif; box-shadow: 0 -2px 10px rgba(0,0,0,.3); }
    .bar.oben { top: 0; bottom: auto; box-shadow: 0 2px 10px rgba(0,0,0,.3); }
    .text { flex: 1 1 480px; min-width: 0; }
    .brand { margin: 0 0 2px; font-size: 13px; font-weight: 700; color: #c9d4e2; }
    .titel { margin: 0; font-weight: 700; }
    .zeile { margin: 2px 0 0; color: #dfe6ef; }
    .fehler .titel { color: #ffb4a8; }
    ul { margin: 4px 0 0; padding-left: 18px; color: #dfe6ef; }
    .farben { display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 8px; font-size: 13px; color: #dfe6ef; }
    .farben span { display: inline-flex; align-items: center; gap: 6px; }
    .farben i { display: inline-block; width: 9px; height: 9px; background: #27333f; }
    .knoepfe { flex: 0 1 auto; max-width: 560px; display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
    button { font: inherit; font-weight: 500; min-height: 32px; padding: 0 12px; border-radius: 6px; border: 1px solid #c9d4e2;
      background: transparent; color: #ffffff; cursor: pointer; }
    button:hover { background: rgba(255,255,255,.08); }
    button.haupt { background: #ffffff; color: #27333f; border-color: #ffffff; font-weight: 700; }
    button.haupt:hover { background: #e8edf3; }
    button:focus-visible { outline: 2px solid #ffffff; outline-offset: 2px; }
    .pfad { margin-top: 6px; }
    .pfad code { display: block; margin: 2px 0; font: 12px/18px ui-monospace, monospace; color: #ffffff; word-break: break-all; user-select: all; }
    .pfad small { display: block; font-size: 12px; line-height: 16px; color: #c9d4e2; }
  `;
  const HOST_STYLE = [['all', 'initial'], ['display', 'block'], ['opacity', '1'], ['visibility', 'visible']];
  // The marks in the form (filler.js) differ in colour and in line, so they also work without colours.
  const LEGEND = [
    ['2px solid #4caf50', 'ausgefüllt'], ['2px dashed #ff9800', 'offen'], ['3px double #ef5350', 'selbst bestätigen'],
    ['2px dotted #64b5f6', 'Entwurf der KI, bitte prüfen'],
  ];
  const BUTTONS = {
    hier: ['Hier ausfüllen', 'formular-hier'],
    nicht_hier: ['Nicht hier', 'formular-stoppen'],
    ordner: ['Dateien im Ordner zeigen', 'formular-ordner'],
    abgeschickt: ['Abgeschickt? Ja', 'formular-abgeschickt'],
    stoppen: ['Nicht mehr ausfüllen', 'formular-stoppen'],
    suche_abbrechen: ['Suche abbrechen', 'suche-abbrechen'],
    rav_ja: ['Eingetragen? Ja', 'rav-eingetragen'],
    rav_ueberspringen: ['Überspringen', 'rav-ueberspringen'],
    rav_stoppen: ['Beenden', 'rav-stoppen'],
    rav_formular: ['Zum Formular', 'rav-zum-formular'],
  };

  let host = null;
  let root = null;
  let atTop = false;
  let sizeWatch = null;
  let room = null; // the margin of the page before the bar took its room

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

  function personClick(el, action) {
    el.addEventListener('click', (event) => { if (event.isTrusted && barVisible()) action(); });
  }

  /** `id` says which entry the bar is about while it is shown: a late click cannot hit another one (MIN-347). */
  function button([text, art], id, main) {
    const el = element('button', main ? 'haupt' : '', text);
    el.type = 'button';
    personClick(el, () => send(art, id));
    return el;
  }

  function copyButton(path) {
    const copy = element('button', '', 'Ordnerpfad kopieren');
    copy.type = 'button';
    personClick(copy, async () => {
      try {
        await navigator.clipboard.writeText(path);
        copy.textContent = 'Kopiert';
      } catch {
        copy.textContent = 'Bitte von Hand markieren'; // a page can forbid the clipboard
      }
    });
    return copy;
  }

  function folderLines(balken) {
    const box = element('div', 'pfad');
    box.append(element('p', 'zeile', balken.pfadText || 'Den Dateidialog öffnet der Browser. Dort diesen Ordner wählen:'),
      element('code', '', balken.pfad), element('small', '', IN_THE_DIALOG));
    return box;
  }

  /** The page moves by the height of the bar: the bar takes its own room and covers nothing. */
  function makeRoom(bar) {
    const page = document.documentElement;
    if (!room) room = { top: page.style.getPropertyValue('margin-top'), bottom: page.style.getPropertyValue('margin-bottom') };
    const apply = () => {
      const height = `${Math.ceil(bar.getBoundingClientRect().height)}px`;
      page.style.setProperty(atTop ? 'margin-top' : 'margin-bottom', height, 'important');
      page.style.setProperty(atTop ? 'margin-bottom' : 'margin-top', atTop ? room.bottom : room.top);
    };
    if (sizeWatch) sizeWatch.disconnect();
    sizeWatch = new ResizeObserver(apply);
    sizeWatch.observe(bar);
    apply();
  }

  function giveRoomBack() {
    if (sizeWatch) sizeWatch.disconnect();
    sizeWatch = null;
    if (!room) return;
    const page = document.documentElement;
    page.style.setProperty('margin-top', room.top);
    page.style.setProperty('margin-bottom', room.bottom);
    room = null;
  }

  function moveButton(bar) {
    const el = element('button', '', atTop ? 'Leiste nach unten' : 'Leiste nach oben');
    el.type = 'button';
    el.addEventListener('click', () => {
      atTop = !atTop;
      bar.classList.toggle('oben', atTop);
      el.textContent = atTop ? 'Leiste nach unten' : 'Leiste nach oben';
      makeRoom(bar);
    });
    return el;
  }

  function legend(kind) {
    const box = element('div', 'farben');
    for (const [line, text] of kind === 'rav' ? LEGEND.slice(0, 2) : LEGEND) {
      const item = element('span');
      const swatch = element('i');
      swatch.style.outline = line;
      swatch.style.outlineOffset = '1px';
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

  function remove() {
    giveRoomBack();
    if (host) host.remove();
    host = null;
    setTitleMark(false);
  }

  /**
   * balken: { titel, text, hinweise, farben (true|'rav'), knoepfe, id, pfad, pfadText, fehler, aufmerksamkeit, ende }.
   * The first button is the main one. With `ende` the bar only offers to close itself.
   */
  function show(balken) {
    const bar = element('div', atTop ? 'bar oben' : 'bar');
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', 'Bewerbungsbegleiter');
    const text = element('div', balken.fehler ? 'text fehler' : 'text');
    text.append(element('p', 'brand', 'Bewerbungsbegleiter'));
    if (balken.titel) text.append(element('p', 'titel', balken.titel));
    if (balken.text) text.append(element('p', balken.titel ? 'zeile' : 'titel', balken.text));
    if (balken.hinweise && balken.hinweise.length) {
      const list = element('ul');
      list.append(...balken.hinweise.map((hint) => element('li', '', hint)));
      text.append(list);
    }
    if (balken.pfad) text.append(folderLines(balken)); // the root is closed: the page does not learn the path
    if (balken.farben) text.append(legend(balken.farben));
    const buttons = element('div', 'knoepfe');
    if (balken.ende) {
      const close = element('button', '', 'Leiste schliessen');
      close.type = 'button';
      personClick(close, remove);
      buttons.append(close);
    } else {
      const keys = balken.knoepfe || [];
      buttons.append(...keys.map((key, index) => button(BUTTONS[key], balken.id, index === 0)));
      if (balken.pfad) buttons.append(copyButton(balken.pfad));
      if (!keys.includes('suche_abbrechen')) buttons.append(moveButton(bar));
    }
    const style = element('style');
    style.textContent = STYLE;
    bar.append(text, buttons);
    ensureRoot().replaceChildren(style, bar);
    makeRoom(bar);
    setTitleMark(Boolean(balken.aufmerksamkeit));
  }

  globalThis.bewerbungsbegleiterBar = { show };
  chrome.runtime.onMessage.addListener((message) => {
    if (message && message.art === 'formular-balken') show(message.balken);
    if (message && message.art === 'formular-ende') show({ ...(message.balken || { titel: message.text }), ende: true });
  });
})();
