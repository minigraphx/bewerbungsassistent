// Fills the form in one frame of a tab the person opened from the app (MIN-346). It never presses a button that
// sends, never sets a checkbox, fills no hidden field, keeps what is there and does not fill a field twice, so what
// the person removes stays removed. A password field stops it: logging in is for the person.
(function () {
  'use strict';
  if (globalThis.bewerbungsbegleiterFiller) return;
  const logic = globalThis.bewerbungsbegleiterForm;
  const isTop = window === window.top;
  // Colour and line differ (design MIN-369), so the marks work without colours too; the legend is in bar.js.
  const LINES = { filled: '2px solid #2e7d32', open: '2px dashed #ef6c00', consent: '3px double #c62828', draft: '2px dotted #1565c0',
                  aiFile: '2px dotted #1565c0' };
  const FIELD_SELECTOR = 'input, select, textarea';
  const SKIPPED_TYPES = new Set(['hidden', 'submit', 'button', 'reset', 'image', 'search', 'range', 'color']);
  const MUTATION_WAIT_MS = 600;
  const MAX_NEARBY_TEXT = 120;
  const NEARBY_LEVELS = 3;
  const MAX_STAND_IN_HEIGHT = 120;
  const MARK = 'data-bewerbungsbegleiter';
  const MIN_SIZE = 4;
  const MIN_OPACITY = 0.1;
  const MAX_PAGE_TOP = 30000;
  const FRAME_WAIT_MS = 1000;
  const OBSERVED = { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style', 'hidden'] };
  const TICK_TYPES = new Set(['checkbox', 'radio']);
  const AI_WAIT_MS = 1200; // forms build their fields bit by bit: one question instead of many
  const MAX_AI_FIELDS = 12;
  const MAX_AI_OPTIONS = 20;
  const MAX_AI_LABEL = 300; // the limits of the app: a page cannot fill the extension's storage with its texts
  const MAX_AI_NAME = 100;
  const MAX_AI_HINT = 150;
  const MAX_AI_OPTION = 60;
  const LARGE_FILE_BYTES = 10000000; // forms rarely say their limit before they refuse
  const BYTES_PER_MB = 1000000;

  const handled = new Map(); // element → status
  let job = null; // { values, uploads, ai }
  let stopped = false;
  let observer = null;
  let timer = null;
  let running = null;
  let lastSent = '';
  let hints = [];
  let frameTimer = null;
  const askedAi = new WeakSet();
  let nextRef = 1;
  let aiTimer = null;
  let aiBusy = false;

  function allRoots(start = document) {
    const hosts = [...start.querySelectorAll('*')].filter((el) => el.shadowRoot);
    return [start, ...hosts.flatMap((host) => allRoots(host.shadowRoot))];
  }

  function allFields() {
    return allRoots().flatMap((root) => [...root.querySelectorAll(FIELD_SELECTOR)])
      .filter((el) => !SKIPPED_TYPES.has((el.type || '').toLowerCase()));
  }

  function parentOf(node) {
    return node.parentElement || node.getRootNode().host || null;
  }

  /** Nearly transparent, or inside a box of no size: a person cannot see it, a page can still read it. */
  function hiddenByStyle(el) {
    let opacity = 1;
    for (let node = el; node; node = parentOf(node)) {
      const style = getComputedStyle(node);
      opacity *= Number(style.opacity);
      if (opacity < MIN_OPACITY) return true;
      if (node === el && style.clipPath !== 'none') return true;
      if (node !== el && style.overflow !== 'visible') {
        const box = node.getBoundingClientRect();
        if (box.width < MIN_SIZE || box.height < MIN_SIZE) return true;
      }
    }
    return false;
  }

  function seen(el) {
    if (!el.isConnected || !el.checkVisibility({ checkVisibilityCSS: true, visibilityProperty: true })) return false;
    const box = el.getBoundingClientRect();
    if (box.width < MIN_SIZE || box.height < MIN_SIZE) return false;
    const onPage = box.right + window.scrollX > 0 && box.bottom + window.scrollY > 0
      && box.left + window.scrollX < window.innerWidth && box.top + window.scrollY < MAX_PAGE_TOP;
    return onPage && !hiddenByStyle(el);
  }

  /** Styled upload and tick boxes hide their input: what the person sees is the label or a small wrapper. */
  function standIn(el) {
    const stand = el.labels?.[0] || el.parentElement;
    return stand && stand.getBoundingClientRect().height <= MAX_STAND_IN_HEIGHT && seen(stand) ? stand : null;
  }

  /** Hidden fields stay empty: forms can collect data and files in them. */
  function eligible(el) {
    if (seen(el)) return true;
    return (el.type === 'file' || TICK_TYPES.has(el.type)) && Boolean(standIn(el));
  }

  function textOf(el) {
    return (el.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function nearbyText(el) {
    let node = el;
    for (let level = 0; node && level < NEARBY_LEVELS; level += 1) {
      const before = node.previousElementSibling;
      if (before && !before.querySelector(FIELD_SELECTOR) && textOf(before)) return textOf(before).slice(0, MAX_NEARBY_TEXT);
      node = node.parentElement;
    }
    return '';
  }

  function labelOf(el) {
    const own = el.labels ? [...el.labels].map(textOf).join(' ') : '';
    if (own) return own;
    const ids = (el.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean);
    const named = ids.map((id) => el.getRootNode().getElementById?.(id)).filter(Boolean).map(textOf).join(' ');
    return named || nearbyText(el);
  }

  function describe(el) {
    const names = [el.name, el.id, el.getAttribute('data-automation-id'), el.getAttribute('data-testid'), el.getAttribute('data-qa')];
    return {
      tag: el.tagName.toLowerCase(), type: (el.type || '').toLowerCase(), autocomplete: el.getAttribute('autocomplete') || '',
      name: names.filter(Boolean).join(' '), label: labelOf(el), ariaLabel: el.getAttribute('aria-label') || '',
      placeholder: el.getAttribute('placeholder') || '', multiple: Boolean(el.multiple), accept: el.getAttribute('accept') || '',
    };
  }

  function mark(el, status) {
    handled.set(el, status);
    const target = seen(el) ? el : standIn(el);
    if (!target || !LINES[status]) return;
    target.style.setProperty('outline', LINES[status], 'important');
    target.style.setProperty('outline-offset', '1px', 'important');
    target.setAttribute(MARK, status);
  }

  function setNative(el, value) {
    const proto = Object.getPrototypeOf(el);
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
    for (const type of ['input', 'change']) el.dispatchEvent(new Event(type, { bubbles: true }));
    el.dispatchEvent(new Event('blur'));
  }

  function fillSelect(el, value) {
    if (el.selectedIndex > 0 && el.value) return 'kept';
    const options = [...el.options].map((o) => ({ value: o.value, label: o.text }));
    const position = logic.matchOption(options, value);
    if (position < 0) return 'open';
    setNative(el, el.options[position].value);
    return 'filled';
  }

  function fillValue(el, key) {
    const value = job.values[key];
    if (!value || el.disabled || el.readOnly) return el.value ? 'kept' : 'open';
    if (el.tagName === 'SELECT') return fillSelect(el, value);
    if (el.value.trim()) return 'kept';
    setNative(el, value);
    return el.value === value ? 'filled' : 'open'; // a date or number field refuses text
  }

  async function fetchFile(key) {
    const answer = await chrome.runtime.sendMessage({ art: 'formular-datei', schluessel: key });
    if (!answer || answer.fehler) throw new Error((answer && answer.fehler) || 'Datei nicht erhalten');
    const bytes = Uint8Array.from(atob(answer.daten), (c) => c.charCodeAt(0));
    return new File([bytes], answer.name, { type: answer.typ });
  }

  async function fillFile(el, field) {
    if (el.files && el.files.length) return 'kept';
    const { keys, hinweis } = logic.documentsFor(field, job.uploads);
    if (hinweis) hints = [...hints, hinweis];
    if (!keys.length) return 'open';
    return await placeFiles(el, keys) ? 'filled' : 'open';
  }

  /** @returns {Promise<boolean>} whether they went in; `stillWanted` asks again after the wait for the files */
  async function placeFiles(el, keys, stillWanted = () => true) {
    const files = await Promise.all(keys.map(fetchFile));
    if (!stillWanted()) return false;
    const transfer = new DataTransfer();
    for (const file of files) {
      transfer.items.add(file);
      if (file.size > LARGE_FILE_BYTES) addHints([`„${file.name}“ ist ${Math.round(file.size / BYTES_PER_MB)} MB gross. Manche Formulare nehmen weniger.`]);
    }
    el.files = transfer.files;
    for (const type of ['input', 'change']) el.dispatchEvent(new Event(type, { bubbles: true }));
    return true;
  }

  async function act(el, field, found) {
    if (found.kind === 'value') return fillValue(el, found.key);
    if (found.kind === 'file') {
      try {
        return await fillFile(el, field);
      } catch (error) {
        hints = [...hints, `Datei nicht hochgeladen: ${error.message}`];
        return 'open';
      }
    }
    if (found.kind === 'consent') return el.checked ? 'kept' : 'consent';
    return el.value && el.type !== 'checkbox' && el.type !== 'radio' ? 'kept' : 'open';
  }

  function stillOpen(el, status) {
    if (status === 'consent') return !el.checked;
    if (status !== 'open') return false;
    if (el.type === 'checkbox' || el.type === 'radio') return false; // optional unless the form says otherwise
    return el.type === 'file' ? !el.files?.length : !el.value;
  }

  function report(fields, login) {
    const present = [...handled].filter(([el]) => el.isConnected);
    const count = (status) => present.filter(([, s]) => s === status).length;
    return {
      felder: login ? 0 : fields.length, gefuellt: count('filled'),
      offen: present.filter(([el, s]) => s === 'open' && stillOpen(el, s)).length,
      einwilligungen: present.filter(([el, s]) => s === 'consent' && stillOpen(el, s)).length,
      entwuerfe: count('draft'), kiDateien: count('aiFile'), ki: aiBusy ? 1 : 0, anmeldung: login, hinweise: hints,
    };
  }

  function canTakeHelp(el) {
    return el.isConnected && handled.get(el) === 'open' && !el.disabled && !el.readOnly && !el.value.trim()
      && !TICK_TYPES.has(el.type) && el.type !== 'file' && eligible(el);
  }

  function canTakeFile(el) {
    return el.isConnected && handled.get(el) === 'open' && el.type === 'file' && !el.disabled && !el.files?.length && eligible(el);
  }

  function aiMayLookAt(el, found) {
    if (found.kind === 'file') return canTakeFile(el) && logic.fileNeedsHelp(describe(el), job.uploads);
    return logic.needsHelp(found) && canTakeHelp(el);
  }

  /** The open fields no rule could decide, each only once. */
  function fieldsForAi() {
    const fields = allFields().filter(eligible);
    if (fields.some((el) => el.type === 'password')) return [];
    const found = logic.classifyAll(fields.map(describe));
    if (found.some((f) => f.kind === 'password')) return [];
    return fields.map((el, position) => ({ el, found: found[position] }))
      .filter(({ el, found: f }) => aiMayLookAt(el, f) && !askedAi.has(el));
  }

  /** What the page shows of a field, nothing of the person. */
  function askAbout({ el, found }) {
    const field = describe(el);
    const isList = el.tagName === 'SELECT';
    const asked = found.kind === 'freetext' && !isList ? 'frage' : 'unklar';
    return {
      ref: `f${nextRef++}`, art: found.kind === 'file' ? 'datei' : asked,
      label: [...new Set([field.label, field.ariaLabel])].filter(Boolean).join(' ').slice(0, MAX_AI_LABEL),
      name: field.name.slice(0, MAX_AI_NAME), hinweis: field.placeholder.slice(0, MAX_AI_HINT),
      optionen: isList ? [...el.options].slice(0, MAX_AI_OPTIONS).map((o) => o.text.slice(0, MAX_AI_OPTION)) : [],
      laenge: el.maxLength > 0 ? el.maxLength : 0, einzeilig: el.tagName !== 'TEXTAREA',
    };
  }

  function addHints(more) {
    hints = [...new Set([...hints, ...more])];
  }

  /** A draft that does not arrive as written is not left in the field: unmarked it would look like the person's text. */
  function fillDraft(el, text) {
    if (typeof text !== 'string' || !text) return 'open';
    if (el.maxLength > 0 && text.length > el.maxLength) return 'open';
    const wanted = text.replace(/\r\n?/g, '\n');
    setNative(el, wanted);
    if (el.value === wanted) return 'draft';
    setNative(el, '');
    return 'open';
  }

  /** Marked like a draft: the person checks what the AI chose. A file can reach the company at once, so never over one already there. */
  async function placeChosenFile(el, kind) {
    const { keys, hinweis } = logic.documentsForKind(describe(el), job.uploads, kind);
    if (hinweis) addHints([hinweis]);
    if (!keys.length) return;
    try {
      if (await placeFiles(el, keys, () => !stopped && canTakeFile(el))) mark(el, 'aiFile');
    } catch (error) {
      addHints([`Datei nicht hochgeladen: ${error.message}`]);
    }
  }

  /** The answer of the AI, checked again here: the person may have typed meanwhile, and only known values exist. */
  async function applyHelp(answer, byRef) {
    for (const [ref, key] of Object.entries(answer.zuordnung || {})) {
      const el = byRef.get(ref);
      if (el && canTakeHelp(el) && Object.hasOwn(job.values, key)) mark(el, fillValue(el, key));
    }
    for (const [ref, text] of Object.entries(answer.entwuerfe || {})) {
      const el = byRef.get(ref);
      if (el && canTakeHelp(el)) mark(el, fillDraft(el, text));
    }
    for (const [ref, kind] of Object.entries(answer.dateien || {})) {
      const el = byRef.get(ref);
      if (el && canTakeFile(el)) await placeChosenFile(el, kind);
    }
    if (Array.isArray(answer.hinweise)) addHints(answer.hinweise.filter((h) => typeof h === 'string'));
  }

  async function askAi() {
    aiTimer = null;
    try {
      const open = stopped ? [] : fieldsForAi().slice(0, MAX_AI_FIELDS);
      if (open.length) {
        const requests = open.map(askAbout);
        const byRef = new Map(open.map(({ el }, position) => [requests[position].ref, el]));
        open.forEach(({ el }) => askedAi.add(el));
        const answer = await chrome.runtime.sendMessage({ art: 'formular-ki', felder: requests });
        if (!answer || answer.fehler) throw new Error((answer && answer.fehler) || 'Keine Antwort');
        if (!stopped) await applyHelp(answer, byRef);
      }
    } catch (error) {
      addHints([`KI-Hilfe: ${error.message}`]);
    } finally {
      aiBusy = false;
      schedule(); // the state for the bar, and fields beyond this request
    }
  }

  function startHelp() {
    if (!job.ai || aiBusy || stopped || !fieldsForAi().length) return;
    aiBusy = true;
    aiTimer = setTimeout(askAi, AI_WAIT_MS);
  }

  async function pass() {
    const fields = allFields().filter(eligible);
    const secret = fields.some((el) => el.type === 'password' && seen(el));
    const found = logic.classifyAll(fields.map(describe));
    const login = secret || found.some((f) => f.kind === 'password');
    const countable = fields.filter((el) => !TICK_TYPES.has(el.type)); // tick boxes alone are a filter or a cookie banner
    if (login || countable.length < logic.MIN_FIELDS) return report([], login);
    for (const [position, el] of fields.entries()) {
      if (!handled.has(el)) mark(el, await act(el, describe(el), found[position]));
    }
    startHelp();
    return report(countable, false);
  }

  /** One pass at a time; what changes meanwhile is picked up by the next one. */
  function run() {
    if (!running) running = pass().finally(() => { running = null; });
    return running;
  }

  function sendIfChanged(bericht) {
    const text = JSON.stringify(bericht);
    if (text === lastSent) return;
    lastSent = text;
    chrome.runtime.sendMessage({ art: 'formular-stand', bericht }).catch(() => { /* the extension was reloaded */ });
  }

  function schedule() {
    if (stopped) return;
    clearTimeout(timer);
    timer = setTimeout(() => run().then(sendIfChanged, () => {}), MUTATION_WAIT_MS);
  }

  /** Application systems often build their frame after the page has loaded; those frames need the scripts too. */
  function frameLoaded(event) {
    if (stopped || !event.target || event.target.tagName !== 'IFRAME') return;
    clearTimeout(frameTimer);
    frameTimer = setTimeout(() => {
      chrome.runtime.sendMessage({ art: 'formular-rahmen' }).catch(() => { /* the extension was reloaded */ });
    }, FRAME_WAIT_MS);
  }

  /** A frame that goes away while the AI is asked can no longer say that it is done. */
  function leaving() {
    if (!aiBusy) return;
    aiBusy = false;
    sendIfChanged({ ...JSON.parse(lastSent || '{}'), ki: 0 });
  }

  function watch() {
    if (observer) return;
    window.addEventListener('pagehide', leaving);
    observer = new MutationObserver(schedule);
    observer.observe(document.documentElement, OBSERVED);
    document.addEventListener('change', schedule, true);
    document.addEventListener('input', schedule, true);
    document.addEventListener('load', frameLoaded, true);
  }

  async function fill(values, uploads, ai) {
    job = { values, uploads, ai: ai === true };
    stopped = false;
    watch();
    const bericht = await run();
    lastSent = JSON.stringify(bericht);
    return bericht;
  }

  function clearMarks() {
    for (const root of allRoots()) {
      for (const el of root.querySelectorAll(`[${MARK}]`)) {
        el.style.removeProperty('outline');
        el.style.removeProperty('outline-offset');
        el.removeAttribute(MARK);
      }
    }
  }

  function stop() {
    stopped = true;
    clearTimeout(timer);
    clearTimeout(aiTimer);
    aiBusy = false;
    if (observer) observer.disconnect();
    observer = null;
    document.removeEventListener('change', schedule, true);
    document.removeEventListener('input', schedule, true);
    document.removeEventListener('load', frameLoaded, true);
    clearTimeout(frameTimer);
    clearMarks();
  }

  function follow() {
    // With a field on the page a button may be what sends it, even outside a form: then only links.
    const hasField = allFields().some(seen);
    const nodes = [...document.querySelectorAll('a[href], button, [role="button"]')]
      .filter((el) => seen(el) && (el.tagName === 'A' || !hasField));
    const candidates = nodes.map((el) => ({
      text: textOf(el) || el.getAttribute('aria-label') || '', href: el.href, tag: el.tagName.toLowerCase(),
      type: el.tagName === 'BUTTON' ? el.type : el.getAttribute('type') || '', inForm: Boolean(el.closest('form')),
    }));
    const position = logic.findApplyTarget(candidates);
    if (position < 0) return {};
    if (candidates[position].tag === 'a') return { url: nodes[position].href };
    nodes[position].click();
    return { geklickt: true };
  }

  globalThis.bewerbungsbegleiterFiller = { fill, follow, stop, isTop };
  chrome.runtime.onMessage.addListener((message) => {
    if (message && message.art === 'formular-ende') stop();
  });
})();
