"use strict";
// On Stellen (#210): the hint after a search, counted by the app without AI, and the list narrowed to the hits behind a
// piece of evidence („#beleg=…“). The way to the check with its cost (G15) is on Suche einstellen (#263).
window.SuchbegriffeStart = (() => {
  const { holen, senden, status, textsatz } = window.App;
  const L = window.SuchbegriffeLogik;
  const $ = id => document.getElementById(id);
  let beleg = null;  // { begriff, ids: Set } while the list shows only these hits

  const geaendert = () => document.dispatchEvent(new CustomEvent("suchbegriffe-beleg"));

  function zeigeHinweis(hinweis, kosten, texte) {
    $("begriff-hinweis").hidden = !hinweis;
    if (!hinweis) return;
    $("begriff-hinweis-text").textContent = L.hinweisText(hinweis);
    $("begriff-hinweis-nachsatz").textContent = `${texte.hinweisNachsatz} ${L.schaetzung(kosten)}.`;
    $("begriff-hinweis-aus").onclick = async () => {
      try {
        await senden("/api/suchbegriffe/ausblenden", { begriff: hinweis.begriff });
        $("begriff-hinweis").hidden = true;
      } catch (fehler) {
        status($("status"), fehler.message, "fehler");
      }
    };
  }

  /** Called with each load of the list; only a job search has it. */
  async function zeige(art) {
    if (art === "lehrstelle") {
      $("begriff-hinweis").hidden = true;
      return;
    }
    try {
      const [antwort, satz] = await Promise.all([holen("/api/suchbegriffe/hinweis"), textsatz()]);
      const texte = L.texte(satz);
      zeigeHinweis(antwort.verfuegbar ? antwort.hinweis : null, antwort.kosten_usd, texte);
    } catch {
      $("begriff-hinweis").hidden = true;  // the hint is extra; the list works without it
    }
  }

  async function belegLaden() {
    const begriff = L.belegAusAdresse(location.hash);
    if (!begriff) {
      beleg = null;
      $("beleg-filter").hidden = true;
      geaendert();
      return;
    }
    try {
      const antwort = await holen("/api/suchbegriffe/beleg", { begriff });
      beleg = { begriff: antwort.begriff, ids: new Set(antwort.ids) };
      $("beleg-filter-text").textContent = `Gezeigt: ${antwort.ids.length} Treffer, die nur über «${antwort.begriff}» hereinkamen.`;
      $("beleg-filter").hidden = false;
    } catch (fehler) {
      beleg = null;
      status($("status"), fehler.message, "fehler");
    }
    geaendert();
  }

  $("beleg-alle").addEventListener("click", () => {
    history.replaceState(null, "", location.pathname + location.search);
    belegLaden();
  });
  window.addEventListener("hashchange", belegLaden);
  belegLaden();

  /** The ids the list is narrowed to, or null for the usual list. */
  const ids = () => (beleg ? beleg.ids : null);
  return { zeige, ids };
})();
