"use strict";
// What the page Stellen says about itself (#220, UX findings 8 and 9): the one line that sums up the
// settings, why „Jetzt suchen“ cannot start, the empty list before the first search and the line of the last search.
// No DOM, so it can be tested (tests/treffer_quickwins.test.cjs).
(function (global) {
  const MAX_BEGRIFFE = 3;
  const OHNE_ERWEITERUNG = "Zuerst die Erweiterung einrichten.";
  const NOCH_NICHT = { titel: "Noch nicht gesucht.", text: "Die erste Suche dauert einige Minuten." };

  function aufzaehlung(namen) {
    return namen.length > 1 ? `${namen.slice(0, -1).join(", ")} und ${namen[namen.length - 1]}` : namen.join("");
  }

  function begriffeText(begriffe, lehrstelle) {
    if (!begriffe.length) return lehrstelle ? "Noch keine Berufe" : "Noch keine Suchbegriffe";
    const gezeigt = begriffe.slice(0, MAX_BEGRIFFE).join(", ");
    const rest = begriffe.length - MAX_BEGRIFFE;
    return `Sucht nach ${gezeigt}${rest > 0 ? ` und ${rest} weiteren` : ""}`;
  }

  /** Where the search looks: a radius for apprenticeships, else cantons or the whole country with the home first. */
  function regionText(region, lehrstelle) {
    if (!region) return "";
    const orte = Array.isArray(region.orte) ? region.orte : [];
    const kantone = Array.isArray(region.kantone) ? region.kantone : [];
    if (lehrstelle && orte.length && region.umkreis_km) return `${region.umkreis_km} km um ${orte[0]}`;
    if (kantone.length && !region.schweizweit) return `${kantone.length === 1 ? "Kanton" : "Kantone"} ${aufzaehlung(kantone)}`;
    return orte.length ? `ganze Schweiz, nahe ${orte[0]} zuerst` : "ganze Schweiz";
  }

  /** The closed settings in one line: terms, region, number of portals (the page adds „Ändern“). */
  function zusammenfassung({ begriffe = [], region = null, portale = 0, lehrstelle = false } = {}) {
    const anzahl = portale === 1 ? "1 Portal" : `${portale} Portale`;
    return [begriffeText(begriffe, lehrstelle), regionText(region, lehrstelle), anzahl].filter(Boolean).join(" · ");
  }

  /**
   * Why „Jetzt suchen“ cannot start; "" when it can, while a search runs (the button says so) and while the page still
   * waits for the extension to answer (erweiterung null), so nobody reads „einrichten“ who has it.
   */
  function sperrgrund({ erweiterung = null, laeuft = false, profil = "" } = {}) {
    if (laeuft) return "";
    if (profil) return profil;
    return erweiterung === false ? OHNE_ERWEITERUNG : "";
  }

  /** Title and text of the empty list per view; before the first search the new hits say so instead of „Keine neuen“. */
  function leer(zustand, gesucht, keineText) {
    if (zustand === "neu") return gesucht ? { titel: "Keine neuen Treffer", text: keineText } : NOCH_NICHT;
    return { titel: zustand === "uebernommen" ? "Noch nichts gemerkt" : "Nichts verworfen", text: "" };
  }

  /**
   * The line under the title: the last search; without one only what is there, never „Noch keine Suche.“ beside hits.
   * `wann` is the day as the app names it (#208): „heute“, „gestern“ or „am 24.10.2026“; runs store no time.
   */
  function letzteSuche(lauf, alle, datum, wann = "") {
    const neu = alle.filter(x => x.zustand === "neu").length;
    const anzahl = `${alle.length} Treffer, ${neu} neu`;
    if (!lauf) return alle.length ? anzahl : "";  // the empty list says „Noch nicht gesucht.“
    const portale = Object.keys(lauf.portale || {});
    const tag = wann || `am ${datum(lauf.datum)}`;
    return `Letzte Suche ${tag} · ${portale.length === 1 ? portale[0] : `${portale.length} Portale`} · ${anzahl}`;
  }

  /** A problem line; a portal that will catch up says from when (#208), the app words the sentence. */
  function problemZeile(problem, nachholen = "") {
    return nachholen ? `${problem} ${nachholen}` : problem;
  }

  const WAHL_TAGE = [7, 14, 21, 30, 45, 60];
  const VORGABE_TAGE = 21;

  /** The choices of „Inserate der letzten“; another value from the profile stays as its own choice. */
  function zeitfensterWahl(aktuell) {
    const tage = WAHL_TAGE.includes(aktuell) || !Number.isInteger(aktuell) ? WAHL_TAGE : [...WAHL_TAGE, aktuell].sort((a, b) => a - b);
    return tage.map(wert => ({ wert, text: `${wert} Tage${wert === VORGABE_TAGE ? " (Vorgabe)" : ""}` }));
  }

  /** One portal under „Stand der Portale“ in the settings. */
  function portalStand(zeile) {
    const zuletzt = zeile.problem ? "Problem bei der letzten Suche" : zeile.zuletzt ? `zuletzt ${zeile.zuletzt}` : "noch nie gesucht";
    return `${zeile.portal}: ${zuletzt} · nächste Suche ab ${zeile.ab}`;
  }

  /** The title filters in one sentence for Suche einstellen (#263, A4); empty without any. */
  function titelfilterText(positiv = [], ausschluss = []) {
    const woerter = anzahl => `${anzahl} ${anzahl === 1 ? "Wort" : "Wörtern"}`;
    if (positiv.length && ausschluss.length) return `Titel enthält eines von ${woerter(positiv.length)}, keines von ${ausschluss.length}`;
    if (positiv.length) return `Titel enthält eines von ${woerter(positiv.length)}`;
    return ausschluss.length ? `Titel enthält keines von ${woerter(ausschluss.length)}` : "";
  }

  const anzeige = { OHNE_ERWEITERUNG, NOCH_NICHT, zusammenfassung, regionText, titelfilterText, sperrgrund, leer, letzteSuche, problemZeile,
    zeitfensterWahl, portalStand };
  if (typeof module !== "undefined") module.exports = anzeige;
  else global.SucheAnzeige = anzeige;
})(typeof window !== "undefined" ? window : globalThis);
