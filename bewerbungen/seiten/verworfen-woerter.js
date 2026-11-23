"use strict";
// On Suche einstellen (#225, G66): a title word many dismissed hits share, proposed under Was nicht. The app counts
// without AI; „nicht mehr zeigen“ adds the word to the title exclusion with drafts, „Nicht jetzt“ puts it aside until
// more dismissed hits have it. Nothing changes without one of these clicks. Logic in verworfen-woerter-logik.js.
(() => {
  const { holen, senden, status, textsatz } = window.App;
  const L = window.VerworfenWoerterLogik;
  const $ = id => document.getElementById(id);
  const ROUTE = "/api/suche/verworfen-woerter";
  // Messages in the app language through Texte (#425); the word itself is a title word of the hits and stays.
  const nichtGeladen = fehler => window.Texte.t("Der Vorschlag aus den verworfenen Stellen fehlt. {fehler}", { fehler });
  const nichtGespeichert = fehler => window.Texte.t("Nicht gespeichert. {fehler}", { fehler });
  let vorschlag = null;

  function zeige(neu, satz) {
    vorschlag = neu;
    $("wort-vorschlag").hidden = !neu;
    if (!neu) return;
    $("wort-vorschlag-text").textContent = L.satz(neu, satz, window.Texte);
    $("wort-vorschlag-andere").textContent = L.andere(neu);
    $("wort-vorschlag-ja").textContent = L.knopf(neu);
    $("wort-vorschlag-ansehen").textContent = L.link(neu);
    $("wort-vorschlag-ansehen").href = L.adresse(neu);
  }

  async function lade() {
    try {
      const [{ vorschlaege }, satz] = await Promise.all([holen(ROUTE), textsatz()]);
      zeige(vorschlaege[0] || null, satz);
    } catch (fehler) {
      zeige(null);  // the proposal is extra; the card works without it
      status($("nicht-meldung"), nichtGeladen(fehler.message), "fehler");
    }
  }

  async function antworte(pfad, danach) {
    if (!vorschlag) return;
    const wort = vorschlag.wort;
    try {
      await senden(`${ROUTE}/${pfad}`, { wort });
      danach(wort);
    } catch (fehler) {
      status($("nicht-meldung"), nichtGespeichert(fehler.message), "fehler");
      lade();
    }
  }

  // The pressed button goes away; focus stays in the card instead of falling back to the start of the page.
  const fokus = () => (vorschlag ? $("wort-vorschlag-ja") : $("nicht-aendern")).focus();

  $("wort-vorschlag-ja").addEventListener("click", () => antworte("ausschliessen", wort => {
    zeige(null);
    fokus();
    status($("nicht-meldung"), L.uebernommen(wort), "ok");
    document.dispatchEvent(new CustomEvent("suchprofil-geaendert"));
  }));
  $("wort-vorschlag-nein").addEventListener("click", () => antworte("nicht-jetzt", () => lade().then(fokus)));
  document.addEventListener("suchprofil-geaendert", lade);
  lade();
})();
