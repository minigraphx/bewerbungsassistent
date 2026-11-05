// What a field of an application form is (MIN-346). Pure logic without the page: rules only, the values stay out.
// Runs in the frames of a form as a content script, and in Node for the tests.
(function (root) {
  'use strict';

  const MIN_FIELDS = 3;
  const MAX_LINK_TEXT = 40;
  const LONG_QUESTION = 40;

  // Addresses and names of others: a company's address is not the person's.
  const OTHER_PARTY = /firma|firmen|arbeitgeber|unternehmen|company|employer|employeur|entreprise|referenz|reference|référence|kontaktperson|vorgesetzt|notfall|emergency|schule|school|hochschule|universit/i;
  const OTHER_PEOPLE = /referenz|reference|référence|kontaktperson|vorgesetzt|notfall|emergency|eltern|parents/i;
  const ADDRESS_EXTRA = /address.?line.?2|adresszusatz|zusatz|complément|\bc\/o\b/i;
  const LOGIN = /benutzername|username|user name|anmeldename|\blogin\b|identifiant|nom d'utilisateur/i;
  const CONSENT = /datenschutz|einwillig|zustimm|stimme|einverstanden|akzeptier|\bagb\b|nutzungsbedingung|talent.?pool|privacy|consent|terms|accept|agree|gdpr|dsgvo|confidentialit|conditions/i;
  const BARE_NAME = /^\s*(ihr\s+|your\s+|votre\s+)?(name|nom)\s*[*:]*\s*$/i;

  // Order counts: „Vorname“ before „Name“, „E-Mail-Adresse“ before „Adresse“.
  const VALUE_RULES = [
    ['last_first', /(nach)?name,\s*vorname|nom,\s*prénom|last name,\s*first name/i],
    ['postal_city', /\bplz\b\s*(\/|,|&|und)\s*\bort\b|\bnpa\b\s*(\/|,|&|et)\s*(localité|lieu)|zip.*\bcity\b|post.?code.*\bcity\b/i],
    ['full_name', /vor-?\s*(und|&|\/)\s*nach|vorname und name|full.?name|vollständiger name|nom complet|prénom et nom|nom et prénom/i],
    ['first_name', /vorname|first.?name|given.?name|prénom|prenom/i],
    ['last_name', /nachname|familienname|last.?name|family.?name|surname|nom de famille/i],
    ['email', /e-?mail|courriel/i],
    ['linkedin', /linkedin/i],
    ['github', /github/i],
    ['website', /website|webseite|homepage|portfolio|site web/i],
    ['phone', /telefon|\btel\b|mobile?\b|handy|natel|phone|téléphone|portable/i],
    ['postal_code', /\bplz\b|postleitzahl|post.?code|\bzip\b|code postal|\bnpa\b/i],
    ['city', /\bort\b|wohnort|\bstadt\b|\bcity\b|\btown\b|\bville\b|localité/i],
    ['country', /\bland\b|country|\bpays\b/i],
    ['street', /strasse|straße|adresse|address|\brue\b/i],
    ['availability', /verfügbar|eintritt|start.?date|earliest|frühest|disponib/i],
    ['notice', /kündigungsfrist|notice period|préavis|délai de congé/i],
    ['salary', /lohn|gehalt|salär|salary|salaire|prétention/i],
  ];

  const AUTOCOMPLETE = {
    name: 'full_name', 'given-name': 'first_name', 'family-name': 'last_name', email: 'email', tel: 'phone',
    'tel-national': 'phone', 'street-address': 'street', 'address-line1': 'street', 'postal-code': 'postal_code',
    'address-level2': 'city', country: 'country', 'country-name': 'country', url: 'website',
  };
  const AUTOCOMPLETE_LOGIN = new Set(['username']);
  const AUTOCOMPLETE_SECRET = new Set(['current-password', 'new-password', 'one-time-code']);
  const AUTOCOMPLETE_OTHER = new Set(['organization', 'organization-title', 'bday', 'sex', 'cc-number']);

  const COUNTRY_NAMES = { schweiz: ['schweiz', 'suisse', 'svizzera', 'switzerland', 'ch', 'che'] };

  const DOCUMENT_RULES = [
    ['lebenslauf', /lebenslauf|curriculum|\bcv\b|resume|résumé/i],
    ['anschreiben', /anschreiben|motivation|cover.?letter|lettre/i],
    ['zeugnis', /zeugnis|reference letter|certificat de travail/i],
    ['zertifikate', /zertifikat|certificate|diplom|attestation/i],
  ];
  const ALL_FILES = 'unterlagen'; // one PDF with everything, from the app
  const PROOFS = 'nachweise'; // one PDF with references and certificates
  const PROOF_KINDS = ['zeugnis', 'zertifikate'];
  const ANY_DOCUMENT = /unterlagen|dokument|anhang|anhänge|anlage|beilage|attachment|document|upload|datei|fichier|pièce|\bfile/i;
  const NAMES_THE_DOCUMENTS = /unterlagen|dokument|document|beilage|anlage|bewerbung|candidature|pièces/i; // in what the person sees
  // Kinds of file the app does not hold. A generic word beside them says nothing, and the whole dossier must not end up there.
  const NOT_A_DOCUMENT = /foto\b|photo|bild\b|picture|image|portrait|avatar|selfie|video|logo|ausweis|\bpass\b|reisepass|passport|\bid.?(card|copy)|identit|strafregister|casier|betreibung|poursuite|arbeitsprobe|portfolio|work.?sample|bewilligung|permis|permit|visa\b/i;
  const MIME_BY_SUFFIX = { pdf: ['application/pdf'], zip: ['application/zip', 'application/x-zip-compressed'] };

  const APPLY_TEXT = /^(jetzt |online |hier |direkt |gleich )*(online )?(bewerben|bewerbung starten|zur bewerbung|zum bewerbungsformular|apply( now| here| online)?|postuler( maintenant)?|candidater)\b/i;
  const SEND_TEXT = /absenden|abschicken|versenden|senden|submit|\bsend\b|envoyer/i;

  /** "firstName_field-2" → "first Name field 2": names and ids read like words. */
  function words(text) {
    return String(text || '').replace(/([a-zäöü])([A-Z])/g, '$1 $2').replace(/[_\-.[\]]+/g, ' ');
  }

  function fromAutocomplete(value) {
    const tokens = String(value || '').toLowerCase().split(/\s+/).filter(Boolean);
    return tokens[tokens.length - 1] || '';
  }

  function ruleFor(text) {
    const found = VALUE_RULES.find(([, pattern]) => pattern.test(text));
    return found ? found[0] : null;
  }

  function classifyCheckbox(field, label) {
    return { kind: field.type === 'checkbox' && CONSENT.test(label) ? 'consent' : 'choice' };
  }

  function classifyByAutocomplete(token) {
    if (AUTOCOMPLETE_SECRET.has(token)) return { kind: 'password' };
    if (AUTOCOMPLETE_LOGIN.has(token)) return { kind: 'login' };
    if (AUTOCOMPLETE_OTHER.has(token)) return { kind: 'unclear', final: true };
    return AUTOCOMPLETE[token] ? { kind: 'value', key: AUTOCOMPLETE[token] } : null;
  }

  /** Pages often repeat the label as aria-label: that is not a longer text. */
  function longestLabel(field) {
    return Math.max(String(field.label || '').length, String(field.ariaLabel || '').length);
  }

  function classifyByText(field, label) {
    const sources = [label, field.placeholder || '', words(field.name)];
    for (const source of sources) {
      if (OTHER_PARTY.test(source) || ADDRESS_EXTRA.test(source)) return { kind: 'unclear', final: true };
      if (LOGIN.test(source)) return { kind: 'login' };
      const key = ruleFor(source);
      if (key) return { kind: 'value', key };
      if (BARE_NAME.test(source)) return { kind: 'value', key: 'full_name', bare: true };
    }
    return null;
  }

  /**
   * @param {{tag: string, type?: string, autocomplete?: string, name?: string, label?: string, ariaLabel?: string, placeholder?: string}} field
   * @returns {{kind: 'value'|'consent'|'choice'|'file'|'password'|'login'|'freetext'|'unclear', key?: string, bare?: boolean, final?: boolean}}
   */
  function classify(field) {
    const type = field.type || '';
    const label = [field.label, field.ariaLabel].filter(Boolean).join(' ');
    if (type === 'password') return { kind: 'password' };
    if (type === 'file') return { kind: 'file' };
    if (type === 'checkbox' || type === 'radio') return classifyCheckbox(field, label);
    const byAutocomplete = classifyByAutocomplete(fromAutocomplete(field.autocomplete));
    if (byAutocomplete) return byAutocomplete;
    const byText = classifyByText(field, label);
    const asks = [field.label, field.ariaLabel].some((text) => String(text || '').trim().endsWith('?'));
    // „Warum zu unserer Firma?“ is no company's name; a question about other people stays with the person.
    if (byText && byText.final && asks && !OTHER_PEOPLE.test(label) && !ADDRESS_EXTRA.test(label)) return { kind: 'freetext' };
    // The type of the field says more than a word in its label; another party or a login stays what it is.
    if (byText && byText.kind !== 'value') return byText;
    if (type === 'email') return { kind: 'value', key: 'email' };
    if (type === 'tel') return { kind: 'value', key: 'phone' };
    if (byText) return byText;
    if (field.tag === 'textarea' || asks || longestLabel(field) > LONG_QUESTION) return { kind: 'freetext' };
    return { kind: 'unclear' };
  }

  /** A form with „Name“ and „Vorname“ means the family name by „Name“. */
  function classifyAll(fields) {
    const found = fields.map(classify);
    const hasFirstName = found.some((f) => f.key === 'first_name');
    return found.map((f) => (f.bare && hasFirstName ? { kind: 'value', key: 'last_name' } : f));
  }

  /** A field the AI may look at. What the rules settled stays settled: another party's fields never get the person's values. */
  function needsHelp(found) {
    return found.kind === 'freetext' || (found.kind === 'unclear' && !found.final);
  }

  function normal(text) {
    return String(text || '').trim().toLowerCase();
  }

  /** Position of the option meaning this value, or -1: a guess would be worse than an open field. */
  function matchOption(options, value) {
    const names = COUNTRY_NAMES[normal(value)] || [normal(value)];
    return options.findIndex((o) => names.includes(normal(o.label)) || names.includes(normal(o.value)));
  }

  function accepts(accept, fileName) {
    const tokens = String(accept || '').split(',').map(normal).filter(Boolean);
    if (!tokens.length) return true;
    const suffix = normal(fileName).split('.').pop();
    const mimes = MIME_BY_SUFFIX[suffix] || [];
    return tokens.some((t) => t === `.${suffix}` || mimes.includes(t) || t === '*/*'
      || (t.endsWith('/*') && mimes.some((m) => m.startsWith(t.slice(0, -1)))));
  }

  function shownText(field) {
    return [field.label, field.ariaLabel].filter(Boolean).join(' ');
  }

  function fieldText(field) {
    return [shownText(field), words(field.name)].filter(Boolean).join(' ');
  }

  /** A generic word says little, and most file inputs have one in their id: for one file it must be a label naming the documents. */
  function wantedDocuments(field) {
    const text = fieldText(field);
    const named = DOCUMENT_RULES.filter(([, pattern]) => pattern.test(text)).map(([kind]) => kind);
    if (named.length) return named;
    if (NOT_A_DOCUMENT.test(text) || !ANY_DOCUMENT.test(text)) return [];
    return field.multiple || NAMES_THE_DOCUMENTS.test(shownText(field)) ? DOCUMENT_RULES.map(([kind]) => kind) : [];
  }

  /** The joined PDF that answers for these kinds of file, if there is one that does not add anything unasked for. */
  function joinedKey(kinds) {
    if (kinds.length === DOCUMENT_RULES.length) return ALL_FILES;
    return kinds.every((kind) => PROOF_KINDS.includes(kind)) ? PROOFS : null;
  }

  function pick(field, uploads, kinds) {
    const matching = uploads.filter((u) => kinds.some((kind) => u.schluessel === kind || u.schluessel.startsWith(`${kind}-`)));
    const fitting = matching.filter((u) => accepts(field.accept, u.name));
    if (matching.length && !fitting.length) return { keys: [], hinweis: `„${matching[0].name}“ passt nicht in dieses Feld.` };
    if (fitting.length > 1 && !field.multiple) {
      const joined = uploads.find((u) => u.schluessel === joinedKey(kinds));
      if (joined && accepts(field.accept, joined.name)) return { keys: [joined.schluessel] };
      return { keys: [], hinweis: 'Ein Feld für nur eine Datei: bitte selbst wählen.' };
    }
    return { keys: fitting.map((u) => u.schluessel) };
  }

  /**
   * Which files belong into a file field.
   * @param {{label?: string, ariaLabel?: string, name?: string, multiple?: boolean, accept?: string}} field
   * @param {{schluessel: string, name: string}[]} uploads
   * @returns {{keys: string[], hinweis?: string}}
   */
  function documentsFor(field, uploads) {
    return pick(field, uploads, wantedDocuments(field));
  }

  /** The files for the kind the AI named; the same checks of the field as for the rules. */
  function documentsForKind(field, uploads, kind) {
    const joined = uploads.find((u) => u.schluessel === kind);
    if (joined && accepts(field.accept, joined.name)) return { keys: [kind] };
    if (kind === ALL_FILES) return pick(field, uploads, DOCUMENT_RULES.map(([name]) => name));
    return pick(field, uploads, kind === PROOFS ? PROOF_KINDS : [kind]);
  }

  /** A file field the rules cannot place, and no reason they gave: only then the AI may look at it. */
  function fileNeedsHelp(field, uploads) {
    const { keys, hinweis } = documentsFor(field, uploads);
    return uploads.length > 0 && !keys.length && !hinweis && !NOT_A_DOCUMENT.test(fieldText(field));
  }

  /**
   * The link or button to the form on a page with only the ad; never a button that sends something.
   * @param {{text: string, href?: string, tag: string, type?: string, inForm?: boolean}[]} candidates
   * @returns {number} position or -1
   */
  function findApplyTarget(candidates) {
    return candidates.findIndex((c) => {
      const text = String(c.text || '').trim();
      if (!text || text.length > MAX_LINK_TEXT || !APPLY_TEXT.test(text) || SEND_TEXT.test(text)) return false;
      if (c.tag === 'a') return /^https?:/i.test(c.href || '');
      return !c.inForm && c.type !== 'submit';
    });
  }

  const api = { MIN_FIELDS, accepts, classify, classifyAll, documentsFor, documentsForKind, fileNeedsHelp, findApplyTarget, matchOption, needsHelp };
  root.bewerbungsbegleiterForm = api;
  if (typeof module !== 'undefined') module.exports = api;
})(globalThis);
