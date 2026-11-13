"use strict";
// The window „KI einrichten“ (G60, #272): over the page, first the consent (for apprenticeships with the parent's
// confirmation in its text), then the way to the AI: invitation code, own Claude subscription or own key. The setup,
// a feature that needs the AI and an invitation link open it through App.kiEinrichten; closing it leaves the person on
// the page they were on. It reports the AI status it ends with, to the caller and as the event „ki-fenster-geschlossen“.
window.KiFenster = (() => {
  const { holen, senden, el, status } = window.App;
  const TITLE_ID = "ki-fenster-titel";
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

  function doneLine(ki) {
    const budget = ki.vermittlung && typeof ki.budget_usd === "number"
      ? ` Diesen Monat verbraucht: ${Number(ki.verbraucht_usd || 0).toFixed(2)} von ${ki.budget_usd.toFixed(2)} USD.` : "";
    return `${DONE}${budget}`;
  }

  /** Texts that speak to the person, in the set of the setup (Sie, du, Lehrstelle). */
  const texts = satz => key => window.Texte.text(key, satz);

  // ---------- The parts of the window ----------

  function invitationPart(state, t) {
    const code = el("input", { class: "input setup__code", id: "ki-fenster-code", autocomplete: "off", spellcheck: "false",
                               placeholder: "XXXX-XXXX-XXXX-XXXX" });
    const redeem = el("button", { type: "button", class: "btn btn--primary", disabled: true }, "Einladung einlösen");
    code.addEventListener("input", () => { redeem.disabled = !code.value.trim(); });
    redeem.addEventListener("click", () => state.run(redeem, async () => {
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
    const key = el("input", { class: "input", id: "ki-fenster-schluessel", type: "password", autocomplete: "off", spellcheck: "false" });
    const save = el("button", { type: "button", class: "btn btn--primary", disabled: true }, "Prüfen und speichern");
    const ready = () => { save.disabled = !tick.checked || !key.value.trim(); };
    tick.addEventListener("change", ready);
    key.addEventListener("input", ready);
    save.addEventListener("click", () => state.run(save, async () => {
      try {
        await senden("/api/schluessel/speichern", { schluessel: key.value, bestaetigt: tick.checked });
      } finally {
        key.value = "";
        ready();
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
                                                             onChoose: way => { state.way = way; draw(state); } });
    }
    for (const [way, part] of Object.entries(parts.ways)) {
      part.part.hidden = now !== "wahl" || state.way !== way;
      part.show(ki);
    }
    parts.done.hidden = now !== "fertig";
    if (now === "fertig") parts.done.textContent = doneLine(ki);
    parts.without.hidden = now === "fertig";
    parts.close.textContent = now === "fertig" ? "Weiter" : "Schliessen";
    parts.close.className = now === "fertig" ? "btn btn--primary" : "btn";
  }

  function build(state, satz) {
    const t = texts(satz);
    const dialog = el("dialog", { class: "dialog ki-fenster", "aria-labelledby": TITLE_ID });
    const message = el("p", { class: "status-line", role: "status", "aria-live": "polite" });
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
    state.run = async (knopf, action) => {
      knopf.disabled = true;
      try {
        state.update(await action());
      } catch (fehler) {
        status(state.message, fehler.message, "fehler");
      } finally {
        knopf.disabled = false;
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
