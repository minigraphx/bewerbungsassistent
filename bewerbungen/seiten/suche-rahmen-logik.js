"use strict";
// Region, Pensum, exclusions and title filter on Suche einstellen (#286, G64), without DOM: what each card sends to
// /api/suche/rahmen and how its fields are filled. The server checks every value again (search_frame.py).
(global => {
  const UMKREISE = [10, 25, 50];  // as the form in Meine Angaben offers them
  const UMKREIS_VORGABE = 25;  // search_plan.DEFAULT_RADIUS_KM
  const titelfilterLeer = "Kein Titelfilter";

  const zeilen = text => String(text || "").split("\n").map(zeile => zeile.trim()).filter(Boolean);
  const alsText = liste => (Array.isArray(liste) ? liste : []).join("\n");

  function koerper(karte, felder, lehrstelle) {
    if (karte === "region") {
      const ort = { wohnort: String(felder.wohnort || "").trim(), kantone: felder.kantone || [] };
      return lehrstelle ? { ...ort, umkreis_km: Number(felder.umkreis) } : { ...ort, pensum: String(felder.pensum || "").trim() };
    }
    if (karte === "nicht") return { ausschluss: zeilen(felder.inserat), titel_ausschluss: zeilen(felder.titel) };
    return { titel_positiv: zeilen(felder.positiv), titel_ausschluss: zeilen(felder.ausschluss) };
  }

  /** The excluded companies (#226, G65): the whole list, one per line; the app drops repeats. */
  const firmenKoerper = text => ({ firmen: zeilen(text) });

  /** Whether saving the card writes the search profile; an apprenticeship's Was nicht has only the companies. */
  const mitProfil = (karte, lehrstelle) => !(karte === "nicht" && lehrstelle);

  const umkreisGewaehlt = aktuell => (Number.isInteger(aktuell) ? aktuell : UMKREIS_VORGABE);

  function umkreisWahl(aktuell) {
    const werte = [...new Set([...UMKREISE, umkreisGewaehlt(aktuell)])].sort((a, b) => a - b);
    return werte.map(wert => ({ wert, text: `${wert} km` }));
  }

  function kantoneHinweis(lehrstelle) {
    return lehrstelle
      ? "Gesucht wird im Umkreis des Wohnorts. Die Kantone helfen beim Einordnen."
      : "Ohne Auswahl sucht die App in der ganzen Schweiz, Stellen nahe dem Wohnort zuerst.";
  }

  const logik = { zeilen, alsText, koerper, firmenKoerper, mitProfil, umkreisWahl, umkreisGewaehlt, kantoneHinweis, titelfilterLeer };
  if (typeof module !== "undefined") module.exports = logik;
  else global.SucheRahmenLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
