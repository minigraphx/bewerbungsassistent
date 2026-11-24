"use strict";
// What the page Stellen says about itself (#220, UX findings 8 and 9): the one line that sums up the
// settings, why „Jetzt suchen“ cannot start, the empty list before the first search and the line of the last search.
// No DOM, so it can be tested (tests/treffer_quickwins.test.cjs). Texts in the app language through Texte.t (#421,
// tests/search_logic_languages.test.cjs); search terms, cantons, places and portals are data and stay as they are.
(function (global) {
  const MAX_BEGRIFFE = 3;
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const ohneErweiterung = () => Texte.t("Zuerst die Erweiterung einrichten.");
  const nochNicht = () => ({ titel: Texte.t("Noch nicht gesucht."), text: Texte.t("Die erste Suche dauert einige Minuten.") });

  function aufzaehlung(namen) {
    if (namen.length <= 1) return namen.join("");
    return Texte.t("{liste} und {letzter}", { liste: namen.slice(0, -1).join(", "), letzter: namen[namen.length - 1] });
  }

  function begriffeText(begriffe, lehrstelle) {
    const Texte = texts();
    if (!begriffe.length) return lehrstelle ? Texte.t("Noch keine Berufe") : Texte.t("Noch keine Suchbegriffe");
    const gezeigt = begriffe.slice(0, MAX_BEGRIFFE).join(", ");
    const rest = begriffe.length - MAX_BEGRIFFE;
    if (rest <= 0) return Texte.t("Sucht nach {begriffe}", { begriffe: gezeigt });
    // one more is its own text for French and English; the German reads the same for every number
    return rest === 1 ? Texte.t("Sucht nach {begriffe} und 1 weiteren", { begriffe: gezeigt })
      : Texte.t("Sucht nach {begriffe} und {anzahl} weiteren", { begriffe: gezeigt, anzahl: rest });
  }

  /** Where the search looks: a radius for apprenticeships, else cantons or the whole country with the home first. */
  function regionText(region, lehrstelle) {
    if (!region) return "";
    const Texte = texts();
    const orte = Array.isArray(region.orte) ? region.orte : [];
    const kantone = Array.isArray(region.kantone) ? region.kantone : [];
    if (lehrstelle && orte.length && region.umkreis_km) return Texte.t("{km} km um {ort}", { km: region.umkreis_km, ort: orte[0] });
    if (kantone.length && !region.schweizweit) {
      return kantone.length === 1 ? Texte.t("Kanton {kantone}", { kantone: aufzaehlung(kantone) })
        : Texte.t("Kantone {kantone}", { kantone: aufzaehlung(kantone) });
    }
    return orte.length ? Texte.t("ganze Schweiz, nahe {ort} zuerst", { ort: orte[0] }) : Texte.t("ganze Schweiz");
  }

  /** Whether the niches are bound to chosen cantons: a job search with niches and cantons (G111). */
  const nischenInRegion = (region, lehrstelle) => Boolean(!lehrstelle && region && region.nischen
    && Array.isArray(region.kantone) && region.kantone.length && !region.schweizweit);

  /**
   * The row «Nischen» of the region card (G111, #387): niches run without a place, and with chosen cantons only hits in
   * them, at the person's places or with remote work stay; without remote work when the switch under Erweitert is off
   * (G125, `region.nischen_remote` false). "" without niches or for an apprenticeship: no row.
   */
  function nischenText(region, lehrstelle, du = false) {
    if (lehrstelle || !region || !region.nischen) return "";
    const Texte = texts();
    if (!nischenInRegion(region, lehrstelle)) return Texte.t("Ohne Ort gesucht, in der ganzen Schweiz.");
    const werte = { kantone: aufzaehlung(region.kantone) };
    if (region.nischen_remote === false) {
      return du ? Texte.t("Ohne Ort gesucht. Behalten werden Stellen in {kantone} und an deinen Orten.", werte)
        : Texte.t("Ohne Ort gesucht. Behalten werden Stellen in {kantone} und an Ihren Orten.", werte);
    }
    return du ? Texte.t("Ohne Ort gesucht. Behalten werden Stellen in {kantone}, an deinen Orten oder mit Remote.", werte)
      : Texte.t("Ohne Ort gesucht. Behalten werden Stellen in {kantone}, an Ihren Orten oder mit Remote.", werte);
  }

  /** G125: the switch for remote niche hits shows where the Nischen row speaks of the cantons. */
  const nischenSchalter = (region, lehrstelle) => nischenInRegion(region, lehrstelle);

  /** „1 Portal“ or „3 Portale“. */
  const portaleText = anzahl => (anzahl === 1 ? Texte.t("1 Portal") : Texte.t("{anzahl} Portale", { anzahl }));

  /** The closed settings as the parts of one «·» line (#342): terms, region, number of portals (the page adds „Ändern“). */
  function zusammenfassung({ begriffe = [], region = null, portale = 0, lehrstelle = false } = {}) {
    return [begriffeText(begriffe, lehrstelle), regionText(region, lehrstelle), portaleText(portale)].filter(Boolean);
  }

  /**
   * Why „Jetzt suchen“ cannot start; "" when it can, while a search runs (the button says so) and while the page still
   * waits for the extension to answer (erweiterung null), so nobody reads „einrichten“ who has it.
   */
  function sperrgrund({ erweiterung = null, laeuft = false, profil = "" } = {}) {
    if (laeuft) return "";
    if (profil) return profil;
    return erweiterung === false ? ohneErweiterung() : "";
  }

  /** Title and text of the empty list per view; before the first search the new hits say so instead of „Keine neuen“. */
  function leer(zustand, gesucht, keineText, nurAbgeschlossene = false) {
    const Texte = texts();
    if (zustand === "neu") return gesucht ? { titel: Texte.t("Keine neuen Treffer"), text: keineText } : nochNicht();
    // #373: the finished ones wait behind „Anzeigen“ below, so the tab is not empty, only without open hits
    if (zustand === "uebernommen" && nurAbgeschlossene) {
      return {
        titel: Texte.t("Alles abgeschlossen"),
        text: Texte.t("Jede Bewerbung aus diesen Treffern ist abgeschlossen. „Anzeigen“ unten zeigt sie."),
      };
    }
    if (zustand === "uebernommen") {
      return { titel: Texte.t("Noch nichts in Bewerbungen"), text: Texte.t("Mit Merken oder Bewerbung vorbereiten kommt ein Treffer hierher.") };
    }
    return { titel: Texte.t("Nichts verworfen"), text: "" };
  }

  /** „3 Treffer, 2 neu“: how many hits there are and how many of them are new. */
  function trefferZahl(alle, neu) {
    const Texte = texts();
    const treffer = alle === 1 ? Texte.t("1 Treffer") : Texte.t("{anzahl} Treffer", { anzahl: alle });
    const neue = neu === 1 ? Texte.t("1 neu") : Texte.t("{anzahl} neu", { anzahl: neu });
    return `${treffer}, ${neue}`;
  }

  /**
   * The line under the title: the last search; without one only what is there, never „Noch keine Suche.“ beside hits.
   * `wann` is the day as the app names it (#208): „heute“, „gestern“ or „am 24.10.2026“; runs store no time.
   * The parts of a «·» line (#342).
   */
  function letzteSuche(lauf, alle, datum, wann = "") {
    const Texte = texts();
    const anzahl = trefferZahl(alle.length, alle.filter(x => x.zustand === "neu").length);
    if (!lauf) return alle.length ? [anzahl] : [];  // the empty list says „Noch nicht gesucht.“
    const portale = Object.keys(lauf.portale || {});
    const tag = wann || Texte.t("am {datum}", { datum: datum(lauf.datum) });
    return [Texte.t("Letzte Suche {tag}", { tag }), portale.length === 1 ? portale[0] : portaleText(portale.length), anzahl];
  }

  /** A problem line; a portal that will catch up says from when (#208), the app words the sentence. */
  function problemZeile(problem, nachholen = "") {
    return nachholen ? `${problem} ${nachholen}` : problem;
  }

  const WAHL_TAGE = [7, 14, 21, 30, 45, 60];
  const VORGABE_TAGE = 21;

  /** A choice of days; a profile may hold a single day (search_plan.MIN_WINDOW_DAYS), which French and English say in
   * the singular, while the German reads as it always did. */
  function tageText(wert) {
    const Texte = texts();
    if (wert === VORGABE_TAGE) return Texte.t("{anzahl} Tage (Vorgabe)", { anzahl: wert });
    return wert === 1 ? Texte.t("1 Tage") : Texte.t("{anzahl} Tage", { anzahl: wert });
  }

  /** The choices of „Inserate der letzten“; another value from the profile stays as its own choice. */
  function zeitfensterWahl(aktuell) {
    const tage = WAHL_TAGE.includes(aktuell) || !Number.isInteger(aktuell) ? WAHL_TAGE : [...WAHL_TAGE, aktuell].sort((a, b) => a - b);
    return tage.map(wert => ({ wert, text: tageText(wert) }));
  }

  /** One portal under „Stand der Portale“ in the settings, as the parts of a «·» line (#342). */
  function portalStand(zeile) {
    const Texte = texts();
    const zuletzt = zeile.problem ? Texte.t("Problem bei der letzten Suche")
      : zeile.zuletzt ? Texte.t("zuletzt {wann}", { wann: zeile.zuletzt }) : Texte.t("noch nie gesucht");
    return [Texte.t("{portal}: {stand}", { portal: zeile.portal, stand: zuletzt }), Texte.t("nächste Suche ab {datum}", { datum: zeile.ab })];
  }

  // OHNE_ERWEITERUNG and NOCH_NICHT are read when they are shown, so they follow the app language.
  const anzeige = { get OHNE_ERWEITERUNG() { return ohneErweiterung(); }, get NOCH_NICHT() { return nochNicht(); },
    zusammenfassung, regionText, nischenText, nischenSchalter, sperrgrund, leer, letzteSuche, trefferZahl, problemZeile, zeitfensterWahl, portalStand };
  if (typeof module !== "undefined") module.exports = anzeige;
  else global.SucheAnzeige = anzeige;
})(typeof window !== "undefined" ? window : globalThis);
