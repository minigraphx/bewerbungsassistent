"use strict";
// The title word many dismissed hits share (#225, G66), without DOM: what the proposal on Suche einstellen says and
// where „Die Stellen ansehen“ leads. Every number comes from the app (dismissed_words.py), never from the AI.
(global => {
  const ADRESSE = /^#verworfen=(.+)$/;

  /** The sentence of the proposal, in the address of the text set. */
  const satz = (vorschlag, textsatz, texte) =>
    texte.text("einstellen.verworfen", textsatz, { anzahl: vorschlag.verworfen, wort: vorschlag.wort });

  /** How many hits that are not dismissed the exclusion would keep away too. */
  function andere(vorschlag) {
    if (!vorschlag.andere) return "Von den übrigen Stellen hat keine dieses Wort im Titel.";
    return vorschlag.andere === 1
      ? "Auch 1 Stelle, die nicht verworfen ist, hat dieses Wort im Titel."
      : `Auch ${vorschlag.andere} Stellen, die nicht verworfen sind, haben dieses Wort im Titel.`;
  }

  const knopf = vorschlag => `«${vorschlag.wort}» nicht mehr zeigen`;
  const link = vorschlag => `Die ${vorschlag.verworfen} Stellen ansehen`;
  const adresse = vorschlag => `/treffer#verworfen=${encodeURIComponent(vorschlag.wort)}`;
  const uebernommen = wort => `«${wort}» steht jetzt unter «Im Titel». Gilt ab der nächsten Suche.`;
  const filterText = (anzahl, wort) => `Gezeigt: ${anzahl} verworfene ${anzahl === 1 ? "Stelle" : "Stellen"} mit «${wort}» im Titel.`;

  /** The word from a link such as „#verworfen=Aussendienst“, or null. */
  function ausAdresse(hash) {
    const gefunden = ADRESSE.exec(hash || "");
    if (!gefunden) return null;
    try {
      return decodeURIComponent(gefunden[1]).trim() || null;
    } catch {
      return null;
    }
  }

  const logik = { satz, andere, knopf, link, adresse, uebernommen, filterText, ausAdresse };
  if (typeof module !== "undefined") module.exports = logik;
  else global.VerworfenWoerterLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
