"use strict";
// Card «Sprache» under Einstellungen, KI, Budget und Sprache (G10, G12, #94, A10): the language of the app and the
// languages the person applies in. Each change saves at once; saves run one after the other, so the last change wins.
// Until the person confirms, the application languages are the suggestion from the CV.
(() => {
  const { holen, senden, status, el } = window.App;
  const L = window.SpracheLogik;
  const $ = id => document.getElementById(id);
  const NAME = "bewerbungssprache";

  let queue = Promise.resolve();
  let drawn = false;

  const boxes = () => [...document.querySelectorAll(`input[name="${NAME}"]`)];

  function checkbox(option) {
    const input = el("input", { type: "checkbox", name: NAME, value: option.value });
    input.addEventListener("change", saveApplications);
    return el("label", { class: "language__option" }, input, el("span", { class: "language__label" }));
  }

  function buildOnce(view) {
    if (drawn) return;
    drawn = true;
    $("sprache-app").replaceChildren(...L.APP_LANGUAGES.map(({ value, label, lang }) => el("option", { value, lang }, label)));
    $("sprache-optionen").replaceChildren(...view.options.map(checkbox));
  }

  function draw(state) {
    const view = L.view(state);
    buildOnce(view);
    $("sprache-app").value = view.app;
    $("sprache-folgt").textContent = view.pending || "";
    $("sprache-folgt").hidden = !view.pending;
    for (const [index, option] of view.options.entries()) {
      const input = boxes()[index];
      input.checked = option.checked;
      input.parentElement.querySelector(".language__label").replaceChildren(...window.DotLine.render(option.parts, el));
    }
    $("sprache-uebernehmen-zeile").hidden = !view.confirm;
    return view;
  }

  /** Send one change after the ones before it; on failure the page shows the stored state again. */
  function save(body, done, field) {
    queue = queue.then(async () => {
      try {
        draw(await senden("/api/sprachen", body()));
        window.Meldungen.clearInputError($("sprache-meldung"));
        status($("sprache-meldung"), done, "ok");
      } catch (fehler) {
        window.Meldungen.showFailure($("sprache-meldung"), field, fehler);
        await holen("/api/sprachen").then(draw, () => null);
      }
    });
    return queue;
  }

  function saveApplications() {
    return save(() => ({ bewerbung: L.checkedValues(boxes()) }), "Bewerbungssprachen gespeichert.", $("sprache-bewerbung"));
  }

  $("sprache-app").addEventListener("change", event => {
    const app = event.target.value;
    save(() => ({ app }), "Sprache der App gespeichert.", $("sprache-app"));
  });

  $("sprache-uebernehmen").addEventListener("click", async () => {
    await save(() => ({ bewerbung: L.checkedValues(boxes()) }), "Vorschlag übernommen.", $("sprache-bewerbung"));
    // The button is gone once the choice is stored; the focus goes to the choice it confirmed.
    if ($("sprache-uebernehmen-zeile").hidden) (boxes().find(box => box.checked) || boxes()[0])?.focus();
  });

  holen("/api/sprachen").then(draw, fehler => status($("sprache-meldung"), fehler.message, "fehler"));
})();
