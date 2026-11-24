// Only in the page „Meine Angaben“ of the app (G84): the kind of a document, guessed from its name and file type.
// Nothing else is looked at, and nothing leaves the computer: no content, no AI, no request. The person corrects it.
// Diplomas and references are named as on „Lebenslauf und Dateien“ (DateienLogik, bewerbungen/seiten/dateien-logik.js).
"use strict";

const GUESS_CV = "lebenslauf-bisher";
const GUESS_LETTER = "anschreiben-bisher";
const GUESS_CERTIFICATE = "zertifikate";
const GUESS_REFERENCE = "zeugnisse";
const IMAGE_TYPE = "image";
// The names are folded first (foldDocumentName), so umlauts and accents are plain letters here.
const CV_NAME = /lebenslauf|curriculum|vitae|(?:^|[^a-z])cv(?:[^a-z]|$)|resume|linkedin|profile/;
const LETTER_NAME = /anschreiben|bewerbungsschreiben|motivationsschreiben|motivationsbrief|begleitschreiben|cover ?letter|lettre de motivation/;
const CERTIFICATE_NAME = /zertifikat|zertifizierung|certificate|kursbest(?:a|ae)tigung|teilnahmebest(?:a|ae)tigung|sprachdiplom|goethe|delf|dalf|cambridge|toefl|ielts|multicheck|stellwerk|basic ?check/;
const SCHNUPPER_NAME = /schnupper/;
// First match wins; „Bewerbung“ alone is no cover letter. Images are never a CV or a letter.
const GUESS_RULES = [
  { category: GUESS_CV, documentsOnly: true, matches: (name) => CV_NAME.test(name) },
  { category: GUESS_LETTER, documentsOnly: true, matches: (name) => LETTER_NAME.test(name) },
  { category: GUESS_CERTIFICATE, matches: (name) => DateienLogik.DIPLOMA_NAME.test(name) || CERTIFICATE_NAME.test(name) },
  { category: GUESS_REFERENCE, matches: (name) => DateienLogik.REFERENCE_NAME.test(name) || SCHNUPPER_NAME.test(name) },
];

/** The name without its extension, in small letters without accents, with _ - . as spaces. */
function foldDocumentName(name) {
  const text = String(name);
  const dot = text.lastIndexOf(".");
  const stem = dot > 0 ? text.slice(0, dot) : text;
  return stem.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[_.\-]+/g, " ").replace(/\s+/g, " ").trim();
}

function isImageName(form, name) {
  return form.documents.fileTypes[IMAGE_TYPE].extensions.includes(documentExtension(name));
}

/** { category, sure }: sure when a rule matched; without one it is a certificate or diploma, to be checked. */
function guessDocumentKind(form, name) {
  const folded = foldDocumentName(name);
  const image = isImageName(form, name);
  const rule = GUESS_RULES.find((r) => !(image && r.documentsOnly) && r.matches(folded));
  return rule ? { category: rule.category, sure: true } : { category: GUESS_CERTIFICATE, sure: false };
}

/** The singular name of a kind for a row in the app language, e.g. „Zeugnis“ (form.json kindLabel). */
function kindLabel(form, track, category) {
  return T(forTrack(documentCategories(form).get(category).kindLabel, track));
}

/**
 * The singular name inside a sentence: „als früheres Anschreiben“, while the list of kinds keeps the capital. German
 * nouns keep theirs; French and English start small, but an abbreviation such as „CV“ stays as it is (#433).
 */
function kindInSentence(form, track, category) {
  const german = forTrack(documentCategories(form).get(category).kindLabel, track);
  const label = T(german);
  if (label === german) return label.replace(/^Früheres\b/, "früheres");
  return /^\p{Lu}\p{Ll}/u.test(label) ? label.charAt(0).toLowerCase() + label.slice(1) : label;
}

/**
 * The kind for „{datei} ist jetzt als {art} eingeordnet.“, whose French and English put it in quotes, as „Lebenslauf
 * und Dateien“ says it: there the kind stands as the list shows it, in German as in a sentence.
 */
function kindInQuotes(form, track, category) {
  const german = forTrack(documentCategories(form).get(category).kindLabel, track);
  return T(german) === german ? kindInSentence(form, track, category) : T(german);
}

/** The plural name of a kind for its limit in the app language, e.g. „Lebensläufe“ (form.json kindPlural). */
function kindPlural(form, track, category) {
  return T(forTrack(documentCategories(form).get(category).kindPlural, track));
}

/** The kinds a file may have by its type, in the order of form.json: [{ id, label }]. */
function kindOptions(form, track, name) {
  const ext = documentExtension(name);
  return form.documents.categories
    .filter((category) => allowedExtensions(form, category).includes(ext))
    .map((category) => ({ id: category.id, label: kindLabel(form, track, category.id) }));
}
