"use strict";
// Gemeinsame Hilfen aller Seiten. Inhalte werden nur als Text eingesetzt (textContent), nie als HTML.
window.App = (() => {
  const DOWNLOAD_BEHALTEN_MS = 600000;
  const NACHSEHEN_MS = 5000;
  // The FAQ (#108); the website renders the same file with GitHub's heading ids, so an anchor works on both.
  const FRAGEN_URL = "https://github.com/minigraphx/bewerbungsassistent/blob/main/docs/fragen.md";
  const TOKEN = document.querySelector('meta[name="token"]').content;
  // The window „KI einrichten“ (G60, #272): an answer with this action, or an address with ?ki=einrichten, opens it.
  const KI_EINRICHTEN = "ki-einrichten";
  const KI_SKRIPTE = [["Texte", "/texte.js"], ["Einwilligung", "/einwilligung.js"], ["KiZugang", "/ki-zugang.js"], ["KiFenster", "/ki-fenster.js"]];

  /** Claude writes into the app while a page is open (MIN-377): look again as long as the page can be seen. */
  function beobachten(nachsehen) {
    const einmal = () => { if (!document.hidden) nachsehen(); };
    setInterval(einmal, NACHSEHEN_MS);
    document.addEventListener("visibilitychange", einmal);
  }

  function url(pfad, parameter = {}) {
    return pfad + "?" + new URLSearchParams({ t: TOKEN, ...parameter });
  }

  async function antwortLesen(antwort) {
    const typ = antwort.headers.get("Content-Type") || "";
    const daten = typ.includes("json") ? await antwort.json() : {};
    if (!antwort.ok) {
      if (daten.aktion === KI_EINRICHTEN) kiEinrichten().catch(() => { /* the message of the page still says it */ });
      const fehler = new Error(daten.fehler || antwort.statusText);
      fehler.status = antwort.status;
      fehler.daten = daten;
      throw fehler;
    }
    return daten;
  }

  async function holen(pfad, parameter = {}) {
    return antwortLesen(await fetch(url(pfad, parameter)));
  }

  async function senden(pfad, body, parameter = {}) {
    const ziel = Object.keys(parameter).length ? pfad + "?" + new URLSearchParams(parameter) : pfad;
    return antwortLesen(await fetch(ziel, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Token": TOKEN },
      body: JSON.stringify(body),
    }));
  }

  // PDF laden und als blob:-Adresse liefern; Fehler des Servers (JSON) kommen als Error mit Meldung.
  // Pro Anzeigeort (ort) wird nur die eigene vorherige Adresse freigegeben.
  const letztePdfs = new Map();
  async function pdfAdresse(pfad, parameter = {}, ort = "standard") {
    const antwort = await fetch(url(pfad, parameter));
    if (!antwort.ok) await antwortLesen(antwort);
    if (!(antwort.headers.get("Content-Type") || "").includes("pdf")) throw new Error("Antwort ist kein PDF");
    const adresse = URL.createObjectURL(await antwort.blob());
    if (letztePdfs.has(ort)) URL.revokeObjectURL(letztePdfs.get(ort));
    letztePdfs.set(ort, adresse);
    return adresse;
  }

  // el("a", {href: "/x", class: "y"}, "Text", kindElement)
  function el(tag, attribute = {}, ...kinder) {
    const e = document.createElement(tag);
    for (const [name, wert] of Object.entries(attribute)) {
      if (wert === false || wert === null || wert === undefined) continue;
      if (name.startsWith("on")) e.addEventListener(name.slice(2), wert);
      else if (name === "class") e.className = wert;
      else e.setAttribute(name, wert === true ? "" : wert);
    }
    for (const kind of kinder.flat()) {
      if (kind === null || kind === undefined || kind === false) continue;
      e.append(kind instanceof Node ? kind : document.createTextNode(String(kind)));
    }
    return e;
  }

  // Every message goes through the one helper (meldungen.js, #215): errors stay until closed, others fade.
  function status(element, text, art = "", optionen = {}) {
    window.Meldungen.zeige(element, text, art, optionen);
  }

  function alsBase64(datei) {
    return new Promise((resolve, reject) => {
      const leser = new FileReader();
      leser.onload = () => resolve(leser.result.split(",")[1] || "");
      leser.onerror = () => reject(new Error(`${datei.name} liess sich nicht lesen.`));
      leser.readAsDataURL(datei);
    });
  }

  function zeitpunkt(iso) {
    return new Date(iso).toLocaleString("de-CH", { dateStyle: "medium", timeStyle: "short" });
  }

  // Box in editors: the newest drafts of the file being edited, with a link to all of them (MIN-303)
  const LETZTE_ENTWUERFE = 3;
  const STELLENINSERAT = /^bewerbungen\/[^/]+\/stelle\.md$/;
  async function letzteEntwuerfe(element, datei) {
    element.dataset.datei = datei;
    // Job ads have no place on Entwürfe und Versionen (#120), so their box links nowhere
    const alle = STELLENINSERAT.test(datei) ? null : el("a", { href: "/entwuerfe?" + new URLSearchParams({ datei }) }, "Alle Entwürfe dieser Datei");
    let inhalt;
    try {
      const { entwuerfe } = await holen("/api/entwuerfe", { datei, anzahl: LETZTE_ENTWUERFE });
      // a «·» line of whole parts (#342, dot-line.js, loaded before this file on every page)
      const eintraege = entwuerfe.map(e => el("li", {}, window.DotLine.render([
        el("time", { datetime: e.zeit }, zeitpunkt(e.zeit)), e.beschreibung || "ohne Beschreibung",
        e.genutzt ? el("span", { class: "leise", title: e.genutzt_fuer.join(", ") }, "versendet") : null], el)));
      inhalt = eintraege.length ? el("ul", {}, eintraege) : el("p", { class: "leer" }, "Noch keine Entwürfe.");
    } catch (fehler) {
      inhalt = el("p", { class: "leise" }, "Entwürfe nicht lesbar: " + fehler.message);
    }
    if (element.dataset.datei !== datei) return;  // another file was chosen meanwhile
    element.replaceChildren(el("h2", {}, "Letzte Entwürfe"), inhalt, alle);
  }

  function datum(iso) {
    if (!iso) return "";
    const [j, m, t] = iso.split("-");
    return `${t}.${m}.${j}`;
  }

  // Zweistufiger Knopf statt confirm(): erster Klick fragt nach, zweiter führt aus
  /** `noetig` says whether there is anything to confirm right now. */
  function bestaetigen(knopf, frage, aktion, noetig = () => true) {
    const text = knopf.textContent;
    let bereit = false;
    knopf.addEventListener("click", async () => {
      if (!noetig()) {
        await aktion();
        return;
      }
      if (!bereit) {
        bereit = true;
        knopf.textContent = frage;
        setTimeout(() => { bereit = false; knopf.textContent = text; }, 4000);
        return;
      }
      bereit = false;
      knopf.textContent = text;
      await aktion();
    });
  }

  // Text set from the setup (MIN-369): the pages fill their data-text elements, the menu names the search.
  // Without the route (or before a choice) the page keeps the words it was written with: a job, Sie.
  let wahl = holen("/api/einrichtung/wahl").catch(() => null);
  /** After the setup stored a new choice: what follows, such as the window „KI einrichten“, speaks in its set. */
  function wahlNeuLaden() {
    wahl = holen("/api/einrichtung/wahl").catch(() => null);
    return wahl;
  }
  async function textsatz() {
    const gewaehlt = await wahl;
    return gewaehlt ? gewaehlt.textsatz : "stelle-sie";
  }
  textsatz().then(satz => {
    document.documentElement.dataset.textsatz = satz;
    window.Texte?.anwenden(document, satz);
  });

  // „Zurück“: zur vorherigen Seite der App (behält dort Sortierung und Scrollposition), sonst zur Übersicht
  function zurueck() {
    const knopf = document.getElementById("zurueck");
    if (!knopf) return;
    knopf.addEventListener("click", e => {
      let intern = false;
      try { intern = new URL(document.referrer).origin === location.origin; } catch { /* kein Referrer */ }
      if (intern && history.length > 1) {
        e.preventDefault();
        history.back();
      }
    });
  }
  zurueck();

  // Until a data folder is chosen (or when it is gone), every page leads to the setup, with a request for the window
  // „KI einrichten“; true when it leaves.
  async function zurEinrichtung() {
    if (location.pathname === "/einrichtung") return false;
    try {
      const info = await holen("/api/app/einrichtung");
      if (!info.eingerichtet || info.fehlt) {
        location.replace("/einrichtung" + location.search);
        return true;
      }
      if (info.gewechselt) location.reload();  // the folder is back: show its data, not the placeholder's
    } catch { /* plain app without setup */ }
    return false;
  }

  function ladeSkript(src) {
    return new Promise((resolve, reject) => {
      document.head.append(el("script", { src, onload: resolve, onerror: () => reject(new Error(`${src} liess sich nicht laden.`)) }));
    });
  }

  /** Opens the window „KI einrichten“ over the page, loading its scripts once; resolves with the AI status it closed with. */
  async function kiEinrichten() {
    for (const [name, src] of KI_SKRIPTE) {
      if (!window[name]) await ladeSkript(src);
    }
    return window.KiFenster.oeffnen();
  }

  /** Did the address ask for the window (an invitation link)? The request leaves the address, so a reload asks no more. */
  function kiAnfrageNehmen() {
    const suche = new URLSearchParams(location.search);
    if (suche.get("ki") !== "einrichten") return false;
    suche.delete("ki");
    const rest = suche.toString();
    history.replaceState(history.state, "", location.pathname + (rest ? `?${rest}` : "") + location.hash);
    return true;
  }

  // The setup page takes the request itself: before the data folder there is nowhere to keep the consent.
  function kiAusAdresse() {
    if (location.pathname === "/einrichtung" || !kiAnfrageNehmen()) return;
    kiEinrichten().catch(() => { /* without its scripts the page stays as it is */ });
  }

  // The browser chosen for the app did not start (G99, #369): desktop/app_browser.py opened the default browser
  // instead and added this parameter. The request leaves the address, so a reload shows no notice again.
  const BROWSER_FEHLT = "browser-fehlt";
  const BROWSER_NAMEN = { chrome: "Google Chrome", edge: "Microsoft Edge" };
  function browserFehltNehmen() {
    const suche = new URLSearchParams(location.search);
    if (!suche.has(BROWSER_FEHLT)) return null;
    const browser = suche.get(BROWSER_FEHLT);
    suche.delete(BROWSER_FEHLT);
    const rest = suche.toString();
    history.replaceState(history.state, "", location.pathname + (rest ? `?${rest}` : "") + location.hash);
    return Object.hasOwn(BROWSER_NAMEN, browser) ? BROWSER_NAMEN[browser] : null;
  }

  function browserHinweis() {
    const name = browserFehltNehmen();
    if (!name) return;
    const schliessen = el("button", { type: "button", class: "status__close", "aria-label": "Meldung schliessen" }, "×");
    const hinweis = el("div", { class: "notice notice--warning", role: "status" },
      el("p", { class: "notice__body" }, `${name} liess sich nicht starten, darum ist die App im Standardbrowser offen. `
        + "Der Browser für die App lässt sich unter Einstellungen, Browser und Erweiterung wählen."),
      el("div", { class: "notice__actions" }, el("a", { class: "btn btn--sm", href: "/einstellungen#browser" }, "Zu den Einstellungen"),
        schliessen));
    schliessen.addEventListener("click", () => hinweis.remove());
    document.querySelector("main")?.prepend(hinweis);
  }

  // "About the app" under Einstellungen (#81, G54): the AS logo marks the author; name and app icon stay as they are.
  // In the Store package (#344) the Store brings updates, so the app offers none and says so here only.
  function ueberDieApp(version, store) {
    return el("div", { class: "about" },
      el("img", { class: "about__logo", src: "/as-logo.svg", width: "40", height: "40", alt: "Logo AS" }),
      el("div", {},
        el("p", { class: "about__name" }, "Bewerbungsbegleiter"),
        el("p", { class: "about__meta version" }, `Version ${version}`),
        el("p", { class: "about__meta" }, "von Andreas Schmidt"),
        store ? el("p", { class: "about__meta" }, "Updates kommen über den Microsoft Store.") : updateSuche()));
  }

  // «Nach Updates suchen» (#370, G100): the server at once, with the result in a live line under the button. The button
  // stays focusable while it checks (aria-disabled), and a check without an answer in time counts as failed.
  const UPDATE_SUCHE_MS = 10000;
  const ANSAGE_PAUSE_MS = 100;  // an emptied live line, then the text: screen readers announce a repeated result
  const UPDATE_SUCHE_FEHLER = "Die Suche nach Updates hat nicht geklappt. Vielleicht fehlt die Internetverbindung; bitte später nochmals versuchen.";

  function mitFrist(versprechen, ms) {
    let uhr;
    const frist = new Promise((_, reject) => { uhr = setTimeout(() => reject(new Error(UPDATE_SUCHE_FEHLER)), ms); });
    return Promise.race([versprechen, frist]).finally(() => clearTimeout(uhr));
  }

  function zeitJetzt() {
    return new Date().toLocaleTimeString("de-CH", { hour: "2-digit", minute: "2-digit" });
  }

  function sucheErgebnis(antwort) {
    if (antwort.update) {
      const meldung = el("span", {}, updateText(antwort.update).trim());
      const knopf = updateKnopf(antwort.update, "Jetzt aktualisieren");
      if (antwort.update.automatisch) knopf.addEventListener("click", () => installieren(knopf, meldung));
      return [meldung, " ", knopf];
    }
    const beta = antwort.vorabversionen ? " Vorabversionen eingeschlossen." : "";
    return [`Version ${antwort.version} ist die neueste. Geprüft um ${zeitJetzt()}.${beta}`];
  }

  function updateSuche() {
    const knopf = el("button", { type: "button", class: "btn", "aria-describedby": "update-suche" }, "Nach Updates suchen");
    const zeile = el("p", { id: "update-suche", class: "status-line", role: "status", "aria-live": "polite" });
    let schreiben = null;
    let lauf = 0;
    const zeige = (teile, warnung = false) => {
      clearTimeout(schreiben);
      zeile.replaceChildren();
      zeile.removeAttribute("data-level");
      schreiben = setTimeout(() => {
        if (warnung) zeile.setAttribute("data-level", "warning");
        zeile.replaceChildren(...teile);
      }, ANSAGE_PAUSE_MS);
    };
    knopf.addEventListener("click", async () => {
      if (knopf.getAttribute("aria-disabled") === "true") return;
      const dieser = ++lauf;
      knopf.setAttribute("aria-disabled", "true");
      zeige(["Sucht nach Updates …"]);
      try {
        const antwort = await mitFrist(senden("/api/app/updates-suchen", {}), UPDATE_SUCHE_MS);
        if (dieser === lauf) zeige(sucheErgebnis(antwort));
      } catch {
        if (dieser !== lauf) return;
        zeige([UPDATE_SUCHE_FEHLER], true);
        if (!document.activeElement || document.activeElement === document.body) knopf.focus();
      } finally {
        if (dieser === lauf) knopf.removeAttribute("aria-disabled");
      }
    });
    return el("div", { class: "about__update" }, knopf, zeile);
  }

  // A new version (#32, G8): the first page after a start asks in a dialog; after "later" a banner stays for this run.
  function updateText(update) {
    const zeitpunkt = update.beimBeenden ? "Sie wird beim Beenden installiert, oder gleich hier. " : "";
    return `Version ${update.version} ist verfügbar. ${zeitpunkt}${update.hinweis || ""} `;
  }

  // Dialog, banner and «Nach Updates suchen» may all offer the update: one install at a time, and all their buttons
  // follow it.
  const installKnoepfe = new Set();
  let installLaeuft = false;

  async function installieren(knopf, meldung) {
    if (installLaeuft) {
      meldung.textContent = "Das Update läuft schon. ";
      return false;
    }
    installLaeuft = true;
    installKnoepfe.forEach(k => { k.disabled = true; });
    meldung.textContent = "Neue Version wird geladen und geprüft …";
    try {
      await senden("/api/app/aktualisieren", {});
      meldung.textContent = "Die neue Version wird installiert und öffnet sich danach selbst in einem neuen Tab. Dieser Tab lässt sich dann schliessen.";
      installKnoepfe.forEach(k => k.remove());
      return true;
    } catch (fehler) {
      meldung.textContent = fehler.message + " ";
      installKnoepfe.forEach(k => { k.disabled = false; });
      installLaeuft = false;
      return false;
    }
  }

  // Without a self-update the person loads the new version from its page.
  function updateKnopf(update, beschriftung) {
    if (!update.automatisch) return el("a", { href: update.seite, target: "_blank", rel: "noopener" }, "Neue Version herunterladen");
    const knopf = el("button", { type: "button", class: "haupt" }, beschriftung);
    knopf.disabled = installLaeuft;
    installKnoepfe.add(knopf);
    return knopf;
  }

  function updateBanner(update) {
    const meldung = el("span", {}, updateText(update));
    const knopf = updateKnopf(update, "Jetzt aktualisieren");
    if (update.automatisch) knopf.addEventListener("click", () => installieren(knopf, meldung));
    document.querySelector("main")?.prepend(el("div", { class: "banner", role: "status" }, meldung, knopf));
  }

  function updateDialog(update) {
    const meldung = el("p", { class: "dialog__text", id: "update-text" }, updateText(update));
    const spaeter = el("button", { type: "button", class: "btn" }, "Später");
    const knopf = updateKnopf(update, "Installieren");
    knopf.classList.add("btn", "btn--primary");
    const dialog = el("dialog", { class: "dialog", id: "update-dialog", "aria-labelledby": "update-titel", "aria-describedby": "update-text" },
      el("h2", { class: "dialog__title", id: "update-titel" }, "Neue Version verfügbar"),
      meldung, el("div", { class: "dialog__actions" }, spaeter, knopf));
    let entschieden = false;
    const verschieben = async () => {
      entschieden = true;
      dialog.close();
      dialog.remove();
      try { await senden("/api/app/spaeter", {}); } catch { /* then the next page asks once more */ }
      updateBanner(update);
    };
    spaeter.addEventListener("click", verschieben);
    if (update.automatisch) {
      knopf.addEventListener("click", async () => {
        entschieden = true;
        spaeter.disabled = true;
        if (await installieren(knopf, meldung)) spaeter.remove();
        else entschieden = spaeter.disabled = false;
      });
    } else {
      knopf.addEventListener("click", verschieben);  // the download page opens in its own tab
    }
    dialog.addEventListener("cancel", event => event.preventDefault());  // Escape does not choose
    // Browsers may still close it on a repeated Escape; that counts as "later", never as a silent dismissal.
    dialog.addEventListener("close", () => { if (!entschieden) verschieben(); });
    document.body.append(dialog);
    dialog.showModal();
  }

  // Packaged app only (G36): the app quits a minute after its last page went. Each page says it is here and says
  // goodbye with keepalive, which outlives the page and, unlike sendBeacon, carries the token header.
  const DA_MS = 20000;
  function anwesend() {
    const seite = crypto.randomUUID();
    const melden = (pfad, keepalive = false) => fetch(pfad, {
      method: "POST", keepalive,
      headers: { "Content-Type": "application/json", "X-Token": TOKEN },
      body: JSON.stringify({ seite }),
    }).catch(() => { /* the app is gone or busy; the next heartbeat tries again */ });
    const da = () => melden("/api/app/da");
    da();
    setInterval(da, DA_MS);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) da(); });
    window.addEventListener("pageshow", event => { if (event.persisted) da(); });
    window.addEventListener("pagehide", () => melden("/api/app/weg", true));
  }

  // Packaged app only (MIN-342): the offer of a new version, button to quit. The plain app has no such route.
  async function desktop() {
    let info;
    try { info = await holen("/api/app/version"); } catch { kiAusAdresse(); return; }
    anwesend();
    const ort = document.getElementById("ueber-die-app");
    if (ort) {
      const beenden = el("button", { type: "button", class: "beenden" }, "Beenden");
      bestaetigen(beenden, "Wirklich beenden?", async () => {
        let ergebnis = {};
        try { ergebnis = await senden("/api/app/beenden", {}); } catch { /* already gone */ }
        document.body.replaceChildren(ergebnis.aktualisiert
          ? el("main", {}, el("h1", {}, "Bewerbungsbegleiter wird aktualisiert"),
            el("p", {}, `Version ${ergebnis.aktualisiert} wird im Hintergrund geladen und installiert, danach beendet sich die App. Dieses Fenster lässt sich jetzt schliessen. Beim nächsten Start läuft die neue Version.`))
          : el("main", {}, el("h1", {}, "Bewerbungsbegleiter beendet"),
            el("p", {}, "Dieses Fenster lässt sich jetzt schliessen. Die App startet wieder mit einem Doppelklick.")));
      });
      ort.append(ueberDieApp(info.version, info.store), el("div", { class: "knoepfe" }, beenden));
      ort.hidden = false;
      document.getElementById("ueber-link")?.removeAttribute("hidden");
    }
    if (await zurEinrichtung()) return;
    browserHinweis();
    kiAusAdresse();
    if (!info.update) return;
    if (info.update.fragen) updateDialog(info.update);
    else updateBanner(info.update);
  }
  desktop();

  // Backup (MIN-359): it counts as done only when writing worked, or when the person says the download arrived.
  async function holeSicherung() {
    const antwort = await fetch(url("/api/sicherung/datei"));
    if (!antwort.ok) await antwortLesen(antwort);
    return antwort.blob();
  }

  async function schreibeSicherung(griff) {
    try {
      const schreiben = await griff.createWritable();
      await schreiben.write(await holeSicherung());
      await schreiben.close();
    } catch (fehler) {
      await griff.remove?.().catch(() => {});  // choosing the place left an empty file, it must not look like a backup
      throw fehler;
    }
  }

  function ladeSicherungHerunter(inhalt, name) {
    const adresse = URL.createObjectURL(inhalt);
    el("a", { href: adresse, download: name }).click();
    setTimeout(() => URL.revokeObjectURL(adresse), DOWNLOAD_BEHALTEN_MS);  // the browser reads it after the click
  }

  function sicherungsMeldung(art, inhalt, optionen = {}) {
    let zeile = document.getElementById("sicherung-meldung");
    if (!zeile) {
      zeile = el("p", { id: "sicherung-meldung", class: "status", role: "status" });
      document.querySelector("main")?.prepend(zeile);
    }
    status(zeile, inhalt, art, optionen);
  }

  async function sicherungGespeichert(datei) {
    await senden("/api/sicherung/erledigt", {});
    document.getElementById("sicherung-hinweis")?.remove();
    sicherungsMeldung("ok", `Sicherung erstellt: ${datei}. Am besten auf einem USB-Stick ablegen; zum Wiederherstellen entpacken und den Ordner in der App wählen.`);
  }

  // Without the dialog the page cannot know whether the download arrived, so the person says so.
  async function sicherungAlsDownload(datei) {
    ladeSicherungHerunter(await holeSicherung(), datei);
    sicherungsMeldung("", `Der Browser lädt ${datei} herunter.`, { aktion: { text: "Datei ist gespeichert", ausfuehren: () =>
      sicherungGespeichert(datei).catch(fehler => sicherungsMeldung("fehler", fehler.message)) } });
  }

  async function erstelleSicherung() {
    try {
      const { datei } = await holen("/api/sicherung/stand");
      if (!window.showSaveFilePicker) {
        sicherungsMeldung("", "Sicherung wird erstellt …");
        await sicherungAlsDownload(datei);
        return;
      }
      const griff = await window.showSaveFilePicker({ suggestedName: datei,
        types: [{ description: "ZIP-Datei", accept: { "application/zip": [".zip"] } }] });
      sicherungsMeldung("", "Sicherung wird erstellt …");
      await schreibeSicherung(griff);
      await sicherungGespeichert(datei);
    } catch (fehler) {
      if (fehler.name === "AbortError") document.getElementById("sicherung-meldung")?.remove();  // cancelled in the dialog
      else sicherungsMeldung("fehler", fehler.message);
    }
  }

  // Under Einstellungen, Daten und Sicherung (G54); the overview offers it as well when one is due.
  function sicherungKnopf() {
    document.getElementById("daten-knoepfe")?.prepend(el("button", { type: "button", onclick: erstelleSicherung }, "Sicherung erstellen"));
  }
  sicherungKnopf();

  // A calm hint in the overview only, and nothing at all when the question fails.
  async function sicherungHinweis() {
    if (location.pathname !== "/") return;
    let stand;
    try { stand = await holen("/api/sicherung/stand"); } catch { return; }
    if (!stand.faellig) return;
    const text = stand.zuletzt ? `Die letzte Sicherung ist vom ${datum(stand.zuletzt)}. ` : "Für diese Daten gibt es noch keine Sicherung. ";
    document.querySelector("main")?.prepend(el("p", { id: "sicherung-hinweis", class: "banner", role: "status" }, text,
      el("button", { type: "button", onclick: erstelleSicherung }, "Sicherung erstellen")));
  }
  sicherungHinweis();

  /** A link to one question of the FAQ; `anker` is the GitHub id of its heading. */
  function fragenLink(anker, text) {
    return el("a", { href: `${FRAGEN_URL}#${anker}`, target: "_blank", rel: "noopener" }, text);
  }

  return { url, holen, senden, el, status, alsBase64, datum, zeitpunkt, bestaetigen, pdfAdresse, letzteEntwuerfe, beobachten,
           wahl: () => wahl, wahlNeuLaden, textsatz, fragenLink, kiEinrichten, kiAnfrageNehmen };
})();
