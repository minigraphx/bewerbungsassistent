"use strict";
// „Dateien im Ordner zeigen“ on the page of an application (MIN-346): for upload fields the extension could not fill.
// Texts in the app language through Texte (#427); the server's remarks come as it words them.
(() => {
  const { senden, status } = window.App;
  const Texte = window.Texte;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");

  const message = (text, type = "") => status($("ordner-status"), text, type);
  const count = files => (files === 1 ? Texte.t("1 Datei im Ordner.") : Texte.t("{anzahl} Dateien im Ordner.", { anzahl: files }));

  $("ordner-zeigen").addEventListener("click", async () => {
    message(Texte.t("Wird vorbereitet …"));
    try {
      const { ordner, dateien, hinweise } = await senden("/api/bewerben/ordner", { id: ID });
      $("ordner-text").textContent = ordner;
      $("ordner-pfad").hidden = false;
      message([count(dateien.length), ...hinweise].join(" "), hinweise.length ? "hinweis" : "ok");
    } catch (error) {
      message(error.message, "fehler");
    }
  });

  $("ordner-kopieren").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("ordner-text").textContent);
      message(Texte.t("Pfad kopiert."), "ok");
    } catch {
      message(Texte.t("Kopieren nicht möglich, bitte von Hand markieren."), "hinweis");
    }
  });
})();
