// Fills the Job-Room form for work efforts in the tab of a run (MIN-347) and watches for the message after saving.
// It only sets values and the choices of this one entry, and never touches a button: saving sends the entry to the RAV,
// and that stays with the person.
(function () {
  'use strict';
  if (globalThis.bewerbungsbegleiterRav) return;
  globalThis.bewerbungsbegleiterRav = true;
  const logic = globalThis.bewerbungsbegleiterRavFields;
  const POLL_MS = 700;
  const NO_FORM_POLLS = 6;
  const COLORS = { filled: '#2e7d32', open: '#ef6c00' };
  const DATE_CONTROL = '[alvformcontrolname="date"]';
  const FORM_PATH = '/work-efforts/create';
  const MIN_FORM_FIELDS = 5;
  const DIALOGS = 'ngb-modal-window, .modal, [role="dialog"]';
  const FIELDS = 'input:not([type="hidden"]), select, textarea';
  const NOT_OURS = /gehört nicht/; // the run has ended

  let timer = null;
  let busy = false;
  let filledFor = null;
  let filledForm = null;
  let savedFor = null;
  let polls = 0;
  let noFormSaid = false;
  let lastCount = -1;
  let unsent = null; // the report about a filled form, kept until the service worker has taken it

  function send(art, data) {
    return chrome.runtime.sendMessage({ art, ...data });
  }

  function stop() {
    clearInterval(timer);
  }

  /** The form by its controls; on the right address also one that has lost them, so the change can be reported. */
  function findForm() {
    const forms = [...document.querySelectorAll('form')];
    const known = forms.find((form) => form.querySelector(DATE_CONTROL));
    if (known) return known;
    if (!location.pathname.endsWith(FORM_PATH)) return null;
    return forms.find((form) => form.querySelectorAll(FIELDS).length >= MIN_FORM_FIELDS) || null;
  }

  function savedShown() {
    return [...document.querySelectorAll(DIALOGS)].some((dialog) => logic.isSavedTitle(dialog.textContent));
  }

  function describe(el) {
    const type = (el.type || '').toLowerCase();
    return {
      control: el.closest('[alvformcontrolname]')?.getAttribute('alvformcontrolname') || '',
      type,
      label: el.labels?.[0]?.textContent || '',
      combobox: el.getAttribute('role') === 'combobox',
      filled: type === 'checkbox' || type === 'radio' ? el.checked : Boolean(el.value),
    };
  }

  function mark(el, color) {
    const target = el.type === 'checkbox' || el.type === 'radio' ? el.labels?.[0] || el : el;
    target.style.setProperty('outline', `2px solid ${color}`, 'important');
    target.style.setProperty('outline-offset', '1px', 'important');
  }

  function setText(el, value) {
    Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value').set.call(el, value);
    for (const type of ['input', 'change']) el.dispatchEvent(new Event(type, { bubbles: true }));
    el.dispatchEvent(new Event('blur'));
  }

  function fillForm(form, values) {
    const elements = [...form.querySelectorAll(FIELDS)];
    const found = logic.plan(elements.map(describe), values);
    for (const action of found.actions) {
      const el = elements[action.index];
      if (action.kind === 'text') setText(el, action.value);
      else el.click();
      mark(el, COLORS.filled);
    }
    for (const index of found.open) mark(elements[index], COLORS.open);
    return found;
  }

  async function fillNow(form) {
    const answer = await send('rav-daten');
    if (!answer || answer.fehler) {
      filledForm = form; // the bar says what is wrong; asking again would not change it
      if (answer && NOT_OURS.test(answer.fehler)) stop();
      return;
    }
    const found = fillForm(form, answer.werte);
    filledFor = answer.id;
    filledForm = form;
    unsent = { id: answer.id, hinweise: found.hints, geaendert: found.changed };
    await sendReport();
  }

  async function sendReport() {
    await send('rav-stand', unsent);
    unsent = null;
  }

  async function step() {
    if (unsent) await sendReport();
    if (savedShown()) {
      if (filledFor && savedFor !== filledFor) {
        await send('rav-gespeichert', { id: filledFor });
        savedFor = filledFor;
      }
      return;
    }
    const form = findForm();
    if (!form) {
      polls += 1;
      lastCount = -1;
      if (polls >= NO_FORM_POLLS && !noFormSaid) {
        await send('rav-kein-formular');
        noFormSaid = true;
      }
      return;
    }
    polls = 0;
    noFormSaid = false;
    const count = form.querySelectorAll(FIELDS).length;
    const settled = count === lastCount;
    lastCount = count;
    // The same form stays as filled; a new one after a route change gets the entry again, unless it was just saved.
    if (!settled || form === filledForm || savedFor === filledFor && filledFor) return;
    await fillNow(form);
  }

  async function tick() {
    if (busy) return;
    busy = true;
    try {
      await step();
    } catch {
      // Reloaded extension: this script has lost its connection. Otherwise the next poll tries again.
      if (!chrome.runtime?.id) stop();
    } finally {
      busy = false;
    }
  }

  chrome.runtime.onMessage.addListener((message) => {
    if (message && message.art === 'formular-ende') stop();
  });
  timer = setInterval(tick, POLL_MS);
  send('rav-wartet').catch(() => { /* the bar comes with the first report */ });
})();
