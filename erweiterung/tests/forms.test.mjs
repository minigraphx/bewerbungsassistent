// What a form field is and what goes into it (MIN-346): rules for German, French and English forms.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';

const require = createRequire(import.meta.url);
const { accepts, classify, classifyAll, documentsFor, findApplyTarget, matchOption } = require('../form/fields.js');

const text = (label, extra = {}) => ({ tag: 'input', type: 'text', label, ...extra });

test('labels in three languages give the same value', () => {
  const cases = {
    first_name: ['Vorname *', 'First name', 'Prénom'],
    last_name: ['Nachname', 'Familienname', 'Last Name', 'Nom de famille'],
    full_name: ['Vor- und Nachname', 'Full name', 'Ihr Name'],
    last_first: ['Name, Vorname', 'Nachname, Vorname', 'Nom, prénom'],
    postal_city: ['PLZ / Ort', 'PLZ, Ort', 'Zip code and city'],
    email: ['E-Mail-Adresse', 'Email', 'Courriel'],
    phone: ['Telefon', 'Mobile', 'Natel', 'Téléphone'],
    street: ['Strasse und Nr.', 'Adresse', 'Street address', 'Rue'],
    postal_code: ['PLZ', 'Postleitzahl', 'Code postal', 'ZIP'],
    city: ['Ort', 'Wohnort', 'City', 'Ville'],
    country: ['Land', 'Country', 'Pays'],
    linkedin: ['LinkedIn-Profil'],
    availability: ['Frühester Eintritt', 'Verfügbar ab', 'Earliest start date'],
    salary: ['Lohnvorstellung', 'Salary expectation', 'Prétention de salaire'],
  };
  for (const [key, labels] of Object.entries(cases)) {
    for (const label of labels) assert.deepEqual(classify(text(label)).key, key, label);
  }
});

test('the autocomplete attribute goes first, also with section words', () => {
  assert.equal(classify(text('Etwas', { autocomplete: 'given-name' })).key, 'first_name');
  assert.equal(classify(text('Etwas', { autocomplete: 'section-a home tel' })).key, 'phone');
  assert.equal(classify(text('Name', { autocomplete: 'organization' })).kind, 'unclear');
});

test('names and ids count when the label says nothing', () => {
  assert.equal(classify({ tag: 'input', type: 'text', name: 'applicant_firstName' }).key, 'first_name');
  assert.equal(classify({ tag: 'input', type: 'text', name: 'legalNameSection_lastName' }).key, 'last_name');
  assert.equal(classify({ tag: 'input', type: 'text', placeholder: 'Ihre E-Mail' }).key, 'email');
  assert.equal(classify({ tag: 'input', type: 'email', label: 'Kontakt' }).key, 'email');
});

test('„Name“ beside „Vorname“ is the family name, alone it is the whole name', () => {
  assert.deepEqual(classifyAll([text('Name'), text('Vorname')]).map((f) => f.key), ['last_name', 'first_name']);
  assert.equal(classifyAll([text('Name'), text('E-Mail')])[0].key, 'full_name');
});

test('addresses and names of others stay open', () => {
  for (const label of ['Firmenname', 'Name des Arbeitgebers', 'E-Mail Ihrer Referenzperson', 'Adresse der Schule', 'Company address', 'Notfallkontakt Telefon']) {
    assert.equal(classify(text(label)).kind, 'unclear', label);
  }
});

test('a second address line stays open', () => {
  for (const label of ['Address line 2', 'Adresszusatz', 'c/o']) assert.equal(classify(text(label)).kind, 'unclear', label);
});

test('the type of a field goes before a word in its label', () => {
  assert.equal(classify({ tag: 'input', type: 'email', label: 'Kontaktadresse' }).key, 'email');
  assert.equal(classify({ tag: 'input', type: 'tel', label: 'Erreichbar in Bern, Ort egal' }).key, 'phone');
  assert.equal(classify({ tag: 'input', type: 'email', label: 'E-Mail des Arbeitgebers' }).kind, 'unclear');
  assert.equal(classify({ tag: 'input', type: 'email', label: 'Login' }).kind, 'login');
});

test('words that only contain a rule stay open', () => {
  for (const label of ['Geburtsort', 'Sortierung', 'Heimatort', 'Hotel', 'Nationalität', 'Geburtsdatum']) {
    assert.equal(classify(text(label)).kind, 'unclear', label);
  }
});

test('never a value for a password, a login or a tick box', () => {
  assert.equal(classify({ tag: 'input', type: 'password', label: 'E-Mail' }).kind, 'password');
  assert.equal(classify(text('Geheim', { autocomplete: 'new-password' })).kind, 'password');
  assert.equal(classify(text('Benutzername')).kind, 'login');
  assert.equal(classify({ tag: 'input', type: 'checkbox', label: 'Ich akzeptiere die Datenschutzerklärung' }).kind, 'consent');
  assert.equal(classify({ tag: 'input', type: 'checkbox', label: 'I agree to the terms' }).kind, 'consent');
  assert.equal(classify({ tag: 'input', type: 'checkbox', label: 'E-Mail' }).kind, 'choice');
  assert.equal(classify({ tag: 'input', type: 'radio', label: 'Frau' }).kind, 'choice');
});

