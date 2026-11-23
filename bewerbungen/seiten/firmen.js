"use strict";
// The page Firmen (G35, #188, docs/design/firmen.md): one row per company from hits and applications, with what
// kununu says. „Prüfen“ reads the value through the extension on the person's click (#189, kununu-pruefen.js), or
// only opens kununu in a new tab without it; what cannot be read the person enters by hand.
(() => {
  const { holen, senden, el } = window.App;
  const logik = window.FirmenLogik;
  const $ = id => document.getElementById(id);
  const ARIA_SORT = { aufsteigend: "ascending", absteigend: "descending" };
  // Texts in the app language (#423): fixed words through Texte.t, the sets of texte.js through text below.
  const Texte = window.Texte;
  const neuerTab = () => Texte.t(", öffnet neuen Tab");
  // Without the extension „Prüfen“ only opens kununu in a new tab.
  const erweiterungDa = () => Boolean(document.documentElement.dataset.bewerbungsbegleiterErweiterung);

  let firmen = [];
  let heute = "";
  let satz = "stelle-sie";
  let filter = "alle";
  let sortierung = logik.STANDARD_SORTIERUNG;
  let offen = null;      // the company whose choice of several is open
  let zuordnen = null;   // the company of the dialog „Selbst zuordnen“
  let vonHand = null;    // the company of the dialog „Von Hand eintragen“
  const nichtGelesen = new Set();  // companies with a value whose new check found nothing readable

  const text = (schluessel, werte) => Texte.text(schluessel, satz, werte);
  /** A «·» line of whole parts (#342, dot-line.js): never starts with «·», screen readers hear commas. */
  const dotLine = parts => window.DotLine.render(parts, el);
  const meldung = (inhalt, stufe = "", optionen = {}) => window.Meldungen.zeige($("status"), inhalt, stufe, optionen);

  function extern(href, beschriftung, firma, klasse = "btn btn--sm") {
    return el("a", { class: klasse, href, target: "_blank", rel: "noopener noreferrer" }, beschriftung,
      el("span", { class: "visually-hidden" }, `: ${firma.name}${neuerTab()}`));
  }

  async function pruefen(firma, knopf) {
    knopf.disabled = true;
    meldung(Texte.t("{firma}: wird bei kununu geprüft …", { firma: firma.name }));
    const ergebnis = logik.pruefErgebnis(await window.KununuPruefen.pruefe(firma), firma.name);
    knopf.disabled = false;
    if (!ergebnis) return meldung("");
    if (ergebnis.vonHand) nichtGelesen.add(firma.schluessel);
    else nichtGelesen.delete(firma.schluessel);
    await laden(firma.schluessel).catch(fehler => meldung(fehler.message, "warning"));
    meldung(ergebnis.text, ergebnis.stufe);
    if (ergebnis.vonHand) oeffneVonHand(firma);
  }

  function pruefenKnopf(firma, beschriftung) {
    return el("button", { type: "button", class: "btn btn--sm", "data-firma": firma.schluessel,
      onclick: event => pruefen(firma, event.currentTarget) },
    beschriftung, el("span", { class: "visually-hidden" }, `: ${firma.name}${erweiterungDa() ? "" : neuerTab()}`));
  }

  function knopf(firma, beschriftung, aktion, attribute = {}) {
    return el("button", { type: "button", class: "btn btn--sm", "data-firma": firma.schluessel, onclick: aktion, ...attribute }, beschriftung);
  }

  function lernende(k) {
    if (satz !== "lehrstelle-du" || !k.lernende?.bewertungen) return null;
    return el("span", { class: "rating__meta" }, Texte.t("Lernende: {wert} von 5, {bewertungen}",
      { wert: logik.wert(k.lernende.wert), bewertungen: logik.bewertungen(k.lernende.bewertungen) }));
  }

  function wertBlock(firma, zustand) {
    const k = firma.kununu;
    const wenige = zustand === "wenige";
    const empfehlung = typeof k.empfehlung === "number" ? Texte.t("{prozent} empfehlen", { prozent: logik.prozent(k.empfehlung) }) : "";
    const meta = wenige ? Texte.t("Nur {bewertungen}, wenig aussagekräftig.", { bewertungen: logik.bewertungen(k.bewertungen) })
      : dotLine([logik.bewertungen(k.bewertungen), empfehlung]);
    return el("div", { class: "rating", "data-state": wenige ? "few" : null },
      el("span", { class: "rating__value" }, el("b", {}, logik.wert(k.wert)), Texte.t(" von 5")),
      el("span", { class: "rating__meta" }, meta), lernende(k), el("span", { class: "rating__meta" }, logik.seite(k)));
  }

  function kununuZelle(firma) {
    const zustand = logik.zustand(firma);
    if (logik.MIT_WERT.includes(zustand)) return wertBlock(firma, zustand);
    if (zustand === "fehler") {
      return el("p", { class: "status-line", "data-level": "warning" },
        Texte.t("Nicht geprüft. kununu war nicht erreichbar. Bitte später nochmals prüfen."));
    }
    const worte = { keine: () => Texte.t("Noch keine Bewertungen"), mehrere: () => text("firmen.mehrere"),
                    nicht_gefunden: () => Texte.t("Bei kununu nicht gefunden"),
                    zugeordnet: () => Texte.t("Noch nicht geprüft, Seite zugeordnet"), ungeprueft: () => Texte.t("Noch nicht geprüft") };
    return el("span", { class: zustand === "mehrere" ? "rating__state" : "rating__state rating__state--quiet" }, worte[zustand]());
  }

  function verknuepft(firma) {
    const bewerbungen = firma.bewerbungen.map(b => el("span", { class: "line" },
      el("a", { href: "/bewerbung?" + new URLSearchParams({ id: b.id }) }, b.stelle || Texte.t("Bewerbung")),
      el("span", { class: "marke-status", "data-status": b.status }, window.Texte.statusName(b.status, satz))));
    const treffer = firma.treffer.length ? [el("span", { class: "line" }, el("a", { href: "/treffer" }, logik.trefferText(firma.treffer)))] : [];
    return el("div", { class: "companies__links" }, ...bewerbungen, ...treffer);
  }

  function geprueft(firma) {
    const am = firma.kununu?.geprueft_am;
    if (!am || logik.zustand(firma) === "zugeordnet") return el("span", { class: "muted" }, "–");
    return logik.veraltet(firma, heute) ? [el("span", { class: "muted" }, Texte.t("Stand ")), logik.datum(am)] : logik.datum(am);
  }

  function aktionen(firma) {
    const zustand = logik.zustand(firma);
    const k = firma.kununu || {};
    const ansehen = k.link ? extern(k.link, Texte.t("Bei kununu ansehen"), firma) : null;
    const je = {
      ungeprueft: () => [pruefenKnopf(firma, Texte.t("Prüfen"))],
      zugeordnet: () => [pruefenKnopf(firma, Texte.t("Prüfen")), ansehen],
      fehler: () => [pruefenKnopf(firma, Texte.t("Nochmals prüfen"))],
      nicht_gefunden: () => [extern(firma.suche, Texte.t("Bei kununu suchen"), firma, "btn btn--sm btn--quiet"),
        knopf(firma, Texte.t("Selbst zuordnen"), () => oeffneDialog(firma))],
      mehrere: () => [knopf(firma, Texte.t("Passende wählen"), () => waehlen(firma),
        { "aria-expanded": String(offen === firma.schluessel), "aria-controls": `wahl-${firma.schluessel}` })],
    };
    const gefunden = () => [logik.pruefungFaellig(firma, heute) ? pruefenKnopf(firma, Texte.t("Neu prüfen")) : null, ansehen];
    const hand = logik.vonHandAnbieten(firma, heute, nichtGelesen)
      ? knopf(firma, Texte.t("Von Hand eintragen"), () => oeffneVonHand(firma)) : null;
    return el("div", { class: "btn-row" }, ...(je[zustand] || gefunden)().filter(Boolean), hand, sucheKnopf(firma));
  }

  // Excluded companies (#226, G65): their hits leave the search; the row stays, so the person can take it back here.
  // The same words as on a hit and on an application (#303).
  function sucheKnopf(firma) {
    const name = el("span", { class: "visually-hidden" }, `: ${firma.name}`);
    return firma.ausgeschlossen
      ? el("button", { type: "button", class: "btn btn--sm", onclick: () => zeigeWieder(firma) }, text("firmen.wieder-zeigen"), name)
      : el("button", { type: "button", class: "btn btn--sm btn--quiet", onclick: () => schliesseAus(firma) }, text("firmen.ausschliessen"), name);
  }

  async function schliesseAus(firma) {
    try {
      await window.FirmenAusschluss.ausschliessen(firma.name);
      await laden(firma.schluessel);
      meldung(text("firmen.ausgeschlossen", { firma: firma.name }), "success");
    } catch (fehler) {
      meldung(`${text("firmen.nicht-geaendert", { firma: firma.name })} ${fehler.message}`, "warning");
    }
  }

  async function zeigeWieder(firma) {
    try {
      await window.FirmenAusschluss.wiederZeigen(firma.schluessel);
      await laden(firma.schluessel);
      meldung(text("firmen.wieder-gezeigt", { firma: firma.name }), "success");
    } catch (fehler) {
      meldung(`${text("firmen.nicht-geaendert", { firma: firma.name })} ${fehler.message}`, "warning");
    }
  }

  function zeile(firma) {
    return el("tr", { "data-schluessel": firma.schluessel, class: offen === firma.schluessel ? "is-open" : null },
      el("td", { "data-label": "" }, el("span", { class: "table__main" }, firma.name), firma.ort ? el("span", { class: "table__sub" }, firma.ort) : null,
        firma.ausgeschlossen ? el("span", { class: "table__sub" }, Texte.t("Nicht mehr in der Suche")) : null),
      el("td", { "data-label": "kununu" }, kununuZelle(firma)),
      el("td", { "data-label": Texte.t("Treffer und Bewerbungen") }, verknuepft(firma)),
      el("td", { "data-label": Texte.t("Geprüft"), class: "num" }, geprueft(firma)),
      el("td", { "data-label": "", class: "companies__actions" }, aktionen(firma)));
  }

  function wahlZeile(firma) {
    const name = `wahl-${firma.schluessel}`;
    const kandidaten = (firma.kununu.kandidaten || []).map(kandidat => el("label", { class: "choice" },
      el("input", { type: "radio", name, value: kandidat.link }),
      el("span", {}, el("span", { class: "choice__name" }, kandidat.name),
        el("span", { class: "choice__meta" }, dotLine([kandidat.ort, typeof kandidat.bewertungen === "number" ? logik.bewertungen(kandidat.bewertungen) : ""]))),
      el("a", { href: kandidat.link, target: "_blank", rel: "noopener noreferrer" }, Texte.t("Bei kununu ansehen"),
        el("span", { class: "visually-hidden" }, `: ${kandidat.name}${neuerTab()}`))));
    const keine = el("label", { class: "choice" }, el("input", { type: "radio", name, value: "" }),
      el("span", {}, el("span", { class: "choice__name" }, Texte.t("Keine davon passt"))), el("span", {}));
    const legende = el("legend", { tabindex: "-1" },
      Texte.t("Welche ist {firma}?", { firma: [firma.name, firma.ort].filter(Boolean).join(", ") }));
    return el("tr", { class: "chooser", id: name }, el("td", { colspan: "5", "data-label": "" }, el("fieldset", {}, legende,
      el("p", { class: "field__hint" }, Texte.t("Ort und Anzahl Bewertungen helfen beim Wählen.")), ...kandidaten, keine,
      el("div", { class: "btn-row" },
        el("button", { type: "button", class: "btn btn--sm btn--primary", onclick: () => zuordnenAusWahl(firma) }, Texte.t("Zuordnen")),
        el("button", { type: "button", class: "btn btn--sm", onclick: () => { offen = null; zeige(firma.schluessel); } },
          Texte.t("Abbrechen"))))));
  }

  function fokusAuf(schluessel) {
    const ziel = document.querySelector(`tr[data-schluessel="${CSS.escape(schluessel)}"] .companies__actions .btn`);
    ziel?.focus();
  }

  function zeigeKoepfe() {
    for (const kopf of document.querySelectorAll("th[data-spalte]")) {
      if (kopf.dataset.spalte === sortierung.spalte) kopf.setAttribute("aria-sort", ARIA_SORT[sortierung.richtung]);
      else kopf.removeAttribute("aria-sort");
    }
  }

  function zeigeKopfzeile() {
    const { anzahl, gefunden, zuletzt } = logik.zusammenfassung(firmen);
    // one company or one found: keys of their own, so French and English say it in the singular (#423)
    $("zeile").replaceChildren(...dotLine([
      anzahl === 1 ? text("firmen.zeile.eins") : text("firmen.zeile", { anzahl }),
      gefunden === 1 ? text("firmen.zeile.gefunden-eins") : text("firmen.zeile.gefunden", { gefunden }),
      zuletzt ? Texte.t("zuletzt geprüft am {datum}", { datum: logik.datum(zuletzt) }) : ""]));
    const zahlen = logik.zaehlen(firmen);
    for (const knopf of document.querySelectorAll("[data-filter]")) {
      knopf.setAttribute("aria-pressed", String(knopf.dataset.filter === filter));
      knopf.querySelector("[data-zahl]").textContent = String(zahlen[knopf.dataset.filter]);
    }
  }

  /** Draws the list; `fokus` is the company whose row gets the focus back. */
  function zeige(fokus = null) {
    zeigeKopfzeile();
    zeigeKoepfe();
    const sichtbar = logik.sortiert(logik.gefiltert(firmen, filter, $("suche").value), sortierung);
    $("leer").hidden = firmen.length > 0;
    $("nichts").hidden = firmen.length === 0 || sichtbar.length > 0;
    $("tabelle").hidden = sichtbar.length === 0;
    $("liste").replaceChildren(...sichtbar.flatMap(f => (offen === f.schluessel ? [zeile(f), wahlZeile(f)] : [zeile(f)])));
    if (fokus) fokusAuf(fokus);
  }

  function waehlen(firma) {
    offen = offen === firma.schluessel ? null : firma.schluessel;
    zeige(offen ? null : firma.schluessel);
    if (offen) document.querySelector(`#wahl-${CSS.escape(firma.schluessel)} legend`)?.focus();
  }

  async function laden(fokus = null) {
    const antwort = await holen("/api/firmen");
    firmen = antwort.firmen;
    heute = antwort.heute;
    zeige(fokus);
  }

  async function zuordnenAusWahl(firma) {
    const gewaehlt = document.querySelector(`#wahl-${CSS.escape(firma.schluessel)} input:checked`);
    if (!gewaehlt) {
      return meldung(Texte.t("Bitte eine Firma wählen oder «Keine davon passt»."), "warning",
        { input: document.getElementById(`wahl-${firma.schluessel}`) });
    }
    try {
      await senden("/api/firmen/waehlen", gewaehlt.value ? { link: gewaehlt.value } : { keine: true }, { firma: firma.schluessel });
      offen = null;
      await laden(firma.schluessel);
      meldung(gewaehlt.value ? Texte.t("{firma}: Seite bei kununu zugeordnet.", { firma: firma.name })
        : Texte.t("{name}: bei kununu nicht gefunden.", { name: firma.name }));
    } catch (fehler) {
      meldung(fehler.message, "warning");
    }
  }

  function oeffneDialog(firma) {
    zuordnen = firma;
    $("zuordnen-titel").textContent = text("firmen.dialog", { firma: firma.name });
    $("zuordnen-link").value = "";
    $("zuordnen-fehler").textContent = "";
    $("zuordnen-link").removeAttribute("aria-invalid");
    $("zuordnen-dialog").showModal();
  }

  async function dialogAbschicken(ereignis) {
    ereignis.preventDefault();
    try {
      await senden("/api/firmen/zuordnen", { link: $("zuordnen-link").value }, { firma: zuordnen.schluessel });
      $("zuordnen-dialog").close();
      await laden(zuordnen.schluessel);
      meldung(Texte.t("{firma}: Seite bei kununu zugeordnet. Der Wert kommt mit der nächsten Prüfung.", { firma: zuordnen.name }));
    } catch (fehler) {
      const abgelehnt = window.Meldungen.isInputRejection(fehler);
      $("zuordnen-link").setAttribute("aria-invalid", "true");
      $("zuordnen-fehler").textContent = abgelehnt ? text("firmen.dialog-fehler") : fehler.message;
      if (abgelehnt) window.Meldungen.clearOnInput($("zuordnen-fehler"), $("zuordnen-link"));
      $("zuordnen-link").focus();
    }
  }

  function oeffneVonHand(firma) {
    vonHand = firma;
    $("hand-titel").textContent = Texte.t("kununu-Wert für {firma} eintragen", { firma: firma.name });
    for (const feld of ["wert", "bewertungen"]) {
      $(`hand-${feld}`).value = "";
      $(`hand-${feld}`).removeAttribute("aria-invalid");
      $(`hand-${feld}-fehler`).textContent = "";
    }
    $("hand-dialog").showModal();
  }

  async function vonHandAbschicken(ereignis) {
    ereignis.preventDefault();
    const werte = logik.vonHandWerte($("hand-wert").value, $("hand-bewertungen").value);
    for (const feld of ["wert", "bewertungen"]) {
      const falsch = werte.feld === feld;
      $(`hand-${feld}-fehler`).textContent = falsch ? werte.fehler : "";
      if (falsch) $(`hand-${feld}`).setAttribute("aria-invalid", "true");
      else $(`hand-${feld}`).removeAttribute("aria-invalid");
      if (falsch) window.Meldungen.clearOnInput($(`hand-${feld}-fehler`), $(`hand-${feld}`));
    }
    if (werte.fehler) return $(`hand-${werte.feld}`).focus();
    try {
      await senden("/api/firmen/von-hand", werte, { firma: vonHand.schluessel });
      $("hand-dialog").close();
      nichtGelesen.delete(vonHand.schluessel);
      await laden(vonHand.schluessel);
      meldung(Texte.t("{firma}: kununu-Wert eingetragen.", { firma: vonHand.name }), "success");
    } catch (fehler) {
      $("hand-wert-fehler").textContent = fehler.message;
    }
  }

  function verbinden() {
    for (const kopf of document.querySelectorAll("th[data-spalte]")) {
      kopf.querySelector("button").addEventListener("click", () => { sortierung = logik.naechsteSortierung(sortierung, kopf.dataset.spalte); zeige(); });
    }
    for (const knopf of document.querySelectorAll("[data-filter]")) {
      knopf.addEventListener("click", () => { filter = logik.gueltigerFilter(knopf.dataset.filter); zeige(); });
    }
    $("suche").addEventListener("input", () => zeige());
    $("zuordnen-form").addEventListener("submit", dialogAbschicken);
    $("zuordnen-abbrechen").addEventListener("click", () => { $("zuordnen-dialog").close(); fokusAuf(zuordnen.schluessel); });
    $("hand-form").addEventListener("submit", vonHandAbschicken);
    $("hand-abbrechen").addEventListener("click", () => { $("hand-dialog").close(); fokusAuf(vonHand.schluessel); });
  }

  verbinden();
  window.App.textsatz().then(gewaehlt => {
    satz = gewaehlt;
    $("suche").placeholder = text("firmen.suchen");
    document.title = text("firmen.titel");
    return laden();
  }).catch(fehler => meldung(fehler.message, "warning"));
})();
