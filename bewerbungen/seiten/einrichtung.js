"use strict";
// Setup of the packaged app (MIN-342), in five steps (MIN-369): what is sought (job or apprenticeship, form of
// address, RAV), data folder, einstieg file, AI invitation, browser extension. Each step is a section; the hash
// says which one is shown, so the browser's back button works. Folder and file are chosen in the system's own
// dialog; the server reads the file from disk. The choice of the first step is stored in the data folder, so before
// a folder exists the page keeps it (sessionStorage) and stores it right after the folder.
(() => {
  const { holen, senden, el } = window.App;
  const { text, anwenden } = window.Texte;
  const $ = id => document.getElementById(id);
  const usd = wert => `${Number(wert || 0).toFixed(2)} USD`;

  const SCHRITTE = [
    { id: "gesucht", titel: "Gesucht" },
    { id: "datenordner", titel: "Datenordner" },
    { id: "vorlage", titel: "Datei" },
    { id: "ki", titel: "KI" },
    { id: "erweiterung", titel: "Erweiterung" },
  ];
  const SPEICHER = "bewerbungsassistent-einrichtung";

  let info = null;         // /api/app/einrichtung; null in the plain app without setup
  let wahl = null;         // /api/einrichtung/wahl, or what the page keeps until there is a folder
  let ki = null;           // /api/ki/status
  let importiert = false;
  let ravBeruehrt = false; // the default for RAV follows the choice until the person picks one
  const sitzung = ladeSitzung();  // { wahl, bestaetigt, uebersprungen: {vorlage, ki, erweiterung} }

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

  function meldung(element, inhalt, stufe = "") {
    element.textContent = inhalt;
    if (stufe) element.dataset.level = stufe;
    else delete element.dataset.level;
  }

  // State of the steps

  const bereit = () => Boolean(info && info.eingerichtet && !info.fehlt);
  const kiVerbunden = () => Boolean(ki && ki.eingerichtet);
  const erweiterungGeladen = () => document.documentElement.dataset.bewerbungsbegleiterErweiterung || "";
  const erweiterungZustand = () => window.EinrichtungLogik.erweiterungZustand(erweiterungGeladen(), info?.erweiterung?.version,
                                                                             "bewerbungsbegleiterEntpackt" in document.documentElement.dataset);
  const satz = () => wahl ? (wahl.gesucht === "lehrstelle" ? "lehrstelle-du" : `stelle-${wahl.anrede}`) : "stelle-sie";

  function erledigt(id) {
    switch (id) {
      case "gesucht": return Boolean(wahl && (wahl.gewaehlt || sitzung.bestaetigt));
      case "datenordner": return bereit();
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
      case "datenordner": return bereit() ? ordnerName(info.datenordner) : "Dokumente";
      case "vorlage": return info?.lebenslauf || importiert ? "übernommen" : sitzung.uebersprungen.vorlage ? "übersprungen" : "freiwillig";
      case "ki": return kiVerbunden() ? "verbunden" : sitzung.uebersprungen.ki ? "übersprungen" : "Einladungscode";
      case "erweiterung":
        if (!info?.erweiterung) return "nur in der installierten App";
        return erweiterungGeladen() ? "geladen" : sitzung.uebersprungen.erweiterung ? "später" : "1 bis 2 Minuten";
      default: return "";
    }
  }

  const sichtbareSchritte = () => info ? SCHRITTE : SCHRITTE.slice(0, 1);  // the plain app only knows the choice
  const ersterOffener = () => sichtbareSchritte().find(s => !erledigt(s.id))?.id || "fertig";

  function erreichbar(id) {
    if (id === "gesucht") return true;
    if (!info) return id === "fertig" && erledigt("gesucht");
    if (bereit()) return true;  // with a folder every step can be visited again
    const ids = SCHRITTE.map(s => s.id);
    return ids.indexOf(id) !== -1 && ids.indexOf(id) <= ids.indexOf(ersterOffener());
  }

  function aktueller() {
    const gewuenscht = location.hash.slice(1);
    return gewuenscht && erreichbar(gewuenscht) ? gewuenscht : ersterOffener();
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
    if (jetzt === "gesucht") zeigeWahl();
    if (jetzt === "datenordner") zeigeOrdner();
    if (jetzt === "vorlage") zeigeVorlage();
    if (jetzt === "ki") zeigeKi();
    if (jetzt === "erweiterung") zeigeErweiterung();
    if (jetzt === "fertig") zeigeFertig();
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
    if (!ravBeruehrt) document.querySelector(`input[name=rav][value=${gesucht === "lehrstelle" ? "nein" : "ja"}]`).checked = true;
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
    delete sitzung.wahl;
    merke();
  }

  async function bestaetigeWahl() {
    const werte = gewaehlteWahl();
    $("gesucht-weiter").disabled = true;
    try {
      if (!info || bereit()) {
        await speichereWahl(werte);
      } else {
        wahl = { ...werte, gewaehlt: false };  // stored with the folder
        sitzung.wahl = werte;
      }
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

  // 2. Data folder

  let ordnerAngezeigt = false;

  function ordnerKnopf() {
    const gleich = bereit() && $("ordner").value.trim() === info.datenordner;
    $("ordner-uebernehmen").textContent = gleich ? "Weiter" : "Ordner anlegen und weiter";
  }

  function zeigeOrdner() {
    if (!info) return;
    if (!ordnerAngezeigt) {
      $("ordner").value = info.datenordner || info.vorschlag;
      ordnerAngezeigt = true;
    }
    $("ordner-fehlt").hidden = !info.fehlt;
    $("ordner-fehlt").textContent = info.fehlt
      ? `Der Datenordner ${info.datenordner} wurde nicht gefunden (z.B. USB-Stick nicht eingesteckt). Sobald er wieder verfügbar ist, diese Seite neu laden; oder einen anderen Ordner wählen.`
      : "";
    if (bereit()) meldung($("ordner-status"), `Datenordner: ${info.datenordner}`, "success");
    ordnerKnopf();
  }

  async function pruefeOrdner() {
    const pfad = $("ordner").value.trim();
    ordnerKnopf();
    if (!pfad || (bereit() && pfad === info.datenordner)) return;
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

  async function uebernehmeOrdner() {
    if (bereit() && $("ordner").value.trim() === info.datenordner) return naechster("datenordner");
    $("ordner-uebernehmen").disabled = true;
    try {
      info = await senden("/api/app/datenordner", { pfad: $("ordner").value });
      // The choice belongs into the new folder; a folder that already has one keeps it unless one was just made.
      if (sitzung.wahl) await speichereWahl(sitzung.wahl);
      else wahl = await holen("/api/einrichtung/wahl");
      naechster("datenordner");
    } catch (fehler) {
      meldung($("ordner-status"), fehler.message, "danger");
    } finally {
      $("ordner-uebernehmen").disabled = false;
    }
  }

  $("ordner").addEventListener("input", ordnerKnopf);
  $("ordner").addEventListener("change", pruefeOrdner);
  $("ordner-waehlen").addEventListener("click", () => waehle("ordner", "ordner", "ordner-status", pruefeOrdner));
  $("ordner-uebernehmen").addEventListener("click", uebernehmeOrdner);

  // 3. Einstieg file

  function zeigeImport(ergebnis) {
    const zeilen = [
      ...ergebnis.geschrieben.map(datei => el("li", { "data-stufe": "ok" }, `Angelegt: ${datei}`)),
      ...(ergebnis.unveraendert || []).map(datei => el("li", { "data-stufe": "hinweis" },
        `Unverändert gelassen: ${datei}. Die Datei lässt sich nicht lesen; zu ändern unter „Inhalte als Text“.`)),
      ergebnis.dokumente.length ? el("li", { "data-stufe": "ok" }, `${ergebnis.dokumente.length} Dokument(e) abgelegt`) : null,
      ergebnis.unvollstaendig ? el("li", { "data-stufe": "hinweis" }, text("einrichtung.vorlage.unvollstaendig", satz())) : null,
    ];
    $("import-ergebnis").replaceChildren(...zeilen.filter(Boolean));
  }

  async function importiere(ersetzen = false) {
    $("ersetzen").hidden = true;
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
      $("ersetzen").hidden = !vorhanden;
    }
  }

  function zeigeVorlage() {
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
  $("importieren").addEventListener("click", () => importiere(false));
  $("ersetzen").addEventListener("click", () => importiere(true));
  $("vorlage-ueberspringen").addEventListener("click", () => ueberspringe("vorlage"));
  $("vorlage-weiter").addEventListener("click", () => ueberspringe("vorlage"));

  // 4. AI

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

  // 5. Browser extension (MIN-339): from the Chrome or Edge store (#75, #87), by hand as developer add-on otherwise

  function zeigeErweiterung() {
    if (!info?.erweiterung) {
      meldung($("erweiterung-zustand"), "Die Erweiterung gibt es nur in der installierten App.", "warning");
      $("erweiterung-schritte").hidden = true;
      $("erweiterung-warten").hidden = true;
      $("erweiterung-weiter").disabled = false;
      return;
    }
    $("erweiterung-ordner").textContent = info.erweiterung.ordner;
    const geladen = erweiterungGeladen();
    $("erweiterung-schritte").hidden = Boolean(geladen);
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
    const zeile = (titel, inhalt, gut) => el("li", { class: `notice${gut ? " notice--success" : ""}` },
      el("span", { class: "notice__title" }, titel), el("p", { class: "notice__body" }, inhalt));
    const geladen = erweiterungGeladen();
    $("fertig-liste").replaceChildren(
      zeile("Gesucht", zusammenfassung(), true),
      zeile("Datenordner", info?.datenordner || "", bereit()),
      zeile("KI", kiVerbunden() ? "Verbunden" : "Ohne KI, lässt sich später einrichten", kiVerbunden()),
      zeile("Erweiterung", geladen ? `Geladen, Version ${geladen}` : "Noch nicht geladen, lässt sich später einrichten", Boolean(geladen)),
    );
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
    if (sitzung.wahl && !(wahl && wahl.gewaehlt)) wahl = { ...sitzung.wahl, gewaehlt: false };
    if (!wahl) wahl = { gesucht: "stelle", anrede: "sie", rav: true, gewaehlt: false };
    if (info) await ladeKi();
    window.addEventListener("hashchange", zeige);
    zeige();
  }

  start();
})();
