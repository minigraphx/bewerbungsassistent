// The browser asks for the access only after a click on a page of the extension (MIN-346).
const say = (text) => { document.getElementById('meldung').textContent = text; };
const forSearch = new URLSearchParams(location.search).get('fuer') === 'suche';
const REFUSED_FORMS = 'Ohne diesen Zugriff füllt die Erweiterung keine Formulare aus. Bewerben geht weiterhin von Hand.';
const REFUSED_SEARCH = 'Ohne diesen Zugriff sucht die Erweiterung nur auf den Portalen weiter.';

if (forSearch) {
  document.getElementById('fuer-formulare').hidden = true;
  document.getElementById('fuer-suche').hidden = false;
  document.getElementById('erlauben').textContent = 'Zugriff erlauben';
}

document.getElementById('erlauben').addEventListener('click', async () => {
  try {
    const granted = await chrome.permissions.request({ origins: ['<all_urls>'] });
    if (!granted) {
      say(forSearch ? REFUSED_SEARCH : REFUSED_FORMS);
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
