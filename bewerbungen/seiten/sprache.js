"use strict";
// Card «Sprache» under Einstellungen, KI, Budget und Sprache (G10, G12, #94, A10): the language of the app and the
// languages the person applies in. Each change saves at once; saves run one after the other, so the last change wins.
// Until the person changes a box, the suggestion from the CV is the setting; the first change saves every visible box.
(() => {
  const { holen, senden, status, el } = window.App;
  const L = window.SpracheLogik;
  const $ = id => document.getElementById(id);
  const NAME = "bewerbungssprache";
  const noteId = value => `sprache-hinweis-${value}`;

  let queue = Promise.resolve();
  let drawn = false;
  let stored = null;  // the last state the server sent; a refused change goes back to it

  const boxes = () => [...document.querySelectorAll(`input[name="${NAME}"]`)];

  // The note stands under the name, outside the label, so the label names the language only.
  function checkbox(option) {
    const input = el("input", { type: "checkbox", name: NAME, value: option.value, id: `sprache-${option.value}` });
    input.addEventListener("change", saveApplications);
    return el("div", { class: "language__option" },
      el("label", { class: "language__choice" }, input, el("span", { class: "language__label" }, option.label)),
      el("p", { class: "field__hint language__note", id: noteId(option.value), hidden: true }));
  }

  function buildOnce(view) {
    if (drawn) return;
    drawn = true;
    $("sprache-app").replaceChildren(...L.APP_LANGUAGES.map(({ value, label, lang }) => el("option", { value, lang }, label)));
    $("sprache-optionen").replaceChildren(...view.options.map(checkbox));
  }

  function drawPending(pending) {
    const line = $("sprache-folgt");
    line.textContent = pending ? pending.text : "";
    line.hidden = !pending;
    if (pending) line.setAttribute("lang", pending.lang);
    else line.removeAttribute("lang");
  }

  function drawOption(input, option) {
    const note = $(noteId(option.value));
    input.checked = option.checked;
    note.textContent = option.note || "";
    note.hidden = !option.note;
    if (option.note) input.setAttribute("aria-describedby", note.id);
    else input.removeAttribute("aria-describedby");
  }

  function draw(state) {
    stored = state;
    const view = L.view(state);
    buildOnce(view);
    $("sprache-app").value = view.app;
    drawPending(view.pending);
    const inputs = boxes();
    for (const [index, option] of view.options.entries()) drawOption(inputs[index], option);
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
        draw(stored);
      }
    });
    return queue;
  }

  function saveApplications() {
    return save(() => ({ bewerbung: L.checkedValues(boxes()) }), window.Texte.t("Bewerbungssprachen gespeichert."),
                $("sprache-bewerbung"));
  }

  $("sprache-app").addEventListener("change", event => {
    const app = event.target.value;
    save(() => ({ app }), window.Texte.t("Sprache der App gespeichert."), $("sprache-app"));
  });

  holen("/api/sprachen").then(draw, fehler => status($("sprache-meldung"), fehler.message, "fehler"));
})();
