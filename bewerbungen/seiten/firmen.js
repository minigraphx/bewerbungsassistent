"use strict";
// The page Firmen (G35, #188, docs/design/firmen.md): one row per company from hits and applications, with what
// kununu says. „Prüfen“ opens the company at kununu in a new tab; reading the value there is #189.
(() => {
  const { holen, senden, el } = window.App;
  const logik = window.FirmenLogik;
  const $ = id => document.getElementById(id);
  const ARIA_SORT = { aufsteigend: "ascending", absteigend: "descending" };
  const NEUER_TAB = ", öffnet neuen Tab";

  let firmen = [];
  let heute = "";
  let satz = "stelle-sie";
  let filter = "alle";
  let sortierung = logik.STANDARD_SORTIERUNG;
  let offen = null;      // the company whose choice of several is open
  let zuordnen = null;   // the company of the dialog „Selbst zuordnen“

  const text = (schluessel, werte) => window.Texte.text(schluessel, satz, werte);
  const meldung = (inhalt, stufe = "") => { $("status").textContent = inhalt; $("status").dataset.level = stufe; };

  function extern(href, beschriftung, firma, klasse = "btn btn--sm") {
    return el("a", { class: klasse, href, target: "_blank", rel: "noopener noreferrer" }, beschriftung,
      el("span", { class: "visually-hidden" }, `: ${firma.name}${NEUER_TAB}`));
  }

  function pruefenKnopf(firma, beschriftung) {
    return el("button", { type: "button", class: "btn btn--sm", "data-firma": firma.schluessel,
      onclick: () => window.open(logik.pruefenLink(firma), "_blank", "noopener,noreferrer") },
    beschriftung, el("span", { class: "visually-hidden" }, `: ${firma.name}${NEUER_TAB}`));
  }

  function knopf(firma, beschriftung, aktion, attribute = {}) {
    return el("button", { type: "button", class: "btn btn--sm", "data-firma": firma.schluessel, onclick: aktion, ...attribute }, beschriftung);
  }

  function lernende(k) {
    if (satz !== "lehrstelle-du" || !k.lernende?.bewertungen) return null;
    return el("span", { class: "rating__meta" }, `Lernende: ${logik.wert(k.lernende.wert)} von 5, ${logik.bewertungen(k.lernende.bewertungen)}`);
  }

  function wertBlock(firma, zustand) {
    const k = firma.kununu;
    const wenige = zustand === "wenige";
    const meta = wenige ? `Nur ${logik.bewertungen(k.bewertungen)}, wenig aussagekräftig.`
      : [logik.bewertungen(k.bewertungen), typeof k.empfehlung === "number" ? `${logik.prozent(k.empfehlung)} empfehlen` : ""].filter(Boolean).join(" · ");
    return el("div", { class: "rating", "data-state": wenige ? "few" : null },
      el("span", { class: "rating__value" }, el("b", {}, logik.wert(k.wert)), " von 5"),
      el("span", { class: "rating__meta" }, meta), lernende(k), el("span", { class: "rating__meta" }, logik.seite(k)));
  }

  function kununuZelle(firma) {
    const zustand = logik.zustand(firma);
    if (logik.MIT_WERT.includes(zustand)) return wertBlock(firma, zustand);
    if (zustand === "fehler") {
      return el("p", { class: "status-line", "data-level": "warning" }, "Nicht geprüft. kununu war nicht erreichbar. Bitte später nochmals prüfen.");
    }
    const worte = { keine: "Noch keine Bewertungen", mehrere: text("firmen.mehrere"), nicht_gefunden: "Bei kununu nicht gefunden",
                    zugeordnet: "Noch nicht geprüft, Seite zugeordnet", ungeprueft: "Noch nicht geprüft" };
    return el("span", { class: zustand === "mehrere" ? "rating__state" : "rating__state rating__state--quiet" }, worte[zustand]);
  }

  function verknuepft(firma) {
    const bewerbungen = firma.bewerbungen.map(b => el("span", { class: "line" },
      el("a", { href: "/bewerbung?" + new URLSearchParams({ id: b.id }) }, b.stelle || "Bewerbung"),
      el("span", { class: "marke-status", "data-status": b.status }, window.Texte.statusName(b.status, satz))));
    const treffer = firma.treffer.length ? [el("span", { class: "line" }, el("a", { href: "/treffer" }, logik.trefferText(firma.treffer)))] : [];
    return el("div", { class: "companies__links" }, ...bewerbungen, ...treffer);
  }

  function geprueft(firma) {
    const am = firma.kununu?.geprueft_am;
    if (!am || logik.zustand(firma) === "zugeordnet") return el("span", { class: "muted" }, "–");
    return logik.veraltet(firma, heute) ? [el("span", { class: "muted" }, "Stand "), logik.datum(am)] : logik.datum(am);
  }

  function aktionen(firma) {
    const zustand = logik.zustand(firma);
    const k = firma.kununu || {};
    const ansehen = k.link ? extern(k.link, "Bei kununu ansehen", firma) : null;
    const selbst = knopf(firma, "Selbst zuordnen", () => oeffneDialog(firma));
    const je = {
      ungeprueft: [pruefenKnopf(firma, "Prüfen")],
      zugeordnet: [pruefenKnopf(firma, "Prüfen"), ansehen],
      fehler: [pruefenKnopf(firma, "Nochmals prüfen")],
      nicht_gefunden: [extern(firma.suche, "Bei kununu suchen", firma, "btn btn--sm btn--quiet"), selbst],
      mehrere: [knopf(firma, "Passende wählen", () => waehlen(firma),
        { "aria-expanded": String(offen === firma.schluessel), "aria-controls": `wahl-${firma.schluessel}` })],
    };
    const gefunden = [logik.veraltet(firma, heute) ? pruefenKnopf(firma, "Neu prüfen") : null, ansehen];
    return el("div", { class: "btn-row" }, ...(je[zustand] || gefunden).filter(Boolean));
  }

  function zeile(firma) {
    return el("tr", { "data-schluessel": firma.schluessel, class: offen === firma.schluessel ? "is-open" : null },
      el("td", { "data-label": "" }, el("span", { class: "table__main" }, firma.name), firma.ort ? el("span", { class: "table__sub" }, firma.ort) : null),
      el("td", { "data-label": "kununu" }, kununuZelle(firma)),
      el("td", { "data-label": "Treffer und Bewerbungen" }, verknuepft(firma)),
      el("td", { "data-label": "Geprüft", class: "num" }, geprueft(firma)),
      el("td", { "data-label": "", class: "companies__actions" }, aktionen(firma)));
  }

  function wahlZeile(firma) {
    const name = `wahl-${firma.schluessel}`;
    const kandidaten = (firma.kununu.kandidaten || []).map(kandidat => el("label", { class: "choice" },
      el("input", { type: "radio", name, value: kandidat.link }),
      el("span", {}, el("span", { class: "choice__name" }, kandidat.name),
        el("span", { class: "choice__meta" }, [kandidat.ort, kandidat.branche, typeof kandidat.bewertungen === "number" ? logik.bewertungen(kandidat.bewertungen) : ""].filter(Boolean).join(" · "))),
      el("a", { href: kandidat.link, target: "_blank", rel: "noopener noreferrer" }, "Bei kununu ansehen",
        el("span", { class: "visually-hidden" }, `: ${kandidat.name}${NEUER_TAB}`))));
    const keine = el("label", { class: "choice" }, el("input", { type: "radio", name, value: "" }), el("span", {}, el("span", { class: "choice__name" }, "Keine davon passt")), el("span", {}));
    const legende = el("legend", { tabindex: "-1" }, `Welche ist ${[firma.name, firma.ort].filter(Boolean).join(", ")}?`);
    return el("tr", { class: "chooser", id: name }, el("td", { colspan: "5", "data-label": "" }, el("fieldset", {}, legende,
      el("p", { class: "field__hint" }, "Ort und Branche helfen beim Wählen."), ...kandidaten, keine,
      el("div", { class: "btn-row" },
        el("button", { type: "button", class: "btn btn--sm btn--primary", onclick: () => zuordnenAusWahl(firma) }, "Zuordnen"),
        el("button", { type: "button", class: "btn btn--sm", onclick: () => { offen = null; zeige(firma.schluessel); } }, "Abbrechen")))));
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
    $("zeile").textContent = [text("firmen.zeile", { anzahl, gefunden }), zuletzt ? `zuletzt geprüft am ${logik.datum(zuletzt)}` : ""].filter(Boolean).join(" · ");
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
    if (!gewaehlt) return meldung("Bitte eine Firma wählen oder «Keine davon passt».", "warning");
    try {
      await senden("/api/firmen/waehlen", gewaehlt.value ? { link: gewaehlt.value } : { keine: true }, { firma: firma.schluessel });
      offen = null;
      await laden(firma.schluessel);
      meldung(gewaehlt.value ? `${firma.name}: Seite bei kununu zugeordnet.` : `${firma.name}: bei kununu nicht gefunden.`);
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
      meldung(`${zuordnen.name}: Seite bei kununu zugeordnet. Der Wert kommt mit der nächsten Prüfung.`);
    } catch (fehler) {
      $("zuordnen-link").setAttribute("aria-invalid", "true");
      $("zuordnen-fehler").textContent = fehler.status === 400 ? text("firmen.dialog-fehler") : fehler.message;
      $("zuordnen-link").focus();
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
  }

  verbinden();
  window.App.textsatz().then(gewaehlt => {
    satz = gewaehlt;
    $("suche").placeholder = text("firmen.suchen");
    document.title = text("firmen.titel");
    return laden();
  }).catch(fehler => meldung(fehler.message, "warning"));
})();
