"use strict";
// Section „Mit dem eigenen Claude-Abo arbeiten“ (MIN-377). Only the desktop app has these routes; elsewhere it stays hidden.
(() => {
  const { holen, senden, el, status } = window.App;
  const $ = id => document.getElementById(id);
  const TOKEN = document.querySelector('meta[name="token"]').content;
  const TITEL = { einstieg: "Einstieg", jobsuche: "Stellensuche", bewerbung: "Bewerbung" };

  function zeige(stand) {
    $("abo-aus").hidden = stand.zugang;
    $("abo-an").hidden = !stand.zugang;
    const veraltet = stand.desktop_veraltet;
    $("abo-desktop").textContent = veraltet ? "Eintrag in Claude Desktop erneuern" : stand.desktop_eingetragen ? "Aus Claude Desktop entfernen" : "In Claude Desktop eintragen";
    $("abo-desktop").dataset.eintragen = veraltet || !stand.desktop_eingetragen ? "ja" : "nein";
    $("abo-desktop-stand").textContent = veraltet ? "Der Eintrag zeigt auf einen alten Ort der App."
      : stand.desktop_eingetragen ? "Eingetragen. Claude Desktop einmal ganz beenden und neu öffnen." : "";
    $("abo-code").textContent = stand.code_befehl;
    $("abo-text").textContent = stand.desktop_text;
    $("abo-datei").textContent = stand.desktop_datei;
    $("abo-skills").replaceChildren(...stand.skills.map(name => el("li", {},
      el("a", { href: `/api/claude/skill?name=${encodeURIComponent(name)}&t=${encodeURIComponent(TOKEN)}`, download: `${name}.zip` }, `${TITEL[name] || name} (${name}.zip)`))));
  }

  async function ausfuehren(pfad, daten, meldung) {
    try {
      zeige(await senden(pfad, daten));
      status($("abo-meldung"), meldung, "ok");
    } catch (fehler) {
      status($("abo-meldung"), fehler.message, "fehler");
    }
  }

  $("abo-bestaetigt").addEventListener("change", event => { $("abo-einschalten").disabled = !event.target.checked; });
  $("abo-einschalten").addEventListener("click", () => ausfuehren("/api/claude/zugang", { an: true, bestaetigt: $("abo-bestaetigt").checked }, "Der Zugang ist eingeschaltet."));
  $("abo-ausschalten").addEventListener("click", async () => {
    await ausfuehren("/api/claude/zugang", { an: false }, "Der Zugang ist ausgeschaltet. Claude erreicht die App nicht mehr.");
    $("abo-bestaetigt").checked = false;
    $("abo-einschalten").disabled = true;
  });
  $("abo-desktop").addEventListener("click", event => {
    const eintragen = event.target.dataset.eintragen === "ja";
    ausfuehren("/api/claude/desktop", { eintragen }, eintragen ? "In Claude Desktop eingetragen." : "Aus Claude Desktop entfernt.");
  });

  holen("/api/claude/stand").then(zeige, () => {});  // the app without the desktop part has no such section
})();
