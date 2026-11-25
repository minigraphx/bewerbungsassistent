"use strict";
// Setup logic without a page. Step „Erweiterung“ (MIN-407): a version from the store lags behind the app after every
// release, and only a hand-loaded extension can do anything about a difference. Step „Datei“: the choice per file (G26).
// Which steps show, which store button leads and what the end still lists (#219, tests/einrichtung_quickwins.test.cjs).
// The AI is no step (G60, #272): the window „KI einrichten“ sets it up, opened from the setup or wherever it is needed.
(function (global) {
  // Loaded before this file on the page; required in the tests. Texts in the app language through Texte.t (#418).
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);

  /** The steps in order. The data folder is a line of the first step; „Datei“ only shows with a file in Downloads,
   *  otherwise it is reached under „Erweitert“ and shows while it is the current one. */
  function schritte({ installiert, einstiegDatei, jetzt = "" }) {
    if (!installiert) return ["gesucht"];
    const datei = einstiegDatei || jetzt === "vorlage" ? ["vorlage"] : [];
    return ["gesucht", ...datei, "erweiterung"];
  }

  /** „edge“, „chrome“ or „andere“ from the user agent; other Chromium browsers have no store of ours. */
  function browserVon(userAgent) {
    const ua = String(userAgent || "");
    if (/\bEdg(?:A|iOS)?\//.test(ua)) return "edge";
    if (/\b(?:OPR|Opera|Vivaldi|YaBrowser|SamsungBrowser)\//.test(ua)) return "andere";
    return /\b(?:Chrome|Chromium)\//.test(ua) ? "chrome" : "andere";
  }

  /** One main store button: the own browser's, Chrome where the browser is another. */
  function storeKnoepfe(browser) {
    return browser === "edge" ? { haupt: "edge", leise: "chrome" } : { haupt: "chrome", leise: "edge" };
  }

  /** An open point of the end with its words in the app language, read when it is asked for. */
  function offenerPunkt(id) {
    const Texte = texts();
    return id === "ki"
      ? { id, titel: Texte.t("KI"), text: Texte.t("Noch nicht verbunden. Ohne KI gibt es keine Noten und keine Entwürfe."),
          knopf: Texte.t("KI einrichten"), aktion: "ki-einrichten" }
      : { id, titel: Texte.t("Erweiterung"), text: Texte.t("Noch nicht geladen. Ohne sie sucht die App nicht auf den Portalen."),
          knopf: Texte.t("Erweiterung laden"), ziel: "#erweiterung" };
  }

  /** What is still open at the end, each with its button; the extension only where the app can bring it. */
  function offenePunkte({ kiVerbunden, erweiterungMoeglich, erweiterungGeladen }) {
    return [!kiVerbunden && "ki", erweiterungMoeglich && !erweiterungGeladen && "erweiterung"].filter(Boolean).map(offenerPunkt);
  }

  function abschlussTitel(offen) {
    const Texte = texts();
    return offen.length ? Texte.t("Fast fertig") : Texte.t("Alles eingerichtet");
  }

  /** The choice of the first step in one line, „eine Stelle, Sie, mit RAV“; the stored values themselves stay German.
   *  One template, so French can space its colon in „ORP : oui“. */
  function zusammenfassung(wahl) {
    if (!wahl) return "";
    const Texte = texts();
    const was = wahl.gesucht === "lehrstelle" ? Texte.t("eine Lehrstelle") : Texte.t("eine Stelle");
    const anrede = wahl.anrede === "du" ? Texte.t("du") : Texte.t("Sie");
    const rav = wahl.rav ? Texte.t("mit RAV") : Texte.t("ohne RAV");
    return Texte.t("{was}, {anrede}, {rav}", { was, anrede, rav });
  }

  /** „fehlt“, „veraltet“ (a reload helps) or „bereit“. */
  function erweiterungZustand(geladen, mitgebracht, entpackt) {
    if (!geladen) return "fehlt";
    return entpackt && mitgebracht && geladen !== mitgebracht ? "veraltet" : "bereit";
  }

  // Step „Datei“ (G26): existing Markdown files are kept unless the person picks replacing, per file.
  const ZEICHEN = { gleich: "  ", weg: "− ", neu: "+ ", luecke: "…" };

  function startWahl(dateien) {
    return Object.fromEntries(dateien.map(d => [d.datei, "behalten"]));
  }

  function zuErsetzen(wahl) {
    return Object.keys(wahl).filter(datei => wahl[datei] === "ersetzen");
  }

  function zeilenZeichen(art) {
    return ZEICHEN[art] || "  ";
  }

  // A reload for the new language (#435) keeps the first step's unsaved choice in the session; each value is checked,
  // because what comes back from the browser's storage is not trusted.
  const KEPT_VALUES = { gesucht: ["stelle", "lehrstelle"], anrede: ["sie", "du"] };

  function keptChoice(wahl, entwurf) {
    const kept = entwurf && typeof entwurf === "object" ? entwurf : {};
    const valid = {};
    for (const [key, allowed] of Object.entries(KEPT_VALUES)) if (allowed.includes(kept[key])) valid[key] = kept[key];
    if (typeof kept.rav === "boolean") valid.rav = kept.rav;
    return { wahl: { ...wahl, ...valid }, ravBeruehrt: kept.ravBeruehrt === true,
             ordner: typeof kept.ordner === "string" ? kept.ordner : null };
  }

  const logik = { erweiterungZustand, startWahl, zuErsetzen, zeilenZeichen, schritte, browserVon, storeKnoepfe, offenePunkte,
                  abschlussTitel, zusammenfassung, keptChoice };
  if (typeof module !== "undefined") module.exports = logik;
  else global.EinrichtungLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
