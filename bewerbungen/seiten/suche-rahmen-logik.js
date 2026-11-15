"use strict";
// Region, Pensum, exclusions and title filter on Suche einstellen (#286, G64), without DOM: what each card sends to
// /api/suche/rahmen and how its fields are filled. The server checks every value again (search_frame.py).
(global => {
  const UMKREISE = [10, 25, 50];  // as the form in Meine Angaben offers them
  const UMKREIS_VORGABE = 25;  // search_plan.DEFAULT_RADIUS_KM
  const titelfilterLeer = "Kein Titelfilter";
  // Place lines of single portals (#301): they go before Wohnort and Kantone, so the card shows those the profile has.
  const PORTAL_FELDER = ["orte", "plz", "regionen"];

  const zeilen = text => String(text || "").split("\n").map(zeile => zeile.trim()).filter(Boolean);
  const alsText = liste => (Array.isArray(liste) ? liste : []).join("\n");

  /** The place lines the form shows; a field the form leaves out is not sent, so its line stays as it is. */
  function portalKoerper(felder) {
    const werte = PORTAL_FELDER.filter(feld => felder[feld] !== undefined)
      .map(feld => [feld, Array.isArray(felder[feld]) ? felder[feld] : zeilen(felder[feld])]);
    return Object.fromEntries(werte);
  }

  function koerper(karte, felder, lehrstelle) {
    if (karte === "region") {
      const ort = { wohnort: String(felder.wohnort || "").trim(), kantone: felder.kantone || [] };
      if (lehrstelle) return { ...ort, umkreis_km: Number(felder.umkreis) };
      return { ...ort, pensum: String(felder.pensum || "").trim(), ...portalKoerper(felder) };
    }
    if (karte === "nicht") return { ausschluss: zeilen(felder.inserat), titel_ausschluss: zeilen(felder.titel) };
    return { titel_positiv: zeilen(felder.positiv), titel_ausschluss: zeilen(felder.ausschluss) };
  }

  /** The excluded companies (#226, G65): the whole list, one per line; the app drops repeats. */
  const firmenKoerper = text => ({ firmen: zeilen(text) });

  /**
   * The one request that saves a card. Was nicht saves exclusions and companies together or neither (#303), so a
   * failure never leaves half of it saved; an apprenticeship's Was nicht has only the companies.
   */
  function anfrage(karte, felder, lehrstelle) {
    if (karte !== "nicht") return { pfad: "/api/suche/rahmen", koerper: koerper(karte, felder, lehrstelle) };
    const profil = lehrstelle ? {} : koerper(karte, felder, lehrstelle);
    return { pfad: "/api/suche/was-nicht", koerper: { ...profil, ...firmenKoerper(felder.firmen) } };
  }

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

  /** Which place fields the region card shows: those whose line the profile has, never for an apprenticeship. */
  const portalFelder = (werte, lehrstelle) =>
    (lehrstelle ? [] : PORTAL_FELDER.filter(feld => Array.isArray(werte[feld]) && werte[feld].length));

  /** The closed card's line: per portal with its own line, where it searches instead of Wohnort and Kantone. */
  const proPortalText = liste => (Array.isArray(liste) ? liste : [])
    .map(eintrag => `${eintrag.portal}: ${eintrag.orte.join(", ")}`).join(" · ");

  const logik = { zeilen, alsText, koerper, firmenKoerper, anfrage, umkreisWahl, umkreisGewaehlt, kantoneHinweis, titelfilterLeer,
    portalFelder, proPortalText };
  if (typeof module !== "undefined") module.exports = logik;
  else global.SucheRahmenLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
