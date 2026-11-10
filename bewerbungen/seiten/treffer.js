"use strict";
// Hits of the job search (MIN-339): list, rate with the AI in packages (MIN-372), take over into the register, discard.
// The search itself runs in the browser extension; this page starts it through app-bridge.js.
(() => {
  const { holen, senden, el, status, datum, beobachten, textsatz } = window.App;
  const logik = window.TrefferLogik;
  const { text: textAus, anwenden } = window.Texte;
  const EINSTELLEN_OFFEN = "suche.einstellen";  // remembered per browser: whether the settings stay open
  const $ = id => document.getElementById(id);
  const SEITE = "bewerbungsbegleiter-seite";
  const ERWEITERUNG = "bewerbungsbegleiter-erweiterung";

  let alle = [];
  let gezeigt = "";  // the hits as last loaded, to see whether Claude changed them
  let einstellungen = { auto_bewerten: true, zuschauen: false, beruf_sterne: {}, sortierung: "note" };
  let paket = 10;
  let grenze = 30;
  let lehrstelle = false;
  let bewertungslauf = null;  // { halt: bool } while a run is going
  let letzterSuchlauf = "";
  let wartetSeit = null;     // ISO time since the page waits for a search, to tell its run from older ones
  let stille = null;         // timer: no word from the extension for a while
  let zustand = "neu";       // which hits the list shows
  let gewaehlt = null;       // id of the hit in the detail column
  let firmen = new Map();    // hit id → its company with what kununu says (#190)
  let heute = "";
  let satz = "stelle-sie";
  const t = (schluessel, werte) => textAus(schluessel, satz, werte);
  const zeile = (element, inhalt, stufe = "", optionen = {}) => window.Meldungen.zeige(element, inhalt, stufe, optionen);
  const meldung = (inhalt, stufe) => zeile($("status"), inhalt, stufe);

  function anzeigen(treffer) {
    alle = alle.map(t => (t.id === treffer.id ? treffer : t));
    zeigeListe();
  }

  async function bewerte(t, knopf) {
    if (knopf) knopf.disabled = true;
    meldung(`KI bewertet „${t.stelle}“ …`);
    try {
      anzeigen(await senden("/api/suche/bewerten", {}, { id: t.id }));
      meldung("");
      return true;
    } catch (fehler) {
      meldung(`${t.stelle}: ${fehler.message}`, "fehler");
      if (knopf) knopf.disabled = false;
      return false;
    }
  }

  async function uebernimm(t, knopf) {
    knopf.disabled = true;
    try {
      const neu = await senden("/api/suche/uebernehmen", {}, { id: t.id });
      anzeigen(neu);
      meldung(`„${t.stelle}“ ist jetzt im Register.`, "ok");
    } catch (fehler) {
      meldung(fehler.message, "fehler");
      knopf.disabled = false;
      lade();
    }
  }

  async function verwirf(t, zurueck) {
    try {
      anzeigen(await senden("/api/suche/verwerfen", { zurueck }, { id: t.id }));
    } catch (fehler) {
      meldung(fehler.message, "fehler");
    }
  }

  function liste(titel, eintraege) {
    return eintraege && eintraege.length ? el("div", {}, el("h3", {}, titel), el("ul", {}, eintraege.map(e => el("li", {}, e)))) : null;
  }

  const notenText = window.Texte.notenText;
  const notenWort = n => (n >= 5.5 ? "passt sehr gut" : n >= 4.5 ? "passt gut" : n >= 4 ? "passt knapp" : "passt wenig");

  /** Grade as in the design: value, six bars, a word; a name when there are two (apprenticeships). */
  function note(wert, { name = "", unsicher = false, klein = true, wort = !klein } = {}) {
    const balken = [1, 2, 3, 4, 5, 6].map(k => el("i", { class: wert >= k ? "on" : wert >= k - 0.5 ? "half" : "" }));
    const span = el("span", { class: `grade-meter${klein ? " grade-meter--sm" : ""}`, "aria-label": `${name ? name + ": " : ""}Note ${wert} von 6, ${notenWort(wert)}${unsicher ? ", unsicher" : ""}` },
      name ? el("span", { class: "search__grade-name", "aria-hidden": "true" }, name) : null,
      el("span", { class: "grade-meter__value" }, notenText(wert)),
      el("span", { class: "grade-meter__bar", "aria-hidden": "true" }, balken),
      wort ? el("span", { class: "grade-meter__word", "aria-hidden": "true" }, notenWort(wert)) : null);
    if (unsicher) span.dataset.uncertain = "";
    return span;
  }

  function noten(treffer, optionen = {}) {
    const b = treffer.bewertung;
    if (!b) return [el("span", { class: "search__hint" }, "noch keine Note")];
    const unsicher = Boolean(b.unsicher);
    if (lehrstelle && b.beruf_note) return [note(b.beruf_note, { name: "Beruf", ...optionen }), note(b.note, { name: "Lehrstelle", unsicher, ...optionen })];
    return [note(b.note, { unsicher, ...optionen })];
  }

  function aktionen(treffer) {
    if (treffer.zustand === "uebernommen") {
      return [el("a", { class: "btn btn--primary", href: "/bewerbung?" + new URLSearchParams({ id: treffer.bewerbung_id }) }, "Zur Bewerbung")];
    }
    if (treffer.zustand === "verworfen") {
      return [el("button", { type: "button", class: "btn", onclick: () => verwirf(treffer, true) }, "Zurückholen")];
    }
    const b = treffer.bewertung;
    const empfohlen = b && b.note >= 4;
    const uebernehmen = el("button", { type: "button", class: empfohlen ? "btn btn--primary" : "btn" }, b && !empfohlen ? "Trotzdem übernehmen" : "Übernehmen");
    uebernehmen.addEventListener("click", () => uebernimm(treffer, uebernehmen));
    const bewerten = el("button", { type: "button", class: "btn btn--quiet", disabled: bewertungslauf !== null }, b ? "Neu bewerten" : "Bewerten");
    bewerten.addEventListener("click", () => bewerte(treffer, bewerten));
    return [uebernehmen, el("button", { type: "button", class: "btn btn--quiet", onclick: () => verwirf(treffer, false) }, "Verwerfen"), bewerten];
  }

  function inseratKnopf(treffer) {
    const textFeld = el("pre", { class: "inserat", hidden: true });
    const knopf = el("button", { type: "button", class: "btn btn--sm" }, "Inserat hier lesen");
    knopf.addEventListener("click", async () => {
      if (textFeld.hidden && !textFeld.textContent) {
        try { textFeld.textContent = (await holen("/api/suche/text", { id: treffer.id })).text || "Kein Text gespeichert."; }
        catch (fehler) { textFeld.textContent = fehler.message; }
      }
      textFeld.hidden = !textFeld.hidden;
      knopf.textContent = textFeld.hidden ? "Inserat hier lesen" : "Inserat verbergen";
    });
    return [knopf, textFeld];
  }

  function zeigeDetail(treffer) {
    if (!treffer) return $("detail").replaceChildren();
    const b = treffer.bewertung;
    const rahmen = [treffer.ort, treffer.pensum || treffer.lehrbeginn].filter(Boolean).join(" · ");
    const weitere = (treffer.weitere || []).map(w => el("li", {}, el("a", { href: w.link, target: "_blank", rel: "noopener" }, `Auch auf ${w.portal}`)));
    const [knopf, textFeld] = inseratKnopf(treffer);
    $("detail").replaceChildren(...[
      el("div", { class: "search__detail-head" },
        el("h2", { id: "detail-titel" }, treffer.stelle),
        el("p", {}, [treffer.firma, rahmen].filter(Boolean).join(", ")),
        el("p", { class: "search__hint" }, el("a", { href: treffer.link, target: "_blank", rel: "noopener" }, `Inserat auf ${treffer.portal} öffnen`),
          ` · gefunden ${datum(treffer.gefunden_am)}`, treffer.alter_tage !== undefined ? ` · ${treffer.alter_tage} ${treffer.alter_tage === 1 ? "Tag" : "Tage"} online` : ""),
        eigeneSterne(treffer)),
      treffer.hinweis ? el("div", { class: "notice" }, el("span", { class: "notice__title" }, "Schon im Register"), el("p", { class: "notice__body" }, treffer.hinweis)) : null,
      treffer.vorpruefung ? el("div", { class: "notice" }, el("span", { class: "notice__title" }, "Passt nach den festen Regeln nicht"), el("p", { class: "notice__body" }, treffer.vorpruefung)) : null,
      el("article", { class: "ai-result" },
        el("header", { class: "ai-result__head" }, el("h3", { class: "ai-result__kind" }, "Einschätzung der KI"),
          el("span", { class: "search__grades" }, noten(treffer, { klein: false }))),
        b ? el("p", {}, b.zusammenfassung) : el("p", { class: "search__hint" }, "Noch nicht bewertet."),
        b && b.unsicher ? el("p", { class: "status-line", "data-level": "warning" }, `Note unsicher: ${b.unsicher}`) : null,
        b ? el("div", { class: "ai-result__cols" }, liste("Was passt", b.passt), liste("Was fehlt oder unsicher ist", b.haken)) : null,
        b && b.nachpruefung ? el("p", { class: "search__hint" }, logik.nachpruefungText(b, notenText)) : null,
        b && b.auffaellig && b.auffaellig.length ? el("p", { class: "status-line", "data-level": "danger" }, "Auffällige Zeilen im Inserat (nicht befolgt): " + b.auffaellig.join(" · ")) : null,
        el("div", { class: "btn-row" }, aktionen(treffer)),
        b ? el("p", { class: "ai-result__foot" }, "Eine Einschätzung, kein Urteil. Die KI kann sich irren.") : null),
      window.TrefferFirma.zeile(firmen.get(treffer.id), heute,
        { lehrstelle, alle: t("firmen.alle"), wo: t("firmen.titel"), nachPruefen: kununuGeprueft }),
      weitere.length ? el("ul", { class: "search__more" }, weitere) : null,
      el("div", { class: "btn-row" }, knopf), textFeld].filter(Boolean));
  }

  // Own stars per hit (G22): only for the order of the list; they never go to the AI and leave its grade alone.
  function eigeneSterne(treffer) {
    const aktuell = treffer.eigene_sterne || 0;
    const knoepfe = [1, 2, 3, 4, 5].map(zahl => el("button", {
      type: "button", "aria-label": `${zahl} von 5 Sternen für diesen Treffer`, "aria-pressed": String(zahl === aktuell),
      onclick: () => eigeneSterneSetzen(treffer, zahl === aktuell ? 0 : zahl),
    }, zahl <= aktuell ? "★" : "☆"));
    return el("p", { role: "group", "aria-label": "Eigene Bewertung" },
      "Eigene Bewertung: ", el("span", { class: "sterne" }, knoepfe),
      el("span", { class: "search__hint" }, "Nur für die Reihenfolge der Liste, geht nicht an die KI."));
  }

  function eigeneSterneSetzen(treffer, anzahl) {
    senden("/api/suche/sterne", { sterne: anzahl }, { id: treffer.id })
      .then(neu => { alle = alle.map(x => x.id === neu.id ? neu : x); zeigeListe(); })
      .catch(fehler => meldung(fehler.message, "fehler"));
  }

  // „Jetzt prüfen“ (#191): the app has stored the value, so badge and company line load it again.
  async function kununuGeprueft(ergebnis) {
    try {
      const daten = await holen("/api/firmen");
      firmen = window.FirmenLogik.nachTreffer(daten.firmen);
      heute = daten.heute || "";
      zeigeListe();
      meldung(ergebnis.text, ergebnis.stufe);
    } catch (fehler) {
      meldung(fehler.message, "fehler");
    }
  }

  function trefferZeile(treffer) {
    const sterne = treffer.beruf ? einstellungen.beruf_sterne[treffer.beruf] : 0;
    const rahmen = [treffer.ort, treffer.pensum || treffer.lehrbeginn].filter(Boolean).join(" · ");
    const marken = [
      logik.istSchnupperlehre(treffer) ? "Schnupperlehre" : "",
      treffer.hinweis ? "schon im Register" : "",
      treffer.vorpruefung ? "passt nicht: " + treffer.vorpruefung : "",
      sterne ? `${"★".repeat(sterne)}` : "",
      treffer.eigene_sterne ? `Eigene: ${"★".repeat(treffer.eigene_sterne)}` : "",
    ].filter(Boolean);
    const knopf = el("button", { type: "button", class: "hit", "aria-current": String(treffer.id === gewaehlt) },
      el("span", { class: "hit__grades" }, noten(treffer)),
      el("span", { class: "hit__text" },
        el("span", { class: "hit__title" }, treffer.stelle),
        el("span", { class: "hit__where" }, treffer.firma, window.TrefferFirma.marke(firmen.get(treffer.id)),
          treffer.firma && rahmen ? " · " : "", rahmen),
        el("span", { class: "hit__meta" }, [treffer.portal + ((treffer.weitere || []).length ? ` +${treffer.weitere.length}` : ""), datum(treffer.gefunden_am)].join(" · "),
          ...marken.map(m => [" · ", el("strong", {}, m)]).flat())));
    knopf.addEventListener("click", () => {
      gewaehlt = treffer.id;
      zeigeListe();
      $("detail").scrollTop = 0;  // the next hit starts at its top, not where the last one was left
      if (window.matchMedia("(max-width: 900px)").matches) $("detail").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    return knopf;
  }

  function zeigeListe() {
    $("art").hidden = !logik.beideArten(alle);
    const art = $("art").hidden ? "" : $("art").value;
    const passend = logik.nachArt(alle.filter(x => x.zustand === zustand), art);
    const sortierung = logik.gueltigeSortierung(einstellungen.sortierung);
    $("sortierung").value = sortierung;
    const sichtbar = logik.sortiert(passend, einstellungen.beruf_sterne, sortierung);
    for (const knopf of document.querySelectorAll("[data-zustand]")) knopf.setAttribute("aria-pressed", String(knopf.dataset.zustand === zustand));
    for (const name of ["neu", "uebernommen", "verworfen"]) document.querySelector(`[data-zahl=${name}]`).textContent = String(alle.filter(x => x.zustand === name).length);
    if (!sichtbar.some(x => x.id === gewaehlt)) gewaehlt = sichtbar[0]?.id ?? null;
    $("liste").classList.toggle("search__list--two", lehrstelle);  // two grades: the same width for every row
    $("liste").replaceChildren(...sichtbar.map(trefferZeile));
    zeigeDetail(sichtbar.find(x => x.id === gewaehlt));
    $("ergebnisse").hidden = sichtbar.length === 0;
    $("leer").hidden = sichtbar.length > 0;
    $("leer-titel").textContent = zustand === "neu" ? "Keine neuen Treffer" : zustand === "uebernommen" ? "Noch nichts übernommen" : "Nichts verworfen";
    $("leer-text").textContent = zustand === "neu" ? t("suche.keine") : "";
    $("leer-einstellen").hidden = zustand !== "neu";
    zeigeBewerten();
  }

  function zeigeBewerten() {
    const ids = logik.zuBewerten(alle).map(t => t.id);
    const laeuft = bewertungslauf !== null;
    $("bewerten-box").hidden = !laeuft;
    $("bewerten-knoepfe").replaceChildren(...(laeuft ? [] : logik.knoepfe(ids.length, paket, grenze).map(knopf => {
      return el("button", { type: "button", class: "btn btn--sm", onclick: () => starteBewertung(ids.slice(0, knopf.anzahl)) }, knopf.text);
    })));
    const proTreffer = logik.kostenProTreffer(alle);
    const kosten = ids.length && proTreffer !== null ? `Bisher etwa ${proTreffer.toFixed(3)} USD pro Treffer.` : "";
    $("kosten-hinweis").textContent = laeuft ? "" : logik.alleBewertet(alle) ? "Alle Treffer sind bewertet." : kosten;
    $("auto-bewerten").checked = einstellungen.auto_bewerten;
    $("zuschauen").checked = einstellungen.zuschauen;
    $("auto-text").textContent = `Neue Treffer nach der Suche automatisch bewerten (höchstens ${grenze} pro Suche)`;
    zeigeBerufe();
  }

  function sterneWaehlen(beruf, anzahl) {
    senden("/api/suche/beruf-sterne", { beruf, sterne: anzahl })
      .then(neu => { einstellungen = neu; zeigeListe(); })
      .catch(fehler => meldung(fehler.message, "fehler"));
  }

  function zeigeBerufe() {
    const berufe = [...new Set(alle.map(t => t.beruf).filter(Boolean))].sort((a, b) => a.localeCompare(b, "de"));
    $("berufe").hidden = !lehrstelle || berufe.length === 0;
    $("berufe-liste").replaceChildren(...berufe.map(beruf => {
      const aktuell = einstellungen.beruf_sterne[beruf] || 0;
      const knoepfe = [1, 2, 3, 4, 5].map(zahl => el("button", {
        type: "button", "aria-label": `${zahl} von 5 Sternen für ${beruf}`, "aria-pressed": String(zahl === aktuell),
        onclick: () => sterneWaehlen(beruf, zahl === aktuell ? 0 : zahl),
      }, zahl <= aktuell ? "★" : "☆"));
      return el("li", {}, el("span", { class: "sterne" }, knoepfe), el("span", {}, beruf));
    }));
  }

  function schlussText(stand) {
    const teile = [`${stand.bewertet} von ${stand.von} Treffern bewertet`];
    if (stand.offen.length) teile.push(`${stand.offen.length} ohne brauchbare Antwort, die lassen sich einzeln nochmals versuchen`);
    if (stand.ohneText) teile.push(`${stand.ohneText} ohne Inseratstext`);
    if (stand.gestoppt) teile.push("angehalten");
    const rest = logik.zuBewerten(alle).length;
    if (rest && !stand.gestoppt && !stand.fehler) teile.push(`noch ${rest} offen`);
    return `${teile.join(", ")}. Kosten: ${stand.kosten.toFixed(2)} USD.`;
  }

  /** Rate in packages with progress; one run at a time. The list updates after every package. */
  async function starteBewertung(ids) {
    if (bewertungslauf || !ids.length) return;
    const lauf = { halt: false };
    bewertungslauf = lauf;
    $("anhalten").disabled = false;
    zeigeListe();
    meldung("");
    $("bewerten-zahl").textContent = `0 von ${ids.length}`;
    const stand = await logik.bewerteAlle(ids, {
      paket,
      sende: gruppe => senden("/api/suche/bewerten-paket", { ids: gruppe }),
      angehalten: () => lauf.halt,
      fortschritt: (zwischen, treffer) => {
        const neu = new Map(treffer.map(t => [t.id, t]));
        alle = alle.map(t => (neu.has(t.id) ? { ...neu.get(t.id), ohne_text: false } : t));
        zeigeListe();
        $("bewerten-zahl").textContent = `${zwischen.bewertet} von ${ids.length}`;
      },
    });
    bewertungslauf = null;
    zeigeListe();
    if (stand.fehler) meldung(`${stand.fehler} ${schlussText(stand)}`, "fehler");
    else meldung(schlussText(stand), stand.offen.length || stand.gestoppt ? "hinweis" : "ok");
  }

  function bewerteNachSuche() {
    if (einstellungen.auto_bewerten) starteBewertung(logik.zuBewerten(alle).slice(0, grenze).map(t => t.id));
  }

  // A hint with a field in „Meine Angaben“ leads there.
  function hinweisZeile(text, ziele) {
    const inhalt = ziele[text] ? el("a", { href: `/angaben#${new URLSearchParams({ feld: ziele[text] })}` }, text) : text;
    return el("li", { "data-stufe": "hinweis" }, inhalt);
  }

  function zeigeLetzteSuche(lauf, hinweise, ziele) {
    const portale = Object.keys(lauf?.portale || {});
    const neu = alle.filter(x => x.zustand === "neu").length;
    $("letzte").textContent = lauf
      ? `Letzte Suche am ${datum(lauf.datum)} · ${portale.length === 1 ? portale[0] : `${portale.length} Portale`} · ${alle.length} Treffer, ${neu} neu`
      : "Noch keine Suche.";
    const probleme = Object.entries(lauf?.portale || {}).filter(([, p]) => p.problem).map(([, p]) => p.problem);
    $("probleme").replaceChildren(
      ...probleme.map(p => el("li", { "data-stufe": "fehler" }, p)),
      ...hinweise.map(h => hinweisZeile(h, ziele)));
  }

  function aufzaehlung(namen) {
    return namen.join(", ").replace(/, ([^,]*)$/, " und $1");
  }

  // The page follows the search profile: apprenticeships search other portals and know trial apprenticeships.
  function zeigeArt(art, angebote) {
    lehrstelle = art === "lehrstelle";
    $("angebot-wahl").hidden = !lehrstelle;
    $("angebot").value = logik.wahlAus(angebote);
    $("suchen").textContent = "Jetzt suchen";
  }

  // Only the desktop app has „Meine Angaben“; without it there is nothing to say.
  async function zeigeNichtUebernommen() {
    const offen = await holen("/api/angaben/offen").then(a => a.offen, () => false);
    $("angaben-offen").hidden = !offen;
    $("angaben-offen-text").textContent = t("suche.angaben-offen");
  }

  let ladeNummer = 0;

  /** Claude adds and rates hits while this page is open; a rating run of the page updates the list itself. */
  async function nachsehen() {
    if (bewertungslauf) return;
    try {
      const { treffer } = await holen("/api/suche/liste");
      if (!bewertungslauf && JSON.stringify(treffer) !== gezeigt) await lade();
    } catch {
      /* the app is closing; the next action says so */
    }
  }

  async function lade() {
    const nummer = ++ladeNummer;
    try {
      // Without the companies the list still shows, only without kununu.
      const [daten, firmenDaten] = await Promise.all([holen("/api/suche/liste"), holen("/api/firmen").catch(() => null)]);
      if (nummer !== ladeNummer) return; // a newer load is on its way, and this answer may be older
      firmen = firmenDaten ? window.FirmenLogik.nachTreffer(firmenDaten.firmen) : new Map();
      heute = firmenDaten?.heute || "";
      gezeigt = JSON.stringify(daten.treffer);
      alle = daten.treffer;
      einstellungen = daten.einstellungen;
      paket = daten.paket;
      grenze = daten.grenze;
      zeigeArt(daten.art, daten.angebote || []);
      window.PortalWahl.zeige(daten.portale_wahl || [], lade);
      window.Suchbegriffe.zeige(daten.art, daten.gesuchte_berufe || [], daten.gesuchte_schluessel || []);
      zeigeListe();
      zeigeLetzteSuche(daten.letzte_suche, daten.hinweise || [], daten.hinweis_ziele || {});
      zeigeNichtUebernommen();
      if (!alle.length && !einstellenGemerkt()) zeigeEinstellen(true);
    } catch (fehler) {
      meldung(fehler.message, "fehler");
    }
  }

  // Extension: present (marker or message), progress of a running search
  function erweiterungDa() {
    $("suchen").disabled = false;
    $("ohne-erweiterung").hidden = true;
  }

  function laufText(lauf) {
    if (lauf.zustand === "fehler") return [lauf.fehler || "Die Suche ist abgebrochen.", "fehler"];
    if (lauf.zustand === "fertig" && lauf.ergebnis?.abgebrochen) return ["Suche abgebrochen. Was schon gefunden war, ist da.", "hinweis"];
    if (lauf.zustand === "fertig") return ["Suche fertig.", "ok"];
    const s = lauf.schritt || {};
    if (s.phase === "suche") return [`${s.portal}: suche „${s.stichwort}“, Seite ${s.seite} …`, ""];
    if (s.phase === "texte") return [`${s.portal}: lese Inserate (${s.fertig} von ${s.von}) …`, ""];
    return ["Suche startet …", ""];
  }

  // The extension's worker may stop and lose this page's connection: without word for a while, the page asks.
  function warte() {
    clearTimeout(stille);
    stille = setTimeout(() => window.postMessage({ quelle: SEITE, art: "status" }, location.origin), logik.STILLE_MS);
  }

  function folge(lauf) {
    const [text, art] = laufText(lauf);
    const laeuft = lauf.zustand === "laeuft";
    $("lauf-box").hidden = !laeuft;
    zeile($("lauf"), laeuft ? text : "");
    if (!laeuft) meldung(text, art);
    $("suchen").disabled = laeuft;
    $("suchen").textContent = laeuft ? "Suche läuft …" : "Jetzt suchen";
    $("suchen").setAttribute("aria-busy", String(laeuft));
    const eben = letzterSuchlauf === "laeuft" && lauf.zustand === "fertig";
    letzterSuchlauf = lauf.zustand;
    if (laeuft) {
      wartetSeit = wartetSeit || lauf.beginn || new Date().toISOString();
      warte();
      return;
    }
    clearTimeout(stille);
    wartetSeit = null;
    // Only a search that ended while this page was open starts a rating by itself.
    if (eben) lade().then(bewerteNachSuche);
    else lade();
  }

  window.addEventListener("message", event => {
    if (event.source !== window || event.origin !== location.origin) return;
    const daten = event.data;
    if (!daten || daten.quelle !== ERWEITERUNG) return;
    erweiterungDa();
    if (daten.art === "lauf") {
      folge(daten.lauf);
    } else if (daten.art === "antwort" && daten.frage === "status") {
      if (wartetSeit) folge(logik.laufNachStatus(daten.antwort, wartetSeit));
    } else if (daten.art === "antwort" && daten.antwort?.fehler) {
      folge({ zustand: "fehler", fehler: daten.antwort.fehler });
    }
  });

  $("suchen").addEventListener("click", () => {
    $("suchen").disabled = true;
    $("lauf-box").hidden = false;
    zeile($("lauf"), "Suche startet …");
    wartetSeit = new Date().toISOString();
    warte();
    window.postMessage({ quelle: SEITE, art: "suche-starten" }, location.origin);
  });
  for (const knopf of document.querySelectorAll("[data-zustand]")) knopf.addEventListener("click", () => { zustand = knopf.dataset.zustand; zeigeListe(); });
  $("art").addEventListener("change", zeigeListe);
  $("sortierung").addEventListener("change", () => {
    senden("/api/suche/einstellungen", { sortierung: $("sortierung").value })
      .then(neu => { einstellungen = neu; zeigeListe(); })
      .catch(fehler => meldung(fehler.message, "fehler"));
  });
  $("angebot").addEventListener("change", async () => {
    try {
      const { angebote } = await senden("/api/suche/angebot", { wahl: $("angebot").value });
      meldung(`Gesucht wird: ${logik.sucheText(angebote).replace(/ suchen$/, "")}.`, "ok");
    } catch (fehler) {
      meldung(fehler.message, "fehler");
      lade();
    }
  });
  $("anhalten").addEventListener("click", () => {
    if (bewertungslauf) bewertungslauf.halt = true;
    $("anhalten").disabled = true;
    meldung("Wird nach dem laufenden Paket angehalten …");
  });
  $("auto-bewerten").addEventListener("change", event => {
    senden("/api/suche/einstellungen", { auto_bewerten: event.target.checked })
      .then(neu => { einstellungen = neu; })
      .catch(fehler => { meldung(fehler.message, "fehler"); zeigeBewerten(); });
  });

  $("zuschauen").addEventListener("change", event => {
    senden("/api/suche/einstellungen", { zuschauen: event.target.checked })
      .then(neu => { einstellungen = neu; })
      .catch(fehler => { meldung(fehler.message, "fehler"); zeigeBewerten(); });
  });

  // Settings: open on request, and at first while there are no hits yet
  function einstellenGemerkt() {
    try { return localStorage.getItem(EINSTELLEN_OFFEN) !== null; } catch { return false; }
  }

  function zeigeEinstellen(offen, merken = false) {
    $("einstellen").hidden = !offen;
    $("einstellen-knopf").setAttribute("aria-expanded", String(offen));
    $("einstellen-knopf").textContent = offen ? "Einstellungen schliessen" : "Suche einstellen";
    if (merken) { try { localStorage.setItem(EINSTELLEN_OFFEN, offen ? "1" : "0"); } catch { /* without storage it stays as it is now */ } }
  }

  $("einstellen-knopf").addEventListener("click", () => zeigeEinstellen($("einstellen").hidden, true));
  $("leer-einstellen").addEventListener("click", () => { zeigeEinstellen(true, true); $("einstellen").scrollIntoView({ behavior: "smooth" }); });
  try { if (localStorage.getItem(EINSTELLEN_OFFEN) === "1") zeigeEinstellen(true); } catch { /* closed by default */ }

  if (document.documentElement.dataset.bewerbungsbegleiterErweiterung) erweiterungDa();
  else setTimeout(() => { if ($("suchen").disabled && $("lauf-box").hidden) $("ohne-erweiterung").hidden = false; }, 1500);
  document.addEventListener("suchprofil-geaendert", lade);
  textsatz().then(gewaehlterSatz => { satz = gewaehlterSatz; anwenden(document, satz); }).finally(() => { lade(); beobachten(nachsehen); });
})();
