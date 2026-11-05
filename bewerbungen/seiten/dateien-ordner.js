"use strict";
// „Dateien im Ordner zeigen“ on the page of an application (MIN-346): for upload fields the extension could not fill.
(() => {
  const { senden, status } = window.App;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");

  const message = (text, type = "") => status($("ordner-status"), text, type);

  $("ordner-zeigen").addEventListener("click", async () => {
    message("Wird vorbereitet …");
    try {
      const { ordner, dateien, hinweise } = await senden("/api/bewerben/ordner", { id: ID });
      $("ordner-text").textContent = ordner;
      $("ordner-pfad").hidden = false;
      const count = `${dateien.length} ${dateien.length === 1 ? "Datei" : "Dateien"} im Ordner.`;
      message([count, ...hinweise].join(" "), hinweise.length ? "hinweis" : "ok");
    } catch (error) {
      message(error.message, "fehler");
    }
  });

  $("ordner-kopieren").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("ordner-text").textContent);
      message("Pfad kopiert.", "ok");
    } catch {
      message("Kopieren nicht möglich, bitte von Hand markieren.", "hinweis");
    }
  });
})();
