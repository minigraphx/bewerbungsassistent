"use strict";
// The window „KI einrichten“ (G60, #272): over the page, first the consent (for apprenticeships with the parent's
// confirmation in its text), then the way to the AI: invitation code, own Claude subscription or own key. The setup,
// a feature that needs the AI and an invitation link open it through App.kiEinrichten; closing it leaves the person on
// the page they were on. It reports the AI status it ends with, to the caller and as the event „ki-fenster-geschlossen“.
window.KiFenster = (() => {
  const { holen, senden, el, status } = window.App;
  const TITLE_ID = "ki-fenster-titel";
  // One line for the messages of the window; only one way shows at a time, so it describes the code and the key field.
  const MESSAGE_ID = "ki-fenster-meldung";
  const DONE = "Die KI ist eingerichtet.";
  const NO_MEDIATION = "Diese App hat keine Vermittlung eingebaut. Ein Einladungscode geht hier nicht.";
  const AGREED = "Ich habe das gelesen und bin einverstanden.";
  const KEY_TEXTS = ["einstellungen.kosten-selbst", "einstellungen.vertrag", "einstellungen.linkedin"];
  const CLOSED = "ki-fenster-geschlossen";

  let current = null;  // { promise, ... } while the window is open

  const consentOpen = ki => Boolean(ki?.einwilligung && !ki.einwilligung.erteilt);

  /** „einwilligung“ before anything else, „fertig“ once the AI answers, otherwise the choice of the way. */
  function stage(ki) {
    if (consentOpen(ki)) return "einwilligung";
    return ki?.eingerichtet ? "fertig" : "wahl";
  }

  /** The way in use: the own key goes before the mediation, the subscription counts only while switched on. */
  function wayInUse(ki, abo) {
    if (ki?.eigener_schluessel) return "schluessel";
    if (ki?.eingerichtet && ki.vermittlung) return "einladung";
    return abo?.zugang ? "abo" : null;
  }

  const USED_UP = " Das Guthaben ist aufgebraucht: einen neuen Code anfordern und unter Einstellungen, KI und Guthaben einlösen.";

  const withCredit = ki => Boolean(ki.vermittlung) && typeof ki.guthaben_chf === "number";
  const creditUsedUp = ki => withCredit(ki) && Number(ki.verbraucht_chf || 0) >= ki.guthaben_chf;

  // Written like TrefferLogik.money (#347), which pages without a search do not load; app.js loads this window anywhere.
  const chf = amount => `CHF\u00a0${amount.toFixed(2)}`;

  function doneLine(ki) {
    if (!withCredit(ki)) return DONE;
    const spent = Number(ki.verbraucht_chf || 0);
    const credit = ` Guthaben: ${chf(spent)} von ${chf(ki.guthaben_chf)} verbraucht.`;
    return `${DONE}${credit}${creditUsedUp(ki) ? USED_UP : ""}`;
  }

  /** Texts that speak to the person, in the set of the setup (Sie, du, Lehrstelle). */
  const texts = satz => key => window.Texte.text(key, satz);

  // ---------- The parts of the window ----------

  function invitationPart(state, t) {
    const code = el("input", { class: "input setup__code", id: "ki-fenster-code", autocomplete: "off", spellcheck: "false",
                               placeholder: "XXXX-XXXX-XXXX-XXXX", "aria-describedby": MESSAGE_ID });
    const redeem = el("button", { type: "button", class: "btn btn--primary", disabled: true }, "Einladung einlösen");
    const ready = () => { redeem.disabled = !code.value.trim(); };
    code.addEventListener("input", ready);
    redeem.addEventListener("click", () => state.run({ button: redeem, field: code, ready }, async () => {
      const ki = await senden("/api/ki/einladung", { code: code.value.trim() });
      code.value = "";
      return ki;
    }));
    const field = el("div", { class: "field" }, el("p", { class: "field__hint" }, t("einrichtung.ki.code")),
      el("label", { class: "field__label", for: "ki-fenster-code" }, "Einladungscode"),
      el("div", { class: "setup__path setup__path--code" }, code, redeem));
    const none = el("p", { class: "field__hint" }, NO_MEDIATION);
    return { part: el("div", { class: "ki-fenster__weg" }, field, none), show: ki => { field.hidden = !ki.einladung; none.hidden = Boolean(ki.einladung); } };
  }

  function subscriptionPart(t) {
    return { part: el("div", { class: "ki-fenster__weg" }, el("p", { class: "field__hint" }, t("ki-fenster.abo")),
      el("div", { class: "btn-row" }, el("a", { class: "btn", href: "/einstellungen#claude-abo", target: "_blank", rel: "noopener" },
        "In den Einstellungen einrichten"))), show: () => {} };
  }

  function keyPart(state, t) {
    const tick = el("input", { type: "checkbox" });
    const key = el("input", { class: "input", id: "ki-fenster-schluessel", type: "password", autocomplete: "off", spellcheck: "false",
                              "aria-describedby": MESSAGE_ID });
    const save = el("button", { type: "button", class: "btn btn--primary", disabled: true }, "Prüfen und speichern");
    const ready = () => { save.disabled = !tick.checked || !key.value.trim(); };
    tick.addEventListener("change", ready);
    key.addEventListener("input", ready);
    save.addEventListener("click", () => state.run({ button: save, field: key, ready }, async () => {
      try {
        await senden("/api/schluessel/speichern", { schluessel: key.value, bestaetigt: tick.checked });
      } finally {
        key.value = "";  // sent once, never kept
      }
      return holen("/api/ki/status");
    }));
    return { part: el("div", { class: "ki-fenster__weg" },
      el("ul", { class: "ki-fenster__liste" }, KEY_TEXTS.map(name => el("li", {}, t(name)))),
      el("label", { class: "schalter" }, tick, ` ${AGREED}`),
      el("label", { class: "field__label", for: "ki-fenster-schluessel" }, "API-Schlüssel"), key,
      el("div", { class: "btn-row" }, save)), show: () => {} };
  }

  // ---------- Drawing ----------

  // The shared line would describe the other way's field with a refused code or key; any other failure stays until «×».
  function chooseWay(state, way) {
    window.Meldungen.clearInputError(state.message);
    state.way = way;
    draw(state);
  }

  function draw(state) {
    const { ki, abo, parts } = state;
    const now = stage(ki);
    parts.consent.hidden = now !== "einwilligung";
    if (now === "einwilligung") window.Einwilligung.zeige(parts.consent, ki.einwilligung, next => state.update(next));
    parts.choice.hidden = now !== "wahl";
    if (now === "wahl" && !state.choice) {
      const offered = window.KiZugang.options({ abo: Boolean(abo) });
      const inUse = wayInUse(ki, abo);
      state.way = inUse || (ki.einladung ? "einladung" : "schluessel");
      state.choice = window.KiZugang.render(parts.choice, { name: "ki-fenster-weg", offered, current: inUse, chosen: state.way,
                                                             onChoose: way => chooseWay(state, way) });
    }
    for (const [way, part] of Object.entries(parts.ways)) {
      part.part.hidden = now !== "wahl" || state.way !== way;
      part.show(ki);
    }
    parts.done.hidden = now !== "fertig";
    if (now === "fertig") {
      parts.done.className = `notice ${creditUsedUp(ki) ? "notice--warning" : "notice--success"} ki-fenster__fertig`;
      // One span, or the flex row of the notice puts the link on a line of its own.
      parts.done.replaceChildren(el("span", { class: "notice__body" }, ...window.Texte.withCodeRequestLink(doneLine(ki), el)));
    }
    parts.without.hidden = now === "fertig";
    // The link „anfordern“ comes first in the window; Enter goes on to „Weiter“, not to the website.
    parts.close.autofocus = now === "fertig";
    parts.close.textContent = now === "fertig" ? "Weiter" : "Schliessen";
    parts.close.className = now === "fertig" ? "btn btn--primary" : "btn";
  }

  function build(state, satz) {
    const t = texts(satz);
    const dialog = el("dialog", { class: "dialog ki-fenster", "aria-labelledby": TITLE_ID });
    const message = el("p", { class: "status-line", id: MESSAGE_ID, role: "status", "aria-live": "polite" });
    state.message = message;
    const parts = {
      consent: el("div", { class: "field einwilligung" }),
      choice: el("fieldset", { class: "access-choice" }, el("legend", { class: "visually-hidden" }, "Weg zur KI")),
      ways: { einladung: invitationPart(state, t), abo: subscriptionPart(t), schluessel: keyPart(state, t) },
      done: el("p", { class: "notice notice--success ki-fenster__fertig" }),
      without: el("p", { class: "field__hint" }, t("einrichtung.ki.ohne")),
      close: el("button", { type: "button", class: "btn" }, "Schliessen"),
    };
    parts.close.addEventListener("click", () => dialog.close());
    dialog.append(el("h2", { class: "dialog__title", id: TITLE_ID }, "KI einrichten"),
      el("p", { class: "dialog__text" }, t("einrichtung.ki.aufgabe")), parts.consent, parts.choice,
      ...Object.values(parts.ways).map(part => part.part), parts.done, message, parts.without,
      el("div", { class: "dialog__actions" }, parts.close));
    state.parts = parts;
    return dialog;
  }

  // ---------- Opening and closing ----------

  async function load() {
    const [ki, abo] = await Promise.all([
      holen("/api/ki/status").catch(fehler => ({ eingerichtet: false, hinweis: fehler.message })),
      holen("/api/claude/stand").catch(() => null),  // only the packaged app with its desktop part has the subscription
    ]);
    return { ki, abo };
  }

  function stateFor() {
    const state = { ki: null, abo: null, choice: null, way: null };
    state.update = ki => {
      state.ki = ki;
      if (ki.einladung_fehler) status(state.message, ki.einladung_fehler, "fehler");
      draw(state);
    };
    // A refused code or key is fixed in its field and clears on the first input there (G97, #361, as in Einstellungen);
    // a mediation or Anthropic out of reach stays until «×». `ready` gives the button back the state of its field.
    state.run = async ({ button, field, ready }, action) => {
      let failed = null;
      button.disabled = true;
      try {
        const ki = await action();
        field.removeAttribute("aria-invalid");
        window.Meldungen.clearInputError(state.message);
        state.update(ki);
      } catch (fehler) {
        failed = fehler;
        window.Meldungen.showFailure(state.message, field, fehler);
      } finally {
        ready();
        if (failed) window.Meldungen.focusAfterFailure(failed, field, button);
      }
    };
    return state;
  }

  async function show(resolve) {
    const state = stateFor();
    const [{ ki, abo }, satz] = await Promise.all([load(), window.App.textsatz ? window.App.textsatz() : "stelle-sie"]);
    Object.assign(state, { ki, abo });
    const dialog = build(state, satz);
    const refresh = () => { if (!document.hidden) holen("/api/ki/status").then(state.update, () => {}); };
    dialog.addEventListener("close", () => {
      document.removeEventListener("visibilitychange", refresh);
      dialog.remove();
      current = null;
      document.dispatchEvent(new CustomEvent(CLOSED, { detail: state.ki }));
      resolve(state.ki);
    });
    document.addEventListener("visibilitychange", refresh);  // back from the settings in another tab
    document.body.append(dialog);
    draw(state);
    dialog.showModal();
  }

  /** Opens the window, or returns the one already open; resolves with the AI status once it is closed. */
  function oeffnen() {
    if (!current) {
      current = { promise: new Promise((resolve, reject) => show(resolve).catch(fehler => { current = null; reject(fehler); })) };
    }
    return current.promise;
  }

  return { oeffnen, stage, wayInUse, CLOSED };
})();
