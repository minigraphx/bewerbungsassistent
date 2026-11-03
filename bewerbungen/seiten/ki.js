"use strict";
// AI support on the application page (MIN-334, MIN-338). The server pseudonymizes every request;
// this page only shows the answers, as text.
(() => {
  const { holen, senden, el, status, bestaetigen } = window.App;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const KNOEPFE = ["ki-bewerten", "ki-entwerfen", "ki-pruefen"];
  const STATUS_TEXT = { abgedeckt: "abgedeckt", fehlt: "fehlt", "überdehnt": "überdehnt" };
  const STUFE = { abgedeckt: "ok", fehlt: "hinweis", "überdehnt": "fehler" };

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
      el("li", { "data-stufe": "fehler" }, "Verdächtige Zeile im Text, nicht befolgt: " + z)));
  }

  function fuss(ergebnis) {
    return el("p", { class: "leise" }, `Modell ${ergebnis.model} · ${kosten(ergebnis.cost_usd)}`);
  }

  function zeigeBewertung(e) {
    const uebernehmen = el("button", { type: "button", onclick: () => {
      $("f-passung").value = e.grade;
      meldung(`Note ${e.grade} eingesetzt – „Angaben speichern“ nicht vergessen`, "hinweis");
    } }, "Note übernehmen");
    return el("div", { class: "karte" }, el("strong", {}, `Passung: Note ${e.grade}`), el("p", {}, e.summary),
      liste("Passt", e.fits), liste("Haken", e.hooks),
      liste("Neue Lücken (erst nach Bestätigung in die Bausteine)", e.new_gaps),
      verdaechtig(e.suspicious_lines), el("div", { class: "knoepfe" }, uebernehmen), fuss(e));
  }

  function zeigeEntwurf(e) {
    const belege = (e.claims || []).map(c => `${c.claim} – Beleg: ${c.evidence}`);
    return el("div", { class: "karte" }, el("strong", {}, "Anschreiben entworfen"),
      el("p", {}, "Gespeichert als anschreiben.yaml (der alte Stand liegt unter „Entwürfe“). Jetzt „Unterlagen erstellen“ und das PDF lesen."),
      liste("Aussagen und Belege", belege), liste("Offen benannte Lücken", e.gaps_named),
      verdaechtig(e.suspicious_lines), fuss(e));
  }

  function zeigePruefung(e) {
    const anforderungen = el("ul", { class: "befunde" }, e.requirements.map(r =>
      el("li", { "data-stufe": STUFE[r.status] || "hinweis" }, `${r.requirement}: ${STATUS_TEXT[r.status] || r.status}`,
        r.note ? ` – ${r.note}` : "")));
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

  async function ladeStatus() {
    try {
      const s = await holen("/api/ki/status");
      const monat = `Diesen Monat ${kosten(s.kosten_usd)}.`;
      $("ki-status").textContent = s.eingerichtet
        ? `KI eingerichtet${s.vermittlung ? " (über die Vermittlung)" : " (direkt, Entwicklung)"}. ${monat}`
        : `${s.hinweis} ${monat}`;
      frei(s.eingerichtet);
    } catch (fehler) {
      $("ki-status").textContent = "KI-Status nicht lesbar: " + fehler.message;
    }
  }

  if (!ID) return;
  $("ki-bewerten").addEventListener("click", () => ausfuehren("/api/ki/bewerten", "Passung wird bewertet", zeigeBewertung));
  bestaetigen($("ki-entwerfen"), "Ersetzt anschreiben.yaml – nochmals klicken", async () => {
    if (await ausfuehren("/api/ki/anschreiben", "Anschreiben wird entworfen", zeigeEntwurf)) {
      document.dispatchEvent(new CustomEvent("anschreiben-geaendert"));
    }
  });
  $("ki-pruefen").addEventListener("click", () => ausfuehren("/api/ki/pruefen", "Inhalt wird geprüft", zeigePruefung));
  ladeStatus();
})();
