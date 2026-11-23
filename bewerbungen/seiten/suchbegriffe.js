"use strict";
// The view „Suchbegriffe prüfen“ (#210, option B of docs/design/suchbegriffe.md): one card per change with a checkbox,
// the reason of the AI and the evidence of the app, the result as „So sucht die App danach“, revise, take over, undo.
// Each term is a switch of its own (#371, G102, suchbegriffe-schalter.js): the page sends the terms that are on, and
// the app takes only current and proposed ones, works out the result and writes exactly that. The page's own words in
// the app language through Texte (#425); the server words the changes, the AI its summary and reasons.
(() => {
  const { holen, senden, el, status, textsatz } = window.App;
  const L = window.SuchbegriffeLogik;
  const Schalter = window.SuchbegriffeSchalter;
  const { Texte } = window;
  const $ = id => document.getElementById(id);
  // What routes_terms.STALE_ACTION names: a takeover after the terms changed, known by the action, not by its words.
  const VERALTET = "vorschlag-veraltet";
  const unveraendert = () => Texte.t("Am Suchprofil hat sich nichts geändert.");
  // A pause after a switch before the app is asked again; the first switch asks at once.
  const PAUSE_MS = 250;
  let satz = "stelle-sie";
  let texte = L.texte(satz);
  let vorschlag = null;
  let frueher = [];  // former proposals of this visit, „Vorschlag 1 zeigen“
  let auswahl = null;  // the terms in the result per area, as the switches stand
  let erlaubt = null;
  let grenzen = null;  // the limits of the last answer, to announce only a change of blocked and free
  let anfrage = 0;  // the number of the newest request; an older answer is dropped
  let ruht = true;
  let nachholen = false;
  let abgebrochen = false;

  /**
   * An empty title is hidden, for a text that names its own subject, like the server's «Kein Vorschlag. …» (#348).
   * `stufe` gives the look of stil.css (warning, danger, success); every notice without one is neutral again.
   */
  function meldung(titel, text, knoepfe = [], stufe = "") {
    $("meldung").className = stufe ? `notice notice--${stufe}` : "notice";
    $("meldung").hidden = false;
    $("meldung-titel").hidden = !titel;
    $("meldung-titel").textContent = titel;
    $("meldung-text").textContent = text;
    $("meldung-knoepfe").replaceChildren(...knoepfe);
  }

  const knopf = (text, aktion, klasse = "btn btn--sm") => el("button", { type: "button", class: klasse, onclick: aktion }, text);
  const neuKnopf = () => knopf(Texte.t("Neu vorschlagen"), () => holeVorschlag());

  function warten(an) {
    $("warten").hidden = !an;
    $("warten-titel").textContent = texte.warten;
    $("warten-notiz").textContent = texte.wartenNotiz;
  }

  /**
   * The cost of „Neu vorschlagen“ as on Suche einstellen (#334): GET /api/suchbegriffe/schaetzung in the words of
   * TrefferLogik.costLine, asked after each proposal, since a round changes the credit. A used-up credit links where to
   * ask for a code; the button stays, the proposal route says what is missing.
   */
  async function zeigeAndersKosten() {
    const logik = window.TrefferLogik;
    let zeile;
    try {
      zeile = logik.costLine(await holen("/api/suchbegriffe/schaetzung"));
    } catch (fehler) {
      zeile = { text: logik.estimateFailedText(fehler.message), usedUp: false };
    }
    $("anders-kosten").replaceChildren(...(zeile.usedUp ? window.Texte.withCodeRequestLink(zeile.text, el) : [zeile.text]));
  }

  /**
   * A failed proposal as a warning (#348). #meldung is no live region, so the focus goes to «Nochmals versuchen»,
   * which screen readers announce with the server text that describes it.
   */
  function zeigeFehlschlag(text, body) {
    const nochmals = knopf(Texte.t("Nochmals versuchen"), () => holeVorschlag(body));
    nochmals.setAttribute("aria-describedby", "meldung-text");
    meldung("", text, [nochmals], "warning");
    $("meldung-knoepfe").querySelector("button")?.focus();
  }

  async function holeVorschlag(body = {}) {
    abgebrochen = false;
    $("meldung").hidden = true;
    warten(true);
    try {
      const neu = await senden("/api/suchbegriffe/vorschlag", body);
      if (abgebrochen) return;
      if (vorschlag) frueher = [...frueher, vorschlag];
      window.Meldungen.clearInputError($("anders-status"));
      zeige(neu);
      zeigeAndersKosten();
    } catch (fehler) {
      if (!abgebrochen) zeigeFehlschlag(fehler.message, body);
    } finally {
      warten(false);
    }
  }

  /** A plain mark of the read-only outcome, no switch: each term has exactly one, in the list above. */
  function marke({ begriff, wort, art }) {
    return el("li", { class: `term term--${art}` }, el("span", { class: "term__name" }, begriff), el("span", { class: "term__word" }, wort));
  }

  function beleg(b) {
    const anteil = L.balken(b);
    const alle = el("span", { class: "share__all" });
    const unter = el("span", { class: "share__below" });
    alle.style.width = `${anteil.anteil}%`;
    unter.style.width = `${(anteil.anteil * anteil.unter) / 100}%`;
    return el("div", { class: "change__evidence" },
      el("div", { class: "share", "aria-hidden": "true" }, alle, unter),
      el("p", {}, L.belegSatz(b)),
      L.belegBeispiele(b) ? el("p", { class: "change__examples" }, L.belegBeispiele(b)) : null,
      el("p", {}, el("a", { href: L.belegAdresse(b) }, L.belegLink(b))));
  }

  /** The checkbox of a change switches its terms together; the native mixed state shows when only some are on. */
  function karte(a) {
    const id = `aenderung-${a.nummer}`;
    const haken = el("input", { type: "checkbox", id, "aria-describedby": `${id}-grund` });
    haken.addEventListener("change", () => schalte(L.schalteKarte(auswahl, a, haken.checked)));
    const { liste, teilweise } = Schalter.karte(a, haken, (chip, an) => schalte(L.schalteChip(auswahl, chip, an)));
    const flag = wort => el("span", { class: "term term--flag" }, el("span", { class: "term__word" }, wort));
    return el("div", { class: "change" },
      el("p", { class: "change__area" }, a.bereich_name, a.zu_allgemein ? flag(Texte.t("zu allgemein")) : null,
        L.kartenMarke(a) ? flag(L.kartenMarke(a)) : null),
      el("label", { class: "check", for: id }, haken, el("span", {}, a.satz)),
      teilweise,
      liste,
      el("p", { class: "change__reason", id: `${id}-grund` }, a.grund),
      a.beleg ? beleg(a.beleg) : null);
  }

  function zeigeBisherige(v) {
    const bereiche = L.bisherigeBereiche(v.bisherige);
    $("bisherige").hidden = !bereiche.length;
    $("bisherige-satz").textContent = texte.bisherige;
    $("bisherige-oben").textContent = L.BISHERIGE_OBEN;
    $("bisherige-oben").hidden = !v.aenderungen.some(a => a.entfaellt.length || a.verschoben);
    $("bisherige-bereiche").replaceChildren(...Schalter.bisherige(bereiche, (chip, an) => schalte(L.schalteChip(auswahl, chip, an))));
  }

  /** The switches move at once; the app is asked at once too, then again after a pause for what came meanwhile. */
  function schalte(neu) {
    auswahl = neu;
    Schalter.zeichne(auswahl, erlaubt);
    plane();
  }

  function plane() {
    if (!ruht) {
      nachholen = true;
      return;
    }
    ruht = false;
    frageEndstand();
    setTimeout(() => {
      ruht = true;
      if (!nachholen) return;
      nachholen = false;
      plane();
    }, PAUSE_MS);
  }

  /** A «·» line of whole parts (#340, dot-line.js): never starts with «·», screen readers hear commas. */
  const dotLine = parts => window.DotLine.render(parts, el);

  function zeigeEndstand(antwort) {
    // G108: after the three areas the niches and «Nur» lines, so a move shows where the keyword runs now
    const bloecke = [...L.endstand(vorschlag.jetzt, antwort.endstand, antwort.nur_zeilen || []), ...L.endstandZeilen(antwort)].map(b => el("div", {},
      el("h3", {}, b.name),
      el("ul", { class: "terms" }, ...b.begriffe.map(x => marke({ begriff: x.begriff, wort: x.neu ? Texte.t("neu") : "",
        art: x.neu ? "new" : "kept" })))));
    $("endstand").replaceChildren(...bloecke);
    $("faellt-weg").textContent = L.entfaelltZeile(antwort.entfaellt);
    $("grenzen").replaceChildren(...dotLine(antwort.grenzen.teile));
    $("uebernehmen").textContent = L.HAUPTKNOPF;
    $("uebernehmen").disabled = Boolean(antwort.grenzen.gesperrt);
    zeigeGrund(antwort.grenzen);
  }

  /** The reason under the button; over a limit it links to the legend of the area, where terms can be switched off. */
  function zeigeGrund(g) {
    const bereich = L.zuVielBereich(g);
    const ziel = () => (bereich && Schalter.legende(bereich)) || $("bisherige-titel");
    const link = bereich ? el("a", { href: "#bisherige-titel" }, L.ZU_DEN_BISHERIGEN) : null;
    link?.addEventListener("click", event => {
      event.preventDefault();
      ziel().focus();
    });
    $("uebernehmen-grund").replaceChildren(...(g.gesperrt ? [g.gesperrt, link ? " " : "", link].filter(Boolean) : []));
  }

  function veraltet(text) {
    $("vorschlag").hidden = true;
    meldung(Texte.t("Vorschlag veraltet"), text, [neuKnopf()]);
  }

  async function frageEndstand() {
    anfrage += 1;
    const nummer = anfrage;
    try {
      const antwort = await senden("/api/suchbegriffe/endstand", { vorschlag: vorschlag.vorschlag, danach: auswahl });
      if (nummer !== anfrage) return;
      if (antwort.veraltet) {
        veraltet(antwort.meldung);
        return;
      }
      zeigeEndstand(antwort);
      const ansage = L.ansage(grenzen, antwort.grenzen);
      if (ansage) $("auswahl-ansage").textContent = ansage;
      grenzen = antwort.grenzen;
    } catch (fehler) {
      if (nummer === anfrage) status($("status"), fehler.message, "fehler");
    }
  }

  function zeigeKopf(v) {
    $("vorschlag-kopf").replaceChildren(...dotLine(L.kopfTeile(v.aenderungen.length)));
    $("runde").hidden = v.runde < 2;
    $("runde").replaceChildren(...dotLine(L.rundeTeile(v, satz)));
    $("geaendert").hidden = !v.geaendert;
    $("geaendert").textContent = v.geaendert
      ? Texte.t("Geändert gegenüber Vorschlag {runde}: {geaendert}", { runde: v.runde - 1, geaendert: v.geaendert }) : "";
    $("ihr-hinweis").hidden = !v.hinweis;
    $("ihr-hinweis").textContent = v.hinweis ? Texte.t("{titel}: «{hinweis}»", { titel: texte.ihrHinweis, hinweis: v.hinweis }) : "";
    const davor = frueher[frueher.length - 1];
    $("frueher").hidden = !davor;
    $("frueher").textContent = davor ? Texte.t("Vorschlag {runde} zeigen", { runde: davor.runde }) : "";
    $("frueher").onclick = () => {
      frueher = [...frueher.slice(0, -1), vorschlag];  // swap, so the newer one can come back the same way
      zeige(davor);
    };
  }

  function zeige(v) {
    vorschlag = v;
    anfrage += 1;  // an answer for the proposal shown before no longer counts
    $("gesehen").textContent = texte.gesehen(v.treffer, v.seit);
    $("anders").hidden = false;
    $("anders-hilfe").textContent = texte.andersHilfe;
    if (!v.aenderungen.length) {
      $("vorschlag").hidden = true;
      meldung(texte.passt, texte.passtNotiz);
      return;
    }
    auswahl = { ...v.endstand, [L.VERSCHOBEN]: v.verschoben || [] };
    erlaubt = v.grenzen.erlaubt;
    grenzen = v.grenzen;
    $("vorschlag").hidden = false;
    zeigeKopf(v);
    $("zusammenfassung").textContent = v.zusammenfassung;
    Schalter.beginne();
    $("aenderungen").replaceChildren(...v.aenderungen.map(karte));
    zeigeBisherige(v);
    Schalter.zeichne(auswahl, erlaubt);
    $("fuss-satz").textContent = texte.fuss;
    $("fuss").replaceChildren(...dotLine(L.fussTeile(v)));
    zeigeEndstand(v);
    $("vorschlag-kopf").focus();
  }

  async function rueckgaengig(stand) {
    try {
      await senden("/api/suchbegriffe/rueckgaengig", stand);
      status($("status"), L.RUECKGAENGIG_FERTIG, "ok");
    } catch (fehler) {
      status($("status"), fehler.message, "fehler");
    }
  }

  async function uebernehmen() {
    $("uebernehmen").disabled = true;
    try {
      const stand = await senden("/api/suchbegriffe/uebernehmen", { vorschlag: vorschlag.vorschlag, danach: auswahl });
      $("aenderungen-feld").disabled = true;
      $("verwerfen").hidden = true;
      $("uebernehmen-grund").replaceChildren(el("a", { class: "btn btn--sm", href: "/treffer" }, Texte.t("Jetzt suchen")));
      status($("status"), L.uebernommen(stand.neu, stand.entfallen, stand.verschoben), "ok", { aktion: { text: Texte.t("Rückgängig machen"),
        ausfuehren: () => rueckgaengig({ vorher: stand.vorher, nachher: stand.nachher }) } });
    } catch (fehler) {
      reportTakeoverFailed(fehler);
    }
  }

  /** A stale proposal is known by the action the server names, never by its words, which follow the app language. */
  function reportTakeoverFailed(fehler) {
    $("uebernehmen").disabled = false;
    if (fehler.daten && fehler.daten.aktion === VERALTET) veraltet(fehler.message);
    else status($("status"), fehler.message, "fehler");
  }

  function verwerfen() {
    $("vorschlag").hidden = true;
    meldung(Texte.t("Verworfen"), unveraendert(), [neuKnopf()]);
  }

  /**
   * Without a text the error stands beside the field, which shows in every state of the page, unlike the proposal and
   * its line; it goes with the first input there or the next proposal (G97).
   */
  function anders() {
    const hinweis = $("anders-text").value.trim();
    if (!hinweis) {
      $("anders-text").setAttribute("aria-invalid", "true");
      status($("anders-status"), Texte.t("Bitte schreiben, was anders sein soll."), "fehler", { input: $("anders-text") });
      $("anders-text").focus();
      return;
    }
    holeVorschlag(vorschlag ? { vorher: vorschlag.vorschlag, hinweis } : {});
  }

  async function einwilligungOffen() {
    try {
      const { einwilligung } = await holen("/api/ki/status");
      return einwilligung && !einwilligung.erteilt ? einwilligung : null;
    } catch {
      return null;  // the proposal route says what is missing
    }
  }

  async function start() {
    satz = await textsatz();
    texte = L.texte(satz);
    const vorab = await holen("/api/suchbegriffe/hinweis").catch(() => ({ verfuegbar: true }));
    if (!vorab.verfuegbar) {
      meldung(Texte.t("Nur bei der Stellensuche"), Texte.t("Suchbegriffe prüfen gibt es vorerst nur bei der Stellensuche."));
      return;
    }
    $("gesehen").textContent = texte.gesehen(vorab.treffer, vorab.seit);
    window.SuchbegriffeGezaehlt.zeige();  // counted by the app (G108): shown while the AI works, not awaited
    const offen = await einwilligungOffen();
    if (!offen) {
      holeVorschlag();
      return;
    }
    meldung("", texte.einwilligung);
    window.Einwilligung.zeile($("einwilligung"), offen, neu => {
      if (neu.einwilligung && !neu.einwilligung.erteilt) return;
      $("einwilligung").hidden = true;
      holeVorschlag();
    });
  }

  $("abbrechen").addEventListener("click", () => {
    abgebrochen = true;
    warten(false);
    meldung(Texte.t("Abgebrochen"), unveraendert(), [neuKnopf()]);
  });
  $("uebernehmen").addEventListener("click", uebernehmen);
  $("verwerfen").addEventListener("click", verwerfen);
  $("neu-vorschlagen").addEventListener("click", anders);
  start();
})();
