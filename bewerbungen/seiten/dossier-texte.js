"use strict";
// Greeting and thanks of the dossier (G19) on the application page: shown while the dossier is chosen and not sent.
// The AI drafts both texts (the server replaces name and contacts by placeholders); the person adjusts and saves them.
// An empty text leaves its page out of the dossier.
(() => {
  const { holen, senden, status, bestaetigen } = window.App;
  const W = window.UnterlagenWahl;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const NACH_SPEICHERN = "Für das PDF „Unterlagen erstellen“.";
  const KI_AUS = "Für einen Entwurf zuerst die KI oben unter „Anschreiben“ einrichten. Die Texte lassen sich auch selbst schreiben.";
  let geladen = null; // texts as last loaded or saved; null while the section is hidden
  let kiBereit = false;

  const meldung = (text, art) => status($("dossier-status"), text, art);
  const eingaben = () => ({ gruss: $("dossier-gruss").value, dank: $("dossier-dank").value });
  const hatText = () => Boolean(eingaben().gruss.trim() || eingaben().dank.trim());
  const geaendert = () => geladen !== null && JSON.stringify(eingaben()) !== JSON.stringify(geladen);

  function zeigeTexte(texte) {
    $("dossier-gruss").value = texte.gruss;
    $("dossier-dank").value = texte.dank;
    geladen = { gruss: texte.gruss, dank: texte.dank };
  }

  function leer(texte) {
    const fehlt = [!texte.gruss && "Begrüssung", !texte.dank && "Dank"].filter(Boolean);
    return fehlt.length ? ` Ohne ${fehlt.join(" und ")} entfällt die Seite dazu.` : "";
  }

  async function ladeTexte() {
    try {
      zeigeTexte(await holen("/api/dossier/texte", { id: ID }));
      if (!kiBereit) meldung(KI_AUS);
    } catch (fehler) {
      meldung("Begrüssung und Dank nicht lesbar: " + fehler.message, "fehler");
    }
  }

  /** Follows the page: visible with a chosen dossier until sent; the texts load when the section opens. */
  function folge(event) {
    const b = event.detail.bewerbung;
    const zeigen = W.gewaehlt(b) === "dossier" && !b.versand;
    $("dossier-texte").hidden = !zeigen;
    if (!zeigen) geladen = null;
    else if (geladen === null) ladeTexte();
  }

  async function speichern() {
    $("dossier-speichern").disabled = true;
    try {
      const texte = await senden("/api/dossier/texte", eingaben(), { id: ID });
      zeigeTexte(texte);
      meldung(`Gespeichert. ${NACH_SPEICHERN}${leer(texte)}`, "ok");
    } catch (fehler) {
      meldung("Speichern fehlgeschlagen: " + fehler.message, "fehler");
    } finally {
      $("dossier-speichern").disabled = false;
    }
  }

  async function entwerfen() {
    $("dossier-entwerfen").disabled = true;
    meldung("Begrüssung und Dank werden entworfen … das kann bis zu einer Minute dauern.");
    try {
      const ergebnis = await senden("/api/ki/dossier-texte", {}, { id: ID });
      zeigeTexte(ergebnis);
      const verdaechtig = (ergebnis.suspicious_lines || []).length
        ? ` Verdächtige Zeilen im Inserat, nicht befolgt: ${ergebnis.suspicious_lines.join(" · ")}` : "";
      meldung(`Entworfen und gespeichert; ein früherer Stand liegt unter „Entwürfe“. Bitte lesen und anpassen. ${NACH_SPEICHERN}${verdaechtig}`,
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
      kiBereit = false; // the AI section above says why
    }
    $("dossier-entwerfen").disabled = !kiBereit;
  }

  if (!ID) return;
  document.addEventListener("bewerbung-geladen", folge);
  $("dossier-speichern").addEventListener("click", speichern);
  bestaetigen($("dossier-entwerfen"), "Vorhandene Texte ersetzen? Nochmals klicken", entwerfen, () => hatText() || geaendert());
  ladeKi();
})();
