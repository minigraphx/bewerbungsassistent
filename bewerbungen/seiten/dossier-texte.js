"use strict";
// Greeting and thanks of the dossier (G19) in the dialog «Dossier gestalten» (#322, dossier-dialog.js): the AI drafts
// both texts (the server replaces name and contacts by placeholders); the person adjusts them, and «Übernehmen» saves
// them. An empty text leaves its page out of the dossier. The dossier line shows their state.
(() => {
  const { holen, senden, status, bestaetigen } = window.App;
  const W = window.UnterlagenWahl;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  // Texts in the app language (#429); the AI's lines and the server's reasons stay as they come
  const Texte = { t: (deutsch, werte) => window.Texte.t(deutsch, werte) };
  let geladen = null; // texts as last loaded or saved; null while no dossier is chosen
  let kiBereit = false;

  const meldung = (text, art) => status($("dossier-status"), text, art);
  const eingaben = () => ({ gruss: $("dossier-gruss").value, dank: $("dossier-dank").value });
  const hatText = () => Boolean(eingaben().gruss.trim() || eingaben().dank.trim());
  const geaendert = () => geladen !== null && JSON.stringify(eingaben()) !== JSON.stringify(geladen);

  function merke(texte) {
    geladen = { gruss: texte.gruss, dank: texte.dank };
    $("dossier-kurz-texte").textContent = window.UnterlagenErgebnis.textsState(geladen);
  }

  function fuelle(texte) {
    $("dossier-gruss").value = texte.gruss;
    $("dossier-dank").value = texte.dank;
  }

  async function ladeTexte() {
    try {
      merke(await holen("/api/dossier/texte", { id: ID }));
      return true;
    } catch (fehler) {
      meldung(Texte.t("Begrüssung und Dank nicht lesbar: {fehler}", { fehler: fehler.message }), "fehler");
      return false;
    }
  }

  /** Follows the page: with a chosen dossier until sent the texts load once, for the line and the dialog. */
  function folge(event) {
    const b = event.detail.bewerbung;
    const zeigen = W.gewaehlt(b) === "dossier" && !b.versand;
    if (!zeigen) geladen = null;
    else if (geladen === null) ladeTexte().then(ok => { if (ok) fuelle(geladen); });
  }

  /** When the dialog opens: the texts as saved, read anew, unless unsaved ones are still in the fields. */
  async function oeffnen() {
    meldung("");
    if (geaendert()) return;
    if (geladen) fuelle(geladen);
    const vorher = JSON.stringify(eingaben());
    if (await ladeTexte() && JSON.stringify(eingaben()) === vorher) fuelle(geladen);
  }

  /** Saves changed texts with «Übernehmen»; null when nothing changed. Errors go to the dialog. */
  async function speichern() {
    if (!geaendert()) return null;
    const texte = await senden("/api/dossier/texte", eingaben(), { id: ID });
    merke(texte);
    fuelle(texte);
    return texte;
  }

  function verwerfen() {
    if (geladen) fuelle(geladen);
  }

  async function entwerfen() {
    $("dossier-entwerfen").disabled = true;
    meldung(Texte.t("Begrüssung und Dank werden entworfen … das kann bis zu einer Minute dauern."));
    try {
      const ergebnis = await senden("/api/ki/dossier-texte", {}, { id: ID });
      merke(ergebnis);
      fuelle(ergebnis);
      const verdaechtig = (ergebnis.suspicious_lines || []).length > 0;
      const zeilen = verdaechtig ? ergebnis.suspicious_lines.join(" · ") : "";
      meldung(verdaechtig
        ? Texte.t("Entworfen und gespeichert; ein früherer Stand liegt unter „Entwürfe“. Bitte lesen und anpassen. Für das PDF „Unterlagen erstellen“. Verdächtige Zeilen im Inserat, nicht befolgt: {zeilen}", { zeilen })
        : Texte.t("Entworfen und gespeichert; ein früherer Stand liegt unter „Entwürfe“. Bitte lesen und anpassen. Für das PDF „Unterlagen erstellen“."),
      verdaechtig ? "hinweis" : "ok");
    } catch (fehler) {
      meldung(fehler.message, "fehler");
    } finally {
      $("dossier-entwerfen").disabled = !kiBereit;
    }
  }

  async function ladeKi() {
    try {
      const s = await holen("/api/ki/status");
      kiBereit = Boolean(s.eingerichtet && s.einwilligung?.erteilt);
    } catch {
      kiBereit = false; // the AI section of the page says why
    }
    $("dossier-entwerfen").disabled = !kiBereit;
    // a lasting reason beside the switched-off button, not a message that fades
    $("dossier-ki-aus").hidden = kiBereit;
  }

  window.DossierTexte = { oeffnen, geaendert, speichern, verwerfen };
  if (!ID) return;
  document.addEventListener("bewerbung-geladen", folge);
  bestaetigen($("dossier-entwerfen"), Texte.t("Vorhandene Texte ersetzen? Nochmals klicken"), entwerfen, () => hatText() || geaendert());
  ladeKi();
})();