test('long questions and text areas are free text', () => {
  assert.equal(classify({ tag: 'textarea', label: 'Bemerkungen' }).kind, 'freetext');
  assert.equal(classify(text('Warum möchten Sie bei uns arbeiten?')).kind, 'freetext');
  assert.equal(classify({ tag: 'textarea', label: 'Adresse' }).key, 'street');
});

test('an option is taken only when it means the value', () => {
  const countries = [{ value: '', label: 'Bitte wählen' }, { value: 'DE', label: 'Deutschland' }, { value: 'CH', label: 'Switzerland' }];
  assert.equal(matchOption(countries, 'Schweiz'), 2);
  assert.equal(matchOption([{ value: 'ch', label: 'Suisse' }], 'Schweiz'), 0);
  assert.equal(matchOption(countries, 'Österreich'), -1);
  assert.equal(matchOption([{ value: 'a', label: 'Bern' }], 'bern'), 0);
});

const UPLOADS = [
  { schluessel: 'lebenslauf', name: 'Lebenslauf_E.pdf' }, { schluessel: 'anschreiben', name: 'Anschreiben_E.pdf' },
  { schluessel: 'zertifikate', name: 'Zertifikate_E.zip' }, { schluessel: 'zeugnis-0', name: 'Z1.pdf' }, { schluessel: 'zeugnis-1', name: 'Z2.pdf' },
];

test('a named upload field gets its document', () => {
  assert.deepEqual(documentsFor({ label: 'Lebenslauf' }, UPLOADS).keys, ['lebenslauf']);
  assert.deepEqual(documentsFor({ label: 'Motivationsschreiben' }, UPLOADS).keys, ['anschreiben']);
  assert.deepEqual(documentsFor({ name: 'resumeUpload' }, UPLOADS).keys, ['lebenslauf']);
  assert.deepEqual(documentsFor({ label: 'Zertifikate', accept: '.zip,.pdf' }, UPLOADS).keys, ['zertifikate']);
  assert.deepEqual(documentsFor({ label: 'Arbeitszeugnisse', multiple: true }, UPLOADS).keys, ['zeugnis-0', 'zeugnis-1']);
});

test('a general field takes everything only with several files', () => {
  assert.equal(documentsFor({ label: 'Unterlagen hochladen', multiple: true }, UPLOADS).keys.length, 5);
  const single = documentsFor({ label: 'Unterlagen hochladen' }, UPLOADS);
  assert.deepEqual(single.keys, []);
  assert.ok(single.hinweis);
});

test('a field that takes no ZIP stays open and says so', () => {
  const answer = documentsFor({ label: 'Zertifikate', accept: '.pdf' }, UPLOADS);
  assert.deepEqual(answer.keys, []);
  assert.match(answer.hinweis, /Zertifikate_E\.zip/);
});

test('a field without a meaning gets nothing', () => {
  assert.deepEqual(documentsFor({ label: 'Foto', accept: 'image/*' }, UPLOADS), { keys: [] });
});

test('the types a field accepts', () => {
  assert.ok(accepts('', 'a.zip'));
  assert.ok(accepts('.PDF, .doc', 'a.pdf'));
  assert.ok(accepts('application/pdf', 'a.pdf'));
  assert.ok(accepts('application/*', 'a.zip'));
  assert.ok(!accepts('image/*', 'a.pdf'));
  assert.ok(!accepts('.pdf', 'a.zip'));
});

test('follows a link to the form', () => {
  const link = (linkText, href = 'https://a.ch/x') => ({ text: linkText, href, tag: 'a' });
  assert.equal(findApplyTarget([link('Kontakt'), link('Jetzt bewerben')]), 1);
  assert.equal(findApplyTarget([link('Apply now')]), 0);
  assert.equal(findApplyTarget([link('Postuler')]), 0);
  assert.equal(findApplyTarget([link('Bewerben', 'javascript:go()')]), -1);
  assert.equal(findApplyTarget([link('Bewerbungstipps für Berufseinsteiger')]), -1);
});

test('never a button that sends', () => {
  assert.equal(findApplyTarget([{ text: 'Bewerben', tag: 'button', type: 'submit', inForm: true }]), -1);
  assert.equal(findApplyTarget([{ text: 'Bewerben', tag: 'button', type: 'submit', inForm: false }]), -1);
  assert.equal(findApplyTarget([{ text: 'Bewerbung absenden', tag: 'button', type: 'button' }]), -1);
  assert.equal(findApplyTarget([{ text: 'Jetzt bewerben', tag: 'button', type: 'button', inForm: true }]), -1);
  assert.equal(findApplyTarget([{ text: 'Jetzt bewerben', tag: 'button', type: 'button', inForm: false }]), 0);
});
