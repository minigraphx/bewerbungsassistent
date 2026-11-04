"use strict";
(() => {
  const { holen, senden, el, status, datum } = window.App;
  const $ = id => document.getElementById(id);
  // Spalten: Schlüssel im Register, Überschrift, Art (bestimmt die Sortierung)
  const SPALTEN = [
    ["firma", "Firma", "text"], ["stelle", "Stelle", "text"], ["status", "Status", "status"],
    ["passung", "Passung", "zahl"], ["eingetragen_am", "Eingetragen", "datum"],
    ["beworben_am", "Beworben", "datum"], ["absage_am", "Absage", "datum"], ["variante", "Variante", "text"],
    ["ausfuellen", "Formular", "text"],
    ["link", "Inserat", "keine"],  // nicht sortierbar
  ];
  const FORM_STATE_TEXT = { geoeffnet: "geöffnet", ausgefuellt: "ausgefüllt", abgeschickt: "abgeschickt" };
  const PAGE_SOURCE = "bewerbungsassistent-seite";
  const EXTENSION_SOURCE = "bewerbungsassistent-erweiterung";
  const EXTENSION_MARK = "bewerbungsassistentErweiterung";
  const START_ACTION = "bewerben-starten";
  const NO_EXTENSION = "Zum Ausfüllen im Browser braucht es die Erweiterung (siehe Einrichtung).";
  const ANSWER_TIMEOUT_MS = 60000;
  const ANSICHT = "uebersicht.ansicht";  // Sortierung, Suche, Filter und Scrollposition bleiben beim Seitenwechsel erhalten
  let wiederhergestellt = false;  // Scrollposition erst speichern, wenn die gemerkte gesetzt ist
  let alle = [];
  let statusReihe = [];
  let sortierung = { spalte: null, richtung: 1 };  // null = Reihenfolge des Servers (nach Status)
  let blockers = new Map();  // id → reason it cannot be opened; only what the app listed can be ticked
  let chosen = new Set();
  let maxPerRun = 0;
  let answerTimer = null;

  // Browser-Speicher kann fehlen oder gesperrt sein (privates Fenster): dann gilt einfach die Standardansicht
  function merken() {
    try {
      const scroll = wiederhergestellt ? Math.round(window.scrollY) : gemerkt().scroll;
      localStorage.setItem(ANSICHT, JSON.stringify({ sortierung, suche: $("suche").value, filter: $("statusfilter").value, scroll }));
    } catch { /* ohne Speicher keine Erinnerung */ }
  }

  function gemerkt() {
    try {
      const a = JSON.parse(localStorage.getItem(ANSICHT) || "{}");
      const gueltig = a.sortierung && SPALTEN.some(([s, , art]) => s === a.sortierung.spalte && art !== "keine") && [1, -1].includes(a.sortierung.richtung);
      return { sortierung: gueltig ? a.sortierung : { spalte: null, richtung: 1 },
               suche: typeof a.suche === "string" ? a.suche : "", filter: typeof a.filter === "string" ? a.filter : "",
               scroll: Number.isFinite(a.scroll) && a.scroll > 0 ? a.scroll : 0 };
    } catch {
      return { sortierung: { spalte: null, richtung: 1 }, suche: "", filter: "", scroll: 0 };
    }
  }

  function wert(b, spalte, art) {
    const w = b[spalte];
    if (art === "status") return statusReihe.indexOf(w);
    if (art === "zahl") return typeof w === "number" ? w : null;
    return w ? String(w).toLowerCase() : null;  // ISO-Datum sortiert als Text richtig
  }

  // Leere Werte immer ans Ende, unabhängig von der Richtung
  function vergleiche(a, b) {
    const [spalte, , art] = SPALTEN.find(([s]) => s === sortierung.spalte);
    const x = wert(a, spalte, art), y = wert(b, spalte, art);
    if (x === null || y === null) return (x === null) - (y === null);
    return (x < y ? -1 : x > y ? 1 : 0) * sortierung.richtung;
  }

  function kopf() {
    $("kopf").replaceChildren(el("th", {}, "Wahl"), ...SPALTEN.map(([spalte, text, art]) => {
      if (art === "keine") return el("th", {}, text);
      const aktiv = sortierung.spalte === spalte;
      const pfeil = aktiv ? (sortierung.richtung === 1 ? " ▲" : " ▼") : "";
      const knopf = el("button", { type: "button", class: "sortieren", onclick: () => sortiere(spalte, art) }, text + pfeil);
      return el("th", { "aria-sort": aktiv ? (sortierung.richtung === 1 ? "ascending" : "descending") : "none" }, knopf);
    }));
  }

  function sortiere(spalte, art) {
    // Erster Klick: Text und Status aufsteigend, Zahlen und Daten absteigend (beste Note, neuestes Datum zuerst)
    const richtung = sortierung.spalte === spalte ? -sortierung.richtung : (art === "zahl" || art === "datum" ? -1 : 1);
    sortierung = { spalte, richtung };
    zeige();
  }

  function updateChoice() {
    const count = chosen.size;
    $("bewerben").disabled = count === 0 || count > maxPerRun;
    $("bewerben").textContent = count ? `Bewerben (${count})` : "Bewerben";
    $("bewerben-hilfe").textContent = count > maxPerRun
      ? `Pro Durchgang höchstens ${maxPerRun}.`
      : "Öffnet pro Bewerbung einen Tab und füllt das Formular aus. Abschicken bleibt bei Ihnen.";
  }

  function choiceBox(b) {
    const reason = blockers.has(b.id) ? blockers.get(b.id) : "Noch nicht geprüft";
    const box = el("input", { type: "checkbox", "aria-label": `${b.firma} zum Bewerben wählen`, title: reason || "" });
    box.disabled = Boolean(reason);
    box.checked = chosen.has(b.id);
    box.addEventListener("change", () => {
      chosen = box.checked ? new Set([...chosen, b.id]) : new Set([...chosen].filter(id => id !== b.id));
      updateChoice();
    });
    return box;
  }

  function zeile(b) {
    const link = el("a", { href: "/bewerbung?id=" + encodeURIComponent(b.id) }, b.firma);
    return el("tr", {},
      el("td", {}, choiceBox(b)),
      el("td", {}, link),
      el("td", {}, b.stelle),
      el("td", {}, el("span", { class: "marke-status", "data-status": b.status }, b.status)),
      el("td", { class: "zahl" }, b.passung ?? ""),
      el("td", {}, datum(b.eingetragen_am)),
      el("td", {}, datum(b.beworben_am)),
      el("td", {}, datum(b.absage_am)),
      el("td", {}, b.variante || ""),
      el("td", {}, FORM_STATE_TEXT[b.ausfuellen] || ""),
      el("td", {}, b.link ? el("a", { href: b.link, target: "_blank", rel: "noopener noreferrer", title: b.link }, "Inserat ↗") : ""),
    );
  }

  function zeige() {
    const suche = $("suche").value.trim().toLowerCase();
    const filter = $("statusfilter").value;
    const auswahl = alle.filter(b =>
      (!filter || b.status === filter) &&
      (!suche || `${b.firma} ${b.stelle} ${b.notiz || ""}`.toLowerCase().includes(suche)));
    const sortiert = sortierung.spalte ? [...auswahl].sort(vergleiche) : auswahl;
    kopf();
    merken();
    $("liste").replaceChildren(...sortiert.map(zeile));
    $("leer").hidden = sortiert.length > 0;
  }

  async function loadChoice() {
    const auswahl = await holen("/api/bewerben/auswahl");
    blockers = new Map(auswahl.bewerbungen.map(row => [row.id, row.grund]));
    maxPerRun = auswahl.hoechstens;
    chosen = new Set([...chosen].filter(id => blockers.get(id) === null));
    $("bewerben-zeile").hidden = false;
    updateChoice();
  }

  function startRun(bestaetigt) {
    const ids = [...chosen];
    if (!document.documentElement.dataset[EXTENSION_MARK]) {
      status($("bewerben-status"), NO_EXTENSION, "fehler");
      return;
    }
    $("bewerben-frage").hidden = true;
    $("bewerben").disabled = true;
    status($("bewerben-status"), "Die Unterlagen werden geprüft …", "");
    clearTimeout(answerTimer);
    answerTimer = setTimeout(() => {
      status($("bewerben-status"), "Die Erweiterung antwortet nicht. Bitte sie neu laden und es nochmals versuchen.", "fehler");
      updateChoice();
    }, ANSWER_TIMEOUT_MS);
    window.postMessage({ quelle: PAGE_SOURCE, art: START_ACTION, ids, bestaetigt }, location.origin);
  }

  function showDuplicates(doppelt) {
    $("bewerben-frage-text").replaceChildren(
      el("strong", {}, "Doppelbewerbung?"),
      ...doppelt.map(d => el("div", {}, `${d.firma}: auch „${d.stelle}“ (${d.status})`)));
    $("bewerben-frage").hidden = false;
  }

  function showRefused(abgelehnt) {
    status($("bewerben-status"), abgelehnt.map(a => `${a.firma}: ${a.grund}`).join(" · "), "fehler");
  }

  function showAnswer(answer) {
    if (answer && answer.laeuft) return;
    clearTimeout(answerTimer);
    updateChoice();
    status($("bewerben-status"), "", "");
    if (!answer || answer.fehler) status($("bewerben-status"), (answer && answer.fehler) || "Die Erweiterung antwortet nicht.", "fehler");
    else if (answer.berechtigung) status($("bewerben-status"), "Bitte im neuen Tab den Zugriff erlauben; danach geht es weiter.", "hinweis");
    else if (answer.abgelehnt && answer.abgelehnt.length) showRefused(answer.abgelehnt);
    else if (answer.doppelt && answer.doppelt.length) showDuplicates(answer.doppelt);
    else if (answer.geoeffnet) {
      chosen = new Set();
      status($("bewerben-status"), `${answer.geoeffnet} Tab(s) geöffnet. Abgeschickt wird erst durch Sie.`, "ok");
      laden();
    }
  }

  async function laden() {
    try {
      const daten = await holen("/api/bewerbungen");
      await loadChoice();
      alle = daten.bewerbungen;
      statusReihe = daten.status;
      $("statusfilter").replaceChildren(el("option", { value: "" }, "Alle Status"),
        ...daten.status.map(s => el("option", { value: s }, `${s} (${alle.filter(b => b.status === s).length})`)));
      const ansicht = gemerkt();
      sortierung = ansicht.sortierung;
      $("suche").value = ansicht.suche;
      $("statusfilter").value = daten.status.includes(ansicht.filter) ? ansicht.filter : "";
      zeige();
      requestAnimationFrame(() => { window.scrollTo(0, ansicht.scroll); wiederhergestellt = true; });
    } catch (fehler) {
      status($("status"), "Laden fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  // Die Liste kommt erst nach dem Laden: Scrollposition selbst verwalten statt dem Browser zu überlassen
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  let scrollTimer = null;
  window.addEventListener("scroll", () => { clearTimeout(scrollTimer); scrollTimer = setTimeout(merken, 150); }, { passive: true });
  window.addEventListener("pagehide", merken);
  $("suche").addEventListener("input", zeige);
  $("statusfilter").addEventListener("change", zeige);
  $("bewerben").addEventListener("click", () => startRun(false));
  $("bewerben-trotzdem").addEventListener("click", () => startRun(true));
  $("bewerben-abbrechen").addEventListener("click", () => { $("bewerben-frage").hidden = true; });
  window.addEventListener("message", event => {
    const data = event.data;
    if (event.source === window && event.origin === location.origin && data?.quelle === EXTENSION_SOURCE
        && data.art === "antwort" && data.frage === START_ACTION) showAnswer(data.antwort);
  });
  // The tabs of the forms report to the app; the list shows it on the way back.
  document.addEventListener("visibilitychange", () => { if (!document.hidden) laden(); });
  $("anlegen").addEventListener("click", async () => {
    try {
      const b = await senden("/api/bewerbung/neu", { firma: $("neu-firma").value, stelle: $("neu-stelle").value });
      location.href = "/bewerbung?id=" + encodeURIComponent(b.id);
    } catch (fehler) {
      status($("status"), "Anlegen fehlgeschlagen: " + fehler.message, "fehler");
    }
  });
  holen("/api/grundlagen").then(g => { $("ohne-angaben").hidden = g.lebenslauf; }).catch(() => { /* the list shows the error */ });
  laden();
})();
