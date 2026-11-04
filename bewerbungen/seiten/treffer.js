"use strict";
// Hits of the job search (MIN-339): list, rate with the AI in packages (MIN-372), take over into the register, discard.
// The search itself runs in the browser extension; this page starts it through app-bridge.js.
(() => {
  const { holen, senden, el, status, datum } = window.App;
  const logik = window.TrefferLogik;
  const $ = id => document.getElementById(id);
  const SEITE = "bewerbungsassistent-seite";
  const ERWEITERUNG = "bewerbungsassistent-erweiterung";

  let alle = [];
  let einstellungen = { auto_bewerten: true, zuschauen: false, beruf_sterne: {} };
  let paket = 10;
  let grenze = 30;
  let lehrstelle = false;
  let bewertungslauf = null;  // { halt: bool } while a run is going
  let letzterSuchlauf = "";
  const offen = new Set();  // ids with details shown

  function anzeigen(treffer) {
    alle = alle.map(t => (t.id === treffer.id ? treffer : t));
    zeigeListe();
  }

  async function bewerte(t, knopf) {
    if (knopf) knopf.disabled = true;
    status($("status"), `KI bewertet „${t.stelle}“ …`);
    try {
      anzeigen(await senden("/api/suche/bewerten", {}, { id: t.id }));
      offen.add(t.id);
      zeigeListe();
      status($("status"), "");
      return true;
    } catch (fehler) {
      status($("status"), `${t.stelle}: ${fehler.message}`, "fehler");
      if (knopf) knopf.disabled = false;
      return false;
    }
  }

  async function uebernimm(t, knopf) {
    knopf.disabled = true;
    try {
      const neu = await senden("/api/suche/uebernehmen", {}, { id: t.id });
      anzeigen(neu);
      status($("status"), `„${t.stelle}“ ist jetzt im Register.`, "ok");
    } catch (fehler) {
      status($("status"), fehler.message, "fehler");
      knopf.disabled = false;
      lade();
    }
  }

  async function verwirf(t, zurueck) {
    try {
      anzeigen(await senden("/api/suche/verwerfen", { zurueck }, { id: t.id }));
    } catch (fehler) {
      status($("status"), fehler.message, "fehler");
    }
  }

  function liste(titel, eintraege) {
    return eintraege && eintraege.length ? el("div", {}, el("strong", {}, titel), el("ul", {}, eintraege.map(e => el("li", {}, e)))) : null;
  }

  function details(t) {
    const b = t.bewertung;
    const text = el("pre", { class: "inserat", hidden: true });
    const knopf = el("button", { type: "button" }, "Inserat anzeigen");
    knopf.addEventListener("click", async () => {
      if (text.hidden && !text.textContent) {
        try { text.textContent = (await holen("/api/suche/text", { id: t.id })).text || "Kein Text gespeichert."; }
        catch (fehler) { text.textContent = fehler.message; }
      }
      text.hidden = !text.hidden;
      knopf.textContent = text.hidden ? "Inserat anzeigen" : "Inserat verbergen";
    });
    const weitere = (t.weitere || []).map(w => el("li", {}, el("a", { href: w.link, target: "_blank", rel: "noopener" }, `Auch auf ${w.portal}`)));
    return el("td", { colspan: 8 },
      b ? el("p", {}, b.zusammenfassung) : el("p", { class: "leise" }, "Noch nicht bewertet."),
      b && b.unsicher ? el("p", { class: "status hinweis" }, `Note unsicher: ${b.unsicher}`) : null,
      b && b.beruf_note ? el("p", {}, `Der Beruf passt zu deinen Fähigkeiten und Wünschen: Note ${notenText(b.beruf_note)}. Diese Lehrstelle: Note ${notenText(b.note)}.`) : null,
      b ? liste("Passt", b.passt) : null,
      b ? liste("Haken", b.haken) : null,
      b && b.auffaellig && b.auffaellig.length ? el("p", { class: "status fehler" },
        "Auffällige Zeilen im Inserat (nicht befolgt): " + b.auffaellig.join(" · ")) : null,
      t.hinweis ? el("p", { class: "status hinweis" }, t.hinweis) : null,
      weitere.length ? el("ul", {}, weitere) : null,
      el("div", { class: "knoepfe" }, knopf), text);
  }

  function aktionen(t) {
    if (t.zustand === "uebernommen") {
      return [el("a", { href: "/bewerbung?" + new URLSearchParams({ id: t.bewerbung_id }) }, "Zur Bewerbung")];
    }
    if (t.zustand === "verworfen") {
      return [el("button", { type: "button", onclick: () => verwirf(t, true) }, "Zurückholen")];
    }
    const bewerten = el("button", { type: "button", disabled: bewertungslauf !== null }, t.bewertung ? "Neu bewerten" : "Bewerten");
    bewerten.addEventListener("click", () => bewerte(t, bewerten));
    const uebernehmen = el("button", { type: "button", class: "haupt" }, "Übernehmen");
    uebernehmen.addEventListener("click", () => uebernimm(t, uebernehmen));
    return [bewerten, uebernehmen,
      el("button", { type: "button", onclick: () => verwirf(t, false) }, "Verwerfen")];
  }

  const notenText = note => String(note).replace(".", ",");
  const sternText = anzahl => "★".repeat(anzahl) + "☆".repeat(5 - anzahl);

  function zeile(t) {
    const note = t.bewertung ? notenText(t.bewertung.note) : "–";
    const sterne = t.beruf ? einstellungen.beruf_sterne[t.beruf] : 0;
    const umschalten = el("button", { type: "button", class: "link", "aria-expanded": String(offen.has(t.id)) }, t.stelle);
    umschalten.addEventListener("click", () => {
      if (offen.has(t.id)) offen.delete(t.id); else offen.add(t.id);
      zeigeListe();
    });
    const alter = t.alter_tage !== undefined
      ? el("div", { class: "leise" }, `${t.alter_tage} ${t.alter_tage === 1 ? "Tag" : "Tage"} online`) : null;
    const haupt = el("tr", {},
      el("td", { class: "note" }, note, t.bewertung?.unsicher ? el("span", { class: "unsicher-marke", title: `Note unsicher: ${t.bewertung.unsicher}` }, " ?") : null),
      el("td", {}, logik.istSchnupperlehre(t) ? el("span", { class: "art-marke" }, "Schnupperlehre") : null,
        umschalten, " ", el("a", { href: t.link, target: "_blank", rel: "noopener", title: "Inserat auf dem Portal öffnen" }, "↗"),
        sterne ? el("span", { class: "eigene-sterne", "aria-label": `${sterne} von 5 Sternen` }, sternText(sterne)) : null),
      el("td", {}, t.firma, t.hinweis ? el("span", { class: "marke-status", "data-status": "Beworben", title: t.hinweis }, " schon beworben?") : null),
      el("td", {}, t.ort || ""), el("td", { class: "knapp" }, t.pensum || t.lehrbeginn || ""),
      el("td", {}, t.portal, (t.weitere || []).length ? ` +${t.weitere.length}` : ""),
      el("td", { class: "knapp" }, datum(t.gefunden_am), alter),
      el("td", {}, el("div", { class: "knoepfe" }, aktionen(t))));
    return offen.has(t.id) ? [haupt, el("tr", { class: "details" }, details(t))] : [haupt];
  }

  function zeigeListe() {
    const zustand = $("zustand").value;
    $("art").hidden = !logik.beideArten(alle);
    const art = $("art").hidden ? "" : $("art").value;
    const passend = logik.nachArt(alle.filter(t => !zustand || t.zustand === zustand), art);
    const sichtbar = logik.sortiert(passend, einstellungen.beruf_sterne);
    $("liste").replaceChildren(...sichtbar.flatMap(zeile));
    $("leer").hidden = sichtbar.length > 0;
    zeigeBewerten();
  }

  function zeigeBewerten() {
    const ids = logik.zuBewerten(alle).map(t => t.id);
    const laeuft = bewertungslauf !== null;
    $("anhalten").hidden = !laeuft;
    $("bewerten-knoepfe").replaceChildren(...(laeuft ? [] : logik.knoepfe(ids.length, paket, grenze).map(knopf => {
      return el("button", { type: "button", onclick: () => starteBewertung(ids.slice(0, knopf.anzahl)) }, knopf.text);
    })));
    const proTreffer = logik.kostenProTreffer(alle);
    const kosten = ids.length && proTreffer !== null ? `Bisher etwa ${proTreffer.toFixed(3)} USD pro Treffer.` : "";
    $("kosten-hinweis").textContent = laeuft ? "" : logik.alleBewertet(alle) ? "Alle Treffer sind bewertet." : kosten;
    $("auto-bewerten").checked = einstellungen.auto_bewerten;
    $("zuschauen").checked = einstellungen.zuschauen;
    $("auto-text").textContent = `Neue Treffer nach der Suche automatisch bewerten (höchstens ${grenze} pro Suche)`;
    zeigeBerufe();
  }

  function sterneWaehlen(beruf, anzahl) {
    senden("/api/suche/beruf-sterne", { beruf, sterne: anzahl })
      .then(neu => { einstellungen = neu; zeigeListe(); })
      .catch(fehler => status($("status"), fehler.message, "fehler"));
  }

  function zeigeBerufe() {
    const berufe = [...new Set(alle.map(t => t.beruf).filter(Boolean))].sort((a, b) => a.localeCompare(b, "de"));
    $("berufe").hidden = !lehrstelle || berufe.length === 0;
    $("berufe-liste").replaceChildren(...berufe.map(beruf => {
      const aktuell = einstellungen.beruf_sterne[beruf] || 0;
      const knoepfe = [1, 2, 3, 4, 5].map(zahl => el("button", {
        type: "button", "aria-label": `${zahl} von 5 Sternen für ${beruf}`, "aria-pressed": String(zahl === aktuell),
        onclick: () => sterneWaehlen(beruf, zahl === aktuell ? 0 : zahl),
      }, zahl <= aktuell ? "★" : "☆"));
      return el("li", {}, el("span", { class: "sterne" }, knoepfe), el("span", {}, beruf));
    }));
  }

  function schlussText(stand) {
    const teile = [`${stand.bewertet} von ${stand.von} Treffern bewertet`];
    if (stand.offen.length) teile.push(`${stand.offen.length} ohne brauchbare Antwort, die lassen sich einzeln nochmals versuchen`);
    if (stand.ohneText) teile.push(`${stand.ohneText} ohne Inseratstext`);
    if (stand.gestoppt) teile.push("angehalten");
    const rest = logik.zuBewerten(alle).length;
    if (rest && !stand.gestoppt && !stand.fehler) teile.push(`noch ${rest} offen`);
    return `${teile.join(", ")}. Kosten: ${stand.kosten.toFixed(2)} USD.`;
  }

  /** Rate in packages with progress; one run at a time. The list updates after every package. */
  async function starteBewertung(ids) {
    if (bewertungslauf || !ids.length) return;
    const lauf = { halt: false };
    bewertungslauf = lauf;
    $("anhalten").disabled = false;
    zeigeListe();
    status($("status"), `KI bewertet: 0 von ${ids.length} …`);
    const stand = await logik.bewerteAlle(ids, {
      paket,
      sende: gruppe => senden("/api/suche/bewerten-paket", { ids: gruppe }),
      angehalten: () => lauf.halt,
      fortschritt: (zwischen, treffer) => {
        const neu = new Map(treffer.map(t => [t.id, t]));
        alle = alle.map(t => (neu.has(t.id) ? { ...neu.get(t.id), ohne_text: false } : t));
        zeigeListe();
        status($("status"), `KI bewertet: ${zwischen.bewertet} von ${ids.length} …`);
      },
    });
    bewertungslauf = null;
    zeigeListe();
    if (stand.fehler) status($("status"), `${stand.fehler} ${schlussText(stand)}`, "fehler");
    else status($("status"), schlussText(stand), stand.offen.length || stand.gestoppt ? "hinweis" : "ok");
  }

  function bewerteNachSuche() {
    if (einstellungen.auto_bewerten) starteBewertung(logik.zuBewerten(alle).slice(0, grenze).map(t => t.id));
  }

  // A hint with a field in „Meine Angaben“ leads there.
  function hinweisZeile(text, ziele) {
    const inhalt = ziele[text] ? el("a", { href: `/angaben#${new URLSearchParams({ feld: ziele[text] })}` }, text) : text;
    return el("li", { "data-stufe": "hinweis" }, inhalt);
  }

  function zeigeLetzteSuche(lauf, hinweise, ziele) {
    if (lauf) {
      const neu = Object.values(lauf.portale || {}).reduce((summe, p) => summe + (p.neu || 0), 0);
      $("letzte").textContent = `Letzte Suche am ${datum(lauf.datum)}: ${neu} neue Treffer.`;
    }
    const probleme = Object.entries(lauf?.portale || {}).filter(([, p]) => p.problem).map(([, p]) => p.problem);
    $("probleme").replaceChildren(
      ...probleme.map(p => el("li", { "data-stufe": "fehler" }, p)),
      ...hinweise.map(h => hinweisZeile(h, ziele)));
  }

  function aufzaehlung(namen) {
    return namen.join(", ").replace(/, ([^,]*)$/, " und $1");
  }

  // The page follows the search profile: apprenticeships address the person informally, as everywhere else.
  function zeigeArt(art, portale, angebote) {
    lehrstelle = art === "lehrstelle";
    $("angebot-wahl").hidden = !lehrstelle;
    $("angebot").value = logik.wahlAus(angebote);
    $("titel").textContent = lehrstelle ? "Lehrstellensuche" : "Stellensuche";
    $("suchen").textContent = lehrstelle ? logik.sucheText(angebote) : "Stellen suchen";
    $("spalte-rahmen").textContent = lehrstelle ? "Lehrbeginn" : "Pensum";
    $("erweiterung-link").textContent = lehrstelle ? "So richtest du sie ein" : "So richten Sie sie ein";
    $("hilfe").textContent = lehrstelle
      ? `Die Browser-Erweiterung sucht auf ${aufzaehlung(portale)} nach deinem Suchprofil, in deinem Browser und nur, wenn du die Suche startest. Neue Treffer erscheinen hier, und die KI schätzt die Passung als Note von 1 bis 6 ein: nach der Suche von selbst, wenn diese Seite offen ist, sonst auf Knopfdruck. „Übernehmen“ legt die Bewerbung mit dem Inseratstext an.`
      : `Die Browser-Erweiterung sucht auf ${aufzaehlung(portale)} nach Ihrem Suchprofil, in Ihrem Browser und nur, wenn Sie die Suche starten. Neue Stellen erscheinen hier, und die KI schätzt die Passung als Note von 1 bis 6 ein: nach der Suche von selbst, wenn diese Seite offen ist, sonst auf Knopfdruck. „Übernehmen“ legt die Bewerbung mit dem Inseratstext an.`;
  }

  // Only the desktop app has „Meine Angaben“; without it there is nothing to say.
  async function zeigeNichtUebernommen() {
    const offen = await holen("/api/angaben/offen").then(a => a.offen, () => false);
    $("angaben-offen").hidden = !offen;
    $("angaben-offen-text").textContent = lehrstelle
      ? "In „Meine Angaben“ hast du Änderungen, die noch nicht übernommen sind. Die Suche nimmt noch die bisherigen Angaben. "
      : "In „Meine Angaben“ gibt es Änderungen, die noch nicht übernommen sind. Die Suche nimmt noch die bisherigen Angaben. ";
  }

  let ladeNummer = 0;

  async function lade() {
    const nummer = ++ladeNummer;
    try {
      const daten = await holen("/api/suche/liste");
      if (nummer !== ladeNummer) return; // a newer load is on its way, and this answer may be older
      alle = daten.treffer;
      einstellungen = daten.einstellungen;
      paket = daten.paket;
      grenze = daten.grenze;
      zeigeArt(daten.art, daten.portale || [], daten.angebote || []);
      window.Suchbegriffe.zeige(daten.art, daten.gesuchte_berufe || [], daten.gesuchte_schluessel || []);
      zeigeLetzteSuche(daten.letzte_suche, daten.hinweise || [], daten.hinweis_ziele || {});
      zeigeNichtUebernommen();
      zeigeListe();
    } catch (fehler) {
      status($("status"), fehler.message, "fehler");
    }
  }

  // Extension: present (marker or message), progress of a running search
  function erweiterungDa() {
    $("suchen").disabled = false;
    $("ohne-erweiterung").hidden = true;
  }

  function laufText(lauf) {
    if (lauf.zustand === "fehler") return [lauf.fehler || "Die Suche ist abgebrochen.", "fehler"];
    if (lauf.zustand === "fertig" && lauf.ergebnis?.abgebrochen) return ["Suche abgebrochen. Was schon gefunden war, ist da.", "hinweis"];
    if (lauf.zustand === "fertig") return ["Suche fertig.", "ok"];
    const s = lauf.schritt || {};
    if (s.phase === "suche") return [`${s.portal}: suche „${s.stichwort}“, Seite ${s.seite} …`, ""];
    if (s.phase === "texte") return [`${s.portal}: lese Inserate (${s.fertig} von ${s.von}) …`, ""];
    return ["Suche startet …", ""];
  }

  window.addEventListener("message", event => {
    if (event.source !== window || event.origin !== location.origin) return;
    const daten = event.data;
    if (!daten || daten.quelle !== ERWEITERUNG) return;
    erweiterungDa();
    if (daten.art === "lauf") {
      const [text, art] = laufText(daten.lauf);
      status($("lauf"), text, art);
      $("suchen").disabled = daten.lauf.zustand === "laeuft";
      const eben = letzterSuchlauf === "laeuft" && daten.lauf.zustand === "fertig";
      letzterSuchlauf = daten.lauf.zustand;
      // Only a search that ended while this page was open starts a rating by itself.
      if (eben) lade().then(bewerteNachSuche);
      else if (daten.lauf.zustand === "fertig") lade();
    } else if (daten.art === "antwort" && daten.antwort?.fehler) {
      status($("lauf"), daten.antwort.fehler, "fehler");
      $("suchen").disabled = false;
    }
  });

  $("suchen").addEventListener("click", () => {
    $("suchen").disabled = true;
    status($("lauf"), "Suche startet …");
    window.postMessage({ quelle: SEITE, art: "suche-starten" }, location.origin);
  });
  $("zustand").addEventListener("change", zeigeListe);
  $("art").addEventListener("change", zeigeListe);
  $("angebot").addEventListener("change", async () => {
    try {
      const { angebote } = await senden("/api/suche/angebot", { wahl: $("angebot").value });
      $("suchen").textContent = logik.sucheText(angebote);
      status($("lauf"), "");
    } catch (fehler) {
      status($("lauf"), fehler.message, "fehler");
      lade();
    }
  });
  $("anhalten").addEventListener("click", () => {
    if (bewertungslauf) bewertungslauf.halt = true;
    $("anhalten").disabled = true;
    status($("status"), "Wird nach dem laufenden Paket angehalten …");
  });
  $("auto-bewerten").addEventListener("change", event => {
    senden("/api/suche/einstellungen", { auto_bewerten: event.target.checked })
      .then(neu => { einstellungen = neu; })
      .catch(fehler => { status($("status"), fehler.message, "fehler"); zeigeBewerten(); });
  });

  $("zuschauen").addEventListener("change", event => {
    senden("/api/suche/einstellungen", { zuschauen: event.target.checked })
      .then(neu => { einstellungen = neu; })
      .catch(fehler => { status($("status"), fehler.message, "fehler"); zeigeBewerten(); });
  });

  if (document.documentElement.dataset.bewerbungsassistentErweiterung) erweiterungDa();
  else setTimeout(() => { if ($("suchen").disabled && !$("lauf").textContent) $("ohne-erweiterung").hidden = false; }, 1500);
  document.addEventListener("suchprofil-geaendert", lade);
  lade();
})();
