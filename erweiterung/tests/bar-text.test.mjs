// Words of the bar in a tab (design Erweiterung-Leisten, MIN-369): bold first line, second line, Sie or du.
import test from 'node:test';
import assert from 'node:assert/strict';
import { filledTitle, newAddressBar, ravEntryBar, sentBar, watchingBar, yoursToSend } from '../lib/bar-text.js';

test('the count of the form reads like the design', () => {
  assert.equal(filledTitle({ gefuellt: 5, offen: 3, einwilligungen: 1, entwuerfe: 1 }),
    '5 Felder ausgefüllt, davon 1 Entwurf der KI. 3 offen, 1 Einwilligung bitte selbst prüfen.');
  assert.equal(filledTitle({ gefuellt: 1, offen: 0, kiDateien: 2 }), '1 Feld ausgefüllt, davon 2 Dateien von der KI zugeordnet. 0 offen.');
  assert.equal(yoursToSend('stelle-du'), 'Abschicken bleibt bei dir.');
  assert.equal(yoursToSend(undefined), 'Abschicken bleibt bei Ihnen.');
});

test('a new address names the application and the address', () => {
  const bar = newAddressBar('stelle-sie', { firma: 'Muster AG', stelle: 'Sachbearbeiterin Einkauf' }, 'ats.example');
  assert.equal(bar.titel, 'Bewerbungsformular erkannt: Muster AG, Sachbearbeiterin Einkauf.');
  assert.match(bar.text, /^Neue Adresse: ats\.example\. .*Abschicken bleibt bei Ihnen\.$/);
});

test('after sending, the next step depends on RAV', () => {
  const day = new Date(2026, 10, 6);
  assert.deepEqual(sentBar('stelle-sie', true, day), {
    titel: 'Festgehalten: beworben am 06.11.2026. Die abgeschickte Fassung liegt in der App.',
    text: 'Nächster Schritt: im Job-Room eintragen.',
  });
  assert.equal(sentBar('stelle-sie', false, day, ['Hinweis.']).text, 'Nächster Schritt: Antwort abwarten. Die App erinnert Sie ans Nachfragen. Hinweis.');
});

test('Job-Room and the watched search', () => {
  const bar = ravEntryBar('lehrstelle-du', 2, 4, { firma: 'Muster AG', stelle: 'Kauffrau EFZ', beworben_am: '2026-11-06' });
  assert.equal(bar.titel, 'Eintrag 2 von 4: Muster AG, Kauffrau EFZ, 06.11.2026.');
  assert.match(bar.text, /machst du selbst/);
  assert.equal(ravEntryBar('stelle-sie', 1, 1, { firma: 'A', stelle: 'B' }).titel, 'Eintrag 1 von 1: A, B.');
  assert.equal(watchingBar('stelle-sie', 'jobs.ch').titel, 'Suche läuft: jobs.ch.');
  assert.match(watchingBar('lehrstelle-du', 'yousty').text, /Du kannst in einem anderen Tab/);
});
