"use strict";
// On Stellen (#224, G83): every point under „Was fehlt oder unsicher ist“ gets „Künftig nicht zeigen“, or
// „Ausgeschlossen“ when an entry already excludes it. The form opens inside the point: the app says what it would add,
// the person picks the place, edits the entry and confirms. Errors stay in the form; the confirmation with Rückgängig
// replaces it in the same box, so the feedback stays where the person works. Words in haken-ausschluss-logik.js.
(() => {
  const { holen, senden, el } = window.App;
  const L = window.HakenAusschlussLogik;
  const ROUTE = "/api/suche/haken-ausschluss";

  function setzeAusgeschlossen(zeile, ja) {
    zeile.aktion.replaceChildren(ja ? el("span", { class: "exclusion-point__done" }, L.AUSGESCHLOSSEN) : zeile.knopf);
  }

  /** Shows feedback in the point's box as a status and moves the focus there. */
  function zeigeImPunkt(zeile, ...inhalt) {
    zeile.offen = false;
    zeile.box.replaceChildren(...inhalt.filter(Boolean));  // replaceChildren would write a missing part as „null“
    zeile.box.setAttribute("role", "status");
    zeile.box.hidden = false;
    zeile.knopf.setAttribute("aria-expanded", "false");
    zeile.box.focus();
  }

  const reportInPoint = (zeile, text) => zeigeImPunkt(zeile, el("p", { class: "field__error" }, text));

  function schliesse(zeile) {
    zeile.offen = false;
    zeile.box.replaceChildren();
    zeile.box.removeAttribute("role");
    zeile.box.hidden = true;
    zeile.knopf.setAttribute("aria-expanded", "false");
    zeile.knopf.focus();
  }

  function zeigeBestaetigung(zeile, antwort, fehlerText = "") {
    const zurueck = el("button", { type: "button", class: "btn btn--sm" }, L.RUECKGAENGIG);
    zurueck.addEventListener("click", () => nimmZurueck(zeile, antwort));
    zeigeImPunkt(zeile, el("p", {}, L.uebernommen(antwort.art, antwort.wert)),
      fehlerText ? el("p", { class: "field__error" }, fehlerText) : null, el("div", { class: "btn-row" }, zurueck));
  }

  const reportUndo = (zeile, antwort, text) => zeigeBestaetigung(zeile, antwort, text);

  async function nimmZurueck(zeile, antwort) {
    try {
      await senden(`${ROUTE}/rueckgaengig`, { art: antwort.art, wert: antwort.wert });
      setzeAusgeschlossen(zeile, false);
      zeigeImPunkt(zeile, el("p", {}, L.zurueck(antwort.art, antwort.wert)));
    } catch (fehler) {
      reportUndo(zeile, antwort, `${L.NICHT_ZURUECK} ${fehler.message}`);
    }
  }

  /** The error above the buttons; the field points to it and gets the focus back. */
  function reportInForm(teile, text) {
    teile.fehler.textContent = text;
    teile.fehler.hidden = false;
    teile.feld.setAttribute("aria-invalid", "true");
    teile.feld.setAttribute("aria-describedby", `${teile.intro.id} ${teile.hinweis.id} ${teile.fehler.id}`);
    teile.feld.focus();
  }

  async function speichere(zeile, eintrag, teile) {
    try {
      const antwort = await senden(ROUTE, { id: zeile.treffer.id, punkt: zeile.index, ...eintrag });
      setzeAusgeschlossen(zeile, true);
      zeigeBestaetigung(zeile, antwort);
    } catch (fehler) {
      reportInForm(teile, `${L.NICHT_GESPEICHERT} ${fehler.message}`);
    }
  }

  function arten(name, auswahl, hinweis) {
    return L.ARTEN.map(({ art, text }) => el("label", { class: "choice" },
      el("input", { type: "radio", name, value: art, checked: art === auswahl.art,
        onchange: () => { auswahl.art = art; hinweis.textContent = L.hinweis(art); } }),
      el("span", {}, el("span", { class: "choice__name" }, text))));
  }

  function formular(zeile, vorschlag) {
    const id = zeile.box.id;
    const auswahl = { art: vorschlag.art };
    const intro = el("p", { class: "field__hint", id: `${id}-intro` }, L.frage(zeile.karte, zeile.du));
    const hinweis = el("p", { class: "field__hint", id: `${id}-hinweis` }, L.hinweis(vorschlag.art));
    const feld = el("input", { class: "input", type: "text", id: `${id}-feld`, value: vorschlag.wert,
      spellcheck: "false", "aria-describedby": `${intro.id} ${hinweis.id}` });
    const fehler = el("p", { class: "field__error", id: `${id}-fehler`, hidden: true });
    const form = el("form", { class: "exclusion-adopt__form" }, intro,
      el("fieldset", {}, el("legend", {}, L.WO), arten(`${id}-art`, auswahl, hinweis)), hinweis,
      el("label", { class: "field", for: feld.id }, el("span", { class: "field__label" }, L.FELD), feld), fehler,
      el("div", { class: "btn-row" }, el("button", { type: "submit", class: "btn btn--sm" }, L.EINTRAGEN),
        el("button", { type: "button", class: "btn btn--sm", onclick: () => schliesse(zeile) }, L.ABBRECHEN)));
    form.addEventListener("submit", ereignis => {
      ereignis.preventDefault();
      speichere(zeile, { art: auswahl.art, wert: feld.value }, { feld, fehler, intro, hinweis });
    });
    return { form, feld };
  }

  function zeigeFormular(zeile, vorschlag) {
    const { form, feld } = formular(zeile, vorschlag);
    zeile.box.removeAttribute("role");
    zeile.box.replaceChildren(form);
    zeile.box.hidden = false;
    zeile.knopf.setAttribute("aria-expanded", "true");
    zeile.offen = true;
    feld.focus();
    feld.setSelectionRange(feld.value.length, feld.value.length);
  }

  async function oeffne(zeile) {
    try {
      zeigeFormular(zeile, await holen(ROUTE, { id: zeile.treffer.id, punkt: zeile.index }));
    } catch (fehler) {
      reportInPoint(zeile, `${L.NICHT_GELADEN} ${fehler.message}`);
    }
  }

  /** One point: its text, a line with the button or «Ausgeschlossen», and the box for the form and the feedback. */
  function punktZeile(treffer, punkt, index, kontext) {
    const boxId = `haken-${treffer.id}-${index}`;
    const box = el("div", { class: "exclusion-adopt", id: boxId, tabindex: "-1", hidden: true });
    const knopf = el("button", { type: "button", class: "btn btn--sm", "aria-label": L.knopfLabel(punkt),
      "aria-expanded": "false", "aria-controls": boxId }, L.KNOPF);
    const zeile = { treffer, index, box, knopf, aktion: el("div", { class: "exclusion-point__action" }, knopf),
      offen: false, ...kontext };
    // A second click closes the open form; reopening it would rebuild it over what the person typed.
    knopf.addEventListener("click", () => (zeile.offen ? schliesse(zeile) : oeffne(zeile)));
    box.addEventListener("keydown", ereignis => {
      if (ereignis.key !== "Escape" || !zeile.offen) return;
      ereignis.preventDefault();
      schliesse(zeile);
    });
    return { zeile, li: el("li", { class: "exclusion-point" }, el("span", {}, punkt), zeile.aktion, box) };
  }

  const reportState = (stand, text) => { stand.textContent = text; stand.hidden = false; };

  async function pruefeStand(treffer, zeilen, stand) {
    try {
      const { ausgeschlossen } = await holen(`${ROUTE}/punkte`, { id: treffer.id });
      zeilen.forEach((zeile, index) => { if (ausgeschlossen[index]) setzeAusgeschlossen(zeile, true); });
    } catch (fehler) {
      reportState(stand, `${L.STAND_FEHLT} ${fehler.message}`);
    }
  }

  /** The column of the rating; without `anbieten` (apprenticeships) only the list. `satz` is the set of texts. */
  function liste(treffer, titel, { anbieten, satz }) {
    const punkte = (treffer.bewertung && treffer.bewertung.haken) || [];
    if (!punkte.length) return null;
    if (!anbieten) return el("div", {}, el("h3", {}, titel), el("ul", {}, punkte.map(p => el("li", {}, p))));
    const kontext = { karte: window.Texte.text("einstellen.nicht", satz), du: satz === "stelle-du" };
    const gebaut = punkte.map((punkt, index) => punktZeile(treffer, punkt, index, kontext));
    const stand = el("p", { class: "field__hint", hidden: true });
    pruefeStand(treffer, gebaut.map(g => g.zeile), stand);
    return el("div", {}, el("h3", {}, titel), el("ul", { class: "exclusion-points" }, gebaut.map(g => g.li)), stand);
  }

  window.HakenAusschluss = { liste };
})();
