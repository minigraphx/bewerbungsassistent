"use strict";
// Suggestions for professions on the search page (MIN-375): the AI proposes, the person decides what goes into the search.
(() => {
  const { senden, el, status } = window.App;
  const $ = id => document.getElementById(id);

  async function add(name, button, note) {
    button.disabled = true;
    try {
      await senden("/api/beruf/aufnehmen", { beruf: name });
      button.hidden = true;
      note.textContent = "In deiner Suche. Die nächste Suche sucht auch danach.";
      note.focus();
      document.dispatchEvent(new CustomEvent("suchprofil-geaendert"));
    } catch (fehler) {
      button.disabled = false;
      status($("vorschlag-status"), fehler.message, "fehler");
    }
  }

  function card(item) {
    const note = el("span", { class: "leise", tabindex: "-1" }, item.schon_gesucht ? "Steht schon in deiner Suche." : "");
    const button = el("button", { type: "button", "aria-label": `${item.beruf} in die Suche aufnehmen` }, "In die Suche aufnehmen");
    button.hidden = item.schon_gesucht;
    button.addEventListener("click", () => add(item.beruf, button, note));
    return el("li", {},
      el("strong", {}, item.beruf),
      el("p", {}, item.warum),
      el("p", { class: "leise" }, `Im Alltag: ${item.alltag}`),
      el("p", { class: "leise" }, `In der Schnupperlehre: ${item.pruefen}`),
      el("div", { class: "knoepfe" }, button, note));
  }

  async function ask() {
    $("vorschlag-holen").disabled = true;
    $("vorschlag-liste").replaceChildren();
    status($("vorschlag-status"), "Die KI überlegt, das dauert einen Moment …", "");
    try {
      const { vorschlaege } = await senden("/api/beruf/vorschlag", {
        interessen: $("vorschlag-interessen").value, staerken: $("vorschlag-staerken").value, vermeiden: $("vorschlag-vermeiden").value,
      });
      $("vorschlag-liste").replaceChildren(...vorschlaege.map(card));
      status($("vorschlag-status"), `${vorschlaege.length} Vorschläge. Nimm auf, was dich interessiert.`, "ok");
    } catch (fehler) {
      status($("vorschlag-status"), fehler.message, "fehler");
    } finally {
      $("vorschlag-holen").disabled = false;
    }
  }

  $("vorschlag-holen").addEventListener("click", ask);
})();
