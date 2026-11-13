"use strict";
// Section „Länge des Lebenslaufs“ (G51): the CV has at most two pages unless the person allows three; the cover
// letter always has one. The next build of the documents takes the choice.
(() => {
  const { holen, senden, status } = window.App;
  const $ = id => document.getElementById(id);

  function zeige(stand) {
    $("drei-seiten").checked = stand.lebenslauf_seiten === 3;
  }

  $("drei-seiten").addEventListener("change", async event => {
    const an = event.target.checked;
    event.target.disabled = true;
    try {
      zeige(await senden("/api/unterlagen/seitengrenze", { lebenslauf_seiten: an ? 3 : 2 }));
      status($("seitengrenze-meldung"), an
        ? "Drei Seiten erlaubt. Mit «Unterlagen erstellen» entsteht der Lebenslauf neu."
        : "Höchstens zwei Seiten. Mit «Unterlagen erstellen» entsteht der Lebenslauf neu.", "ok");
    } catch (fehler) {
      event.target.checked = !an;
      status($("seitengrenze-meldung"), fehler.message, "fehler");
    } finally {
      event.target.disabled = false;
    }
  });

  holen("/api/unterlagen/seitengrenze").then(zeige, fehler => status($("seitengrenze-meldung"), fehler.message, "fehler"));
})();
