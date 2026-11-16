"use strict";
// The searched terms on Suche einstellen as an ordered list (#285, G87): the person drags a row by its handle or moves
// it with „Nach oben“ and „Nach unten“, also from the keyboard. Each move is announced in the list's message line,
// focus stays on the moved term's button, and the whole order goes to the server, one request after the other.
// Logic without DOM in suchliste-logik.js; the rows' Entfernen belongs to the page (beruf-vorschlag.js).
window.Suchliste = (() => {
  const { el, senden, status } = window.App;
  const L = window.SuchlisteLogik;
  const ROUTE = "/api/beruf/reihenfolge";
  const ZIEHT = "suchliste__eintrag--zieht";
  let liste = null;
  let begriffe = [];
  let optionen = {};
  let zeilen = [];  // per term its row and buttons, to find the focused one again after drawing anew
  let ziehen = null;
  let offen = 0;
  let kette = Promise.resolve();

  function fokusVorher() {
    const aktiv = document.activeElement;
    const zeile = zeilen.find(z => Object.values(z.knoepfe).includes(aktiv));
    return zeile ? { name: zeile.name, rolle: Object.keys(zeile.knoepfe).find(rolle => zeile.knoepfe[rolle] === aktiv) } : null;
  }

  function knopf(rolle, name, index, anzahl) {
    const namen = L.knopfNamen(name);
    if (rolle === "entfernen") {
      const button = el("button", { type: "button", class: "klein", "aria-label": namen.entfernen }, "Entfernen");
      button.addEventListener("click", () => optionen.entfernen(name, button));
      return button;
    }
    const hoch = rolle === "hoch";
    // aria-disabled instead of disabled: the button keeps focus when its term reaches the end of the list.
    const amEnde = hoch ? index === 0 : index === anzahl - 1;
    const button = el("button", { type: "button", class: "suchliste__pfeil", "aria-label": namen[rolle],
      title: hoch ? "Nach oben" : "Nach unten", "aria-disabled": amEnde ? "true" : null }, hoch ? "↑" : "↓");
    button.addEventListener("click", () => bewege(name, hoch ? index - 1 : index + 1));
    return button;
  }

  function zeile(name, index, anzahl) {
    const ordnen = anzahl > 1;
    const knoepfe = ordnen
      ? { hoch: knopf("hoch", name, index, anzahl), runter: knopf("runter", name, index, anzahl), entfernen: knopf("entfernen", name) }
      : { entfernen: knopf("entfernen", name) };
    const griff = ordnen ? el("span", { class: "suchliste__griff", "aria-hidden": "true", title: "Ziehen, um zu verschieben" }) : null;
    if (griff) griff.addEventListener("pointerdown", event => beginne(event, name));
    const klasse = ziehen && ziehen.name === name ? `suchliste__eintrag ${ZIEHT}` : "suchliste__eintrag";
    const li = el("li", { class: klasse, "data-begriff": name }, griff,
      el("span", { class: "suchliste__nummer" }, `${index + 1}.`), el("span", { class: "suchliste__name" }, name),
      el("span", { class: "suchliste__knoepfe" }, ...Object.values(knoepfe)));
    return { name, li, knoepfe };
  }

  function zeichne() {
    const fokus = fokusVorher();
    zeilen = begriffe.map((name, index) => zeile(name, index, begriffe.length));
    liste.replaceChildren(...zeilen.map(z => z.li));
    const wieder = fokus && zeilen.find(z => z.name === fokus.name);
    if (wieder && wieder.knoepfe[fokus.rolle]) wieder.knoepfe[fokus.rolle].focus();
  }

  function speichere() {
    const reihenfolge = [...begriffe];
    offen += 1;
    kette = kette
      .then(() => senden(ROUTE, { berufe: reihenfolge }))
      .catch(fehler => status(optionen.status, fehler.message, "fehler"))
      .finally(() => {
        offen -= 1;
        // after a refusal too: the page loads what the server has saved
        if (offen === 0) optionen.geaendert();
      });
  }

  function gezogen(name, vorher) {
    if (begriffe.join("\n") === vorher.join("\n")) return;
    status(optionen.status, L.ansage(name, begriffe.indexOf(name) + 1, begriffe.length), "ok");
    speichere();
  }

  function bewege(name, nach) {
    const von = begriffe.indexOf(name);
    if (von < 0 || nach < 0 || nach >= begriffe.length) return;
    const vorher = begriffe;
    begriffe = L.verschoben(begriffe, von, nach);
    zeichne();
    gezogen(name, vorher);
  }

  function beiBewegung(event) {
    if (!ziehen || event.pointerId !== ziehen.pointerId) return;
    const mitten = zeilen.map(z => { const box = z.li.getBoundingClientRect(); return box.top + box.height / 2; });
    const von = begriffe.indexOf(ziehen.name);
    const nach = L.zielIndex(mitten, von, event.clientY);
    if (nach === von) return;
    begriffe = L.verschoben(begriffe, von, nach);
    zeichne();
  }

  function beende(behalten) {
    const { name, vorher } = ziehen;
    ziehen = null;
    document.removeEventListener("pointermove", beiBewegung);
    document.removeEventListener("pointerup", beiLoslassen);
    document.removeEventListener("pointercancel", beiAbbruch);
    document.removeEventListener("keydown", beiTaste);
    if (!behalten) begriffe = vorher;
    zeichne();
    if (behalten) gezogen(name, vorher);
  }

  function beiLoslassen(event) { if (ziehen && event.pointerId === ziehen.pointerId) beende(true); }
  function beiAbbruch(event) { if (ziehen && event.pointerId === ziehen.pointerId) beende(false); }
  function beiTaste(event) {
    if (!ziehen || event.key !== "Escape") return;
    event.preventDefault();
    beende(false);
  }

  // Listeners on the document, not pointer capture on the handle: each move draws the rows anew.
  function beginne(event, name) {
    if (ziehen || (event.pointerType === "mouse" && event.button !== 0)) return;
    event.preventDefault();
    ziehen = { name, vorher: begriffe, pointerId: event.pointerId };
    document.addEventListener("pointermove", beiBewegung);
    document.addEventListener("pointerup", beiLoslassen);
    document.addEventListener("pointercancel", beiAbbruch);
    document.addEventListener("keydown", beiTaste);
    // the row stays until it moves, so that the pointer keeps its handle
    const gezogeneZeile = zeilen.find(z => z.name === name);
    if (gezogeneZeile) gezogeneZeile.li.className = `suchliste__eintrag ${ZIEHT}`;
  }

  /**
   * Draws the terms into `ziel`, the most important first. While a move is being dragged or saved, a reload of the page
   * waits: the list shows what the person did, and the page loads again once the last order is saved.
   * @param {object} ziel  the <ol> of the list
   * @param {string[]} neu  the terms in the order the server reads them
   * @param {{status: object, entfernen: Function, geaendert: Function}} mit  message line, Entfernen, reload
   */
  function zeige(ziel, neu, mit) {
    optionen = mit;
    if (ziehen || offen > 0) return;
    liste = ziel;
    begriffe = [...neu];
    zeichne();
  }

  return { zeige };
})();
