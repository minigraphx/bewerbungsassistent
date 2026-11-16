"use strict";
// On Stellen (#210): the hint after a search, counted by the app without AI, and the list narrowed to the hits behind a
// piece of evidence („#beleg=…“) or to the dismissed hits with one title word („#verworfen=…“, #225, G66). The way to
// the check with its cost (G15) is on Suche einstellen (#263); the hint words the same estimate (#334).
window.SuchbegriffeStart = (() => {
  const { el, holen, senden, status, textsatz } = window.App;
  const L = window.SuchbegriffeLogik;
  const $ = id => document.getElementById(id);
  let beleg = null;  // { begriff, ids: Set } while the list shows only these hits

  const geaendert = () => document.dispatchEvent(new CustomEvent("suchbegriffe-beleg"));

  /** The cost line of GET /api/suchbegriffe/schaetzung in the words of TrefferLogik.costLine, or why it is missing. */
  async function kostenZeile() {
    const logik = window.TrefferLogik;
    try {
      return logik.costLine(await holen("/api/suchbegriffe/schaetzung"));
    } catch (fehler) {
      return { text: logik.estimateFailedText(fehler.message), usedUp: false };
    }
  }

  /** The estimate comes first, so the hint appears whole; it is only asked for when there is a hint. */
  async function zeigeHinweis(hinweis, texte) {
    if (!hinweis) {
      $("begriff-hinweis").hidden = true;
      return;
    }
    const zeile = await kostenZeile();
    const kosten = zeile.usedUp ? window.Texte.withCodeRequestLink(zeile.text, el) : [zeile.text];
    $("begriff-hinweis-text").textContent = L.hinweisText(hinweis);
    $("begriff-hinweis-nachsatz").replaceChildren(`${texte.hinweisNachsatz} `, ...kosten);
    $("begriff-hinweis-aus").onclick = async () => {
      try {
        await senden("/api/suchbegriffe/ausblenden", { begriff: hinweis.begriff });
        $("begriff-hinweis").hidden = true;
      } catch (fehler) {
        status($("status"), fehler.message, "fehler");
      }
    };
    $("begriff-hinweis").hidden = false;
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
      await zeigeHinweis(antwort.verfuegbar ? antwort.hinweis : null, texte);
    } catch {
      $("begriff-hinweis").hidden = true;  // the hint is extra; the list works without it
    }
  }

  /** The hits a link names: those behind a term (#210) or the dismissed ones with a title word (#225, G66). */
  async function belegHolen(begriff, wort) {
    if (begriff) {
      const antwort = await holen("/api/suchbegriffe/beleg", { begriff });
      return { ...antwort, text: `Gezeigt: ${antwort.ids.length} Treffer, die nur über «${antwort.begriff}» hereinkamen.` };
    }
    const antwort = await holen("/api/suche/verworfen-woerter/beleg", { wort });
    return { begriff: antwort.wort, ids: antwort.ids, text: window.VerworfenWoerterLogik.filterText(antwort.ids.length, antwort.wort) };
  }

  async function belegLaden() {
    const begriff = L.belegAusAdresse(location.hash);
    const wort = window.VerworfenWoerterLogik.ausAdresse(location.hash);
    if (!begriff && !wort) {
      beleg = null;
      $("beleg-filter").hidden = true;
      geaendert();
      return;
    }
    try {
      const antwort = await belegHolen(begriff, wort);
      beleg = { begriff: antwort.begriff, ids: new Set(antwort.ids) };
      $("beleg-filter-text").textContent = antwort.text;
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
