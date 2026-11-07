// Words of the page that asks for access to all pages (design: Erweiterung-Erlauben, MIN-369), for forms and for
// further sites of the search, with Sie or du. No DOM; tested in tests/popup.test.mjs.

const FORMS = {
  sie: {
    question: 'Darf die Erweiterung Bewerbungsformulare ausfüllen?',
    text: 'Bewerbungsformulare liegen auf den Seiten der Firmen, oft in eingebetteten Rahmen. Damit die Erweiterung sie ausfüllen kann, braucht sie einmal Ihre Erlaubnis für alle Seiten.',
    does: ['Formulare ausfüllen in Tabs, die Sie in der App mit «Formular öffnen» starten', 'offene Felder markieren'],
    foot: 'Danach fragt der Browser noch einmal selbst nach. Zurücknehmen können Sie die Erlaubnis jederzeit in den Einstellungen der Erweiterung.',
    refused: 'Ohne diese Erlaubnis füllt die Erweiterung keine Formulare aus. Bewerben geht weiterhin von Hand.',
  },
  du: {
    question: 'Darf die Erweiterung Bewerbungsformulare ausfüllen?',
    text: 'Bewerbungsformulare liegen auf den Seiten der Firmen, oft in eingebetteten Rahmen. Damit die Erweiterung sie ausfüllen kann, braucht sie einmal deine Erlaubnis für alle Seiten.',
    does: ['Formulare ausfüllen in Tabs, die du in der App mit «Formular öffnen» startest', 'offene Felder markieren'],
    foot: 'Danach fragt der Browser noch einmal selbst nach. Zurücknehmen kannst du die Erlaubnis jederzeit in den Einstellungen der Erweiterung.',
    refused: 'Ohne diese Erlaubnis füllt die Erweiterung keine Formulare aus. Bewerben geht weiterhin von Hand.',
  },
};

const SEARCH = {
  sie: {
    question: 'Darf die Erweiterung auf Ihren weiteren Seiten suchen?',
    text: 'Sie haben in den Erweiterten Einstellungen Karriereseiten hinzugefügt. Damit die Erweiterung dort Stellen finden kann, braucht sie Ihre Erlaubnis. Der Browser fragt dafür nach allen Seiten; genutzt werden nur Ihre.',
    does: ['Stellenanzeigen auf Ihren Seiten lesen, wenn Sie die Suche starten', 'Bewerbungsformulare ausfüllen, wenn Sie das starten'],
    foot: 'Danach fragt der Browser noch einmal selbst nach. Entfernen Sie den eigenen Schlüssel, gibt die Erweiterung die Erlaubnis wieder ab.',
    refused: 'Ohne diese Erlaubnis sucht die Erweiterung nur auf den Portalen weiter.',
  },
  du: {
    question: 'Darf die Erweiterung auf deinen weiteren Seiten suchen?',
    text: 'Du hast in den Erweiterten Einstellungen Karriereseiten hinzugefügt. Damit die Erweiterung dort Lehrstellen finden kann, braucht sie deine Erlaubnis. Der Browser fragt dafür nach allen Seiten; genutzt werden nur deine.',
    does: ['Lehrstellen auf deinen Seiten lesen, wenn du die Suche startest', 'Bewerbungsformulare ausfüllen, wenn du das startest'],
    foot: 'Danach fragt der Browser noch einmal selbst nach. Entfernst du den eigenen Schlüssel, gibt die Erweiterung die Erlaubnis wieder ab.',
    refused: 'Ohne diese Erlaubnis sucht die Erweiterung nur auf den Portalen weiter.',
  },
};

const NEVER = ['etwas abschicken', 'Einwilligungen bestätigen', 'sich anmelden oder Passwörter lesen'];

/**
 * @param {'formulare'|'suche'} purpose
 * @param {string} set  text set from popup-view.textSet; a job with du searches Stellen, not Lehrstellen
 */
export function permissionText(purpose, set) {
  const address = set === 'stelle-du' || set === 'lehrstelle-du' ? 'du' : 'sie';
  const base = (purpose === 'suche' ? SEARCH : FORMS)[address];
  const forJob = purpose === 'suche' && set === 'stelle-du';
  return {
    ...base,
    text: forJob ? base.text.replace('Lehrstellen finden', 'Stellen finden') : base.text,
    does: forJob ? base.does.map((line) => line.replace('Lehrstellen auf', 'Stellenanzeigen auf')) : base.does,
    never: NEVER,
  };
}
