"use strict";
// The language switch (#435, G10, UI/UX design before building): Deutsch, Français and English, each in its own
// language, at the bottom of the sidebar (inside «Menü» below 900 px) and, on Einrichtung, beside its heading instead.
// It writes the same setting as the card «Sprache» (POST /api/sprachen with `app`), one save after the other. Until
// #434 turns the translation on, a choice is stored and the line under the buttons says the translation is coming;
// afterwards the page reloads in the new language, through the page's own guard for unsaved input, and the focus
// comes back to the chosen language.
(() => {
  const L = window.SpracheLogik;
  const App = window.App;
  if (!L || !App) return;
  const { holen, senden, el } = App;
  const ROUTE = "/api/sprachen";
  // One-shot mark across the reload: the path of the page that reloaded, so another page never takes the focus.
  const RELOAD_KEY = "bewerbungsbegleiter.sprachwahl";
  const RELOAD_EVENT = "sprachwahl-neuladen";  // Einrichtung keeps its unsaved first step on it
  const SAVED_EVENT = "sprache-gespeichert";  // the card and the switch show the same setting on Einstellungen
  // Einrichtung has its own copy in its header; then the sidebar's stays hidden, so there are never two.
  const group = document.getElementById("setup-language") || document.getElementById("nav-language");
  const line = group && document.getElementById(`${group.id}-status`);
  if (!group || !line) return;

  let stored = null;  // the last state the server sent; a failed save goes back to it
  let queue = Promise.resolve();

  const buttons = () => [...group.querySelectorAll(".language-switch__option")];

  function option({ value, label, lang }) {
    const button = el("button", { type: "button", class: "language-switch__option", lang, "data-value": value,
                                  "aria-pressed": "false" }, label);
    button.addEventListener("click", () => choose(value));
    return button;
  }

  function buildOnce() {
    if (buttons().length) return;
    group.setAttribute("aria-label", L.SWITCH_LABEL);
    group.append(...L.APP_LANGUAGES.map(option));
    group.hidden = false;
  }

  function drawPending(pending) {
    window.Meldungen.leere(line);
    if (pending) line.append(el("span", { class: "status__text", lang: pending.lang }, pending.text));
  }

  /** The marking follows the stored setting, like the card, even while the page is still German. */
  function draw(state, { withLine = true } = {}) {
    stored = state;
    const view = L.switchView(state);
    buildOnce();
    for (const button of buttons()) button.setAttribute("aria-pressed", String(button.getAttribute("data-value") === view.app));
    if (withLine) drawPending(view.pending);
    return view;
  }

  function tellOthers(state) {
    document.dispatchEvent(new CustomEvent(SAVED_EVENT, { detail: state }));
  }

  function reload() {
    document.dispatchEvent(new CustomEvent(RELOAD_EVENT));
    try { sessionStorage.setItem(RELOAD_KEY, location.pathname); } catch { /* blocked storage: the focus starts at the top */ }
    location.reload();
  }

  function choose(value) {
    if (stored && L.switchView(stored).app === value) return queue;  // the current language is no action
    queue = queue.then(async () => {
      try {
        const state = await senden(ROUTE, { app: value });
        if (L.switchView(state).translated) return reload();
        draw(state);
        tellOthers(state);
      } catch (fehler) {
        draw(stored, { withLine: false });
        window.Meldungen.showFailure(line, group, fehler);
      }
    });
    return queue;
  }

  function focusAfterReload() {
    let reloaded = null;
    try {
      reloaded = sessionStorage.getItem(RELOAD_KEY);
      sessionStorage.removeItem(RELOAD_KEY);
    } catch { /* blocked storage: nothing was marked */ }
    if (reloaded !== location.pathname) return;
    const current = buttons().find(button => button.getAttribute("aria-pressed") === "true");
    if (current) current.focus();
  }

  /** Einrichtung after a folder was chosen or came back: that folder's language, and the note when it kept its own. */
  async function refresh(carried) {
    try {
      draw(await holen(ROUTE));
    } catch {
      return;  // the app is closing: the switch keeps what it shows
    }
    const note = L.folderNote(carried);
    if (note) window.Meldungen.zeige(line, note, "hinweis");
  }

  document.addEventListener(SAVED_EVENT, event => { if (event.detail && event.detail !== stored) draw(event.detail); });
  window.Sprachwahl = { refresh };
  // Like the sidebar's other parts, the switch stays hidden when its question fails.
  holen(ROUTE).then(state => { draw(state); focusAfterReload(); }, () => {});
})();
