"use strict";
// The choice of the way to the AI (#265, A10): invitation code, own Claude subscription or own key from Anthropic.
// One component for the page „Einstellungen“ and the window that sets up the AI (G60, #272): it draws the choice and
// reports the way picked; what each way then asks for stays with the place that uses it.
(function (global) {
  const GUIDE = "https://github.com/minigraphx/bewerbungsassistent/blob/main/docs";
  const IN_USE = "Eingerichtet.";
  // Texts without an address, so they fit every text set (Sie, du, Lehrstelle).
  const OPTIONS = [
    { value: "einladung", title: "Einladungscode", text: "Kostenlos im Pilot, mit einem Budget pro Monat." },
    { value: "abo", title: "Eigenes Claude-Abo", text: "Die Arbeit läuft in Claude, die App liefert die Werkzeuge.",
      link: { href: `${GUIDE}/eigenes-abo.md`, text: "Anleitung" } },
    { value: "schluessel", title: "Eigener Schlüssel von Anthropic", text: "Für Geübte. Anthropic rechnet die KI direkt ab.",
      link: { href: `${GUIDE}/installation.md#eigener-api-schlüssel-freiwillig`, text: "Woher der Schlüssel kommt und was er kostet" } },
  ];

  /** The ways this app can offer; the subscription only where the packaged app has its routes. */
  function options({ abo = false } = {}) {
    return OPTIONS.filter(option => abo || option.value !== "abo");
  }

  /** The line under the title; the way in use says so first. */
  function line(option, current) {
    return option.value === current ? `${IN_USE} ${option.text}` : option.text;
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
