"use strict";
// The choice of the way to the AI (#265, A10): invitation code, own Claude subscription or own key from Anthropic.
// One component for the page „Einstellungen“ and the window that sets up the AI (G60, #272): it draws the choice and
// reports the way picked; what each way then asks for stays with the place that uses it.
(function (global) {
  const GUIDE = "https://github.com/minigraphx/bewerbungsassistent/blob/main/docs";
  // Texts in the app language (#416); texte.js is loaded before this file on every page, required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);

  // Texts without an address, so they fit every text set (Sie, du, Lehrstelle).
  function allOptions() {
    const Texte = texts();
    return [
      { value: "einladung", title: Texte.t("Einladungscode"), text: Texte.t("Kostenlos im Pilot, mit einem Budget von CHF 5 pro Monat.") },
      { value: "abo", title: Texte.t("Eigenes Claude-Abo"), text: Texte.t("Die Arbeit läuft in Claude, die App liefert die Werkzeuge."),
        link: { href: `${GUIDE}/eigenes-abo.md`, text: Texte.t("Anleitung") } },
      { value: "schluessel", title: Texte.t("Eigener Schlüssel von Anthropic"), text: Texte.t("Für Geübte. Anthropic rechnet die KI direkt ab."),
        link: { href: `${GUIDE}/installation.md#eigener-api-schlüssel-freiwillig`, text: Texte.t("Woher der Schlüssel kommt und was er kostet") } },
    ];
  }

  /** The ways this app can offer; the subscription only where the packaged app has its routes. */
  function options({ abo = false } = {}) {
    return allOptions().filter(option => abo || option.value !== "abo");
  }

  /** The line under the title; the way in use says so first. */
  function line(option, current) {
    const Texte = texts();
    return option.value === current ? Texte.t("Eingerichtet. {weg}", { weg: option.text }) : option.text;
  }

  /**
   * Draws the choice into `container` and calls `onChoose(value)` when the person picks a way.
   * Returns { choose(value) } to mark a way from outside, for example after a change elsewhere on the page.
   */
  function render(container, { name = "ki-zugang", offered, current = null, chosen = current, onChoose = () => {} }) {
    const { el } = global.App;
    const textOf = new Map();
    const inputs = offered.map(option => {
      const input = el("input", { type: "radio", name, value: option.value, class: "access-choice__radio" });
      input.checked = option.value === chosen;
      input.addEventListener("change", () => { if (input.checked) onChoose(option.value); });
      const text = el("span", { class: "access-choice__text" }, line(option, current));
      textOf.set(option.value, text);
      const link = option.link
        ? [" ", el("a", { href: option.link.href, target: "_blank", rel: "noopener" }, option.link.text)] : [];
      container.append(el("label", { class: "access-choice__option" }, input,
        el("span", { class: "access-choice__body" }, el("strong", { class: "access-choice__title" }, option.title),
          el("span", { class: "access-choice__line" }, text, ...link))));
      return input;
    });
    return {
      choose(value) {
        for (const input of inputs) input.checked = input.value === value;
      },
      setCurrent(value) {
        for (const option of offered) textOf.get(option.value).textContent = line(option, value);
      },
    };
  }

  const component = { options, line, render };
  if (typeof module !== "undefined") module.exports = component;
  else global.KiZugang = component;
})(typeof window !== "undefined" ? window : globalThis);
