"use strict";
// „Lebenslauf erstellen“ on the page of an application (G17, #118): stations and summary from Meine Angaben, the
// design apart from them. What it shows and sends: lebenslauf-erstellen-logik.js; what the route writes: cv_creation.py.
(() => {
  const { holen, senden, el, status, url } = window.App;
  const Logic = window.LebenslaufErstellenLogik;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  let state = null;

  const message = (text, type = "") => status($("cv-erstellen-status"), text, type);
  // bewerbung.js loads again, so the new variant stands in the list and is chosen.
  const announceCreated = () => document.dispatchEvent(new CustomEvent("lebenslauf-erstellt"));

  function moveButton(section, station, step, allowed) {
    const label = step < 0 ? "Nach oben" : "Nach unten";
    return el("button", { type: "button", class: "btn btn--sm", disabled: !allowed,
                          "aria-label": `${station.titel}: ${label}`,
                          onclick: () => change(Logic.move(state, section.name, station.index, step)) },
      step < 0 ? "↑" : "↓");
  }

  function stationRow(section, station) {
    const chosen = section.chosen.includes(station.index);
    const { up, down } = Logic.canMove(state, section.name, station.index);
    const box = el("input", { type: "checkbox", checked: chosen,
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
    const focused = document.activeElement?.getAttribute("aria-label") || null;
    state = next;
    $("cv-erstellen-stationen").replaceChildren(...state.sections.map(sectionBlock));
    const again = focused && [...$("cv-erstellen-stationen").querySelectorAll("button")]
      .find(button => button.getAttribute("aria-label") === focused && !button.disabled);
    again?.focus();
  }

  function showForm(answer) {
    state = Logic.start(answer);
    change(state);
    $("cv-erstellen-designs").replaceChildren(...Logic.DESIGNS.map(designTile));
    $("cv-erstellen-beruf").value = answer.berufsbezeichnung;
    $("cv-erstellen-profil").value = answer.kurzprofil;
    $("cv-erstellen-name").value = answer.bezeichnung;
  }

  function setOpen(open) {
    $("cv-erstellen").hidden = !open;
    $("cv-erstellen-oeffnen").setAttribute("aria-expanded", String(open));
  }

  async function open() {
    if (!$("cv-erstellen").hidden) return setOpen(false);
    $("cv-erstellen-pdf").hidden = true;
    try {
      showForm(await holen("/api/lebenslauf/erstellen", { id: ID }));
      setOpen(true);
      $("cv-erstellen-stationen").querySelector("input")?.focus();
    } catch (error) {
      setOpen(true);
      message(`Lebenslauf erstellen geht gerade nicht: ${error.message}`, "fehler");
    }
  }

  async function save() {
    $("cv-erstellen-speichern").disabled = true;
    try {
      const body = Logic.request(state, { id: ID, berufsbezeichnung: $("cv-erstellen-beruf").value,
                                          kurzprofil: $("cv-erstellen-profil").value, bezeichnung: $("cv-erstellen-name").value });
      message("Lebenslauf wird erstellt …");
      const answer = await senden("/api/lebenslauf/erstellen", body);
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
})();
