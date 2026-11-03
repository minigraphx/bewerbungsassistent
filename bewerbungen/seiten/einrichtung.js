"use strict";
// Setup of the packaged app (MIN-342): data folder, import of the einstieg file, AI invitation.
// Folder and file are chosen in the system's own dialog; the server reads the file from disk.
(() => {
  const { holen, senden, el, status } = window.App;
  const $ = id => document.getElementById(id);
  const usd = wert => `${Number(wert || 0).toFixed(2)} USD`;

  let aktuell = null;  // the data folder in use, once chosen

  function ordnerKnopf() {
    $("ordner-uebernehmen").disabled = aktuell !== null && $("ordner").value.trim() === aktuell;
  }

  function zeigeOrdner(info) {
    $("ordner").value = info.datenordner || info.vorschlag;
    const fehlt = $("ordner-fehlt");
    fehlt.hidden = !info.fehlt;
    fehlt.textContent = info.fehlt
      ? `Der Datenordner ${info.datenordner} wurde nicht gefunden (z.B. USB-Stick nicht eingesteckt). Sobald er wieder verfügbar ist, diese Seite neu laden; oder einen anderen Ordner wählen.`
      : "";
    const bereit = info.eingerichtet && !info.fehlt;
    if (bereit) status($("ordner-status"), `Datenordner: ${info.datenordner}`, "ok");
    for (const id of ["datei", "datei-waehlen", "importieren"]) $(id).disabled = !bereit;
    $("ordner-uebernehmen").textContent = bereit ? "Anderen Ordner verwenden" : "Diesen Ordner verwenden";
    $("fertig").hidden = !bereit;
    aktuell = bereit ? info.datenordner : null;
    ordnerKnopf();
  }

  async function pruefeOrdner() {
    const pfad = $("ordner").value.trim();
    if (!pfad) return;
    try {
      const ergebnis = await senden("/api/app/ordner-pruefen", { pfad });
      status($("ordner-status"), ergebnis.text, "hinweis");
    } catch (fehler) {
      status($("ordner-status"), fehler.message, "fehler");
    }
  }

  async function waehle(art, feld, danach) {
    try {
      const ergebnis = await senden("/api/app/waehlen", { art });
      if (ergebnis.pfad) {
        $(feld).value = ergebnis.pfad;
        ordnerKnopf();
        await danach();
      }
    } catch (fehler) {
      status($(art === "ordner" ? "ordner-status" : "import-status"), fehler.message, "fehler");
    }
  }

  async function uebernehmeOrdner() {
    $("ordner-uebernehmen").disabled = true;
    try {
      zeigeOrdner(await senden("/api/app/datenordner", { pfad: $("ordner").value }));
    } catch (fehler) {
      status($("ordner-status"), fehler.message, "fehler");
    } finally {
      ordnerKnopf();
    }
  }

  function zeigeImport(ergebnis) {
    const zeilen = [
      ...ergebnis.geschrieben.map(datei => el("li", { "data-stufe": "ok" }, `Angelegt: ${datei}`)),
      ergebnis.dokumente.length ? el("li", { "data-stufe": "ok" }, `${ergebnis.dokumente.length} Dokument(e) abgelegt`) : null,
      ergebnis.unvollstaendig ? el("li", { "data-stufe": "hinweis" },
        "Einige Angaben fehlen noch; sie werden mit Ihrer Begleitperson aus den Dokumenten ergänzt.") : null,
    ];
    $("import-ergebnis").replaceChildren(...zeilen.filter(Boolean));
  }

  async function importiere(ersetzen = false) {
    $("ersetzen").hidden = true;
    $("import-ergebnis").replaceChildren();
    status($("import-status"), "Wird importiert …");
    try {
      zeigeImport(await senden("/api/app/einstieg", { pfad: $("datei").value, ersetzen }));
      status($("import-status"), "Import abgeschlossen.", "ok");
    } catch (fehler) {
      const vorhanden = fehler.status === 409 && fehler.daten?.vorhanden;
      status($("import-status"), fehler.message, vorhanden ? "hinweis" : "fehler");
      $("ersetzen").hidden = !vorhanden;
    }
  }

  function zeigeKi(s) {
    let text = s.hinweis || "Die KI ist nicht eingerichtet.";
    if (s.eingerichtet) {
      text = s.vermittlung && s.budget_usd !== undefined
        ? `Verbunden. Diesen Monat verbraucht: ${usd(s.verbraucht_usd)} von ${usd(s.budget_usd)}.`
        : "Verbunden.";
    } else if (s.einladung) {
      text = "Noch nicht verbunden: Einladungscode eingeben.";
    }
    status($("ki-zustand"), text, s.eingerichtet ? "ok" : "hinweis");
    $("ki-einladung").hidden = s.eingerichtet || !s.einladung;
  }

  async function ladeKi() {
    try { zeigeKi(await holen("/api/ki/status")); }
    catch (fehler) { status($("ki-zustand"), fehler.message, "fehler"); }
  }

  async function loeseEin() {
    $("ki-einloesen").disabled = true;
    try {
      zeigeKi(await senden("/api/ki/einladung", { code: $("ki-code").value }));
      $("ki-code").value = "";
    } catch (fehler) {
      status($("ki-zustand"), fehler.message, "fehler");
    } finally {
      $("ki-einloesen").disabled = false;
    }
  }

  $("ordner").addEventListener("input", ordnerKnopf);
  $("ordner").addEventListener("change", pruefeOrdner);
  $("ordner-waehlen").addEventListener("click", () => waehle("ordner", "ordner", pruefeOrdner));
  $("ordner-uebernehmen").addEventListener("click", uebernehmeOrdner);
  $("datei-waehlen").addEventListener("click", () => waehle("datei", "datei", async () => {}));
  $("importieren").addEventListener("click", () => importiere(false));
  $("ersetzen").addEventListener("click", () => importiere(true));
  $("ki-einloesen").addEventListener("click", loeseEin);

  holen("/api/app/einrichtung").then(zeigeOrdner)
    .catch(() => status($("ordner-status"), "Die Einrichtung gibt es nur in der installierten App.", "hinweis"));
  ladeKi();
})();
