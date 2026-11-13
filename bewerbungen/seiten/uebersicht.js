"use strict";
// Heute (MIN-369, #260): the next step, Danach, dates and deadlines and the stand by stage; the list of applications
// has its own page since #261 (bewerbungen.js). The next step per application comes from uebersicht-logik.js,
// dates and the stand from heute-logic.js. Forms and Job-Room entries open through the
// browser extension (MIN-346, MIN-347): one application from its card, several together from one item.
(() => {
  const { holen, el, beobachten, textsatz } = window.App;
  const { text } = window.Texte;
  const L = window.UebersichtLogik;
  const H = window.HeuteLogic;
  const $ = id => document.getElementById(id);

  const PAGE_SOURCE = "bewerbungsbegleiter-seite";
  const EXTENSION_SOURCE = "bewerbungsbegleiter-erweiterung";
  const EXTENSION_MARK = "bewerbungsbegleiterErweiterung";
  const START_ACTION = "bewerben-starten";
  const RAV_ACTION = "rav-starten";
  const NO_EXTENSION = "Zum Ausfüllen im Browser braucht es die Erweiterung (siehe Einrichtung).";
  const ANSWER_TIMEOUT_MS = 60000;
  const MAX_AUCH = 3;
  const MAX_DATES = 5;

  let satz = "stelle-sie";
  let rav = false;
  let alle = [];
  let zeilen = [];
  let gezeigt = "";      // the register as last drawn, to see whether Claude changed it
  let gruende = new Map();
  let ravGruende = new Map();
  let maxPerRun = 0;
  let maxRav = 0;
  let erinnerung = null;
  let neueTreffer = null;  // { anzahl, letzte } or null
  let laufendeAnfrage = null;  // { ids } of the run waiting for the extension, for „Trotzdem öffnen“
  let answerTimer = null;

  // Small helpers

  const meldung = (inhalt, stufe = "", optionen = {}) => window.Meldungen.zeige($("lauf-status"), inhalt, stufe, optionen);

  const t = (schluessel, werte) => text(schluessel, satz, werte);
  const lehrstelle = () => satz === "lehrstelle-du";
  const adresse = b => "/bewerbung?id=" + encodeURIComponent(b.id);

  const schrittText = (schritt, anzahl = 1) => L.schrittText(schritt, anzahl, t);

  // „Das steht an“

  function aktion(eintrag, danach = false) {
    const art = eintrag.art;
    const ids = eintrag.eintraege.map(z => z.bewerbung.id);
    const klasse = danach ? "btn" : "btn btn--primary";
    if (art === "entscheiden" && ids.length > 1) {
      const knopf = el("button", { type: "button", class: klasse }, "Durchgang beginnen");
      knopf.addEventListener("click", () => window.Pass.start(H.passQueue(zeilen), durchgangFertig));
      return knopf;
    }
    if (art === "abschicken") {
      const knopf = el("button", { type: "button", class: klasse }, ids.length > 1 ? "Formulare öffnen" : "Formular öffnen");
      knopf.addEventListener("click", () => startRun(ids.slice(0, maxPerRun), false, knopf));
      return knopf;
    }
    if (art === "rav") {
      const knopf = el("button", { type: "button", class: klasse }, "Jetzt eintragen");
      knopf.addEventListener("click", () => startRav(ids.slice(0, maxRav), knopf));
      return knopf;
    }
    if (art === "freigeben") return el("a", { class: klasse, href: adresse(eintrag.eintraege[0].bewerbung) + "#s-anschreiben" }, "Anschreiben lesen");
    if (art === "link") return el("a", { class: klasse, href: adresse(eintrag.eintraege[0].bewerbung) }, "Link eintragen");
    return el("a", { class: klasse, href: adresse(eintrag.eintraege[0].bewerbung) }, "Bewerbung öffnen");
  }

  function kartenText(eintrag) {
    const { schritt } = eintrag.eintraege[0];
    switch (eintrag.art) {
      case "abschicken": return t(eintrag.eintraege.length > 1 ? "uebersicht.karte.abschicken-alle" : "uebersicht.karte.abschicken");
      case "rav": return t("uebersicht.karte.rav");
      case "freigeben": return t("uebersicht.karte.freigeben");
      case "unterlagen": return t("uebersicht.karte.unterlagen");
      case "link": return "Ohne Link zum Bewerbungsformular kann die Erweiterung es nicht öffnen und ausfüllen.";
      case "gespraech": return schritt.frist ? `Termin am ${L.datum(schritt.frist)}. Inserat, Anschreiben und Notizen stehen in der Bewerbung.` : "Den Termin in der Bewerbung eintragen, dann steht er hier.";
      case "entscheiden": return eintrag.eintraege.length > 1 ? t("heute.durchgang.unter", { anzahl: eintrag.eintraege.length })
        : "Bewerben oder verwerfen? Note und Inserat stehen in der Bewerbung.";
      default: return schritt.grund || "";
    }
  }

  function zeigeKarte(eintrag) {
    $("karte").hidden = !eintrag;
    if (!eintrag) return;
    const erste = eintrag.eintraege[0].bewerbung;
    const anzahl = eintrag.eintraege.length;
    const was = schrittText(eintrag.eintraege[0].schritt, anzahl);
    $("karte-zeile").textContent = anzahl > 1 ? "Nächster Schritt" : `Nächster Schritt · ${[erste.stelle, erste.firma].filter(Boolean).join(", ")}`;
    $("karte-titel").textContent = was.titel;
    $("karte-text").textContent = kartenText(eintrag);
    $("karte-knoepfe").replaceChildren(aktion(eintrag));
    const fristen = eintrag.eintraege.map(z => z.schritt.frist).filter(Boolean).sort();
    const fuss = anzahl > 1 && eintrag.art !== "entscheiden" ? eintrag.eintraege.map(z => z.bewerbung.firma).join(", ")
      : fristen.length && eintrag.art !== "gespraech" ? `Frist ${L.datum(fristen[0])}` : "";
    $("karte-fuss").hidden = !fuss;
    $("karte-fuss").textContent = fuss;
  }

  // Danach: what comes after the next step, each with its own button

  function auchZeile(titel, unter, knopf) {
    return el("li", { class: "today__task" },
      el("span", { class: "today__task-text" }, el("strong", {}, titel), unter ? el("span", { class: "today__meta" }, unter) : null), knopf);
  }

  function auchUnter(e) {
    const anzahl = e.eintraege.length;
    if (e.art === "entscheiden" && anzahl > 1) return t("heute.durchgang.unter", { anzahl });
    if (anzahl > 1) return e.eintraege.map(z => z.bewerbung.firma).join(", ");
    const { bewerbung: b, schritt } = e.eintraege[0];
    const wann = schritt.frist ? `Frist ${L.datum(schritt.frist)}` : schrittText(schritt).zusatz;
    return [[b.stelle, b.firma].filter(Boolean).join(", "), wann].filter(Boolean).join(" · ");
  }

  function zeigeAuch(eintraege) {
    const punkte = eintraege.map(e => auchZeile(schrittText(e.eintraege[0].schritt, e.eintraege.length).titel, auchUnter(e), aktion(e, true)));
    if (neueTreffer && neueTreffer.anzahl > 0 && punkte.length < MAX_AUCH) {
      const unter = neueTreffer.letzte ? `Suche vom ${L.datum(neueTreffer.letzte.slice(0, 10))}` : "";
      punkte.push(auchZeile(`${neueTreffer.anzahl} neue Treffer ansehen`, unter, el("a", { class: "btn", href: "/treffer" }, "Treffer ansehen")));
    }
    $("auch").hidden = punkte.length === 0;
    $("auch-liste").replaceChildren(...punkte);
  }

  // The line under the title, Termine und Fristen, Ihr Stand

  function heuteIso() {
    const jetzt = new Date();
    return [jetzt.getFullYear(), jetzt.getMonth() + 1, jetzt.getDate()].map(n => String(n).padStart(2, "0")).join("-");
  }

  function zeigeZeile() {
    const tag = new Date().toLocaleDateString("de-CH", { weekday: "long", day: "numeric", month: "long" });
    const { key, values } = H.waiting(L.stehtAn(zeilen, Infinity).length);
    $("heute-zeile").textContent = `${tag} · ${t(key, values)}`;
  }

  function zeigeTermine() {
    const termine = H.dates(zeilen, heuteIso(), { max: MAX_DATES, interview: window.Texte.statusName("Gespräch", satz) });
    $("termine-liste").replaceChildren(...termine.map(termin =>
      el("li", { class: "today__date" }, el("span", { class: "today__day" }, termin.day), el("span", {}, termin.text))));
    $("termine-liste").hidden = termine.length === 0;
    $("termine-leer").hidden = termine.length > 0;
  }

  function zeigeStand() {
    const gespraech = lehrstelle() ? ["Einladung", "Einladungen"] : ["Gespräch", "Gespräche"];
    const treffer = neueTreffer ? { count: neueTreffer.anzahl, last: neueTreffer.letzte } : null;
    for (const [name, { count, hint }] of Object.entries(H.stand(zeilen, treffer, heuteIso(), { interview: gespraech }))) {
      $(`stand-${name}-zahl`).textContent = String(count);
      $(`stand-${name}-hinweis`).textContent = hint;
    }
  }

  function durchgangFertig(anzahl) {
    meldung(H.passResult(anzahl), "success");
    if ((anzahl.bewerben || 0) + (anzahl.verworfen || 0) > 0) laden();
  }

  function zeigeStehtAn() {
    const an = L.stehtAn(zeilen, MAX_AUCH + 1);
    zeigeZeile();
    zeigeTermine();
    zeigeStand();
    if (alle.length === 0) {
      $("karte").hidden = false;
      $("karte-zeile").textContent = "Nächster Schritt";
      $("karte-titel").textContent = t("uebersicht.leer.titel");
      $("karte-text").textContent = t("uebersicht.leer.text");
      $("karte-knoepfe").replaceChildren(el("a", { class: "btn btn--primary", href: "/treffer" }, t("nav.suche")));
      $("karte-fuss").hidden = true;
      zeigeAuch([]);
      return;
    }
    zeigeKarte(an[0]);
    zeigeAuch(an.slice(1));
  }

  function zeigeRavHinweis() {
    const offen = erinnerung ? erinnerung.ids.filter(id => ravGruende.get(id) === null) : [];
    $("rav-hinweis").hidden = !rav || offen.length === 0;
    if (offen.length) {
      const anzahl = `${offen.length} ${offen.length === 1 ? "Bewerbung" : "Bewerbungen"}`;
      $("rav-hinweis-text").textContent = t("heute.rav", { anzahl, monat: erinnerung.monat, frist: erinnerung.frist });
    }
  }

  function zeige() {
    const ohneAngaben = !grundlagen.lebenslauf && alle.length === 0;
    $("erststart").hidden = !ohneAngaben;
    $("steht-an").hidden = ohneAngaben;
    window.Texte.anwenden(document, satz);
    zeigeRavHinweis();
    if (ohneAngaben) zeigeEinrichtung();
    else zeigeStehtAn();
  }

  /** First step of the way: done when the AI is set up and the extension answers (the sidebar asks both). */
  async function zeigeEinrichtung() {
    if (!window.Sidebar) return;
    const [ki, erweiterung] = await Promise.all([window.Sidebar.aiStatus, window.Sidebar.extension]);
    const bereit = Boolean(ki && ki.eingerichtet) && erweiterung;
    $("weg-einrichtung").dataset.state = bereit ? "done" : "todo";
    $("weg-einrichtung-stand").textContent = bereit ? "· erledigt" : "· noch offen";
    $("weg-einrichtung-link").hidden = bereit;
  }

  // Opening forms and Job-Room entries through the extension

  function askExtension(message, button, waiting) {
    if (!document.documentElement.dataset[EXTENSION_MARK]) {
      meldung(NO_EXTENSION, "danger");
      return;
    }
    if (button) button.disabled = true;
    meldung(waiting);
    clearTimeout(answerTimer);
    answerTimer = setTimeout(() => {
      meldung("Die Erweiterung antwortet nicht. Bitte sie neu laden und es nochmals versuchen.", "danger");
      if (button) button.disabled = false;
    }, ANSWER_TIMEOUT_MS);
    window.postMessage({ quelle: PAGE_SOURCE, ...message }, location.origin);
  }

  function startRun(ids, bestaetigt, button = null) {
    laufendeAnfrage = { ids, button };
    askExtension({ art: START_ACTION, ids, bestaetigt }, button, "Die Unterlagen werden geprüft …");
  }

  function startRav(ids, button = null) {
    askExtension({ art: RAV_ACTION, ids }, button, "Der Job-Room wird geöffnet …");
  }

  function zeigeDoppelt(doppelt) {
    const firmen = [...new Set(doppelt.map(d => d.firma))];
    $("doppelt-titel").textContent = firmen.length === 1 ? `Bei ${firmen[0]} läuft schon eine Bewerbung` : "Bei diesen Firmen läuft schon eine Bewerbung";
    $("doppelt-text").replaceChildren(
      ...doppelt.map(d => el("p", {}, `${d.firma}: ${d.stelle}, Stand ${d.status}.`)),
      el("p", {}, t("uebersicht.doppelt")));
    $("doppelt-dialog").showModal();
  }

  function fertig() {
    clearTimeout(answerTimer);
    for (const knopf of document.querySelectorAll("#karte-knoepfe button, #auch-liste button, #rav-hinweis-knopf")) knopf.disabled = false;
  }

  function showAnswer(answer) {
    if (answer && answer.laeuft) return;
    fertig();
    meldung("");
    if (!answer || answer.fehler) meldung((answer && answer.fehler) || "Die Erweiterung antwortet nicht.", "danger");
    else if (answer.berechtigung) meldung("Bitte im neuen Tab den Zugriff erlauben; danach geht es weiter.", "warning");
    else if (answer.abgelehnt && answer.abgelehnt.length) meldung(answer.abgelehnt.map(a => `${a.firma}: ${a.grund}`).join(" · "), "danger");
    else if (answer.doppelt && answer.doppelt.length) zeigeDoppelt(answer.doppelt);
    else if (answer.geoeffnet) {
      meldung(t("uebersicht.geoeffnet", { anzahl: answer.geoeffnet }), "success");
      laden();
    }
  }

  function showRavAnswer(answer) {
    fertig();
    meldung("");
    if (!answer || answer.fehler) meldung((answer && answer.fehler) || "Die Erweiterung antwortet nicht.", "danger");
    else if (answer.abgelehnt && answer.abgelehnt.length) meldung(answer.abgelehnt.map(a => `${a.firma}: ${a.grund}`).join(" · "), "danger");
    else if (answer.geoeffnet) {
      meldung(t("uebersicht.jobroom-offen", { anzahl: answer.geoeffnet }), "success");
      laden();
    }
  }

  // Loading

  let grundlagen = { lebenslauf: true };

  async function ladeAuswahl() {
    const [auswahl, ravAuswahl] = await Promise.all([holen("/api/bewerben/auswahl"), holen("/api/rav/auswahl")]);
    gruende = new Map(auswahl.bewerbungen.map(row => [row.id, row.grund]));
    maxPerRun = auswahl.hoechstens;
    rav = Boolean(ravAuswahl.sichtbar);
    ravGruende = new Map(rav ? ravAuswahl.bewerbungen.map(row => [row.id, row.grund]) : []);
    maxRav = ravAuswahl.hoechstens;
    erinnerung = ravAuswahl.erinnerung;
  }

  async function ladeTreffer() {
    try {
      const liste = await holen("/api/suche/liste");
      neueTreffer = { anzahl: liste.treffer.filter(h => h.zustand === "neu").length, letzte: liste.letzte_suche?.datum || "" };
    } catch {
      neueTreffer = null;  // no search profile yet: nothing to look at
    }
  }

  async function laden() {
    try {
      const [daten, , gefunden] = await Promise.all([holen("/api/bewerbungen"), ladeAuswahl(), holen("/api/grundlagen").catch(() => grundlagen), ladeTreffer()]);
      grundlagen = gefunden;
      gezeigt = JSON.stringify(daten.bewerbungen);
      alle = daten.bewerbungen;
      zeilen = L.mitSchritten(alle, gruende, ravGruende);
      zeige();
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

  // Wiring

  $("rav-hinweis-knopf").addEventListener("click", e => {
    const offen = erinnerung ? erinnerung.ids.filter(id => ravGruende.get(id) === null) : [];
    startRav(offen.slice(0, maxRav), e.currentTarget);
  });
  $("doppelt-abbrechen").addEventListener("click", () => { $("doppelt-dialog").close(); meldung(""); });
  $("doppelt-trotzdem").addEventListener("click", () => {
    $("doppelt-dialog").close();
    if (laufendeAnfrage) startRun(laufendeAnfrage.ids, true, laufendeAnfrage.button);
  });
  window.addEventListener("message", event => {
    const data = event.data;
    if (event.source !== window || event.origin !== location.origin || data?.quelle !== EXTENSION_SOURCE || data.art !== "antwort") return;
    if (data.frage === START_ACTION) showAnswer(data.antwort);
    if (data.frage === RAV_ACTION) showRavAnswer(data.antwort);
  });
  // The tabs of the forms report to the app; the list shows it on the way back.
  document.addEventListener("visibilitychange", () => { if (!document.hidden) laden(); });
  beobachten(nachsehen);

  (async () => {
    satz = await textsatz();
    await laden();
  })();
})();
