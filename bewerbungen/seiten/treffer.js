"use strict";
// Hits of the job search (MIN-339): list, rate with the AI, take over into the register, discard.
// The search itself runs in the browser extension; this page starts it through app-bridge.js.
(() => {
  const { holen, senden, el, status, datum } = window.App;
  const $ = id => document.getElementById(id);
  const SEITE = "bewerbungsassistent-seite";
  const ERWEITERUNG = "bewerbungsassistent-erweiterung";

  let alle = [];
  const offen = new Set();  // ids with details shown

  function anzeigen(treffer) {
    alle = alle.map(t => (t.id === treffer.id ? treffer : t));
    zeigeListe();
  }

  async function bewerte(t, knopf) {
    if (knopf) knopf.disabled = true;
    status($("status"), `KI bewertet „${t.stelle}“ …`);
    try {
      anzeigen(await senden("/api/suche/bewerten", {}, { id: t.id }));
      offen.add(t.id);
      zeigeListe();
      status($("status"), "");
      return true;
    } catch (fehler) {
      status($("status"), `${t.stelle}: ${fehler.message}`, "fehler");
      if (knopf) knopf.disabled = false;
      return false;
    }
  }

  async function uebernimm(t, knopf) {
    knopf.disabled = true;
    try {
      const neu = await senden("/api/suche/uebernehmen", {}, { id: t.id });
      anzeigen(neu);
      status($("status"), `„${t.stelle}“ ist jetzt im Register.`, "ok");
    } catch (fehler) {
      status($("status"), fehler.message, "fehler");
      knopf.disabled = false;
      lade();
    }
  }

  async function verwirf(t, zurueck) {
    try {
      anzeigen(await senden("/api/suche/verwerfen", { zurueck }, { id: t.id }));
    } catch (fehler) {
      status($("status"), fehler.message, "fehler");
    }
  }

  function liste(titel, eintraege) {
    return eintraege && eintraege.length ? el("div", {}, el("strong", {}, titel), el("ul", {}, eintraege.map(e => el("li", {}, e)))) : null;
  }

  function details(t) {
    const b = t.bewertung;
    const text = el("pre", { class: "inserat", hidden: true });
    const knopf = el("button", { type: "button" }, "Inserat anzeigen");
    knopf.addEventListener("click", async () => {
      if (text.hidden && !text.textContent) {
        try { text.textContent = (await holen("/api/suche/text", { id: t.id })).text || "Kein Text gespeichert."; }
        catch (fehler) { text.textContent = fehler.message; }
      }
      text.hidden = !text.hidden;
      knopf.textContent = text.hidden ? "Inserat anzeigen" : "Inserat verbergen";
    });
    const weitere = (t.weitere || []).map(w => el("li", {}, el("a", { href: w.link, target: "_blank", rel: "noopener" }, `Auch auf ${w.portal}`)));
    return el("td", { colspan: 8 },
      b ? el("p", {}, b.zusammenfassung) : el("p", { class: "leise" }, "Noch nicht bewertet."),
      b ? liste("Passt", b.passt) : null,
      b ? liste("Haken", b.haken) : null,
      b && b.auffaellig && b.auffaellig.length ? el("p", { class: "status fehler" },
        "Auffällige Zeilen im Inserat (nicht befolgt): " + b.auffaellig.join(" · ")) : null,
      t.hinweis ? el("p", { class: "status hinweis" }, t.hinweis) : null,
      weitere.length ? el("ul", {}, weitere) : null,
      el("div", { class: "knoepfe" }, knopf), text);
  }

  function aktionen(t) {
    if (t.zustand === "uebernommen") {
      return [el("a", { href: "/bewerbung?" + new URLSearchParams({ id: t.bewerbung_id }) }, "Zur Bewerbung")];
    }
    if (t.zustand === "verworfen") {
      return [el("button", { type: "button", onclick: () => verwirf(t, true) }, "Zurückholen")];
    }
    const bewerten = el("button", { type: "button" }, t.bewertung ? "Neu bewerten" : "Bewerten");
    bewerten.addEventListener("click", () => bewerte(t, bewerten));
    const uebernehmen = el("button", { type: "button", class: "haupt" }, "Übernehmen");
    uebernehmen.addEventListener("click", () => uebernimm(t, uebernehmen));
    return [bewerten, uebernehmen,
      el("button", { type: "button", onclick: () => verwirf(t, false) }, "Verwerfen")];
  }

  function zeile(t) {
    const note = t.bewertung ? String(t.bewertung.note).replace(".", ",") : "–";
    const umschalten = el("button", { type: "button", class: "link", "aria-expanded": String(offen.has(t.id)) }, t.stelle);
    umschalten.addEventListener("click", () => {
      if (offen.has(t.id)) offen.delete(t.id); else offen.add(t.id);
      zeigeListe();
    });
    const alter = t.alter_tage !== undefined
      ? el("div", { class: "leise" }, `${t.alter_tage} ${t.alter_tage === 1 ? "Tag" : "Tage"} online`) : null;
    const haupt = el("tr", {},
      el("td", { class: "note" }, note),
      el("td", {}, umschalten, " ", el("a", { href: t.link, target: "_blank", rel: "noopener", title: "Inserat auf dem Portal öffnen" }, "↗")),
      el("td", {}, t.firma, t.hinweis ? el("span", { class: "marke-status", "data-status": "Beworben", title: t.hinweis }, " schon beworben?") : null),
      el("td", {}, t.ort || ""), el("td", { class: "knapp" }, t.pensum || ""),
      el("td", {}, t.portal, (t.weitere || []).length ? ` +${t.weitere.length}` : ""),
      el("td", { class: "knapp" }, datum(t.gefunden_am), alter),
      el("td", {}, el("div", { class: "knoepfe" }, aktionen(t))));
    return offen.has(t.id) ? [haupt, el("tr", { class: "details" }, details(t))] : [haupt];
  }

  function zeigeListe() {
    const zustand = $("zustand").value;
    const sichtbar = alle.filter(t => !zustand || t.zustand === zustand)
      .sort((a, b) => (b.bewertung?.note ?? 0) - (a.bewertung?.note ?? 0) || (b.gefunden_am || "").localeCompare(a.gefunden_am || ""));
    $("liste").replaceChildren(...sichtbar.flatMap(zeile));
    $("leer").hidden = sichtbar.length > 0;
    const unbewertet = alle.filter(t => t.zustand === "neu" && !t.bewertung).length;
    $("alle-bewerten").hidden = unbewertet === 0;
    $("alle-bewerten").textContent = `Alle neuen bewerten (${unbewertet})`;
  }

  function zeigeLetzteSuche(lauf, hinweise) {
    if (lauf) {
      const neu = Object.values(lauf.portale || {}).reduce((summe, p) => summe + (p.neu || 0), 0);
      $("letzte").textContent = `Letzte Suche am ${datum(lauf.datum)}: ${neu} neue Treffer.`;
    }
    const probleme = Object.entries(lauf?.portale || {}).filter(([, p]) => p.problem).map(([, p]) => p.problem);
    $("probleme").replaceChildren(
      ...probleme.map(p => el("li", { "data-stufe": "fehler" }, p)),
      ...hinweise.map(h => el("li", { "data-stufe": "hinweis" }, h)));
  }

  async function lade() {
    try {
      const daten = await holen("/api/suche/liste");
      alle = daten.treffer;
      zeigeLetzteSuche(daten.letzte_suche, daten.hinweise || []);
      zeigeListe();
    } catch (fehler) {
      status($("status"), fehler.message, "fehler");
    }
  }

  async function alleBewerten() {
    $("alle-bewerten").disabled = true;
    const offenListe = alle.filter(t => t.zustand === "neu" && !t.bewertung);
    let fehler = 0;
    for (const t of offenListe) {
      if (!(await bewerte(t, null))) fehler += 1;
    }
    $("alle-bewerten").disabled = false;
    status($("status"), fehler ? `${offenListe.length - fehler} bewertet, ${fehler} nicht (siehe Meldung).`
      : `${offenListe.length} Treffer bewertet.`, fehler ? "hinweis" : "ok");
  }

  // Extension: present (marker or message), progress of a running search
  function erweiterungDa() {
    $("suchen").disabled = false;
    $("ohne-erweiterung").hidden = true;
  }

  function laufText(lauf) {
    if (lauf.zustand === "fehler") return [lauf.fehler || "Die Suche ist abgebrochen.", "fehler"];
    if (lauf.zustand === "fertig") return ["Suche fertig.", "ok"];
    const s = lauf.schritt || {};
    if (s.phase === "suche") return [`${s.portal}: suche „${s.stichwort}“, Seite ${s.seite} …`, ""];
    if (s.phase === "texte") return [`${s.portal}: lese Inserate (${s.fertig} von ${s.von}) …`, ""];
    return ["Suche startet …", ""];
  }

  window.addEventListener("message", event => {
    if (event.source !== window || event.origin !== location.origin) return;
    const daten = event.data;
    if (!daten || daten.quelle !== ERWEITERUNG) return;
    erweiterungDa();
    if (daten.art === "lauf") {
      const [text, art] = laufText(daten.lauf);
      status($("lauf"), text, art);
      $("suchen").disabled = daten.lauf.zustand === "laeuft";
      if (daten.lauf.zustand === "fertig") lade();
    } else if (daten.art === "antwort" && daten.antwort?.fehler) {
      status($("lauf"), daten.antwort.fehler, "fehler");
      $("suchen").disabled = false;
    }
  });

  $("suchen").addEventListener("click", () => {
    $("suchen").disabled = true;
    status($("lauf"), "Suche startet …");
    window.postMessage({ quelle: SEITE, art: "suche-starten" }, location.origin);
  });
  $("zustand").addEventListener("change", zeigeListe);
  $("alle-bewerten").addEventListener("click", alleBewerten);

  if (document.documentElement.dataset.bewerbungsassistentErweiterung) erweiterungDa();
  else setTimeout(() => { if ($("suchen").disabled && !$("lauf").textContent) $("ohne-erweiterung").hidden = false; }, 1500);
  lade();
})();
