"use strict";
// Bewerbungen (#261, A5): every application with its stage, grade, next step and date, in views by stage with counts
// (G27), sortable by any column (G28). Ticked ones are discarded or set to another stage in one step (G29); saved jobs
// are rated in one pass (G38, pass.js); a job is entered by hand. The next step comes from uebersicht-logik.js.
(() => {
  const { holen, senden, el, beobachten, textsatz } = window.App;
  const { text } = window.Texte;
  const L = window.UebersichtLogik;
  const H = window.HeuteLogic;
  const A = window.BewerbungenLogic;
  const $ = id => document.getElementById(id);

  const ANSICHT = "uebersicht.ansicht";  // the same key as before #261, so the chosen view stays
  const MIT_FUSS = ["gemerkt", "beworben"];  // views that do not show the finished ones name them below the list
  const NICHTS_GEFUNDEN = "Keine Bewerbung passt zu dieser Suche.";
  const ANSICHT_LEER = "In dieser Ansicht ist keine Bewerbung.";
  const ARIA_SORT = { auf: "ascending", ab: "descending" };
  const DISCARD_STAGES = ["Verworfen", "Zurückgezogen"];
  const GESCHLOSSEN_WORT = { Zusage: ["Zusage", "Zusagen"], Absage: ["Absage", "Absagen"], Verworfen: ["verworfen", "verworfen"],
                             "Zurückgezogen": ["zurückgezogen", "zurückgezogen"] };

  let satz = "stelle-sie";
  let alle = [];
  let zeilen = [];
  let gezeigt = "";      // the register as last drawn, to see whether Claude changed it
  let gruende = new Map();
  let ravGruende = new Map();
  let ansicht = L.STANDARD_ANSICHT;
  let sortierung = null;  // { spalte, richtung } or null for the order of the app
  let wiederhergestellt = false;
  let auswahl = new Set();  // ids ticked in the list (#170)
  let staende = [];         // the stages the register knows, for the menu
  let frage = null;         // what the open dialog will do: { art: "verwerfen", plan } or { art: "stand", ids, stand }

  const meldung = (inhalt, stufe = "") => window.Meldungen.zeige($("lauf-status"), inhalt, stufe);
  const t = (schluessel, werte) => text(schluessel, satz, werte);
  const adresse = b => "/bewerbung?id=" + encodeURIComponent(b.id);
  const wo = b => [b.firma, b.ort].filter(Boolean).join(", ");
  const name = b => [b.stelle || "ohne Titel", b.firma].filter(Boolean).join(", ");

  function merken() {
    try {
      const scroll = wiederhergestellt ? Math.round(window.scrollY) : gemerkt().scroll;
      localStorage.setItem(ANSICHT, JSON.stringify({ ansicht, suche: $("suche").value, scroll, sortierung }));
    } catch { /* without storage the default view applies */ }
  }

  function gemerkt() {
    try {
      const a = JSON.parse(localStorage.getItem(ANSICHT) || "{}");
      return { ansicht: L.gueltigeAnsicht(a.ansicht), suche: typeof a.suche === "string" ? a.suche : "",
               scroll: Number.isFinite(a.scroll) && a.scroll > 0 ? a.scroll : 0, sortierung: L.gueltigeSortierung(a.sortierung) };
    } catch {
      return { ansicht: L.STANDARD_ANSICHT, suche: "", scroll: 0, sortierung: null };
    }
  }

  // Note 1–6 as in the design: value, six bars, a word

  function notenWort(note) {
    return note >= 5.5 ? "passt sehr gut" : note >= 4.5 ? "passt gut" : note >= 4 ? "passt knapp" : "passt wenig";
  }

  function note(b) {
    if (typeof b.passung !== "number") return el("span", { class: "table__sub" }, "keine Note");
    const balken = [1, 2, 3, 4, 5, 6].map(k => el("i", { class: b.passung >= k ? "on" : b.passung >= k - 0.5 ? "half" : "" }));
    return el("span", { class: "grade-meter grade-meter--sm", "aria-label": `Note ${window.Texte.notenText(b.passung)} von 6, ${notenWort(b.passung)}` },
      el("span", { class: "grade-meter__value" }, window.Texte.notenText(b.passung)),
      el("span", { class: "grade-meter__bar", "aria-hidden": "true" }, balken),
      el("span", { class: "grade-meter__word", "aria-hidden": "true" }, notenWort(b.passung)));
  }

  // The list

  function zeile(z) {
    const { bewerbung: b, schritt } = z;
    const was = L.schrittText(schritt, 1, t);
    return el("tr", { "data-selected": auswahl.has(b.id) },
      el("td", { "data-label": "", class: "table__pick" },
        el("input", { type: "checkbox", "data-id": b.id, "aria-label": `Anhaken: ${name(b)}`, checked: auswahl.has(b.id),
                      onchange: () => waehleZeile(b.id) })),
      el("td", { "data-label": "" }, el("a", { class: "table__main", href: adresse(b) }, b.stelle || "ohne Titel"), el("span", { class: "table__sub" }, wo(b))),
      el("td", { "data-label": "Stand" }, el("span", { class: "marke-status", "data-status": b.status }, window.Texte.statusName(b.status, satz))),
      el("td", { "data-label": "Note" }, note(b)),
      el("td", { "data-label": "Nächster Schritt", class: "table__next" }, was.titel || "–"),
      el("td", { "data-label": "Bis wann" }, A.dueText(z)),
      el("td", { "data-label": "Erfasst", class: "num" }, L.datum(b.eingetragen_am)));
  }

  const gezeigteZeilen = () => L.sortiert(L.gefiltert(zeilen, ansicht, $("suche").value), sortierung);

  function zeigeFuss() {
    const fertig = L.abgeschlossenZaehlen(zeilen);
    const teile = Object.entries(fertig).map(([status, n]) => `${n} ${(GESCHLOSSEN_WORT[status] || [status, status])[n === 1 ? 0 : 1]}`);
    $("liste-fuss").hidden = !MIT_FUSS.includes(ansicht) || teile.length === 0;
    $("liste-fuss").replaceChildren(`Abgeschlossen: ${teile.join(", ")}. `,
      el("button", { type: "button", class: "link", onclick: () => waehleAnsicht("abgeschlossen") }, "Anzeigen"));
    $("durchgang").hidden = H.passQueue(zeilen).length === 0;
  }

  function zeigeListe() {
    const gezeigte = gezeigteZeilen();
    for (const kopf of document.querySelectorAll("th[data-spalte]")) {
      if (sortierung?.spalte === kopf.dataset.spalte) kopf.setAttribute("aria-sort", ARIA_SORT[sortierung.richtung]);
      else kopf.removeAttribute("aria-sort");
    }
    for (const knopf of document.querySelectorAll("[data-ansicht]")) knopf.setAttribute("aria-pressed", String(knopf.dataset.ansicht === ansicht));
    for (const [ansichtName, zahl] of Object.entries(L.ansichtenZaehlen(zeilen))) document.querySelector(`[data-zahl=${ansichtName}]`).textContent = String(zahl);
    $("liste").replaceChildren(...gezeigte.map(zeile));
    $("tabelle").hidden = gezeigte.length === 0;
    $("liste-leer").hidden = alle.length > 0;
    $("nichts-gefunden").hidden = alle.length === 0 || gezeigte.length > 0;
    $("nichts-gefunden").textContent = $("suche").value.trim() ? NICHTS_GEFUNDEN : ANSICHT_LEER;
    zeigeAuswahl(gezeigte);
    zeigeFuss();
    merken();
  }

  function sortiereNach(spalte) {
    sortierung = L.naechsteSortierung(sortierung, spalte);
    zeigeListe();
  }

  function waehleAnsicht(neu) {
    ansicht = neu;
    history.replaceState(null, "", `#${neu}`);
    zeigeListe();
  }

  // The ticked ones (#170, G29): only the ticked rows of this view count

  function zeigeAuswahl(gezeigte = gezeigteZeilen()) {
    for (const feld of $("liste").querySelectorAll("input[data-id]")) {
      feld.checked = auswahl.has(feld.dataset.id);
      feld.closest("tr").toggleAttribute("data-selected", feld.checked);
    }
    const zustand = L.selectionState(auswahl, gezeigte);
    $("alle-kopf").checked = zustand === "all";
    $("alle-kopf").indeterminate = zustand === "some";
    const ids = L.selectedIds(auswahl, gezeigte);
    $("verwerfen").disabled = A.discardCount(A.discardPlan(gezeigte, ids)) === 0;
    $("auswahl-zahl").textContent = A.selectionHint(ids.length);
    $("auswahl-leiste").hidden = !L.showBulkBar(ids.length);
    $("stand-setzen").disabled = ids.length === 0 || !$("stand-wahl").value;
  }

  function waehleZeile(id) {
    auswahl = L.toggleOne(auswahl, id);
    zeigeAuswahl();
  }

  function waehleAlle() {
    auswahl = L.toggleAll(auswahl, gezeigteZeilen());
    zeigeAuswahl();
  }

  function fuelleStaende() {
    const gewaehlt = $("stand-wahl").value;
    const optionen = staende.map(stand => el("option", { value: stand, selected: stand === gewaehlt }, window.Texte.statusName(stand, satz)));
    $("stand-wahl").replaceChildren(el("option", { value: "" }, "Anderer Stand …"), ...optionen);
  }

  function zeigeFrage(titel, betroffen, hinweise, knopf) {
    $("stand-titel").textContent = titel;
    $("stand-text").replaceChildren(el("ul", { class: "dialog__list" }, betroffen.map(zeilenText => el("li", {}, zeilenText))),
      ...hinweise.map(hinweis => el("p", {}, hinweis)));
    $("stand-ok").textContent = knopf;
    $("stand-ok").disabled = false;
    $("stand-dialog").showModal();
  }

  function frageVerwerfen() {
    const gezeigte = gezeigteZeilen();
    const plan = A.discardPlan(gezeigte, L.selectedIds(auswahl, gezeigte));
    if (A.discardCount(plan) === 0) return;
    const enden = new Set(DISCARD_STAGES.flatMap(stand => plan[stand]));
    frage = { art: "verwerfen", plan };
    zeigeFrage(A.discardQuestion(plan), gezeigte.filter(z => enden.has(z.bewerbung.id)).map(z => name(z.bewerbung)),
      A.discardNotes(plan), "Verwerfen");
  }

  function frageStand() {
    const gezeigte = gezeigteZeilen();
    const ids = L.selectedIds(auswahl, gezeigte);
    const stand = $("stand-wahl").value;
    if (!ids.length || !stand) return;
    frage = { art: "stand", ids, stand };
    zeigeFrage(L.stageQuestion(ids.length, window.Texte.statusName(stand, satz)),
      gezeigte.filter(z => ids.includes(z.bewerbung.id)).map(z => name(z.bewerbung)),
      stand === "Absage" ? ["Wo das Datum der Absage fehlt, gilt heute."] : [], "Stand setzen");
  }

  async function setze(ids, stand) {
    if (ids.length) await senden("/api/bewerbungen/stand", { ids, status: stand });
  }

  async function bestaetigt() {
    const jetzt = frage;
    if (!jetzt) return;
    $("stand-ok").disabled = true;
    try {
      if (jetzt.art === "verwerfen") {
        for (const stand of DISCARD_STAGES) await setze(jetzt.plan[stand], stand);
      } else {
        await setze(jetzt.ids, jetzt.stand);
      }
      $("stand-dialog").close();
      auswahl = new Set();
      $("stand-wahl").value = "";
      meldung(jetzt.art === "verwerfen" ? A.discardDone(jetzt.plan)
        : L.stageDone(jetzt.ids.length, jetzt.stand, window.Texte.statusName(jetzt.stand, satz), ansicht), "success");
      await laden();  // a failed reload says so in the same line
    } catch (fehler) {
      $("stand-dialog").close();
      meldung(fehler.message, "danger");
      await laden();  // part of the change may have landed
    } finally {
      frage = null;
    }
  }

  // The pass over saved jobs (G38)

  function durchgangFertig(anzahl) {
    meldung(H.passResult(anzahl), "success");
    if ((anzahl.bewerben || 0) + (anzahl.verworfen || 0) > 0) laden();
  }

  // Loading

  async function ladeGruende() {
    const [bereit, ravAuswahl] = await Promise.all([holen("/api/bewerben/auswahl"), holen("/api/rav/auswahl")]);
    gruende = new Map(bereit.bewerbungen.map(row => [row.id, row.grund]));
    ravGruende = new Map(ravAuswahl.sichtbar ? ravAuswahl.bewerbungen.map(row => [row.id, row.grund]) : []);
  }

  async function laden() {
    try {
      const [daten] = await Promise.all([holen("/api/bewerbungen"), ladeGruende()]);
      gezeigt = JSON.stringify(daten.bewerbungen);
      alle = daten.bewerbungen;
      staende = daten.status;
      zeilen = L.mitSchritten(alle, gruende, ravGruende);
      auswahl = L.keepKnown(auswahl, zeilen);
      fuelleStaende();
      window.Texte.anwenden(document, satz);
      $("suche").placeholder = t("uebersicht.suche");
      zeigeListe();
    } catch (fehler) {
      meldung("Laden fehlgeschlagen: " + fehler.message, "danger");
    }
  }

  /** Claude writes into the register while this page is open; drawn anew only when something changed, so nothing jumps. */
  async function nachsehen() {
    try {
      const { bewerbungen } = await holen("/api/bewerbungen");
      if (JSON.stringify(bewerbungen) !== gezeigt) await laden();
    } catch { /* the app is closing; the next action says so */ }
  }

  // Entering a job by hand

  async function anlegen(event) {
    event.preventDefault();
    $("neu-anlegen").disabled = true;
    try {
      const b = await senden("/api/bewerbung/neu", { firma: $("neu-firma").value, stelle: $("neu-stelle").value });
      location.href = adresse(b);
    } catch (fehler) {
      window.Meldungen.zeige($("neu-status"), fehler.message, "danger");
      $("neu-anlegen").disabled = false;
    }
  }

  // Wiring

  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  let scrollTimer = null;
  window.addEventListener("scroll", () => { clearTimeout(scrollTimer); scrollTimer = setTimeout(merken, 150); }, { passive: true });
  window.addEventListener("pagehide", merken);
  window.addEventListener("hashchange", () => {
    const aus = A.viewFromHash(location.hash);
    if (aus && aus !== ansicht) waehleAnsicht(aus);
  });
  $("suche").addEventListener("input", zeigeListe);
  for (const knopf of document.querySelectorAll("[data-ansicht]")) knopf.addEventListener("click", () => waehleAnsicht(knopf.dataset.ansicht));
  for (const kopf of document.querySelectorAll("th[data-spalte]")) kopf.querySelector("button").addEventListener("click", () => sortiereNach(kopf.dataset.spalte));
  $("von-hand").addEventListener("click", () => { window.Meldungen.leere($("neu-status")); $("neu-dialog").showModal(); $("neu-firma").focus(); });
  $("neu-abbrechen").addEventListener("click", () => $("neu-dialog").close());
  $("neu-form").addEventListener("submit", anlegen);
  $("alle-kopf").addEventListener("change", waehleAlle);
  $("verwerfen").addEventListener("click", frageVerwerfen);
  $("stand-wahl").addEventListener("change", () => zeigeAuswahl());
  $("stand-setzen").addEventListener("click", frageStand);
  $("stand-abbrechen").addEventListener("click", () => $("stand-dialog").close());
  $("stand-ok").addEventListener("click", bestaetigt);
  $("durchgang").addEventListener("click", () => window.Pass.start(H.passQueue(zeilen), durchgangFertig));
  document.addEventListener("visibilitychange", () => { if (!document.hidden) laden(); });
  beobachten(nachsehen);

  (async () => {
    const vorher = gemerkt();
    const ausAdresse = A.viewFromHash(location.hash);
    ansicht = ausAdresse || vorher.ansicht;
    $("suche").value = ausAdresse ? "" : vorher.suche;
    sortierung = vorher.sortierung;
    satz = await textsatz();
    await laden();
    requestAnimationFrame(() => { window.scrollTo(0, ausAdresse ? 0 : vorher.scroll); wiederhergestellt = true; });
  })();
})();
