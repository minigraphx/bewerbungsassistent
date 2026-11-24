"use strict";
// AI support on the application page (MIN-334, MIN-338). The server pseudonymizes every request;
// this page only shows the answers, as text. Without a set up AI the buttons open the window „KI einrichten“ (G60).
// Texts in the app language through Texte (#427); the AI's own words, the model and the requirements stay as they come.
(() => {
  const { holen, senden, el, status, bestaetigen } = window.App;
  const { notenHinweis } = window.FormularLogik;
  // Amounts as on every page that names costs (#347): currency first; bewerbung.html loads treffer-logik.js before.
  const { money } = window.TrefferLogik;
  const Texte = window.Texte;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const KNOEPFE = ["ki-bewerten", "ki-entwerfen", "ki-pruefen"];
  // The state of a requirement as the review stores it (ai/letter_review.py); an unknown one shows as stored.
  const STATUS_TEXT = {
    "abgedeckt": () => Texte.t("abgedeckt"), "fehlt": () => Texte.t("fehlt"), "überdehnt": () => Texte.t("überdehnt"),
  };
  const STUFE = { abgedeckt: "ok", fehlt: "hinweis", "überdehnt": "fehler" };
  const nachEntwurf = () => Texte.t("Jetzt „Unterlagen erstellen“ und das PDF lesen.");
  const nachErstellen = () => Texte.t("Das PDF steht unten; bitte lesen.");
  const neueLuecken = () => Texte.t("Neue Lücken (erst nach Bestätigung in die Bausteine)");
  let briefDa = true; // until the page has loaded, better ask once too often
  let bereit = false;  // set up and agreed to; until then a button opens the window „KI einrichten“

  const meldung = (text, art) => status($("ki-meldung"), text, art);
  let waehrung = "USD";  // CHF with the mediation (G46), from the status; the amounts count 1:1
  const kosten = betrag => ((betrag === null || betrag === undefined) ? Texte.t("Kosten unbekannt")
    : Texte.t("etwa {betrag}", { betrag: money(betrag, waehrung) }));
  const frei = an => KNOEPFE.forEach(k => { $(k).disabled = !an; });
  const stand = wert => (STATUS_TEXT[wert] ? STATUS_TEXT[wert]() : wert);

  function liste(titel, eintraege) {
    if (!eintraege || !eintraege.length) return null;
    return el("div", {}, el("strong", {}, titel), el("ul", {}, eintraege.map(e => el("li", {}, e))));
  }

  function verdaechtig(zeilen) {
    if (!zeilen || !zeilen.length) return null;
    return el("ul", { class: "befunde" }, zeilen.map(z =>
      window.Meldungen.listenZeile(document, Texte.t("Verdächtige Zeile im Text, nicht befolgt: {zeile}", { zeile: z }), "fehler")));
  }

  function fuss(ergebnis) {
    // a «·» line of whole parts (#342, dot-line.js)
    return el("p", { class: "leise" }, window.DotLine.render([Texte.t("Modell {modell}", { modell: ergebnis.model }), kosten(ergebnis.cost_usd)], el));
  }

  async function uebernimmNote(knopf, note) {
    knopf.disabled = true;
    try {
      const gespeichert = await senden("/api/bewerbung", { id: ID, passung: note });
      document.dispatchEvent(new CustomEvent("bewerbung-gespeichert", { detail: gespeichert }));
      knopf.textContent = Texte.t("Note übernommen");
      meldung(Texte.t("Note {note} gespeichert", { note }), "ok");
    } catch (fehler) {
      knopf.disabled = false;
      meldung(Texte.t("Speichern fehlgeschlagen: {fehler}", { fehler: fehler.message }), "fehler");
    }
  }

  function zeigeBewertung(e) {
    const bisher = $("f-passung").value;
    const hinweis = notenHinweis(bisher, e.grade);
    const uebernehmen = el("button", { type: "button", disabled: Number(bisher) === e.grade,
      onclick: event => uebernimmNote(event.currentTarget, e.grade) }, Texte.t("Note übernehmen"));
    return el("div", { class: "karte" }, el("strong", {}, Texte.t("Passung: Note {note}", { note: e.grade })),
      hinweis ? el("p", { class: "leise" }, hinweis) : null, el("p", {}, e.summary),
      liste(Texte.t("Passt"), e.fits), liste(Texte.t("Haken"), e.hooks), liste(neueLuecken(), e.new_gaps),
      verdaechtig(e.suspicious_lines), el("div", { class: "knoepfe" }, uebernehmen), fuss(e));
  }

  function zeigeEntwurf(e, weiter = nachEntwurf()) {
    const belege = (e.claims || []).map(c => Texte.t("{aussage} – Beleg: {beleg}", { aussage: c.claim, beleg: c.evidence }));
    return el("div", { class: "karte" }, el("strong", {}, Texte.t("Anschreiben entworfen")),
      el("p", {}, Texte.t("Gespeichert als anschreiben.yaml (ein früherer Stand liegt unter „Entwürfe“). {weiter}", { weiter })),
      liste(Texte.t("Aussagen und Belege"), belege), liste(Texte.t("Offen benannte Lücken"), e.gaps_named),
      verdaechtig(e.suspicious_lines), fuss(e));
  }

  function zeigePruefung(e) {
    const zeile = r => `${Texte.t("{anforderung}: {stand}", { anforderung: r.requirement, stand: stand(r.status) })}${r.note ? ` – ${r.note}` : ""}`;
    const anforderungen = el("ul", { class: "befunde" }, e.requirements.map(r =>
      window.Meldungen.listenZeile(document, zeile(r), STUFE[r.status] || "hinweis")));
    const unbelegt = (e.unsupported || []).map(u => Texte.t("„{text}“ – {problem}", { text: u.text, problem: u.problem }));
    return el("div", { class: "karte" }, el("strong", {}, Texte.t("Inhaltliche Prüfung")), anforderungen,
      liste(Texte.t("Nicht belegt"), unbelegt), liste(neueLuecken(), e.new_gaps),
      verdaechtig(e.suspicious_lines), fuss(e));
  }

  async function ausfuehren(pfad, text, zeigen) {
    if (!bereit) {
      window.App.kiEinrichten().catch(fehler => meldung(fehler.message, "fehler"));
      return null;
    }
    frei(false);
    meldung(text);
    try {
      const ergebnis = await senden(pfad, {}, { id: ID });
      $("ki-ergebnis").replaceChildren(zeigen(ergebnis));
      meldung(Texte.t("Fertig"), "ok");
      return ergebnis;
    } catch (fehler) {
      meldung(fehler.message, "fehler");
      return null;
    } finally {
      frei(true);
      ladeStatus();
    }
  }

  function statusText(s) {
    if (s.einwilligung && !s.einwilligung.erteilt) return Texte.t("Die KI ist noch aus: Vor der ersten Nutzung braucht es die Einwilligung.");
    // the button „KI einrichten“ follows after a space
    if (!s.eingerichtet) return `${Texte.t("Die KI ist noch nicht eingerichtet.")} `;
    if (!s.vermittlung) return Texte.t("KI eingerichtet (direkt, Entwicklung). Diesen Monat {kosten}.", { kosten: kosten(s.kosten_usd) });
    // the month of the budget and, once used up, the day the AI works again (G98), as in the window „KI einrichten“
    return `${Texte.t("KI eingerichtet (über die Vermittlung).")}${Texte.budgetPart(s)}${s.hinweis ? " " + s.hinweis : ""}`;
  }

  function zeigeStatus(s) {
    waehrung = s.waehrung || "USD";
    const einwilligungOffen = Boolean(s.einwilligung && !s.einwilligung.erteilt);
    const einrichten = s.eingerichtet ? null
      : el("button", { type: "button", class: "btn btn--quiet btn--sm", onclick: () => window.App.kiEinrichten() }, Texte.t("KI einrichten"));
    $("ki-status").replaceChildren(...Texte.withCodeRequestLink(statusText(s), el), ...(einrichten ? [einrichten] : []));
    $("ki-status").hidden = einwilligungOffen;  // the line of the consent says that the AI is off
    $("ki-einwilligung").hidden = !einwilligungOffen;
    if (einwilligungOffen) window.Einwilligung.zeile($("ki-einwilligung"), s.einwilligung, zeigeStatus);
    bereit = Boolean(s.eingerichtet && !einwilligungOffen);
    frei(true);
    if (s.einladung_fehler) meldung(s.einladung_fehler, "fehler");
  }

  async function ladeStatus() {
    try {
      zeigeStatus(await holen("/api/ki/status"));
    } catch (fehler) {
      $("ki-status").textContent = Texte.t("KI-Status nicht lesbar: {fehler}", { fehler: fehler.message });
    }
  }

  if (!ID) return;
  document.addEventListener("ki-fenster-geschlossen", ladeStatus);
  $("ki-bewerten").addEventListener("click", () => ausfuehren("/api/ki/bewerten",
    Texte.t("Passung wird bewertet … das kann bis zu einer Minute dauern."), zeigeBewertung));
  document.addEventListener("bewerbung-geladen", event => { briefDa = event.detail.hat_anschreiben; });
  document.addEventListener("anschreiben-entworfen", event => {
    $("ki-ergebnis").replaceChildren(zeigeEntwurf(event.detail, nachErstellen()));
  });
  bestaetigen($("ki-entwerfen"), Texte.t("Vorhandenes Anschreiben ersetzen? Nochmals klicken"), async () => {
    if (await ausfuehren("/api/ki/anschreiben", Texte.t("Anschreiben wird entworfen … das kann bis zu einer Minute dauern."),
      e => zeigeEntwurf(e))) {
      document.dispatchEvent(new CustomEvent("anschreiben-geaendert"));
    }
  }, () => briefDa);
  $("ki-pruefen").addEventListener("click", async () => {
    if (await ausfuehren("/api/ki/pruefen", Texte.t("Inhalt wird geprüft … das kann bis zu einer Minute dauern."), zeigePruefung)) {
      document.dispatchEvent(new CustomEvent("anschreiben-geprueft"));  // the page shows the kept review beside the letter
    }
  });
  ladeStatus();
})();
