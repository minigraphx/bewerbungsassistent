"use strict";
// On „Stellen suchen“ (#210): the hint after a search, counted by the app without AI, the way to the check with its
// cost and what goes to the AI (G15), and the list narrowed to the hits behind a piece of evidence („#beleg=…“).
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
    const stelle = art !== "lehrstelle";
    $("pruefen-block").hidden = !stelle;
    if (!stelle) {
      $("begriff-hinweis").hidden = true;
      return;
    }
    try {
      const [antwort, satz] = await Promise.all([holen("/api/suchbegriffe/hinweis"), textsatz()]);
      const texte = L.texte(satz);
      $("pruefen-block").hidden = !antwort.verfuegbar;
      $("pruefen-kosten").textContent = L.schaetzung(antwort.kosten_usd);
      $("pruefen-satz").textContent = texte.satz;
      $("pruefen-was").textContent = texte.wasGeht;
      zeigeHinweis(antwort.verfuegbar ? antwort.hinweis : null, antwort.kosten_usd, texte);
    } catch {
      $("begriff-hinweis").hidden = true;  // the hint is extra; the list works without it
    }
  }

  async function textAnsehen() {
    try {
      const { text } = await holen("/api/suchbegriffe/text");
      $("ki-text-inhalt").textContent = text;
      $("ki-text").showModal();
      $("ki-text-schliessen").focus();
    } catch (fehler) {
      status($("status"), fehler.message, "fehler");
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

  $("ki-text-ansehen").addEventListener("click", textAnsehen);
  $("ki-text-schliessen").addEventListener("click", () => $("ki-text").close());
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
