"use strict";
// Region und Pensum, Was nicht and the title filter on Suche einstellen (#286, G64): „Ändern“ opens the card's own
// form, „Speichern“ writes to the search profile with drafts, and the page loads anew. Logic in suche-rahmen-logik.js.
// Was nicht also holds the excluded companies (#226, G65), saved to their own list in the data folder.
window.SucheRahmen = (() => {
  const { senden, status, el } = window.App;
  const L = window.SucheRahmenLogik;
  const $ = id => document.getElementById(id);
  const KARTEN = ["region", "nicht", "titelfilter"];
  const GESPEICHERT = "Gespeichert. Gilt ab der nächsten Suche.";
  const NICHT_GESPEICHERT = "Nicht gespeichert.";
  let stand = { werte: {}, alleKantone: [], lehrstelle: false, firmen: [] };

  function kantone(gewaehlt) {
    const an = new Set(gewaehlt || []);
    $("region-kantone").replaceChildren(...stand.alleKantone.map(kanton => el("li", {},
      el("label", { class: "check" }, el("input", { type: "checkbox", value: kanton, checked: an.has(kanton) }), ` ${kanton}`))));
  }

  function fuelleRegion(werte) {
    $("region-wohnort").value = werte.wohnort || "";
    kantone(werte.kantone);
    $("kantone-hinweis").textContent = L.kantoneHinweis(stand.lehrstelle);
    $("region-umkreis-feld").hidden = !stand.lehrstelle;
    $("region-umkreis").replaceChildren(...L.umkreisWahl(werte.umkreis_km).map(w => el("option", { value: String(w.wert) }, w.text)));
    $("region-umkreis").value = String(L.umkreisGewaehlt(werte.umkreis_km));
    $("region-pensum-feld").hidden = stand.lehrstelle;
    $("region-pensum").value = werte.pensum || "";
  }

  function fuelle(karte) {
    const werte = stand.werte;
    if (karte === "region") return fuelleRegion(werte);
    if (karte === "nicht") {
      $("nicht-inserat").value = L.alsText(werte.ausschluss);
      $("nicht-im-titel").value = L.alsText(werte.titel_ausschluss);
      $("nicht-firmen").value = L.alsText(stand.firmen.map(firma => firma.name));
      return;
    }
    $("titelfilter-positiv").value = L.alsText(werte.titel_positiv);
    $("titelfilter-ausschluss").value = L.alsText(werte.titel_ausschluss);
  }

  function felder(karte) {
    if (karte === "region") {
      const gewaehlt = [...$("region-kantone").querySelectorAll("input:checked")].map(kasten => kasten.value);
      return { wohnort: $("region-wohnort").value, kantone: gewaehlt, umkreis: $("region-umkreis").value, pensum: $("region-pensum").value };
    }
    if (karte === "nicht") return { inserat: $("nicht-inserat").value, titel: $("nicht-im-titel").value, firmen: $("nicht-firmen").value };
    return { positiv: $("titelfilter-positiv").value, ausschluss: $("titelfilter-ausschluss").value };
  }

  function oeffne(karte, offen) {
    const form = $(`${karte}-form`);
    const knopf = $(`${karte}-aendern`);
    if (offen) fuelle(karte);
    form.hidden = !offen;
    knopf.hidden = offen;
    knopf.setAttribute("aria-expanded", String(offen));
    if (offen) [...form.querySelectorAll("input, textarea")].find(feld => !feld.closest("[hidden]"))?.focus();
    else knopf.focus();
  }

  async function speichere(karte, event) {
    event.preventDefault();
    const meldung = $(`${karte}-meldung`);
    try {
      const werte = felder(karte);
      if (L.mitProfil(karte, stand.lehrstelle)) await senden("/api/suche/rahmen", L.koerper(karte, werte, stand.lehrstelle));
      if (karte === "nicht") await senden("/api/firmen/ausgeschlossen", L.firmenKoerper(werte.firmen));
      oeffne(karte, false);
      status(meldung, GESPEICHERT, "ok");
      document.dispatchEvent(new CustomEvent("suchprofil-geaendert"));
    } catch (fehler) {
      status(meldung, `${NICHT_GESPEICHERT} ${fehler.message}`, "fehler");
    }
  }

  /** The values of the profile; a form that is open keeps what the person is typing. */
  function zeige(rahmen, lehrstelle, firmen = []) {
    stand = { werte: rahmen.werte || {}, alleKantone: rahmen.alle_kantone || [], lehrstelle, firmen };
  }

  for (const karte of KARTEN) {
    $(`${karte}-aendern`).addEventListener("click", () => oeffne(karte, true));
    $(`${karte}-abbrechen`).addEventListener("click", () => oeffne(karte, false));
    $(`${karte}-form`).addEventListener("submit", event => speichere(karte, event));
  }

  return { zeige };
})();
