"use strict";
// The title word many dismissed hits share (#225, G66), without DOM: what the proposal on Suche einstellen says and
// where „Die Stellen ansehen“ leads. Every number comes from the app (dismissed_words.py), never from the AI. Texts in
// the app language through Texte (#421); the word itself is a title word of the hits and stays as it is.
(global => {
  const ADRESSE = /^#verworfen=(.+)$/;
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };

  /** The sentence of the proposal, in the address of the text set; `Texte` is the page's Texte. */
  const satz = (vorschlag, textsatz, Texte) =>
    Texte.text("einstellen.verworfen", textsatz, { anzahl: vorschlag.verworfen, wort: vorschlag.wort });

  /** How many hits that are not dismissed the exclusion would keep away too. */
  function andere(vorschlag) {
    const Texte = texts();
    if (!vorschlag.andere) return Texte.t("Von den übrigen Stellen hat keine dieses Wort im Titel.");
    return vorschlag.andere === 1
      ? Texte.t("Auch 1 Stelle, die nicht verworfen ist, hat dieses Wort im Titel.")
      : Texte.t("Auch {anzahl} Stellen, die nicht verworfen sind, haben dieses Wort im Titel.", { anzahl: vorschlag.andere });
  }

  const knopf = vorschlag => Texte.t("«{wort}» nicht mehr zeigen", { wort: vorschlag.wort });
  const link = vorschlag => Texte.t("Die {anzahl} Stellen ansehen", { anzahl: vorschlag.verworfen });
  const adresse = vorschlag => `/treffer#verworfen=${encodeURIComponent(vorschlag.wort)}`;
  const uebernommen = wort => Texte.t("«{wort}» steht jetzt unter «Im Titel». Gilt ab der nächsten Suche.", { wort });
  const filterText = (anzahl, wort) => (anzahl === 1
    ? Texte.t("Gezeigt: 1 verworfene Stelle mit «{wort}» im Titel.", { wort })
    : Texte.t("Gezeigt: {anzahl} verworfene Stellen mit «{wort}» im Titel.", { anzahl, wort }));

  /** The word from a link such as „#verworfen=Aussendienst“, or null. */
  function ausAdresse(hash) {
    const gefunden = ADRESSE.exec(hash || "");
    if (!gefunden) return null;
    // URLSearchParams never throws on a broken escape, unlike decodeURIComponent; such a word finds no hits.
    const wort = new URLSearchParams(`w=${gefunden[1].replace(/\+/g, "%2B")}`).get("w");
    return wort.includes("�") ? null : wort.trim() || null;
  }

  const logik = { satz, andere, knopf, link, adresse, uebernommen, filterText, ausAdresse };
  if (typeof module !== "undefined") module.exports = logik;
  else global.VerworfenWoerterLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
