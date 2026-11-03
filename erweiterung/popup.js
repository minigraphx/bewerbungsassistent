// Popup of the extension: connection to the app, start of the search, progress and summary.
import { describeRun } from './lib/progress.js';

const $ = (id) => document.getElementById(id);

function show(id, text, error = false) {
  $(id).textContent = text;
  $(id).classList.toggle('fehler', error);
}

function fill(list, lines) {
  list.replaceChildren(...lines.map((line) => {
    const item = document.createElement('li');
    item.textContent = line.text;
    item.classList.toggle('fehler', Boolean(line.problem));
    return item;
  }));
}

function render(run) {
  if (!run) return;
  const view = describeRun(run);
  $('lauf').hidden = false;
  show('schritt', view.step, run.zustand === 'fehler');
  fill($('portale'), view.portals);
  fill($('hinweise'), view.hints.map((text) => ({ text })));
  $('suchen').disabled = run.zustand === 'laeuft';
}

async function connect() {
  const answer = await chrome.runtime.sendMessage({ art: 'status' });
  if (answer && answer.verbunden) {
    show('verbindung', answer.app ? `Mit der App verbunden (Version ${answer.version}).`
      : `App gefunden (Version ${answer.version}); sie startet bei der Suche.`);
    const { lauf } = await chrome.storage.session.get('lauf');
    $('suchen').disabled = Boolean(lauf && lauf.zustand === 'laeuft');
  } else {
    show('verbindung', (answer && answer.fehler) || 'Die App antwortet nicht.', true);
  }
}

$('suchen').addEventListener('click', async () => {
  $('suchen').disabled = true;
  const answer = await chrome.runtime.sendMessage({ art: 'suche-starten' });
  if (answer && answer.fehler) show('verbindung', answer.fehler, true);
});

$('oeffnen').addEventListener('click', async () => {
  const answer = await chrome.runtime.sendMessage({ art: 'app-oeffnen' });
  if (answer && answer.fehler) show('verbindung', answer.fehler, true);
  else window.close();
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'session' && changes.lauf) render(changes.lauf.newValue);
});

chrome.storage.session.get('lauf').then(({ lauf }) => render(lauf));
connect();
