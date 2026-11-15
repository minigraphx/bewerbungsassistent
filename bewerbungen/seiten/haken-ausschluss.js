"use strict";
// On Stellen (#224, G83): every point under „Was fehlt oder unsicher ist“ gets „Künftig nicht zeigen“. The app says
// what it would add (a title word for the title filter or the point for the exclusions of the ad); the person picks
// the place, edits the entry and confirms. The message after it offers Rückgängig. Words in haken-ausschluss-logik.js.
(() => {
  const { holen, senden, el } = window.App;
  const L = window.HakenAusschlussLogik;
  const ROUTE = "/api/suche/haken-ausschluss";

  function rueckgaengig(art, wert, melde) {
    senden(`${ROUTE}/rueckgaengig`, { art, wert })
      .then(() => melde(L.zurueck(art, wert), "ok"))
      .catch(fehler => melde(`${L.NICHT_ZURUECK} ${fehler.message}`, "fehler"));
  }

  function schliesse(formular, knopf) {
    formular.replaceChildren();
    formular.hidden = true;
    knopf.setAttribute("aria-expanded", "false");
    knopf.focus();
  }

  function arten(vorschlag, name, hinweis) {
    return L.ARTEN.map(({ art, text }) => el("label", { class: "choice" },
      el("input", { type: "radio", name, value: art, checked: art === vorschlag.art,
        onchange: () => { hinweis.textContent = L.hinweis(art); } }),
      el("span", {}, el("span", { class: "choice__name" }, text)), el("span", {})));
  }

  function zeigeFormular(treffer, vorschlag, knopf, formular, { melde, du }) {
    const name = `haken-art-${treffer.id}`;
    const hinweis = el("p", { class: "field__hint" }, L.hinweis(vorschlag.art));
    const feld = el("input", { class: "input", type: "text", value: vorschlag.wert, spellcheck: "false" });
    const eintragen = el("button", { type: "submit", class: "btn btn--sm btn--primary" }, L.EINTRAGEN);
    const abbrechen = el("button", { type: "button", class: "btn btn--sm", onclick: () => schliesse(formular, knopf) }, L.ABBRECHEN);
    const form = el("form", { class: "exclusion-adopt__form" },
      el("fieldset", {}, el("legend", {}, `«${vorschlag.text}»`), el("p", { class: "field__hint" }, L.frage(du)),
        ...arten(vorschlag, name, hinweis),
        el("label", { class: "field" }, el("span", { class: "field__label" }, L.FELD), feld), hinweis,
        el("div", { class: "btn-row" }, eintragen, abbrechen)));
    form.addEventListener("submit", async ereignis => {
      ereignis.preventDefault();
      const art = form.querySelector(`input[name="${name}"]:checked`)?.value || vorschlag.art;
      eintragen.disabled = true;
      try {
        const antwort = await senden(ROUTE, { id: treffer.id, punkt: vorschlag.punkt, art, wert: feld.value });
        schliesse(formular, knopf);
        melde(L.uebernommen(antwort.art, antwort.wert), "ok",
          { aktion: { text: L.RUECKGAENGIG, ausfuehren: () => rueckgaengig(antwort.art, antwort.wert, melde) } });
      } catch (fehler) {
        eintragen.disabled = false;
        melde(`${L.NICHT_GESPEICHERT} ${fehler.message}`, "fehler");
      }
    });
    formular.replaceChildren(form);
    formular.hidden = false;
    knopf.setAttribute("aria-expanded", "true");
    feld.focus();
  }

  async function oeffne(treffer, punkt, knopf, formular, optionen) {
    try {
      const vorschlag = await holen(ROUTE, { id: treffer.id, punkt });
      zeigeFormular(treffer, vorschlag, knopf, formular, optionen);
    } catch (fehler) {
      optionen.melde(`${L.NICHT_GELADEN} ${fehler.message}`, "fehler");
    }
  }

  /** The column of the rating; without `anbieten` (apprenticeships) only the list. */
  function liste(treffer, titel, { anbieten, melde, du = false }) {
    const punkte = (treffer.bewertung && treffer.bewertung.haken) || [];
    if (!punkte.length) return null;
    if (!anbieten) return el("div", {}, el("h3", {}, titel), el("ul", {}, punkte.map(p => el("li", {}, p))));
    const formular = el("div", { class: "exclusion-adopt", hidden: true });
    const zeilen = punkte.map((punkt, index) => {
      const knopf = el("button", { type: "button", class: "btn btn--quiet btn--sm exclusion-adopt__open",
        "aria-label": L.knopfLabel(punkt), "aria-expanded": "false" }, L.KNOPF);
      knopf.addEventListener("click", () => oeffne(treffer, index, knopf, formular, { melde, du }));
      return el("li", {}, el("span", {}, punkt), " ", knopf);
    });
    return el("div", {}, el("h3", {}, titel), el("ul", {}, zeilen), formular);
  }

  window.HakenAusschluss = { liste };
})();
