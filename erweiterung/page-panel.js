// The part of the popup for the open page (MIN-345). Opening the popup is the click that lets the extension read this
// one tab (activeTab); nothing leaves the browser until the person presses a button.
import { adKey, canCheck, describeCheck, missingField, readPage, sourceHint, toAd } from './lib/page-ad.js';

const UNREADABLE = 'Diese Seite lässt sich nicht lesen. Falls sie noch lädt: kurz warten und die Erweiterung nochmals öffnen.';
const $ = (id) => document.getElementById(id);

function say(text, error = false) {
  $('seite-status').textContent = text;
  $('seite-status').classList.toggle('fehler', error);
}

function showCheck(answer) {
  const view = describeCheck(answer);
  $('seite-ergebnis').hidden = false;
  $('seite-note').textContent = view.titel;
  $('seite-zeilen').replaceChildren(...view.zeilen.map((line) => {
    const item = document.createElement('li');
    item.textContent = line.text;
    item.classList.toggle('fehler', Boolean(line.problem));
    return item;
  }));
}

function savedText(answer) {
  const { firma, stelle, status } = answer.bewerbung;
  return answer.neu ? `In der App gespeichert: ${firma} – ${stelle}.` : `Gibt es schon: ${firma} – ${stelle} (${status}).`;
}

function setBusy(busy) {
  $('seite-pruefen').disabled = busy;
  $('seite-speichern').disabled = busy;
}

async function ask(art, anzeige) {
  const answer = await chrome.runtime.sendMessage({ art, anzeige });
  if (!answer || answer.fehler) throw new Error((answer && answer.fehler) || 'Die App antwortet nicht.');
  return answer;
}

async function read(tabId) {
  try {
    const [frame] = await chrome.scripting.executeScript({ target: { tabId }, func: readPage });
    return frame && frame.result ? frame.result : null;
  } catch (error) {
    console.warn('Seite nicht gelesen:', error.message);
    return null;
  }
}

function connectButtons(ad, kept) {
  let rating = kept.pruefung ? kept.pruefung.bewertung : null;
  const { quelle: _source, ...fields } = ad;
  const current = () => ({ ...fields, stelle: $('seite-stelle').value, firma: $('seite-firma').value });

  async function run(saving, working, done) {
    const anzeige = current();
    const missing = missingField(anzeige, saving);
    if (missing) {
      say(missing, true);
      return;
    }
    setBusy(true);
    say(working);
    try {
      done(await ask(saving ? 'seite-speichern' : 'seite-pruefen', saving ? { ...anzeige, bewertung: rating } : anzeige));
    } catch (error) {
      say(error.message, true);
    } finally {
      setBusy(false);
    }
  }

  $('seite-pruefen').addEventListener('click', () => run(false, 'KI prüft die Stelle …', (answer) => {
    rating = answer.bewertung;
    say('');
    showCheck(answer);
  }));
  $('seite-speichern').addEventListener('click', () => run(true, 'Wird gespeichert …', (answer) => say(savedText(answer))));
}

/** Show the ad of the open tab; results of an earlier click on the same page stay visible. */
export async function showOpenPage(appUrl) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !canCheck(tab.url, appUrl)) return;
  $('seite').hidden = false;
  const page = await read(tab.id);
  if (!page) {
    say(UNREADABLE, true);
    return;
  }
  const ad = toAd(page);
  if (ad.fehler) {
    say(ad.fehler);
    return;
  }
  const { seite } = await chrome.storage.session.get('seite');
  const kept = seite && seite.key === adKey(ad) ? seite : {};
  $('seite-felder').hidden = false;
  $('seite-stelle').value = ad.stelle;
  $('seite-firma').value = ad.firma;
  if (kept.pruefung) showCheck(kept.pruefung);
  say(kept.gespeichert ? savedText(kept.gespeichert) : sourceHint(ad.quelle));
  connectButtons(ad, kept);
}
