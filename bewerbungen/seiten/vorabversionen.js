"use strict";
// Section „Vorabversionen“ (#212, G47): pre-releases as updates, off by default. Only the desktop app has the route;
// elsewhere the section stays hidden.
(() => {
  const { holen, senden, status } = window.App;
  const $ = id => document.getElementById(id);

  function zeige(stand) {
    $("vorabversionen").hidden = false;
    $("beta-an").checked = stand.an;
  }

  $("beta-an").addEventListener("change", async event => {
    const an = event.target.checked;
    event.target.disabled = true;
    try {
      zeige(await senden("/api/app/vorabversionen", { an }));
      status($("beta-meldung"), an ? "Vorabversionen eingeschaltet. Die App sucht gleich nach einer neueren Version."
        : "Vorabversionen ausgeschaltet. Das nächste Update kommt mit der nächsten veröffentlichten Version.", "ok");
    } catch (fehler) {
      event.target.checked = !an;
      status($("beta-meldung"), fehler.message, "fehler");
    } finally {
      event.target.disabled = false;
    }
  });

  holen("/api/app/vorabversionen").then(zeige, () => {});  // the app without the desktop part has no such section
})();
