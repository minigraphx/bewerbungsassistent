"use strict";
// Overview (MIN-369): „Das steht an“ with the next step, then the applications in five columns.
// The next step per application comes from uebersicht-logik.js. Forms and Job-Room entries open through the
// browser extension (MIN-346, MIN-347): one application from its card, several together from one item.
(() => {
  const { holen, senden, el, beobachten, textsatz } = window.App;
  const { text } = window.Texte;
  const L = window.UebersichtLogik;
  const $ = id => document.getElementById(id);

  const PAGE_SOURCE = "bewerbungsassistent-seite";
  const EXTENSION_SOURCE = "bewerbungsassistent-erweiterung";
  const EXTENSION_MARK = "bewerbungsassistentErweiterung";
  const START_ACTION = "bewerben-starten";
  const RAV_ACTION = "rav-starten";
  const NO_EXTENSION = "Zum Ausfüllen im Browser braucht es die Erweiterung (siehe Einrichtung).";
  const ANSWER_TIMEOUT_MS = 60000;
  const ANSICHT = "uebersicht.ansicht";  // view, search and scroll position stay when going to another page
  const ANSICHTEN = ["laufend", "abgeschlossen", "alle"];
  const MAX_AUCH = 3;
  const GESCHLOSSEN_WORT = { Zusage: ["Zusage", "Zusagen"], Absage: ["Absage", "Absagen"], Verworfen: ["verworfen", "verworfen"],
                             "Zurückgezogen": ["zurückgezogen", "zurückgezogen"] };

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
  let ansicht = "laufend";
  let laufendeAnfrage = null;  // { ids } of the run waiting for the extension, for „Trotzdem öffnen“
  let answerTimer = null;
  let wiederhergestellt = false;

  // Small helpers

  function meldung(inhalt, stufe = "") {
    $("lauf-status").textContent = inhalt;
    if (stufe) $("lauf-status").dataset.level = stufe;
    else delete $("lauf-status").dataset.level;
  }

  const t = (schluessel, werte) => text(schluessel, satz, werte);
  const lehrstelle = () => satz === "lehrstelle-du";
  const adresse = b => "/bewerbung?id=" + encodeURIComponent(b.id);
  const wo = b => [b.firma, b.ort].filter(Boolean).join(", ");

  function merken() {
    try {
      const scroll = wiederhergestellt ? Math.round(window.scrollY) : gemerkt().scroll;
      localStorage.setItem(ANSICHT, JSON.stringify({ ansicht, suche: $("suche").value, scroll }));
    } catch { /* without storage the default view applies */ }
  }

  function gemerkt() {
    try {
      const a = JSON.parse(localStorage.getItem(ANSICHT) || "{}");
      return { ansicht: ANSICHTEN.includes(a.ansicht) ? a.ansicht : "laufend", suche: typeof a.suche === "string" ? a.suche : "",
               scroll: Number.isFinite(a.scroll) && a.scroll > 0 ? a.scroll : 0 };
    } catch {
      return { ansicht: "laufend", suche: "", scroll: 0 };
    }
  }

  // What a step is called, in the list and on the card

  function schrittText(schritt, anzahl = 1) {
    switch (schritt.art) {
      case "abschicken": return anzahl > 1 ? { titel: `${anzahl} Bewerbungen abschicken`, zusatz: "Formulare sind bereit" } : { titel: "Abschicken", zusatz: "Formular ist bereit" };
      case "freigeben": return { titel: "Anschreiben lesen und freigeben", zusatz: "Entwurf ist fertig" };
      case "unterlagen": return { titel: "Unterlagen erstellen", zusatz: "Lebenslauf-PDF fehlt" };
      case "link": return { titel: "Link zum Formular eintragen", zusatz: "dann füllt die Erweiterung es aus" };
      case "offen": return { titel: schritt.grund || "Bewerbung öffnen", zusatz: "" };
      case "rav": return anzahl > 1 ? { titel: `${anzahl} Bewerbungen im Job-Room eintragen`, zusatz: "fürs RAV" } : { titel: "Im Job-Room eintragen", zusatz: "fürs RAV" };
      case "gespraech": return { titel: t("bewerbung.gespraech"), zusatz: schritt.frist ? L.datum(schritt.frist) : "Termin eintragen" };
      case "entscheiden": return { titel: "Entscheiden", zusatz: "bewerben oder verwerfen" };
      case "warten": return { titel: "Antwort abwarten", zusatz: schritt.zusatz ? `nachfragen ab ${L.datum(schritt.zusatz)}` : "" };
      default: return { titel: "", zusatz: "" };
    }
  }

  // Note 1–6 as in the design: value, six bars, a word
  function notenWort(note) {
    return note >= 5.5 ? "passt sehr gut" : note >= 4.5 ? "passt gut" : note >= 4 ? "passt knapp" : "passt wenig";
  }

  function note(b) {
    if (typeof b.passung !== "number") return el("span", { class: "table__sub" }, "keine Note");
    const balken = [1, 2, 3, 4, 5, 6].map(k => el("i", { class: b.passung >= k ? "on" : b.passung >= k - 0.5 ? "half" : "" }));
    return el("span", { class: "grade-meter grade-meter--sm", "aria-label": `Note ${b.passung} von 6, ${notenWort(b.passung)}` },
      el("span", { class: "grade-meter__value" }, String(b.passung)),
      el("span", { class: "grade-meter__bar", "aria-hidden": "true" }, balken),
      el("span", { class: "grade-meter__word", "aria-hidden": "true" }, notenWort(b.passung)));
  }

  // The list

  function zeile({ bewerbung: b, schritt }) {
    const was = schrittText(schritt);
    return el("tr", {},
      el("td", { "data-label": "" }, el("a", { class: "table__main", href: adresse(b) }, b.stelle || "ohne Titel"), el("span", { class: "table__sub" }, wo(b))),
      el("td", { "data-label": "Stand" }, el("span", { class: "marke-status", "data-status": b.status }, window.Texte.statusName(b.status, satz))),
      el("td", { "data-label": "Note" }, note(b)),
      el("td", { "data-label": "Nächster Schritt", class: "table__next" }, was.titel || "–", was.zusatz ? el("span", { class: "table__sub" }, was.zusatz) : null),
      el("td", { "data-label": "Frist", class: "num" }, L.datum(schritt.frist)));
  }

  function zeigeListe() {
    const gezeigte = L.gefiltert(zeilen, ansicht, $("suche").value);
    for (const knopf of document.querySelectorAll("[data-ansicht]")) knopf.setAttribute("aria-pressed", String(knopf.dataset.ansicht === ansicht));
    for (const name of ANSICHTEN) document.querySelector(`[data-zahl=${name}]`).textContent = String(L.gefiltert(zeilen, name, "").length);
    $("liste").replaceChildren(...gezeigte.map(zeile));
    $("tabelle").hidden = gezeigte.length === 0;
    $("liste-leer").hidden = alle.length > 0;
    $("nichts-gefunden").hidden = alle.length === 0 || gezeigte.length > 0;
    const fertig = L.abgeschlossenZaehlen(zeilen);
    const teile = Object.entries(fertig).map(([status, n]) => `${n} ${(GESCHLOSSEN_WORT[status] || [status, status])[n === 1 ? 0 : 1]}`);
    $("liste-fuss").hidden = ansicht !== "laufend" || teile.length === 0;
    $("liste-fuss").replaceChildren(`Abgeschlossen: ${teile.join(", ")}. `,
      el("button", { type: "button", class: "link", onclick: () => waehleAnsicht("abgeschlossen") }, "Anzeigen"));
    merken();
  }

  function waehleAnsicht(name) {
    ansicht = name;
    zeigeListe();
  }

  // „Das steht an“

  function aktion(eintrag, klein = false) {
    const art = eintrag.art;
    const ids = eintrag.eintraege.map(z => z.bewerbung.id);
    const klasse = klein ? "btn btn--sm" : "btn btn--primary";
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
    if (art === "freigeben") return el("a", { class: klasse, href: adresse(eintrag.eintraege[0].bewerbung) + "#s-anschreiben" }, klein ? "Lesen" : "Anschreiben lesen");
    return el("a", { class: klasse, href: adresse(eintrag.eintraege[0].bewerbung) }, klein ? "Öffnen" : "Bewerbung öffnen");
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
      case "entscheiden": return "Bewerben oder verwerfen? Note und Inserat stehen in der Bewerbung.";
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
    const fuss = anzahl > 1 ? eintrag.eintraege.map(z => z.bewerbung.firma).join(", ")
      : fristen.length && eintrag.art !== "gespraech" ? `Frist ${L.datum(fristen[0])}` : "";
    $("karte-fuss").hidden = !fuss;
    $("karte-fuss").textContent = fuss;
  }

  function auchZeile(titel, unter, knopf) {
    return el("li", { class: "overview__more-item" },
      el("span", {}, el("strong", {}, titel), unter ? el("span", { class: "table__sub" }, unter) : null), knopf);
  }

  function zeigeAuch(eintraege) {
    const punkte = eintraege.map(e => {
      const was = schrittText(e.eintraege[0].schritt, e.eintraege.length);
      const b = e.eintraege[0].bewerbung;
      const unter = e.eintraege.length > 1 ? e.eintraege.map(z => z.bewerbung.firma).join(", ")
        : [b.firma, e.eintraege[0].schritt.frist ? L.datum(e.eintraege[0].schritt.frist) : was.zusatz].filter(Boolean).join(" · ");
      return auchZeile(was.titel, unter, aktion(e, true));
    });
    if (neueTreffer && neueTreffer.anzahl > 0 && punkte.length < MAX_AUCH) {
      const unter = neueTreffer.letzte ? `Suche vom ${L.datum(neueTreffer.letzte.slice(0, 10))}` : "";
      punkte.push(auchZeile(`${neueTreffer.anzahl} neue Treffer ansehen`, unter, el("a", { class: "btn btn--sm", href: "/treffer" }, "Ansehen")));
    }
    $("auch").hidden = punkte.length === 0;
    $("auch-liste").replaceChildren(...punkte);
  }

  function zeigeStehtAn() {
    const an = L.stehtAn(zeilen, MAX_AUCH + 1);
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
      $("rav-hinweis-text").textContent = `${offen.length} ${offen.length === 1 ? "Bewerbung" : "Bewerbungen"} aus dem ${erinnerung.monat} fehlen noch im Job-Room. Das RAV erhält die Einträge bis zum ${erinnerung.frist}.`;
    }
  }

  function zeige() {
    const ohneAngaben = !grundlagen.lebenslauf && alle.length === 0;
    $("erststart").hidden = !ohneAngaben;
    $("steht-an").hidden = ohneAngaben;
    $("liste-teil").hidden = ohneAngaben;
    $("festhalten").dataset.text = rav ? "uebersicht.start.festhalten-rav" : "uebersicht.start.festhalten";
    window.Texte.anwenden(document, satz);
    $("suche").placeholder = t("uebersicht.suche");
    zeigeRavHinweis();
    if (!ohneAngaben) {
      zeigeStehtAn();
      zeigeListe();
    }
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

  // Adding one by hand

  async function anlegen(event) {
    event.preventDefault();
    $("neu-anlegen").disabled = true;
    try {
      const b = await senden("/api/bewerbung/neu", { firma: $("neu-firma").value, stelle: $("neu-stelle").value });
      location.href = adresse(b);
    } catch (fehler) {
      $("neu-status").textContent = fehler.message;
      $("neu-status").dataset.level = "danger";
      $("neu-anlegen").disabled = false;
    }
  }

  // Wiring

  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  let scrollTimer = null;
  window.addEventListener("scroll", () => { clearTimeout(scrollTimer); scrollTimer = setTimeout(merken, 150); }, { passive: true });
  window.addEventListener("pagehide", merken);
  $("suche").addEventListener("input", zeigeListe);
  for (const knopf of document.querySelectorAll("[data-ansicht]")) knopf.addEventListener("click", () => waehleAnsicht(knopf.dataset.ansicht));
  $("rav-hinweis-knopf").addEventListener("click", e => {
    const offen = erinnerung ? erinnerung.ids.filter(id => ravGruende.get(id) === null) : [];
    startRav(offen.slice(0, maxRav), e.currentTarget);
  });
  $("von-hand").addEventListener("click", () => { $("neu-status").textContent = ""; $("neu-dialog").showModal(); $("neu-firma").focus(); });
  $("neu-abbrechen").addEventListener("click", () => $("neu-dialog").close());
  $("neu-form").addEventListener("submit", anlegen);
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
    const ansichtGemerkt = gemerkt();
    ansicht = ansichtGemerkt.ansicht;
    $("suche").value = ansichtGemerkt.suche;
    satz = await textsatz();
    await laden();
    requestAnimationFrame(() => { window.scrollTo(0, ansichtGemerkt.scroll); wiederhergestellt = true; });
  })();
})();
