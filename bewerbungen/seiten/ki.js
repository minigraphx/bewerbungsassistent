"use strict";
// AI support on the application page (MIN-334, MIN-338). The server pseudonymizes every request;
// this page only shows the answers, as text.
(() => {
  const { holen, senden, el, status, bestaetigen } = window.App;
  const { notenHinweis } = window.FormularLogik;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const KNOEPFE = ["ki-bewerten", "ki-entwerfen", "ki-pruefen"];
  const STATUS_TEXT = { abgedeckt: "abgedeckt", fehlt: "fehlt", "überdehnt": "überdehnt" };
  const STUFE = { abgedeckt: "ok", fehlt: "hinweis", "überdehnt": "fehler" };
  const NACH_ENTWURF = "Jetzt „Unterlagen erstellen“ und das PDF lesen.";
  const NACH_ERSTELLEN = "Das PDF steht unten; bitte lesen.";
  let briefDa = true; // until the page has loaded, better ask once too often

  const meldung = (text, art) => status($("ki-meldung"), text, art);
  const kosten = usd => (usd === null || usd === undefined) ? "Kosten unbekannt" : `ca. ${usd.toFixed(2)} USD`;
  const frei = an => KNOEPFE.forEach(k => { $(k).disabled = !an; });

  function liste(titel, eintraege) {
    if (!eintraege || !eintraege.length) return null;
    return el("div", {}, el("strong", {}, titel), el("ul", {}, eintraege.map(e => el("li", {}, e))));
  }

  function verdaechtig(zeilen) {
    if (!zeilen || !zeilen.length) return null;
    return el("ul", { class: "befunde" }, zeilen.map(z =>
      window.Meldungen.listenZeile(document, "Verdächtige Zeile im Text, nicht befolgt: " + z, "fehler")));
  }

  function fuss(ergebnis) {
    return el("p", { class: "leise" }, `Modell ${ergebnis.model} · ${kosten(ergebnis.cost_usd)}`);
  }

  async function uebernimmNote(knopf, note) {
    knopf.disabled = true;
    try {
      const gespeichert = await senden("/api/bewerbung", { id: ID, passung: note });
      document.dispatchEvent(new CustomEvent("bewerbung-gespeichert", { detail: gespeichert }));
      knopf.textContent = "Note übernommen";
      meldung(`Note ${note} gespeichert`, "ok");
    } catch (fehler) {
      knopf.disabled = false;
      meldung("Speichern fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  function zeigeBewertung(e) {
    const bisher = $("f-passung").value;
    const hinweis = notenHinweis(bisher, e.grade);
    const uebernehmen = el("button", { type: "button", disabled: Number(bisher) === e.grade,
      onclick: event => uebernimmNote(event.currentTarget, e.grade) }, "Note übernehmen");
    return el("div", { class: "karte" }, el("strong", {}, `Passung: Note ${e.grade}`),
      hinweis ? el("p", { class: "leise" }, hinweis) : null, el("p", {}, e.summary),
      liste("Passt", e.fits), liste("Haken", e.hooks),
      liste("Neue Lücken (erst nach Bestätigung in die Bausteine)", e.new_gaps),
      verdaechtig(e.suspicious_lines), el("div", { class: "knoepfe" }, uebernehmen), fuss(e));
  }

  function zeigeEntwurf(e, weiter = NACH_ENTWURF) {
    const belege = (e.claims || []).map(c => `${c.claim} – Beleg: ${c.evidence}`);
    return el("div", { class: "karte" }, el("strong", {}, "Anschreiben entworfen"),
      el("p", {}, `Gespeichert als anschreiben.yaml (ein früherer Stand liegt unter „Entwürfe“). ${weiter}`),
      liste("Aussagen und Belege", belege), liste("Offen benannte Lücken", e.gaps_named),
      verdaechtig(e.suspicious_lines), fuss(e));
  }

  function zeigePruefung(e) {
    const anforderungen = el("ul", { class: "befunde" }, e.requirements.map(r =>
      window.Meldungen.listenZeile(document,
        `${r.requirement}: ${STATUS_TEXT[r.status] || r.status}${r.note ? ` – ${r.note}` : ""}`, STUFE[r.status] || "hinweis")));
    const unbelegt = (e.unsupported || []).map(u => `„${u.text}“ – ${u.problem}`);
    return el("div", { class: "karte" }, el("strong", {}, "Inhaltliche Prüfung"), anforderungen,
      liste("Nicht belegt", unbelegt), liste("Neue Lücken (erst nach Bestätigung in die Bausteine)", e.new_gaps),
      verdaechtig(e.suspicious_lines), fuss(e));
  }

  async function ausfuehren(pfad, text, zeigen) {
    frei(false);
    meldung(text + " … das kann bis zu einer Minute dauern.");
    try {
      const ergebnis = await senden(pfad, {}, { id: ID });
      $("ki-ergebnis").replaceChildren(zeigen(ergebnis));
      meldung("Fertig", "ok");
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
    if (s.einwilligung && !s.einwilligung.erteilt) return "Die KI ist noch aus: Vor der ersten Nutzung braucht es die Einwilligung.";
    if (!s.eingerichtet) return s.einladung ? "Die KI ist noch nicht eingerichtet: Einladungscode unten eingeben." : s.hinweis;
    if (!s.vermittlung) return `KI eingerichtet (direkt, Entwicklung). Diesen Monat ${kosten(s.kosten_usd)}.`;
    const budget = typeof s.budget_usd === "number"
      ? ` Budget diesen Monat: ${kosten(s.verbraucht_usd)} von ${s.budget_usd.toFixed(2)} USD.` : "";
    return `KI eingerichtet (über die Vermittlung).${budget}${s.hinweis ? " " + s.hinweis : ""}`;
  }

  function zeigeStatus(s) {
    const einwilligungOffen = Boolean(s.einwilligung && !s.einwilligung.erteilt);
    $("ki-status").textContent = statusText(s);
    $("ki-status").hidden = einwilligungOffen;  // the line of the consent says that the AI is off
    $("ki-einwilligung").hidden = !einwilligungOffen;
    if (einwilligungOffen) window.Einwilligung.zeile($("ki-einwilligung"), s.einwilligung, zeigeStatus);
    $("ki-einladung").hidden = s.eingerichtet || !s.einladung || einwilligungOffen;
    frei(s.eingerichtet && !einwilligungOffen);
    if (s.einladung_fehler) meldung(s.einladung_fehler, "fehler");
  }

  async function ladeStatus() {
    try {
      zeigeStatus(await holen("/api/ki/status"));
    } catch (fehler) {
      $("ki-status").textContent = "KI-Status nicht lesbar: " + fehler.message;
    }
  }

  async function einloesen() {
    $("ki-einloesen").disabled = true;
    try {
      zeigeStatus(await senden("/api/ki/einladung", { code: $("ki-code").value }));
      $("ki-code").value = "";
      meldung("Einladung eingelöst. Die KI ist bereit.", "ok");
    } catch (fehler) {
      meldung(fehler.message, "fehler");
    } finally {
      $("ki-einloesen").disabled = false;
    }
  }

  if (!ID) return;
  $("ki-einloesen").addEventListener("click", einloesen);
  $("ki-bewerten").addEventListener("click", () => ausfuehren("/api/ki/bewerten", "Passung wird bewertet", zeigeBewertung));
  document.addEventListener("bewerbung-geladen", event => { briefDa = event.detail.hat_anschreiben; });
  document.addEventListener("anschreiben-entworfen", event => {
    $("ki-ergebnis").replaceChildren(zeigeEntwurf(event.detail, NACH_ERSTELLEN));
  });
  bestaetigen($("ki-entwerfen"), "Vorhandenes Anschreiben ersetzen? Nochmals klicken", async () => {
    if (await ausfuehren("/api/ki/anschreiben", "Anschreiben wird entworfen", e => zeigeEntwurf(e))) {
      document.dispatchEvent(new CustomEvent("anschreiben-geaendert"));
    }
  }, () => briefDa);
  $("ki-pruefen").addEventListener("click", async () => {
    if (await ausfuehren("/api/ki/pruefen", "Inhalt wird geprüft", zeigePruefung)) {
      document.dispatchEvent(new CustomEvent("anschreiben-geprueft"));  // the page shows the kept review beside the letter
    }
  });
  ladeStatus();
})();
