"use strict";
// Setup of the packaged app (MIN-342, MIN-369, #219): what is sought (job or apprenticeship, form of address, RAV, with
// the data folder as one line), AI invitation, browser extension; the einstieg file is a step only when such a file
// lies in Downloads, otherwise it is reached under „Erweitert“. Each step is a section; the hash says which one is
// shown, so the browser's back button works. Folder and file are chosen in the system's own dialog; the server reads
// the file from disk. The first step creates the folder before it stores the choice there. Which steps were skipped
// the page keeps in sessionStorage.
(() => {
  const { holen, senden, el } = window.App;
  const { text, anwenden } = window.Texte;
  const $ = id => document.getElementById(id);
  const usd = wert => `${Number(wert || 0).toFixed(2)} USD`;

  const L = window.EinrichtungLogik;
  const TITEL = { gesucht: "Gesucht", vorlage: "Datei", ki: "KI", erweiterung: "Erweiterung" };
  const FRUEHER = { datenordner: "gesucht" };  // links to steps that are gone
  const STORE = {
    chrome: { haupt: "Im Chrome Web Store hinzufügen", leise: "Im Chrome Web Store öffnen", name: "Google Chrome", knopf: "Hinzufügen" },
    edge: { haupt: "Im Edge-Store hinzufügen", leise: "Im Edge-Store öffnen", name: "Microsoft Edge", knopf: "Abrufen" },
  };
  const SPEICHER = "bewerbungsassistent-einrichtung";

  let info = null;         // /api/app/einrichtung; null in the plain app without setup
  let wahl = null;         // /api/einrichtung/wahl, or what the page keeps until there is a folder
  let ki = null;           // /api/ki/status
  let importiert = false;
  let dateiWahl = {};      // per existing Markdown file „behalten“ or „ersetzen“ (G26)
  let ravBeruehrt = false; // until the person picks one, RAV stays at its preset Nein (#218: employed people are not registered)
  const sitzung = ladeSitzung();  // { bestaetigt, uebersprungen: {vorlage, ki, erweiterung} }

  function ladeSitzung() {
    try {
      const gespeichert = JSON.parse(sessionStorage.getItem(SPEICHER) || "null");
      if (gespeichert && typeof gespeichert === "object") return { uebersprungen: {}, ...gespeichert };
    } catch { /* private window or blocked storage: the page works without */ }
    return { uebersprungen: {} };
  }

  function merke() {
    try { sessionStorage.setItem(SPEICHER, JSON.stringify(sitzung)); } catch { /* see ladeSitzung */ }
  }

  const meldung = (element, inhalt, stufe = "", optionen = {}) => window.Meldungen.zeige(element, inhalt, stufe, optionen);

  // State of the steps

  const bereit = () => Boolean(info && info.eingerichtet && !info.fehlt);
  const kiVerbunden = () => Boolean(ki && ki.eingerichtet);
  const erweiterungGeladen = () => document.documentElement.dataset.bewerbungsbegleiterErweiterung || "";
  const erweiterungZustand = () => L.erweiterungZustand(erweiterungGeladen(), info?.erweiterung?.version,
                                                                             "bewerbungsbegleiterEntpackt" in document.documentElement.dataset);
  const satz = () => wahl ? (wahl.gesucht === "lehrstelle" ? "lehrstelle-du" : `stelle-${wahl.anrede}`) : "stelle-sie";

  function erledigt(id) {
    switch (id) {
      case "gesucht": return Boolean(wahl && (wahl.gewaehlt || sitzung.bestaetigt)) && (!info || bereit());
      case "vorlage": return Boolean(info?.lebenslauf || importiert || sitzung.uebersprungen.vorlage);
      case "ki": return kiVerbunden() || Boolean(sitzung.uebersprungen.ki);
      case "erweiterung": return !info?.erweiterung || Boolean(erweiterungGeladen()) || Boolean(sitzung.uebersprungen.erweiterung);
      default: return false;
    }
  }

  function zusammenfassung() {
    if (!wahl) return "";
    const was = wahl.gesucht === "lehrstelle" ? "eine Lehrstelle" : "eine Stelle";
    return `${was}, ${wahl.anrede === "du" ? "du" : "Sie"}, ${wahl.rav ? "mit RAV" : "ohne RAV"}`;
  }

  function ordnerName(pfad) {
    const teile = String(pfad || "").split(/[\\/]+/).filter(Boolean);
    return teile[teile.length - 1] || "Dokumente";
  }

  function nebentext(id) {
    const fertig = erledigt(id);
    switch (id) {
      case "gesucht": return fertig ? zusammenfassung() : "Stelle oder Lehrstelle";
      case "vorlage": return info?.lebenslauf || importiert ? "übernommen" : sitzung.uebersprungen.vorlage ? "übersprungen" : "freiwillig";
      case "ki": return kiVerbunden() ? "verbunden" : sitzung.uebersprungen.ki ? "übersprungen" : "Einladungscode";
      case "erweiterung":
        if (!info?.erweiterung) return "nur in der installierten App";
        return erweiterungGeladen() ? "geladen" : sitzung.uebersprungen.erweiterung ? "später" : "1 bis 2 Minuten";
      default: return "";
    }
  }

  const gewuenscht = () => FRUEHER[location.hash.slice(1)] || location.hash.slice(1);
  // the plain app only knows the choice
  const sichtbareSchritte = () => L.schritte({ installiert: Boolean(info), einstiegDatei: info?.einstieg_datei, jetzt: gewuenscht() })
    .map(id => ({ id, titel: TITEL[id] }));
  const ersterOffener = () => sichtbareSchritte().find(s => !erledigt(s.id))?.id || "fertig";

  function erreichbar(id) {
    if (id === "gesucht") return true;
    if (!info) return id === "fertig" && erledigt("gesucht");
    return bereit() && (id in TITEL || id === "fertig");  // every later step needs the folder of the first one
  }

  function aktueller() {
    const id = gewuenscht();
    return id && erreichbar(id) ? id : ersterOffener();
  }

  function gehe(id) {
    if (location.hash.slice(1) === id) zeige();
    else location.hash = id;
  }

  function naechster(nach) {
    const ids = sichtbareSchritte().map(s => s.id);
    const offen = ids.slice(ids.indexOf(nach) + 1).find(id => !erledigt(id));
    gehe(offen || (ids.every(erledigt) ? "fertig" : ersterOffener()));
  }

  // Showing

  function zeigeSchritte(jetzt) {
    $("schritte").replaceChildren(...sichtbareSchritte().map(s => {
      const zustand = s.id === jetzt ? "current" : erledigt(s.id) ? "done" : "todo";
      const marke = s.id !== jetzt && erreichbar(s.id)
        ? el("a", { class: "steps__label", href: `#${s.id}` }, s.titel)
        : el("span", { class: "steps__label" }, s.titel);
      const punkt = el("li", { class: "steps__item", "data-state": zustand },
        el("span", { class: "steps__dot" }), marke, el("span", { class: "steps__meta" }, nebentext(s.id)));
      if (s.id === jetzt) punkt.setAttribute("aria-current", "step");
      return punkt;
    }));
  }

  function zeige() {
    const jetzt = aktueller();
    for (const teil of document.querySelectorAll("[data-schritt]")) teil.hidden = teil.dataset.schritt !== jetzt;
    zeigeSchritte(jetzt);
    anwenden(document, satz());
    if (jetzt === "gesucht") {
      zeigeWahl();
      zeigeOrdner(location.hash.slice(1) === "datenordner");
    }
    if (jetzt === "vorlage") zeigeVorlage();
    if (jetzt === "ki") zeigeKi();
    if (jetzt === "erweiterung") zeigeErweiterung();
    if (jetzt === "fertig") zeigeFertig();
    $("erweitert").hidden = !bereit() || Boolean(info?.einstieg_datei) || jetzt === "vorlage";
  }

  // 1. What is sought

  function gewaehlteWahl() {
    const gesucht = document.querySelector(".choice-card[aria-pressed='true']")?.dataset.gesucht || "stelle";
    const anrede = gesucht === "lehrstelle" ? "du" : document.querySelector("input[name=anrede]:checked")?.value || "sie";
    const rav = document.querySelector("input[name=rav]:checked")?.value === "ja";
    return { gesucht, anrede, rav };
  }

  function setzeGesucht(gesucht) {
    for (const karte of document.querySelectorAll(".choice-card")) karte.setAttribute("aria-pressed", String(karte.dataset.gesucht === gesucht));
    $("anrede").hidden = gesucht === "lehrstelle";
    $("anrede-lehrstelle").hidden = gesucht !== "lehrstelle";
    if (!ravBeruehrt) document.querySelector("input[name=rav][value=nein]").checked = true;
  }

  function zeigeWahl() {
    if (!wahl) return;
    setzeGesucht(wahl.gesucht);
    document.querySelector(`input[name=anrede][value=${wahl.anrede === "du" ? "du" : "sie"}]`).checked = true;
    if (wahl.gewaehlt || sitzung.bestaetigt) {
      ravBeruehrt = true;
      document.querySelector(`input[name=rav][value=${wahl.rav ? "ja" : "nein"}]`).checked = true;
    }
  }

  async function speichereWahl(werte) {
    wahl = await senden("/api/einrichtung/wahl", werte);
  }

  async function bestaetigeWahl() {
    const werte = gewaehlteWahl();
    $("gesucht-weiter").disabled = true;
    try {
      if (info && ordnerGeaendert() && await wechsleOrdner()) {
        zeigeWahl();
        meldung($("gesucht-status"), "In diesem Ordner war schon eine Wahl gespeichert; sie gilt jetzt. Mit Weiter geht es weiter.", "warning");
        zeige();
        return;
      }
      await speichereWahl(werte);
      sitzung.bestaetigt = true;
      merke();
      if (!info) {
        meldung($("gesucht-status"), "Gespeichert.", "success");
        zeigeSchritte("gesucht");
        anwenden(document, satz());
        return;
      }
      naechster("gesucht");
    } catch (fehler) {
      meldung($("gesucht-status"), fehler.message, "danger");
    } finally {
      $("gesucht-weiter").disabled = false;
    }
  }

  for (const karte of document.querySelectorAll(".choice-card")) karte.addEventListener("click", () => setzeGesucht(karte.dataset.gesucht));
  for (const knopf of document.querySelectorAll("input[name=rav]")) knopf.addEventListener("change", () => { ravBeruehrt = true; });
  $("gesucht-weiter").addEventListener("click", bestaetigeWahl);

  // The data folder, a line of the first step (#219): the proposal fits nearly everyone

  let ordnerAngezeigt = false;
  const ordnerPfad = () => $("ordner").value.trim();
  const ordnerGeaendert = () => !bereit() || ordnerPfad() !== info.datenordner;

  function oeffneOrdner(offen) {
    $("ordner-feld").hidden = !offen;
    $("ordner-aendern").setAttribute("aria-expanded", String(offen));
  }

  function zeigeOrdner(oeffnen = false) {
    $("ordner-teil").hidden = !info;
    if (!info) return;
    if (!ordnerAngezeigt) {
      $("ordner").value = info.datenordner || info.vorschlag;
      ordnerAngezeigt = true;
    }
    $("ordner-zeile").textContent = ordnerPfad() || info.vorschlag;
    $("ordner-fehlt").hidden = !info.fehlt;
    $("ordner-fehlt").textContent = info.fehlt
      ? `Der Datenordner ${info.datenordner} wurde nicht gefunden (z.B. USB-Stick nicht eingesteckt). Sobald er wieder verfügbar ist, diese Seite neu laden; oder einen anderen Ordner wählen.`
      : "";
    if (oeffnen || info.fehlt) oeffneOrdner(true);
  }

  async function pruefeOrdner() {
    const pfad = ordnerPfad();
    $("ordner-zeile").textContent = pfad || info.vorschlag;
    if (!pfad || !ordnerGeaendert()) return meldung($("ordner-status"), "");
    try {
      meldung($("ordner-status"), (await senden("/api/app/ordner-pruefen", { pfad })).text, "warning");
    } catch (fehler) {
      meldung($("ordner-status"), fehler.message, "danger");
    }
  }

  async function waehle(art, feld, status, danach) {
    try {
      const ergebnis = await senden("/api/app/waehlen", { art });
      if (ergebnis.pfad) {
        $(feld).value = ergebnis.pfad;
        await danach();
      }
    } catch (fehler) {
      meldung($(status), fehler.message, "danger");
    }
  }

  /** Creates or switches the folder; true when the new folder brought its own choice (another person's folder). */
  async function wechsleOrdner() {
    const vorher = bereit() ? info.datenordner : null;
    info = await senden("/api/app/datenordner", { pfad: ordnerPfad() });
    if (!vorher) return false;
    const dort = await holen("/api/einrichtung/wahl");
    if (!dort.gewaehlt) return false;
    wahl = dort;
    return true;
  }

  $("ordner").addEventListener("input", () => { $("ordner-zeile").textContent = ordnerPfad() || info?.vorschlag || ""; });
  $("ordner").addEventListener("change", pruefeOrdner);
  $("ordner-waehlen").addEventListener("click", () => waehle("ordner", "ordner", "ordner-status", pruefeOrdner));
  $("ordner-aendern").addEventListener("click", () => oeffneOrdner($("ordner-feld").hidden));

  // 2. Einstieg file: a step with a file in Downloads, otherwise under „Erweitert“

  function zeigeImport(ergebnis) {
    const zeile = (inhalt, stufe) => window.Meldungen.listenZeile(document, inhalt, stufe);
    const zeilen = [
      ...ergebnis.geschrieben.map(datei => zeile(`Angelegt: ${datei}`, "ok")),
      ...(ergebnis.nicht_ersetzt || []).map(datei => zeile(`Behalten: ${datei}`, "ok")),
      ...(ergebnis.unveraendert || []).map(datei => zeile(
        `Unverändert gelassen: ${datei}. Die Datei lässt sich nicht lesen; zu ändern unter „Inhalte als Text“.`, "hinweis")),
      ergebnis.dokumente.length ? zeile(`${ergebnis.dokumente.length} Dokument(e) abgelegt`, "ok") : null,
      ergebnis.unvollstaendig ? zeile(text("einrichtung.vorlage.unvollstaendig", satz()), "hinweis") : null,
    ];
    $("import-ergebnis").replaceChildren(...zeilen.filter(Boolean));
  }

  // ersetzen: null on the first try (existing Markdown files come back as a choice), else the files picked for replacing
  async function importiere(ersetzen = null) {
    zeigeDateiWahl([]);
    $("import-ergebnis").replaceChildren();
    meldung($("import-status"), "Wird importiert …");
    try {
      zeigeImport(await senden("/api/app/einstieg", { pfad: $("datei").value, ersetzen }));
      meldung($("import-status"), "Import abgeschlossen.", "success");
      importiert = true;
      info = await holen("/api/app/einrichtung");
      zeigeSchritte("vorlage");
      zeigeVorlage();
    } catch (fehler) {
      const vorhanden = fehler.status === 409 && fehler.daten?.vorhanden;
      meldung($("import-status"), fehler.message, vorhanden ? "warning" : "danger");
      zeigeDateiWahl(vorhanden ? fehler.daten.wahl || [] : []);
    }
  }

  function zeigeDateiWahl(dateien) {
    dateiWahl = L.startWahl(dateien);
    $("import-wahl").replaceChildren(...dateien.map(dateiFrage));
    $("import-wahl").hidden = !dateien.length;
    $("ersetzen").hidden = !dateien.length;
  }

  function dateiFrage(datei, index) {
    const unterschiede = el("div", { "aria-live": "polite" });
    const option = (wert, beschriftung) => el("label", { class: "import-wahl__option" },
      el("input", { type: "radio", name: `import-wahl-${index}`, value: wert, checked: wert === "behalten", onchange: () => {
        dateiWahl = { ...dateiWahl, [datei.datei]: wert };
        unterschiede.replaceChildren(...(wert === "ersetzen" ? [unterschiedeAnsicht(datei.zeilen)] : []));
      } }), ` ${beschriftung}`);
    return el("fieldset", { class: "import-wahl__datei" }, el("legend", {}, `${datei.titel} (${datei.datei})`),
      el("div", { class: "import-wahl__optionen" }, option("behalten", "Behalten"), option("ersetzen", "Ersetzen")), unterschiede);
  }

  function unterschiedeAnsicht(zeilen) {
    if (!zeilen.length) return el("p", { class: "field__hint" }, "Kein Unterschied zum bisherigen Stand.");
    const { zeilenZeichen } = L;
    return el("div", {},
      el("p", { class: "field__hint" }, "Unterschiede zum bisherigen Stand: Zeilen mit − fallen weg, Zeilen mit + kommen dazu."),
      el("pre", { class: "import-wahl__zeilen" }, zeilen.map(z => el("span", { class: `import-wahl__zeile import-wahl__zeile--${z.art}` },
        zeilenZeichen(z.art), z.art === "weg" ? el("del", {}, z.text) : z.art === "neu" ? el("ins", {}, z.text) : z.text, "\n"))));
  }

  function zeigeVorlage() {
    const gefunden = info?.einstieg_datei || "";
    $("vorlage-gefunden").hidden = !gefunden;
    $("vorlage-allgemein").hidden = Boolean(gefunden);
    $("vorlage-name").textContent = ordnerName(gefunden);
    if (gefunden && !$("datei").value) $("datei").value = gefunden;
    const vorhanden = Boolean(info?.lebenslauf || importiert);
    $("vorlage-weiter").hidden = !vorhanden;
    $("vorlage-ueberspringen").hidden = vorhanden;
  }

  function ueberspringe(id) {
    if (!erledigt(id)) {
      sitzung.uebersprungen[id] = true;
      merke();
    }
    naechster(id);
  }

  $("datei-waehlen").addEventListener("click", () => waehle("datei", "datei", "import-status", async () => {}));
  $("importieren").addEventListener("click", () => importiere(null));
  $("ersetzen").addEventListener("click", () => importiere(L.zuErsetzen(dateiWahl)));
  $("vorlage-ueberspringen").addEventListener("click", () => ueberspringe("vorlage"));
  $("vorlage-weiter").addEventListener("click", () => ueberspringe("vorlage"));

  // 3. AI

  function zeigeKi() {
    if (!ki) return;
    let zustand = ki.hinweis || "Die KI ist nicht eingerichtet.";
    if (ki.eingerichtet) {
      zustand = ki.vermittlung && ki.budget_usd !== undefined
        ? `Verbunden. Diesen Monat verbraucht: ${usd(ki.verbraucht_usd)} von ${usd(ki.budget_usd)}.`
        : "Verbunden.";
    } else if (ki.einladung) {
      zustand = "Noch nicht verbunden: Einladungscode eingeben.";
    }
    // Without an invitation in this build the notes on an own key and the Claude subscription are the way in.
    const ohneEinladung = !ki.eingerichtet && !ki.einladung;
    const einwilligungOffen = Boolean(ki.einwilligung && !ki.einwilligung.erteilt);
    meldung($("ki-zustand"), ohneEinladung || einwilligungOffen ? "" : zustand, ki.eingerichtet ? "success" : "");
    if (ki.einladung_fehler) meldung($("ki-zustand"), ki.einladung_fehler, "danger");
    $("ki-einwilligung").hidden = !einwilligungOffen;
    if (einwilligungOffen) window.Einwilligung.zeige($("ki-einwilligung"), ki.einwilligung, neu => { ki = neu; zeigeKi(); });
    $("ki-einladung").hidden = ki.eingerichtet || !ki.einladung || einwilligungOffen;
    $("ki-code-hinweis").hidden = ki.eingerichtet || !ki.einladung;
    $("ki-ohne").hidden = ki.eingerichtet;
    $("ki-ohne").open = ohneEinladung || $("ki-ohne").open;
    $("ki-ohne").querySelector("summary").hidden = ohneEinladung;
    $("ki-ueberspringen").hidden = ki.eingerichtet;
    $("ki-weiter").hidden = !ki.eingerichtet;
  }

  async function ladeKi() {
    try { ki = await holen("/api/ki/status"); }
    catch (fehler) { ki = { eingerichtet: false, hinweis: fehler.message }; }
  }

  async function loeseEin() {
    $("ki-einloesen").disabled = true;
    try {
      ki = await senden("/api/ki/einladung", { code: $("ki-code").value });
      $("ki-code").value = "";
      zeigeKi();
      zeigeSchritte("ki");
    } catch (fehler) {
      meldung($("ki-zustand"), fehler.message, "danger");
    } finally {
      $("ki-einloesen").disabled = false;
    }
  }

  $("ki-einloesen").addEventListener("click", loeseEin);
  $("ki-ueberspringen").addEventListener("click", () => ueberspringe("ki"));
  $("ki-weiter").addEventListener("click", () => ueberspringe("ki"));

  // 4. Browser extension (MIN-339): from the store of the own browser (#75, #87, #219), by hand under „Klappt es nicht?“

  function richteStoreEin() {
    const browser = L.browserVon(navigator.userAgent);
    const { haupt, leise } = L.storeKnoepfe(browser);
    const anderer = browser === "andere" ? "Die Erweiterung läuft in Google Chrome und Microsoft Edge. " : "";
    $("erweiterung-store-text").textContent = `${anderer}Im Store auf „${STORE[haupt].knopf}“ klicken, das dauert eine Minute.`;
    $("store-haupt").dataset.store = haupt;
    $("store-haupt").textContent = STORE[haupt].haupt;
    $("store-leise").dataset.store = leise;
    $("store-leise").textContent = STORE[leise].leise;
    $("store-leise-name").textContent = STORE[leise].name;
  }

  function zeigeErweiterung() {
    if (!info?.erweiterung) {
      meldung($("erweiterung-zustand"), "Die Erweiterung gibt es nur in der installierten App.", "warning");
      $("erweiterung-hand").hidden = true;
      $("erweiterung-store").hidden = true;
      $("erweiterung-warten").hidden = true;
      $("erweiterung-weiter").disabled = false;
      return;
    }
    $("erweiterung-ordner").textContent = info.erweiterung.ordner;
    const geladen = erweiterungGeladen();
    $("erweiterung-hand").hidden = Boolean(geladen);
    $("erweiterung-store").hidden = Boolean(geladen);
    $("erweiterung-warten").hidden = Boolean(geladen);
    $("erweiterung-weiter").disabled = !geladen;
    $("erweiterung-spaeter").hidden = Boolean(geladen);
    if (!geladen) {
      meldung($("erweiterung-zustand"), "");
    } else if (erweiterungZustand() === "veraltet") {
      meldung($("erweiterung-zustand"), `Die Erweiterung ist geladen (Version ${geladen}), die App bringt Version ${info.erweiterung.version} mit. Bitte unter chrome://extensions bei der Erweiterung auf „Neu laden“ klicken.`, "warning");
    } else {
      meldung($("erweiterung-zustand"), `Die Erweiterung ist bereit (Version ${geladen}).`, "success");
    }
  }

  async function kopiere(inhalt, knopf) {
    try {
      await navigator.clipboard.writeText(inhalt);
      knopf.textContent = "Kopiert";
      knopf.dataset.copied = "";
    } catch {
      knopf.textContent = "Bitte von Hand kopieren";
    }
  }

  for (const knopf of document.querySelectorAll("button[data-browser]")) {
    knopf.addEventListener("click", async () => {
      try { await senden("/api/app/erweiterungsseite", { browser: knopf.dataset.browser }); }
      catch (fehler) { meldung($("erweiterung-zustand"), fehler.message, "danger"); }
    });
  }
  for (const knopf of document.querySelectorAll("button[data-store]")) {
    knopf.addEventListener("click", async () => {
      try { await senden("/api/app/erweiterung-store", { browser: knopf.dataset.store }); }
      catch (fehler) { meldung($("erweiterung-zustand"), fehler.message, "danger"); }
    });
  }
  for (const knopf of document.querySelectorAll("button[data-kopieren]")) {
    knopf.addEventListener("click", () => kopiere(knopf.dataset.kopieren, knopf));
  }
  $("pfad-kopieren").addEventListener("click", e => kopiere(info?.erweiterung?.ordner || "", e.currentTarget));
  $("ordner-zeigen").addEventListener("click", async () => {
    try { await senden("/api/app/ordner-zeigen", { art: "erweiterung" }); }
    catch (fehler) { meldung($("erweiterung-zustand"), fehler.message, "danger"); }
  });
  $("erweiterung-spaeter").addEventListener("click", () => ueberspringe("erweiterung"));
  $("erweiterung-weiter").addEventListener("click", () => naechster("erweiterung"));
  window.addEventListener("message", event => {
    if (event.source !== window || event.origin !== location.origin || event.data?.quelle !== "bewerbungsbegleiter-erweiterung") return;
    if (aktueller() !== "erweiterung") return zeigeSchritte(aktueller());
    zeigeErweiterung();
    zeigeSchritte("erweiterung");
    if (erweiterungZustand() === "bereit") setTimeout(() => naechster("erweiterung"), 1200);  // „geht es hier von selbst weiter“
  });

  // Done

  function zeigeFertig() {
    const zeile = (titel, inhalt, gut, knopf = null) => el("li", { class: `notice${gut ? " notice--success" : ""}` },
      el("span", { class: "notice__title" }, titel), el("p", { class: "notice__body" }, inhalt),
      knopf ? el("div", { class: "notice__actions" }, el("a", { class: "btn btn--sm", href: knopf.ziel }, knopf.knopf)) : null);
    const geladen = erweiterungGeladen();
    const offen = L.offenePunkte({ kiVerbunden: !info || kiVerbunden(), erweiterungMoeglich: Boolean(info?.erweiterung),
                                   erweiterungGeladen: geladen });
    const ist = id => offen.find(p => p.id === id);
    $("fertig-titel").textContent = L.abschlussTitel(offen);
    $("fertig-text").textContent = offen.length ? "Das fehlt noch. Es lässt sich auch später einrichten." : "";
    $("fertig-text").hidden = !offen.length;
    $("fertig-liste").replaceChildren(...[
      zeile("Gesucht", zusammenfassung(), true),
      info ? zeile("Datenordner", info.datenordner || "", bereit()) : null,
      info ? (ist("ki") ? zeile(ist("ki").titel, ist("ki").text, false, ist("ki")) : zeile("KI", "Verbunden", true)) : null,
      ist("erweiterung") ? zeile(ist("erweiterung").titel, ist("erweiterung").text, false, ist("erweiterung"))
        : geladen ? zeile("Erweiterung", `Geladen, Version ${geladen}`, true) : null,
    ].filter(Boolean));
    $("fertig-weiter").href = info?.lebenslauf ? "/" : "/angaben";
    $("fertig-weiter").textContent = info?.lebenslauf ? "Zur Übersicht" : "Meine Angaben erfassen";
  }

  // Start

  async function start() {
    try {
      info = await holen("/api/app/einrichtung");
    } catch {
      info = null;
      $("nur-installiert").hidden = false;
    }
    if (!info || bereit()) {
      try { wahl = await holen("/api/einrichtung/wahl"); } catch { wahl = null; }
    }
    if (!wahl) wahl = { gesucht: "stelle", anrede: "sie", rav: false, gewaehlt: false };
    if (info) await ladeKi();
    richteStoreEin();
    window.addEventListener("hashchange", zeige);
    zeige();
  }

  start();
})();
