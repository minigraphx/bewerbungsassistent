// The part of the popup for the open page (MIN-345, design MIN-369). Opening the popup is the click that lets the
// extension read this one tab (activeTab); nothing leaves the browser until the person presses a button.
import { adKey, canCheck, describeCheck, missingField, readPage, sourceHint, toAd } from './lib/page-ad.js';
import { ratingView, words } from './lib/popup-view.js';

const UNREADABLE = 'Diese Seite lässt sich nicht lesen. Falls sie noch lädt: kurz warten und die Erweiterung nochmals öffnen.';
const $ = (id) => document.getElementById(id);
let apprenticeship = false;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function say(text, error = false) {
  $('seite-status').textContent = text;
  $('seite-status').classList.toggle('fehler', error);
}

function noteRow(note) {
  const row = el('div', 'note');
  row.setAttribute('role', 'img');
  row.setAttribute('aria-label', note.label);
  const boxes = el('span', 'note__boxes');
  for (let i = 0; i < 6; i += 1) {
    const box = el('i');
    box.dataset.fill = i < note.filled ? 'full' : i === note.filled && note.half ? 'half' : 'empty';
    boxes.append(box);
  }
  row.append(el('span', 'note__number', note.text), boxes, el('span', '', note.word));
  if (note.name) row.prepend(el('span', 'note__name', note.name));
  return row;
}

function showCheck(answer) {
  const view = ratingView(answer.bewertung, apprenticeship);
  // From the earlier lines only what the summary does not show: already in the register, the AI's own notes, odd text.
  const extra = describeCheck(answer).zeilen.filter((line) => line.problem || line.text === answer.hinweis);
  $('seite-ergebnis').hidden = false;
  $('seite-noten').replaceChildren(...view.notes.map(noteRow));
  $('seite-text').textContent = [view.text, view.unsure].filter(Boolean).join(' ');
  $('seite-zeilen').replaceChildren(...extra.map((line) => el('li', line.problem ? 'fehler' : '', line.text)));
  // After the check, saving is the next step.
  $('seite-pruefen').hidden = true;
  $('seite-speichern').className = '';
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

function showNames() {
  $('seite-titel').textContent = $('seite-stelle').value || 'Stelle unbekannt';
  $('seite-firma-text').textContent = $('seite-firma').value || 'Firma unbekannt';
}

function connectButtons(ad, kept) {
  let rating = kept.pruefung ? kept.pruefung.bewertung : null;
  const { quelle: _source, ...fields } = ad;
  const current = () => ({ ...fields, stelle: $('seite-stelle').value, firma: $('seite-firma').value });

  async function run(saving, working, done) {
    const anzeige = current();
    const missing = missingField(anzeige, saving);
    if (missing) {
      $('seite-felder').hidden = false;
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

  $('seite-korrigieren').addEventListener('click', () => {
    $('seite-felder').hidden = !$('seite-felder').hidden;
    if (!$('seite-felder').hidden) $('seite-stelle').focus();
  });
  for (const id of ['seite-stelle', 'seite-firma']) $(id).addEventListener('input', showNames);
  $('seite-pruefen').addEventListener('click', () => run(false, 'KI prüft die Stelle …', (answer) => {
    rating = answer.bewertung;
    say('');
    showCheck(answer);
  }));
  $('seite-speichern').addEventListener('click', () => run(true, 'Wird gespeichert …', (answer) => say(savedText(answer))));
}

/** Show the ad of the open tab; results of an earlier click on the same page stay visible. */
export async function showOpenPage(appUrl, set) {
  apprenticeship = set === 'lehrstelle-du';
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  $('seite').hidden = false;
  if (!tab || !canCheck(tab.url, appUrl)) {
    say(words(set).noAd);
    return;
  }
  const page = await read(tab.id);
  if (!page) {
    say(UNREADABLE, true);
    return;
  }
  const ad = toAd(page);
  if (ad.fehler) {
    say(words(set).noAd);
    $('seite-status').append(el('span', 'klein', ` ${ad.fehler.replace(/^Auf dieser Seite wurde kein Inserat gefunden\. /, '')}`));
    return;
  }
  const { seite } = await chrome.storage.session.get('seite');
  const kept = seite && seite.key === adKey(ad) ? seite : {};
  $('seite-anzeige').hidden = false;
  $('seite-stelle').value = ad.stelle;
  $('seite-firma').value = ad.firma;
  $('seite-pruefen').textContent = apprenticeship ? 'Lehrstelle prüfen' : 'Stelle prüfen';
  $('seite-speichern').textContent = words(set).save;
  showNames();
  if (kept.pruefung) showCheck(kept.pruefung);
  say(kept.gespeichert ? savedText(kept.gespeichert) : sourceHint(ad.quelle));
  connectButtons(ad, kept);
}
