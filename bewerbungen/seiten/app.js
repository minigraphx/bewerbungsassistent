"use strict";
// Gemeinsame Hilfen aller Seiten. Inhalte werden nur als Text eingesetzt (textContent), nie als HTML.
window.App = (() => {
  const TOKEN = document.querySelector('meta[name="token"]').content;

  function url(pfad, parameter = {}) {
    return pfad + "?" + new URLSearchParams({ t: TOKEN, ...parameter });
  }

  async function antwortLesen(antwort) {
    const typ = antwort.headers.get("Content-Type") || "";
    const daten = typ.includes("json") ? await antwort.json() : {};
    if (!antwort.ok) throw new Error(daten.fehler || antwort.statusText);
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

  function status(element, text, art = "") {
    element.textContent = text;
    element.className = "status " + art;
  }

  function datum(iso) {
    if (!iso) return "";
    const [j, m, t] = iso.split("-");
    return `${t}.${m}.${j}`;
  }

  // Zweistufiger Knopf statt confirm(): erster Klick fragt nach, zweiter führt aus
  function bestaetigen(knopf, frage, aktion) {
    const text = knopf.textContent;
    let bereit = false;
    knopf.addEventListener("click", async () => {
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

  function navigation() {
    const pfad = location.pathname;
    for (const a of document.querySelectorAll("nav a[href]")) {
      if (a.getAttribute("href") === pfad || (pfad === "/bewerbung" && a.getAttribute("href") === "/")) {
        a.setAttribute("aria-current", "page");
      }
    }
  }
  navigation();

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

  return { url, holen, senden, el, status, datum, bestaetigen, pdfAdresse };
})();
