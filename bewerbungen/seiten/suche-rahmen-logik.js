"use strict";
// Region, Pensum, exclusions and title filter on Suche einstellen (#286, G64), without DOM: what each card sends to
// /api/suche/rahmen and how its fields are filled. The server checks every value again (search_frame.py). Its hints
// come in the app language through Texte.t (#424); portals, places and regions are data and stay as they are.
(global => {
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const UMKREISE = [10, 25, 50];  // as the form in Meine Angaben offers them
  const UMKREIS_VORGABE = 25;  // search_plan.DEFAULT_RADIUS_KM
  // Place lines of single portals (#301): they go before Wohnort and Kantone, so the card shows those the profile has.
  const PORTAL_FELDER = ["orte", "plz", "regionen"];
  const REGIONEN_JOBSCOUT24 = "regionen_jobscout24";

  const zeilen = text => String(text || "").split("\n").map(zeile => zeile.trim()).filter(Boolean);
  const alsText = liste => (Array.isArray(liste) ? liste : []).join("\n");

  /** The place lines the form shows; a field the form leaves out is not sent, so its line stays as it is. */
  function portalKoerper(felder) {
    const werte = [...PORTAL_FELDER, REGIONEN_JOBSCOUT24].filter(feld => felder[feld] !== undefined)
      .map(feld => [feld, Array.isArray(felder[feld]) ? felder[feld] : zeilen(felder[feld])]);
    return Object.fromEntries(werte);
  }

  /** G107, #380: the jobscout24 regions can be chosen in every job profile, with or without their line. */
  const regionenJobscout24 = lehrstelle => !lehrstelle;

  /** The hint under jobscout24's regions: it names the PLZ field below only while the card shows that field. */
  const regionenJobscout24Hinweis = mitPlzFeld => (mitPlzFeld
    ? Texte.t("jobscout24 sucht dann pro Begriff einmal in allen gewählten Regionen. Keine gewählt: jobscout24 sucht an den PLZ darunter.")
    : Texte.t("jobscout24 sucht dann pro Begriff einmal in allen gewählten Regionen. Keine gewählt: jobscout24 sucht an der PLZ aus Meine Angaben."));

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

  function kantoneHinweis(lehrstelle, nischen = 0, remote = true) {
    if (lehrstelle) return Texte.t("Gesucht wird im Umkreis des Wohnorts. Die Kantone helfen beim Einordnen.");
    // G111, #387: what the cantons mean for the niches, only in a job profile that has any; G125: `remote` false when
    // a remote mention does not keep them
    if (nischen > 0 && !remote) {
      return Texte.t("Ohne Auswahl sucht die App in der ganzen Schweiz, Stellen nahe dem Wohnort zuerst. Nischen sucht die App ohne Ort; Stellen ausserhalb dieser Kantone behält sie nicht.");
    }
    if (nischen > 0) {
      return Texte.t("Ohne Auswahl sucht die App in der ganzen Schweiz, Stellen nahe dem Wohnort zuerst. Nischen sucht die App ohne Ort; Stellen ausserhalb dieser Kantone behält sie nur, wenn das Inserat Remote nennt.");
    }
    return Texte.t("Ohne Auswahl sucht die App in der ganzen Schweiz, Stellen nahe dem Wohnort zuerst.");
  }

  /** Which place fields the region card shows: those whose line the profile has, never for an apprenticeship. */
  const portalFelder = (werte, lehrstelle) =>
    (lehrstelle ? [] : PORTAL_FELDER.filter(feld => Array.isArray(werte[feld]) && werte[feld].length));

  /**
   * The closed card's line: per portal with its own line, where it searches instead of Wohnort and Kantone; the parts of
   * a «·» line (#342).
   */
  const proPortalText = liste => (Array.isArray(liste) ? liste : [])
    .map(eintrag => (eintrag.vorsatz
      ? Texte.t("{portal}: {vorsatz} {orte}", { portal: eintrag.portal, vorsatz: eintrag.vorsatz, orte: eintrag.orte.join(", ") })
      : Texte.t("{portal}: {orte}", { portal: eintrag.portal, orte: eintrag.orte.join(", ") })));

  const logik = { zeilen, alsText, koerper, firmenKoerper, anfrage, umkreisWahl, umkreisGewaehlt, kantoneHinweis,
    portalFelder, proPortalText, regionenJobscout24, regionenJobscout24Hinweis };
  if (typeof module !== "undefined") module.exports = logik;
  else global.SucheRahmenLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
