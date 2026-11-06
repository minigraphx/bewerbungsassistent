// Popup of the extension (design: Erweiterung-Popups, MIN-369): connection to the app, the search with its last result
// or its progress per portal, the ad of the open page. Texts follow the setup of the app (popup-view.js).
import { describePlan, describeRun } from './lib/progress.js';
import { lastSearch, portalRows, textSet, words } from './lib/popup-view.js';
import { showOpenPage } from './page-panel.js';

const $ = (id) => document.getElementById(id);
let plan = null;
let appRunning = false;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function setConnection(state, text) {
  $('verbindung').dataset.state = state;
  $('verbindung').textContent = text;
}

function showLine(run) {
  const last = lastSearch(run);
  const line = last.text || (appRunning ? describePlan(plan).text : 'Die App startet bei der Suche.');
  $('suche-zeile').textContent = line;
  $('suche-zeile').classList.toggle('fehler', last.problem);
}

function showRun(run) {
  const set = textSet(plan);
  const running = Boolean(run && run.zustand === 'laeuft');
  $('lauf').hidden = !running;
  $('suchen').hidden = running;
  $('suche-zeile').hidden = running;
  if (running) {
    const rows = portalRows(plan, run);
    $('balken').replaceChildren(...rows.map((row) => {
      const part = el('span');
      part.dataset.state = row.state;
      return part;
    }));
    $('portale').replaceChildren(...rows.map((row) => {
      const item = el('li');
      item.dataset.state = row.state;
      item.append(el('span', '', row.name), el('span', 'portal__state', row.text));
      return item;
    }));
    $('lauf-hinweis').textContent = rows.length ? words(set).keepBrowsing : describeRun(run).step;
    return;
  }
  showLine(run);
  const finished = run && run.zustand === 'fertig' ? describeRun(run) : { portals: [], hints: [] };
  const lines = [...finished.portals.filter((p) => p.problem), ...finished.hints.map((text) => ({ text }))];
  $('hinweise').replaceChildren(...lines.map((line) => el('li', line.problem ? 'fehler' : '', line.text)));
}

async function currentRun() {
  const { lauf } = await chrome.storage.session.get('lauf');
  return lauf || null;
}

async function connect() {
  setConnection('', 'wird geprüft …');
  const answer = await chrome.runtime.sendMessage({ art: 'status' }).catch(() => null);
  if (!answer || !answer.verbunden) {
    setConnection('fehlt', 'nicht verbunden');
    $('fehlt').hidden = false;
    $('suche').hidden = true;
    $('seite').hidden = true;
    // Without an answer the setup is unknown: the most frequent form of address.
    $('fehlt-text').textContent = (answer && answer.fehler && !/nicht gefunden/.test(answer.fehler))
      ? answer.fehler : words(textSet(null)).appMissing;
    return;
  }
  plan = answer.plan;
  appRunning = Boolean(answer.app);
  const set = textSet(plan);
  setConnection('ok', 'verbunden');
  $('fehlt').hidden = true;
  $('suche').hidden = false;
  $('suche-titel').textContent = plan && plan.art === 'lehrstelle' ? describePlan(plan).button : words(set).title;
  const run = await currentRun();
  $('suchen').disabled = Boolean(run && run.zustand === 'laeuft');
  showRun(run);
  await showOpenPage(answer.app, set);
}

$('suchen').addEventListener('click', async () => {
  $('suchen').disabled = true;
  const answer = await chrome.runtime.sendMessage({ art: 'suche-starten' });
  if (answer && answer.fehler) {
    $('suche-zeile').textContent = answer.fehler;
    $('suche-zeile').classList.add('fehler');
    $('suchen').disabled = false;
  }
});

$('abbrechen').addEventListener('click', async () => {
  $('abbrechen').disabled = true;
  $('lauf-hinweis').textContent = 'Die Suche hört nach dem laufenden Schritt auf.';
  await chrome.runtime.sendMessage({ art: 'suche-stoppen' }).catch(() => null);
});

$('verbinden').addEventListener('click', connect);

$('oeffnen').addEventListener('click', async () => {
  const answer = await chrome.runtime.sendMessage({ art: 'app-oeffnen' });
  if (answer && answer.fehler) {
    setConnection('fehlt', 'nicht verbunden');
    $('fehlt').hidden = false;
    $('fehlt-text').textContent = answer.fehler;
  } else {
    window.close();
  }
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'session' || !changes.lauf) return;
  const run = changes.lauf.newValue;
  $('suchen').disabled = Boolean(run && run.zustand === 'laeuft');
  $('abbrechen').disabled = false;
  showRun(run);
});

connect();
