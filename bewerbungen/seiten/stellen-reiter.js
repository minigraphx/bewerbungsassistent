"use strict";
// The tabs of Stellen on the page Firmen (G56, #262): the same counts of new, saved and discarded hits as on /treffer.
// Without them the tabs still lead to the list, only without numbers.
(() => {
  const tabs = document.getElementById("reiter");
  if (!tabs || !tabs.dataset.zaehlen || !window.App) return;
  const STATES = ["neu", "uebernommen", "verworfen"];

  window.App.holen("/api/suche/liste").then(({ treffer }) => {
    for (const state of STATES) {
      tabs.querySelector(`[data-zahl="${state}"]`).textContent = String(treffer.filter(hit => hit.zustand === state).length);
    }
  }).catch(() => { /* no search profile yet: the tabs stay without numbers */ });
})();
