"use strict";
// Status messages, the same on every page (#215). Warnings and errors get a close button and stay until it is used
// or a newer message replaces them: an error must not vanish before it was read. Other messages fade after about
// eight seconds, but not while the pointer or the focus is on them. A message with an action stays until the action
// is used or the message is closed. Only DOM methods a small fake can offer (tests/meldungen.test.cjs).
(function (global) {
  const AUSBLENDEN_MS = 8000;
  const SCHLIESSEN = "Meldung schliessen";
  const STUFEN = { ok: "success", success: "success", hinweis: "warning", warning: "warning", fehler: "danger", danger: "danger" };
  const ALTE_KLASSEN = { success: "ok", warning: "hinweis", danger: "fehler" };  // the look of `.status` and `.befunde` lines
  const BLEIBEN = new Set(["warning", "danger"]);
  const zustaende = new WeakMap();

  function zustand(element) {
    if (!zustaende.has(element)) {
      const z = { timer: null, zeiger: false, fokus: false, faellig: false };
      zustaende.set(element, z);
      const vielleichtWeg = () => { if (z.faellig && !z.zeiger && !z.fokus) leere(element); };
      element.addEventListener("mouseenter", () => { z.zeiger = true; });
      element.addEventListener("mouseleave", () => { z.zeiger = false; vielleichtWeg(); });
      element.addEventListener("focusin", () => { z.fokus = true; });
      element.addEventListener("focusout", event => {
        z.fokus = Boolean(event.relatedTarget && element.contains(event.relatedTarget));
        vielleichtWeg();
      });
    }
    return zustaende.get(element);
  }

  function setzeStufe(element, level) {
    if (level) element.dataset.level = level;
    else delete element.dataset.level;
    if (!element.classList.contains("status")) return;
    Object.values(ALTE_KLASSEN).forEach(klasse => element.classList.remove(klasse));
    if (ALTE_KLASSEN[level]) element.classList.add(ALTE_KLASSEN[level]);
  }

  function knopf(element, text, beiKlick, label) {
    const button = element.ownerDocument.createElement("button");
    button.setAttribute("type", "button");
    button.className = label ? "status__close" : "btn btn--sm status__action";
    if (label) button.setAttribute("aria-label", label);
    button.append(text);
    button.addEventListener("click", beiKlick);
    return button;
  }

  /** Remove the message, its level and any waiting fade. */
  function leere(element) {
    const z = zustand(element);
    clearTimeout(z.timer);
    // Removing the children removes whatever held the focus, and no browser reliably tells the line.
    Object.assign(z, { timer: null, faellig: false, fokus: false });
    element.replaceChildren();
    setzeStufe(element, "");
    element.classList.remove("status--closable");
  }

  function ausblendenSpaeter(element, z) {
    z.timer = setTimeout(() => {
      z.timer = null;
      z.faellig = true;
      if (!z.zeiger && !z.fokus) leere(element);
    }, AUSBLENDEN_MS);
  }

  /**
   * Show `inhalt` (text, node or a list of both) in `element`. `stufe`: ok/success, hinweis/warning, fehler/danger
   * or empty. `aktion`: {text, ausfuehren} for a button that does something and then clears the message.
   */
  function zeige(element, inhalt, stufe = "", { aktion = null } = {}) {
    leere(element);
    const teile = (Array.isArray(inhalt) ? inhalt : [inhalt]).filter(t => t !== null && t !== undefined && t !== "");
    if (!teile.length) return;
    const level = STUFEN[stufe] || "";
    const text = element.ownerDocument.createElement("span");
    text.className = "status__text";
    text.append(...teile.map(t => (typeof t === "object" ? t : String(t))));
    element.append(text);
    setzeStufe(element, level);
    const bleibt = BLEIBEN.has(level) || Boolean(aktion);
    if (aktion) element.append(knopf(element, aktion.text, () => { leere(element); aktion.ausfuehren(); }));
    if (bleibt) {
      element.classList.add("status--closable");
      element.append(knopf(element, "×", () => leere(element), SCHLIESSEN));
      return;
    }
    ausblendenSpaeter(element, zustand(element));
  }

  /**
   * A line for a list of findings (`ul.befunde`): the search page's problems and hints, the import result. They
   * show together, so each warning or error gets its own close button; `beiSchliessen` lets the page remember it.
   */
  function listenZeile(document, inhalt, stufe = "", { beiSchliessen = null } = {}) {
    const level = STUFEN[stufe] || "";
    const zeile = document.createElement("li");
    if (ALTE_KLASSEN[level]) zeile.dataset.stufe = ALTE_KLASSEN[level];
    if (level) zeile.dataset.level = level;
    const text = document.createElement("span");
    text.className = "status__text";
    text.append(typeof inhalt === "object" ? inhalt : String(inhalt));
    zeile.append(text);
    if (!BLEIBEN.has(level)) return zeile;
    zeile.classList.add("status--closable");
    zeile.append(knopf(zeile, "×", () => {
      zeile.remove();
      if (beiSchliessen) beiSchliessen();
    }, SCHLIESSEN));
    return zeile;
  }

  const meldungen = { AUSBLENDEN_MS, SCHLIESSEN, zeige, leere, listenZeile };
  if (typeof module !== "undefined") module.exports = meldungen;
  else global.Meldungen = meldungen;
})(typeof window !== "undefined" ? window : globalThis);
