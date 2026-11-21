"use strict";
// Card «Browser der App» under Einstellungen, Browser und Erweiterung (G99, #369): a radio group that saves on change.
// Only the installed app has the route; elsewhere the card stays hidden. The focus stays where the person put it,
// also when saving fails and the previous choice comes back.
(() => {
  const { holen, senden, status, el } = window.App;
  const L = window.BrowserWahlLogik;
  const $ = id => document.getElementById(id);
  const NAME = "app-browser";

  let saved = null;
  let platform = null;
  let latest = 0;

  function radio(option) {
    const input = el("input", { type: "radio", name: NAME, value: option.value, class: "access-choice__radio",
                                disabled: option.disabled, "aria-describedby": option.note ? `browser-fehlt-${option.value}` : null });
    input.checked = option.checked;
    input.addEventListener("change", () => { if (input.checked) choose(option.value); });
    const note = option.note
      ? el("span", { class: "access-choice__line browser-choice__missing", id: `browser-fehlt-${option.value}` }, option.note) : null;
    return el("label", { class: "access-choice__option" }, input,
      el("span", { class: "access-choice__body" }, el("strong", { class: "access-choice__title" }, option.label), note));
  }

  function draw(state) {
    saved = L.options(state).find(option => option.checked).value;
    platform = state.plattform;
    $("browser-optionen").replaceChildren(...L.options(state).map(radio));
  }

  function check(value) {
    for (const input of document.querySelectorAll(`input[name="${NAME}"]`)) input.checked = input.value === value;
  }

  async function choose(value) {
    const ask = ++latest;
    try {
      const state = await senden("/api/app/browser", { wahl: value });
      if (ask !== latest) return;
      saved = state.gewaehlt;
      status($("browser-meldung"), L.savedText(saved, platform), "ok");
    } catch (fehler) {
      // A newer choice is already on its way; its answer speaks, not this older one.
      if (ask === latest) {
        check(saved);
        status($("browser-meldung"), L.failedText(fehler.message), "fehler");
      }
    }
  }

  holen("/api/app/browser").then(state => {
    draw(state);
    $("browser").hidden = false;
    if (location.hash === "#browser") $("browser").scrollIntoView({ block: "start" });
  }, () => { /* the app without the desktop part has no such card */ });
})();
