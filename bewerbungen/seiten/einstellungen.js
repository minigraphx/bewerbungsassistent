"use strict";
// Page „Einstellungen“ (MIN-348, #265): sections on the left, the way to the AI as a choice, the budget of the month.
// The key field is sent once and emptied; the key never comes back.
(() => {
  const { holen, senden, status, bestaetigen, el } = window.App;
  const L = window.EinstellungenLogik;
  const $ = id => document.getElementById(id);
  const SEITE = "bewerbungsbegleiter-seite";
  const anErweiterung = art => window.postMessage({ quelle: SEITE, art }, location.origin);
  const hatErweiterung = () => Boolean(document.documentElement.dataset.bewerbungsbegleiterErweiterung);
  const WAY_PANELS = { einladung: "zugang-einladung", abo: "claude-abo", schluessel: "schluessel-teil" };
  const SOUGHT = { stelle: "Stelle", lehrstelle: "Lehrstelle" };

  let ki = null;
  let abo = null;
  let costs = null;
  let choice = null;
  let shownWay = null;

  // ---------- Sections ----------
  function available(section) {
    const link = document.querySelector(`.settings__nav a[href="#${section}"]`);
    return Boolean(link) && !link.hidden;
  }

  function showSection(hash, { scroll = false } = {}) {
    const wanted = L.sectionOf(hash);
    const section = available(wanted) ? wanted : L.SECTIONS[0].id;
    document.querySelector(".settings").dataset.tabs = "an";
    for (const panel of document.querySelectorAll(".settings__panel")) {
      panel.toggleAttribute("data-aktiv", panel.id === `bereich-${section}`);
    }
    for (const link of document.querySelectorAll(".settings__nav a")) {
      if (link.getAttribute("href") === `#${section}`) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    }
    const way = L.wayOf(hash);
    if (way) showWay(way);
    const target = scroll && document.getElementById(String(hash).replace(/^#/, ""));
    if (target && !target.hidden) target.scrollIntoView({ block: "start" });
  }

  // ---------- Way to the AI ----------
  function showWay(way) {
    shownWay = way;
    choice?.choose(way);
    for (const [name, id] of Object.entries(WAY_PANELS)) $(id).hidden = name !== way;
  }

  function showInvitation() {
    const state = L.invitationState(ki);
    for (const name of ["aktiv", "schluessel", "keine", "eingeben"]) $(`einladung-${name}`).hidden = name !== state;
  }

  function showAccess() {
    const current = L.currentWay(ki, abo);
    if (!choice) {
      const offered = window.KiZugang.options({ abo: Boolean(abo) });
      const wanted = L.wayOf(location.hash);
      choice = window.KiZugang.render($("zugang-wahl"), { offered, current, chosen: wanted || current, onChoose: showWay });
      if (wanted || current) showWay(wanted || current);
    } else {
      choice.setCurrent(current);
    }
    showInvitation();
  }

  async function loadAccess() {
    const [kiAnswer, aboAnswer] = await Promise.all([
      holen("/api/ki/status").catch(fehler => { status($("zugang-meldung"), fehler.message, "fehler"); return null; }),
      holen("/api/claude/stand").catch(() => null),  // the app without the desktop part has no subscription
    ]);
    ki = kiAnswer;
    abo = aboAnswer;
    showAccess();
    if (ki) zeigeEinwilligung(ki);
    showBudget();
  }

  async function redeem() {
    $("einladung-einloesen").disabled = true;
    try {
      ki = await senden("/api/ki/einladung", { code: $("einladung-code").value.trim() });
      $("einladung-code").value = "";
      status($("einladung-status"), "Einladung eingelöst. Die KI ist eingerichtet.", "ok");
      showAccess();
      showBudget();
    } catch (fehler) {
      status($("einladung-status"), fehler.message, "fehler");
    } finally {
      $("einladung-einloesen").disabled = !$("einladung-code").value.trim();
    }
  }

  // ---------- Budget (G46) ----------
  function showBudget() {
    if (!costs) return;
    const view = L.budgetView(ki, costs);
    $("kosten-titel").textContent = view.title;
    $("budget-zeile").textContent = view.headline;
    $("budget-neu").textContent = view.renewal || "";
    $("budget-neu").hidden = !view.renewal;
    $("budget-balken").hidden = view.percent === null;
    $("budget-balken").setAttribute("aria-label", view.percent === null ? "" : `${view.percent} Prozent des Budgets gebraucht`);
    $("budget-fuellung").style.width = `${view.percent || 0}%`;
    $("budget-aufgaben").replaceChildren(...view.rows.flatMap(row => [
      el("dt", {}, `${row.label} (${row.count})`), el("dd", { class: "num" }, row.usd)]));
    $("budget-hinweis").textContent = view.note;
    $("budget-gesamt").textContent = view.total;
  }

  // ---------- Own key ----------
  function zeige(stand) {
    $("ohne-schluessel").hidden = stand.gesetzt;
    $("mit-schluessel").hidden = !stand.gesetzt;
    costs = stand.kosten;
    showBudget();
  }

  async function afterKeyChange(stand) {
    zeige(stand);
    ki = await holen("/api/ki/status").catch(() => ki);
    showAccess();
    showBudget();
  }

  function zeigeEinwilligung(stand) {
    const erteilt = stand.einwilligung.erteilt;
    $("einwilligung-erteilt").hidden = !erteilt;
    $("einwilligung-offen").hidden = erteilt;
    $("einwilligung-link").replaceChildren(...[window.Einwilligung.link(stand.einwilligung)].filter(Boolean));  // none without a built-in address
    if (!erteilt) window.Einwilligung.zeile($("einwilligung-offen"), stand.einwilligung, zeigeEinwilligung);
    status($("einwilligung-meldung"), stand.einladung_fehler || "", stand.einladung_fehler ? "fehler" : "");
  }

  function pruefeBereit() {
    $("speichern").disabled = !$("bestaetigt").checked || !$("schluessel").value.trim();
  }

  async function speichern() {
    $("speichern").disabled = true;
    status($("meldung"), "Der Schlüssel wird geprüft …");
    try {
      await afterKeyChange(await senden("/api/schluessel/speichern", { schluessel: $("schluessel").value, bestaetigt: $("bestaetigt").checked }));
      status($("meldung"), "Gespeichert. Die KI-Aufrufe gehen jetzt direkt an die Claude API.", "ok");
    } catch (fehler) {
      status($("meldung"), fehler.message, "fehler");
    } finally {
      $("schluessel").value = "";
      pruefeBereit();
    }
  }

  async function entfernen() {
    $("entfernen").disabled = true;
    try {
      await afterKeyChange(await senden("/api/schluessel/entfernen", {}));
      $("bestaetigt").checked = false;
      pruefeBereit();
      anErweiterung("zugriff-abgeben");
      const abgabe = hatErweiterung() ? "" : " Die Erweiterung gibt den Zugriff ab, sobald sie das nächste Mal mit der App verbunden ist.";
      status($("meldung"), `Der Schlüssel ist entfernt. Die App läuft wieder über die Vermittlung.${abgabe}`, "ok");
    } catch (fehler) {
      status($("meldung"), fehler.message, "fehler");
    } finally {
      $("entfernen").disabled = false;
    }
  }

  // What the extension answers about the access: it can fail, and then the page must not claim otherwise.
  window.addEventListener("message", ereignis => {
    const daten = ereignis.data;
    if (ereignis.source !== window || ereignis.origin !== location.origin) return;
    if (!daten || daten.quelle !== "bewerbungsbegleiter-erweiterung" || daten.art !== "antwort") return;
    if (daten.frage === "zugriff-abgeben") {
      const text = daten.antwort && daten.antwort.fehler
        ? `Die Erweiterung konnte den Zugriff nicht abgeben (${daten.antwort.fehler}). Das geht auch in ihren Einstellungen im Browser.`
        : daten.antwort && daten.antwort.spaeter
          ? "Die Erweiterung gibt den Zugriff ab, sobald die laufende Suche oder die offenen Formulare fertig sind."
          : "Die Erweiterung hat den Zugriff auf alle Seiten abgegeben.";
      status($("zugriff-meldung"), text, daten.antwort && daten.antwort.fehler ? "fehler" : "ok");
    }
  });

  // ---------- Other sections ----------
  async function showExtension() {
    const connected = await (window.Sidebar?.extension ?? Promise.resolve(hatErweiterung()));
    $("erweiterung-stand").dataset.state = connected ? "connected" : "missing";
    $("erweiterung-stand").textContent = connected ? "Die Erweiterung ist verbunden." : "Die Erweiterung ist nicht verbunden.";
  }

  async function showChoice() {
    try {
      const wahl = await holen("/api/einrichtung/wahl");
      $("wahl-fakten").replaceChildren(
        el("dt", {}, "Gesucht"), el("dd", {}, SOUGHT[wahl.gesucht] || wahl.gesucht),
        el("dt", {}, "Anrede"), el("dd", {}, wahl.anrede === "du" ? "du" : "Sie"),
        el("dt", {}, "RAV"), el("dd", {}, wahl.rav ? "Ja, mit den Schritten zum RAV" : "Nein"));
    } catch (fehler) {
      status($("wahl-meldung"), fehler.message, "fehler");
    }
  }

  $("bestaetigt").addEventListener("change", pruefeBereit);
  $("schluessel").addEventListener("input", pruefeBereit);
  $("speichern").addEventListener("click", speichern);
  $("entfernen").addEventListener("click", entfernen);
  $("einladung-code").addEventListener("input", event => { $("einladung-einloesen").disabled = !event.target.value.trim(); });
  $("einladung-einloesen").addEventListener("click", redeem);
  bestaetigen($("einwilligung-widerruf"), "Wirklich widerrufen? Nochmals klicken", async () => {
    try {
      zeigeEinwilligung(await senden("/api/ki/einwilligung/widerruf", {}));
    } catch (fehler) {
      status($("einwilligung-meldung"), fehler.message, "fehler");
    }
  });
  window.addEventListener("hashchange", () => showSection(location.hash, { scroll: true }));
  // The packaged app reveals „Über die App“ after it asked for its version; an anchor to it waits for that.
  new MutationObserver(() => showSection(location.hash)).observe($("ueber-link"), { attributes: true, attributeFilter: ["hidden"] });
  showSection(location.hash, { scroll: true });
  holen("/api/schluessel").then(zeige).catch(fehler => status($("meldung"), fehler.message, "fehler"));
  loadAccess();
  showExtension();
  showChoice();
})();
