"use strict";
// Excluding a company and taking it back (#226, #303, G65), the same on a hit, on Firmen and on an application.
// The company's hits leave the list or come back, so the sidebar counts the new hits again; a failed change tells
// nobody, because nothing changed. The words for the action are the texts firmen.* in texte.js.
(() => {
  const { senden } = window.App;

  function gemeldet(firma) {
    document.dispatchEvent(new CustomEvent(window.SidebarLogic.HITS_CHANGED));
    return firma;
  }

  /** The company by its name as the page shows it; resolves to { schluessel, ausgeschlossen }. */
  async function ausschliessen(name) {
    return gemeldet((await senden("/api/firmen/ausschliessen", { name })).firma);
  }

  /** The company by its key; its listed hits come back. */
  async function wiederZeigen(schluessel) {
    return gemeldet((await senden("/api/firmen/wieder-zeigen", { schluessel })).firma);
  }

  window.FirmenAusschluss = { ausschliessen, wiederZeigen, gemeldet };
})();
