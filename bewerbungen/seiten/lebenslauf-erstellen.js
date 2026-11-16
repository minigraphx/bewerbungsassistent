"use strict";
// „Lebenslauf erstellen“ on the page of an application (G17, #118): stations and summary from Meine Angaben, the
// design apart from them. What it shows and sends: lebenslauf-erstellen-logik.js; what the route writes: cv_creation.py.
// With AI set up and a job ad, the AI's suggestion is applied on opening (#293, G75); each recommendation is a box the
// person unticks to undo it as a whole. What goes to the AI: ai/cv_suggestions.py.
(() => {
  const { holen, senden, el, status, url, kiEinrichten, textsatz } = window.App;
  const Logic = window.LebenslaufErstellenLogik;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const ROUTE = "/api/lebenslauf/erstellen";
  let state = null;
  let opened = 0; // an answer of the AI for a panel opened before is not applied any more
  let running = null; // the opening whose request to the AI still runs
  let ki = "aus";
  let offer = null;
  let satz = "stelle-sie";

  const say = key => window.Texte.text(key, satz);
  const message = (text, type = "") => status($("cv-erstellen-status"), text, type);
  const aiMessage = (text, type = "") => status($("cv-erstellen-ki-status"), text, type);
  // bewerbung.js loads again, so the new variant stands in the list and is chosen.
  const announceCreated = () => document.dispatchEvent(new CustomEvent("lebenslauf-erstellt"));

  function moveButton(section, station, step, allowed) {
    const label = step < 0 ? "Nach oben" : "Nach unten";
    return el("button", { type: "button", class: "btn btn--sm", disabled: !allowed, "data-key": `${section.name}-${station.index}-${step}`,
                          "aria-label": `${station.titel}: ${label}`,
                          onclick: () => change(Logic.move(state, section.name, station.index, step)) },
      step < 0 ? "↑" : "↓");
  }

  function stationRow(section, station) {
    const chosen = section.chosen.includes(station.index);
    const { up, down } = Logic.canMove(state, section.name, station.index);
    const box = el("input", { type: "checkbox", checked: chosen, "data-key": `${section.name}-${station.index}`,
                              onchange: () => change(Logic.toggle(state, section.name, station.index)) });
    const detail = [station.zusatz, station.zeit].filter(Boolean).join(" · ");
    return el("li", { class: "cv-create__station" },
      el("label", { class: "check cv-create__pick" }, box,
        el("span", {}, el("span", { class: "cv-create__name" }, station.titel),
          detail ? el("span", { class: "cv-create__detail" }, detail) : null)),
      el("span", { class: "cv-create__move" }, moveButton(section, station, -1, up), moveButton(section, station, 1, down)));
  }

  function sectionBlock(section) {
    const byIndex = new Map(section.stations.map(station => [station.index, station]));
    return el("fieldset", { class: "cv-create__section" },
      el("legend", {}, section.title),
      el("ul", { class: "cv-create__list" }, section.order.map(index => stationRow(section, byIndex.get(index)))));
  }

  function designTile(choice) {
    const radio = el("input", { type: "radio", name: "cv-erstellen-design", value: choice.id,
                                checked: choice.id === state.design,
                                onchange: () => { state = Logic.choose(state, choice.id); } });
    return el("label", { class: "design-tile" },
      el("span", { class: `design-tile__sheet design-tile__sheet--${choice.id}`, "aria-hidden": "true" }),
      el("span", { class: "design-tile__name" }, radio, choice.name),
      el("span", { class: "design-tile__text" }, choice.text));
  }

  /** Redraw the stations; keeps the focus on the button or box the person just used. */
  function change(next) {
    const focused = document.activeElement?.dataset?.key || null;
    const summaryBefore = Logic.summary(state);
    state = next;
    $("cv-erstellen-stationen").replaceChildren(...state.sections.map(sectionBlock));
    // A summary the person edited stays theirs; only the one a recommendation set follows it.
    if ($("cv-erstellen-profil").value === summaryBefore) $("cv-erstellen-profil").value = Logic.summary(state);
    const again = focused && [...$("cv-erstellen-stationen").querySelectorAll("[data-key]")]
      .find(element => element.dataset.key === focused && !element.disabled);
    again?.focus();
  }

  function idea(recommendation) {
    const box = el("input", { type: "checkbox", checked: recommendation.on, onchange: event => {
      change(Logic.setRecommendation(state, recommendation.nummer, event.target.checked));
      aiMessage(Logic.recommendationText(recommendation, event.target.checked));
    } });
    return el("li", { class: "cv-create__idea" },
      el("label", { class: "check" }, box,
        el("span", {}, el("span", { class: "cv-create__idea-what" }, recommendation.was),
          el("span", { class: "cv-create__idea-why" }, recommendation.grund))));
  }

  /** The box: its line, the recommendations and at most one offer of Logic.aiOffer. */
  function showAi(line, shown = null) {
    const toAd = shown?.action === "stellentext";
    $("cv-erstellen-ki").hidden = false;
    $("cv-erstellen-ki-zeile").textContent = line;
    $("cv-erstellen-ki-liste").hidden = !state.recommendations.length;
    $("cv-erstellen-ki-liste").replaceChildren(...state.recommendations.map(idea));
    $("cv-erstellen-ki-knoepfe").hidden = !shown;
    $("cv-erstellen-ki-knopf").hidden = !shown || toAd;
    $("cv-erstellen-ki-knopf").textContent = shown && !toAd ? say(shown.button) : "";
    $("cv-erstellen-ki-knopf").removeAttribute("aria-disabled");
    $("cv-erstellen-ki-stellentext").hidden = !toAd;
    $("cv-erstellen-ki-text").hidden = ki !== "bereit";
  }

  function showSuggested(answer, fromButton) {
    const count = state.recommendations.length;
    showAi(count ? say(Logic.APPLIED_LINE) : Logic.suggestedText(0));
    aiMessage(Logic.suggestedText(answer.empfehlungen.length, answer.kosten_text), "ok");
    // Opening leaves the focus on the stations; after the button it goes where the answer stands.
    if (fromButton) ($("cv-erstellen-ki-liste").querySelector("input") || $("cv-erstellen-ki-status")).focus();
  }

  /** The button stays where it is while the AI runs, so the focus does not fall back to the page. */
  async function suggest({ fromButton = false } = {}) {
    const mine = opened;
    if (running === mine) return;
    running = mine;
    $("cv-erstellen-ki-knopf").setAttribute("aria-disabled", "true");
    $("cv-erstellen-ki-zeile").textContent = say("lebenslauf.ki-laeuft");
    try {
      const answer = await senden(`${ROUTE}/vorschlag`, { id: ID, stand: state.stand });
      if (mine !== opened) return;
      change(Logic.suggest(state, answer));
      showSuggested(answer, fromButton);
    } catch (error) {
      if (mine !== opened) return;
      showAi(say(offer.line), { ...offer, button: "lebenslauf.ki-nochmals" });
      aiMessage(error.message, "fehler");
    } finally {
      if (running === mine) running = null;
    }
  }

  function startAi(answer, { fromButton = false } = {}) {
    ki = answer.ki;
    offer = Logic.aiOffer(answer);
    if (!Logic.autoSuggest(answer)) return showAi(say(offer.line), offer);
    showAi("");
    return suggest({ fromButton });
  }

  async function aiButton() {
    if (offer.action === "vorschlagen") return suggest({ fromButton: true });
    try {
      await kiEinrichten();
      return startAi(await holen(ROUTE, { id: ID }), { fromButton: true });
    } catch (error) {
      return aiMessage(error.message, "fehler");
    }
  }

  function toAd() {
    const part = $("s-stelle");
    part.open = true;
    part.scrollIntoView({ behavior: "smooth", block: "start" });
    $("stellentext").focus({ preventScroll: true });
  }

  function showForm(answer) {
    state = Logic.start(answer);
    $("cv-erstellen-profil").value = answer.kurzprofil;
    change(state);
    $("cv-erstellen-designs").replaceChildren(...Logic.DESIGNS.map(designTile));
    $("cv-erstellen-beruf").value = answer.berufsbezeichnung;
    $("cv-erstellen-name").value = answer.bezeichnung;
  }

  function setOpen(open) {
    $("cv-erstellen").hidden = !open;
    $("cv-erstellen-oeffnen").setAttribute("aria-expanded", String(open));
    if (!open) opened += 1;
  }

  async function open() {
    if (!$("cv-erstellen").hidden) return setOpen(false);
    $("cv-erstellen-pdf").hidden = true;
    try {
      const [answer, set] = await Promise.all([holen(ROUTE, { id: ID }), textsatz()]);
      opened += 1;
      satz = set;
      showForm(answer);
      setOpen(true);
      $("cv-erstellen-stationen").querySelector("input")?.focus();
      aiMessage("");
      $("cv-erstellen-ki-text").open = false;
      $("cv-erstellen-ki-text-inhalt").textContent = "";
      startAi(answer);
    } catch (error) {
      setOpen(true);
      message(`Lebenslauf erstellen geht gerade nicht: ${error.message}`, "fehler");
    }
  }

  async function showSentText() {
    const target = $("cv-erstellen-ki-text-inhalt");
    if (!$("cv-erstellen-ki-text").open || target.textContent) return;
    try {
      target.textContent = (await holen(`${ROUTE}/text`, { id: ID })).text;
    } catch (error) {
      aiMessage(error.message, "fehler");
    }
  }

  async function save() {
    $("cv-erstellen-speichern").disabled = true;
    try {
      const body = Logic.request(state, { id: ID, berufsbezeichnung: $("cv-erstellen-beruf").value,
                                          kurzprofil: $("cv-erstellen-profil").value, bezeichnung: $("cv-erstellen-name").value });
      message("Lebenslauf wird erstellt …");
      const answer = await senden(ROUTE, body);
      message(Logic.savedText(answer), answer.gebaut ? "ok" : "hinweis");
      $("cv-erstellen-pdf").href = url("/api/pdf", { id: ID, art: "lebenslauf" });
      $("cv-erstellen-pdf").hidden = !answer.gebaut;
      announceCreated();
    } catch (error) {
      message(error.message, "fehler");
    } finally {
      $("cv-erstellen-speichern").disabled = false;
    }
  }

  // Only before sending: what went out stays as it is.
  document.addEventListener("bewerbung-geladen", event => {
    const sent = Boolean(event.detail.bewerbung.versand);
    $("cv-erstellen-oeffnen").hidden = sent;
    if (sent) setOpen(false);
  });
  $("cv-erstellen-oeffnen").addEventListener("click", open);
  $("cv-erstellen-abbrechen").addEventListener("click", () => setOpen(false));
  $("cv-erstellen-speichern").addEventListener("click", save);
  $("cv-erstellen-ki-knopf").addEventListener("click", aiButton);
  $("cv-erstellen-ki-stellentext").addEventListener("click", toAd);
  $("cv-erstellen-ki-text").addEventListener("toggle", showSentText);
})();
