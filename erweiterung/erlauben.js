// The browser asks for the access only after a click on a page of the extension (MIN-346).
const say = (text) => { document.getElementById('meldung').textContent = text; };

document.getElementById('erlauben').addEventListener('click', async () => {
  try {
    const granted = await chrome.permissions.request({ origins: ['<all_urls>'] });
    if (!granted) {
      say('Ohne diesen Zugriff füllt die Erweiterung keine Formulare aus. Bewerben geht weiterhin von Hand.');
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
