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
  let satz = "stelle-sie";

  function zeigeStand(stand) {
    $("ki-ausschluesse").hidden = !stand.verfuegbar;
    if (!stand.verfuegbar) return;
    const leer = L.zuWenige(stand);
    $("ki-ausschluesse-satz").textContent = leer ? L.leer(stand, satz, window.Texte) : L.einleitung(stand, satz, window.Texte);
    $("ki-ausschluesse-start").hidden = leer;
    $("ki-ausschluesse-was").hidden = leer;
    $("ki-ausschluesse-kosten").replaceChildren(...(leer ? [] : mitLink(L.kosten(stand, window.TrefferLogik))));
  }

  async function lade() {
    try {
      const [stand, neu] = await Promise.all([holen(ROUTE), textsatz()]);
      satz = neu;
      zeigeStand(stand);
    } catch (fehler) {
      $("ki-ausschluesse").hidden = false;  // the reason stays visible; the card works without the box
      $("ki-ausschluesse-start").hidden = true;
      $("ki-ausschluesse-was").hidden = true;
      $("ki-ausschluesse-satz").textContent = "";
      status($("ki-ausschluesse-status"), `${L.NICHT_GELADEN} ${fehler.message}`, "fehler");
    }
  }

  /** The feedback of one proposal, with a button; the focus moves there so it is read out. */
  function rueckmeldung(teile, text, knopf, stufe = "") {
    teile.meldung.replaceChildren(el("p", { class: stufe === "fehler" ? "field__error" : "" }, text),
      el("div", { class: "btn-row" }, knopf));
    teile.meldung.hidden = false;
    teile.aktion.hidden = true;
    teile.meldung.focus();
  }

  function knopf(text, label, aktion) {
    const button = el("button", { type: "button", class: "btn btn--sm", ...(label ? { "aria-label": label } : {}) }, text);
    button.addEventListener("click", () => aktion(button));
    return button;
  }

  async function nimmZurueck(vorschlag, teile, button) {
    button.disabled = true;
    try {
      await senden(`${ROUTE}/rueckgaengig`, { art: vorschlag.art, wert: vorschlag.wert });
      rueckmeldung(teile, L.zurueck(vorschlag), knopf(L.KNOPF, L.knopfLabel(vorschlag), b => uebernimm(vorschlag, teile, b)));
      geaendert();
    } catch (fehler) {
      button.disabled = false;
      rueckmeldung(teile, `${L.NICHT_ZURUECK} ${fehler.message}`, button, "fehler");
    }
  }

  async function uebernimm(vorschlag, teile, button) {
    button.disabled = true;
    try {
      await senden(`${ROUTE}/uebernehmen`, { vorschlag: teile.id, nummer: vorschlag.nummer });
      rueckmeldung(teile, L.uebernommen(vorschlag), knopf(L.RUECKGAENGIG, "", b => nimmZurueck(vorschlag, teile, b)));
      geaendert();
    } catch (fehler) {
      button.disabled = false;
      rueckmeldung(teile, `${L.NICHT_GESPEICHERT} ${fehler.message}`, button, "fehler");
    }
  }

  function karte(vorschlag, id) {
    const teile = { id, meldung: el("div", { class: "ai-exclusion__feedback", role: "status", tabindex: "-1", hidden: true }) };
    teile.aktion = el("div", { class: "btn-row" }, knopf(L.KNOPF, L.knopfLabel(vorschlag), b => uebernimm(vorschlag, teile, b)));
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
    $("ki-ausschluesse-liste").replaceChildren();
    status($("ki-ausschluesse-status"), L.DENKT, "");
    try {
      const antwort = await senden(`${ROUTE}/vorschlag`, {});
      $("ki-ausschluesse-liste").replaceChildren(...antwort.vorschlaege.map(v => karte(v, antwort.vorschlag)));
      status($("ki-ausschluesse-status"), L.fertig(antwort.vorschlaege.length, satz, window.Texte), "ok");
      button.textContent = L.NEU_FRAGEN;
    } catch (fehler) {
      status($("ki-ausschluesse-status"), mitLink(fehler.message), "fehler");
    } finally {
      button.disabled = false;
      $("ki-ausschluesse-status").focus();
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

  $("ki-ausschluesse-was-text").textContent = L.WAS_GEHT;
  $("ki-ausschluesse-knopf").addEventListener("click", frage);
  $("ki-ausschluesse-text").addEventListener("click", textAnsehen);
  // Another card changed the profile: count and cost may differ; proposals already shown stay.
  document.addEventListener("suchprofil-geaendert", lade);
  lade();
})();
