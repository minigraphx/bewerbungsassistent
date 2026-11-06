// The browser asks for the access only after a click on a page of the extension (MIN-346); design MIN-369.
// The words follow the setup of the app, which the service worker remembers when it reads the plan.
import { permissionText } from './lib/permission-text.js';

const $ = (id) => document.getElementById(id);
const say = (text) => { $('meldung').textContent = text; };
const forSearch = new URLSearchParams(location.search).get('fuer') === 'suche';

function list(id, lines) {
  $(id).replaceChildren(...lines.map((line) => {
    const item = document.createElement('li');
    item.textContent = line;
    return item;
  }));
}

const { textsatz } = await chrome.storage.local.get('textsatz').catch(() => ({}));
const words = permissionText(forSearch ? 'suche' : 'formulare', textsatz);
$('frage').textContent = words.question;
$('text').textContent = words.text;
list('tut', words.does);
list('nie', words.never);
$('fuss').textContent = words.foot;

$('ablehnen').addEventListener('click', () => say(words.refused));

$('erlauben').addEventListener('click', async () => {
  try {
    const granted = await chrome.permissions.request({ origins: ['<all_urls>'] });
    if (!granted) {
      say(words.refused);
      return;
    }
    if (forSearch) {
      say('Erlaubt. Die weiteren Seiten kommen bei der nächsten Suche dazu.');
      return;
    }
    const answer = await chrome.runtime.sendMessage({ art: 'bewerben-weiter' });
    if (answer && answer.fehler) {
      say(answer.fehler);
      return;
    }
    window.close();
  } catch (error) {
    say(`Das hat nicht geklappt: ${error.message}`);
  }
});
