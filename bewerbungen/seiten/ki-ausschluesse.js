"use strict";
// On Suche einstellen (#319, G86): under Was nicht, the AI proposes exclusion reasons from the dismissed hits. Before
// the run the box names the count and the cost; with fewer than three dismissed hits it shows its empty state and
// no button. Each proposal names the hits it rests on; „Übernehmen“ writes it with drafts, and the feedback in the
// proposal offers Rückgängig. Nothing changes without these clicks. Words in ki-ausschluesse-logik.js.
(() => {
  const { holen, senden, status, el, textsatz } = window.App;
  const L = window.KiAusschluesseLogik;
  const $ = id => document.getElementById(id);
  const ROUTE = "/api/suche/ki-ausschluesse";
  const geaendert = () => document.dispatchEvent(new CustomEvent("suchprofil-geaendert"));
  const mitLink = text => window.Texte.withCodeRequestLink(text, el);
  const DA = new Set(["uebernommen", "schon"]);  // what a card shows when the entry is in the profile
  let satz = "stelle-sie";
  let karten = [];  // the proposals shown: { vorschlag, teile }

  /** The feedback of one proposal, with a button; `fokus` moves the focus there after a click of the person. */
  function rueckmeldung(teile, angezeigt, text, knopf, { stufe = "", fokus = true } = {}) {
    teile.angezeigt = angezeigt;
    teile.meldung.replaceChildren(el("p", { class: stufe === "fehler" ? "field__error" : "" }, text),
      el("div", { class: "btn-row" }, knopf));
    teile.meldung.classList.toggle("ai-exclusion__feedback--da", DA.has(angezeigt) && stufe !== "fehler");
    teile.meldung.hidden = false;
    teile.aktion.hidden = true;
    if (fokus) teile.meldung.focus();
  }

  function knopf(text, label, aktion) {
    const button = el("button", { type: "button", class: "btn btn--sm", ...(label ? { "aria-label": label } : {}) }, text);
    button.addEventListener("click", () => aktion(button));
    return button;
  }

  const knopfUebernehmen = (vorschlag, teile) => knopf(L.KNOPF, L.knopfLabel(vorschlag), b => uebernimm(vorschlag, teile, b));
  const knopfZurueck = (vorschlag, teile) => knopf(L.RUECKGAENGIG, "", b => nimmZurueck(vorschlag, teile, b));

  /** Another card added or removed the same entry: the proposal says so, without moving the focus. */
  function gleicheAb(vorhanden) {
    for (const { vorschlag, teile } of karten) {
      const neu = L.abgleich(vorschlag, vorhanden, teile.angezeigt);
      if (!neu) continue;
      const weiter = DA.has(neu.angezeigt) ? knopfZurueck(vorschlag, teile) : knopfUebernehmen(vorschlag, teile);
      rueckmeldung(teile, neu.angezeigt, neu.text, weiter, { fokus: false });
    }
  }

  function zeigeStand(stand) {
    $("ki-ausschluesse").hidden = !stand.verfuegbar;
    if (!stand.verfuegbar) return;
    const offen = $("ki-ausschluesse-liste").children.length > 0;
    const ansicht = L.ansicht(stand, offen, satz, window.Texte);
    $("ki-ausschluesse-satz").textContent = ansicht.satz;
    $("ki-ausschluesse-start").hidden = !ansicht.start;
    $("ki-ausschluesse-was").hidden = !ansicht.was;
    $("ki-ausschluesse-kosten").replaceChildren(...(ansicht.start ? mitLink(L.kosten(stand, window.TrefferLogik)) : []));
    if (stand.vorhanden) gleicheAb(stand.vorhanden);
  }

  async function lade() {
    try {
      const [stand, neu] = await Promise.all([holen(ROUTE), textsatz()]);
      satz = neu;
      $("ki-ausschluesse-was-text").textContent = L.wasGeht(satz, window.Texte);
      zeigeStand(stand);
    } catch (fehler) {
      $("ki-ausschluesse").hidden = false;  // the reason stays visible; the card works without the box
      $("ki-ausschluesse-start").hidden = true;
      $("ki-ausschluesse-was").hidden = true;
      $("ki-ausschluesse-satz").textContent = "";
      status($("ki-ausschluesse-status"), `${L.NICHT_GELADEN} ${fehler.message}`, "fehler");
    }
  }

  async function nimmZurueck(vorschlag, teile, button) {
    button.disabled = true;
    try {
      await senden(`${ROUTE}/rueckgaengig`, { art: vorschlag.art, wert: vorschlag.wert });
      rueckmeldung(teile, "zurueck", L.zurueck(vorschlag), knopfUebernehmen(vorschlag, teile));
      geaendert();
    } catch (fehler) {
      button.disabled = false;
      rueckmeldung(teile, teile.angezeigt, `${L.NICHT_ZURUECK} ${fehler.message}`, button, { stufe: "fehler" });
    }
  }

  async function uebernimm(vorschlag, teile, button) {
    button.disabled = true;
    try {
      await senden(`${ROUTE}/uebernehmen`, { vorschlag: teile.id, nummer: vorschlag.nummer });
      rueckmeldung(teile, "uebernommen", L.uebernommen(vorschlag), knopfZurueck(vorschlag, teile));
      geaendert();
    } catch (fehler) {
      button.disabled = false;
      rueckmeldung(teile, teile.angezeigt, `${L.NICHT_GESPEICHERT} ${fehler.message}`, button, { stufe: "fehler" });
    }
  }

  function karte(vorschlag, id) {
    // No role=status: the focus moves to the feedback after a click, so a live region would read it out twice.
    const teile = { id, angezeigt: "offen", meldung: el("div", { class: "ai-exclusion__feedback", tabindex: "-1", hidden: true }) };
    teile.aktion = el("div", { class: "btn-row" }, knopfUebernehmen(vorschlag, teile));
    karten = [...karten, { vorschlag, teile }];
    return el("li", { class: "ai-exclusion" },
      el("p", { class: "ai-exclusion__value" }, el("strong", {}, `«${vorschlag.wert}»`)),
      el("p", { class: "caption" }, L.wo(vorschlag)),
      vorschlag.grund ? el("p", {}, vorschlag.grund) : null,
      el("p", { class: "ai-exclusion__basis" }, L.stuetze(vorschlag)),
      el("ul", { class: "ai-exclusion__hits" }, vorschlag.treffer.map(t => el("li", {}, L.trefferZeile(t)))),
      teile.aktion, teile.meldung);
  }

  async function frage() {
    const button = $("ki-ausschluesse-knopf");
    button.disabled = true;
    karten = [];
    $("ki-ausschluesse-liste").replaceChildren();
    status($("ki-ausschluesse-status"), L.DENKT, "");
    let ziel = $("ki-ausschluesse-status");
    try {
      const antwort = await senden(`${ROUTE}/vorschlag`, {});
      $("ki-ausschluesse-liste").replaceChildren(...antwort.vorschlaege.map(v => karte(v, antwort.vorschlag)));
      status($("ki-ausschluesse-status"), L.fertig(antwort.vorschlaege.length, satz, window.Texte), "ok");
      button.textContent = L.NEU_FRAGEN;
      // The status is a live region and reads the count out; the focus goes to the first proposal to adopt.
      if (karten.length) ziel = karten[0].teile.aktion.querySelector("button");
    } catch (fehler) {
      status($("ki-ausschluesse-status"), mitLink(fehler.message), "fehler");
    } finally {
      button.disabled = false;
      ziel.focus();
    }
  }

  async function textAnsehen() {
    try {
      const { text } = await holen(`${ROUTE}/text`);
      $("ki-text-inhalt").textContent = text;
      $("ki-text").showModal();
      $("ki-text-schliessen").focus();
    } catch (fehler) {
      status($("ki-ausschluesse-status"), fehler.message, "fehler");
    }
  }

  $("ki-ausschluesse-knopf").addEventListener("click", frage);
  $("ki-ausschluesse-text").addEventListener("click", textAnsehen);
  // Another card changed the profile: count and cost may differ, and proposals shown follow the entries it changed.
  document.addEventListener("suchprofil-geaendert", lade);
  lade();
})();
