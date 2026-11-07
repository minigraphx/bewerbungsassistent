// Words of the bar in a tab (design: Erweiterung-Leisten, MIN-369): a bold first line (titel) and a second line (text),
// with Sie or du as in the app. No DOM; used by lib/apply.js, lib/rav.js and the service worker, tested in the tests of those.

const isDu = (set) => set === 'stelle-du' || set === 'lehrstelle-du';
const pick = (set, sie, du) => (isDu(set) ? du : sie);

function plural(count, one, many) {
  return `${count} ${count === 1 ? one : many}`;
}

export const yoursToSend = (set) => pick(set, 'Abschicken bleibt bei Ihnen.', 'Abschicken bleibt bei dir.');

/** „5 Felder ausgefüllt, davon 1 Entwurf der KI. 3 offen, 1 Einwilligung bitte selbst prüfen.“ */
export function filledTitle(merged) {
  const fromAi = [];
  if (merged.entwuerfe) fromAi.push(plural(merged.entwuerfe, 'Entwurf der KI', 'Entwürfe der KI'));
  if (merged.kiDateien) fromAi.push(`${plural(merged.kiDateien, 'Datei', 'Dateien')} von der KI zugeordnet`);
  const first = `${plural(merged.gefuellt, 'Feld', 'Felder')} ausgefüllt${fromAi.length ? `, davon ${fromAi.join(' und ')}` : ''}.`;
  const open = [`${merged.offen} offen`];
  if (merged.einwilligungen) open.push(`${plural(merged.einwilligungen, 'Einwilligung', 'Einwilligungen')} bitte selbst prüfen`);
  if (merged.ki) open.push('die KI sieht sich offene Felder an');
  return `${first} ${open.join(', ')}.`;
}

export const loginBar = (set) => ({
  titel: 'Hier braucht es eine Anmeldung oder ein Konto.',
  text: pick(set, 'Das bleibt bei Ihnen. Danach geht das Ausfüllen weiter.', 'Das bleibt bei dir. Danach geht das Ausfüllen weiter.'),
});

export const noFormBar = (set) => ({
  titel: 'Hier ist kein Formular zu finden.',
  text: pick(set, 'Öffnen Sie das Formular selbst, es wird dann ausgefüllt. Schon abgeschickt? Dann «Abgeschickt? Ja».',
    'Öffne das Formular selbst, es wird dann ausgefüllt. Schon abgeschickt? Dann «Abgeschickt? Ja».'),
});

/** A new address in the tab: the person decides whether to fill here. */
export function newAddressBar(set, entry, host) {
  const names = [entry.firma, entry.stelle].filter(Boolean).join(', ');
  return {
    titel: `Bewerbungsformular erkannt${names ? `: ${names}` : ''}.`,
    text: `Neue Adresse: ${host}. Die Erweiterung füllt aus, was sie weiss. ${yoursToSend(set)}`,
  };
}

/** The folder for the file dialog: the browser does not let the extension choose files. */
export function folderText(set) {
  return pick(set, 'Den Dateidialog öffnet der Browser. Wählen Sie dort diesen Ordner:', 'Den Dateidialog öffnet der Browser. Wähle dort diesen Ordner:');
}

function dayOf(date) {
  return date.toLocaleDateString('de-CH', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

/** After „Abgeschickt? Ja“: what is recorded and the next step, the Job-Room only with RAV. */
export function sentBar(set, rav, now = new Date(), notes = []) {
  const next = rav ? 'Nächster Schritt: im Job-Room eintragen.'
    : `Nächster Schritt: Antwort abwarten. Die App erinnert ${pick(set, 'Sie', 'dich')} ans Nachfragen.`;
  return {
    titel: `Festgehalten: beworben am ${dayOf(now)}. Die abgeschickte Fassung liegt in der App.`,
    text: [next, ...notes].join(' '),
  };
}

export const stoppedBar = () => ({ titel: 'Ausfüllen beendet.', text: 'Die eingetragenen Werte bleiben im Formular.' });

export const aiLimit = (set) => pick(set, 'Für diesen Tab ist die Grenze der KI-Anfragen erreicht. Weitere Felder bleiben bei Ihnen.',
  'Für diesen Tab ist die Grenze der KI-Anfragen erreicht. Weitere Felder bleiben bei dir.');

/** Job-Room: one entry after the other. */
export function ravEntryBar(set, position, total, entry) {
  const day = entry.beworben_am ? `, ${dayOf(new Date(`${entry.beworben_am}T12:00:00`))}` : '';
  return {
    titel: `Eintrag ${position} von ${total}: ${entry.firma}, ${entry.stelle}${day}.`,
    text: pick(set, 'Prüfen Sie den Eintrag. Speichern und anmelden machen Sie selbst; damit geht er ans RAV.',
      'Prüfe den Eintrag. Speichern und anmelden machst du selbst; damit geht er ans RAV.'),
  };
}

/** The visible tab of a search (MIN-370). */
export function watchingBar(set, portal) {
  return {
    titel: `Suche läuft: ${portal}.`,
    text: pick(set, 'Dieser Tab gehört gerade der Suche. Bitte nichts anklicken und nicht schliessen, sonst endet sie. Sie können in einem anderen Tab weiterarbeiten.',
      'Dieser Tab gehört gerade der Suche. Bitte nichts anklicken und nicht schliessen, sonst endet sie. Du kannst in einem anderen Tab weiterarbeiten.'),
  };
}
