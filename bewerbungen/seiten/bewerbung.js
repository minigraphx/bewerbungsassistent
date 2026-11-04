"use strict";
(() => {
  const { holen, senden, el, status, datum, url, bestaetigen } = window.App;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const FELDER = ["firma", "stelle", "firma_schluessel", "ort", "pensum", "vermittler", "portal", "link", "formular_link",
                  "status", "variante", "passung", "eingetragen_am", "beworben_am", "frist", "gespraech_am", "absage_am",
                  "adresse", "kontaktperson", "kontakt", "notiz"];
  const JOBROOM = [["datum", "Datum der Bewerbung"], ["arbeitgeber", "Arbeitgeber"], ["adresse", "Adresse"],
    ["kontaktperson", "Kontaktperson"], ["kontakt", "Telefon / E-Mail"], ["stelle", "Stelle"], ["pensum", "Pensum"],
    ["art", "Art der Bewerbung"], ["ergebnis", "Ergebnis"], ["rav_zuweisung", "Zuweisung des RAV"]];
  let bewerbung = null;

  const meldung = (text, art) => status($("status"), text, art);
  const meldungOben = (text, art) => status($("status-oben"), text, art);

  function optionen(select, werte, gewaehlt) {
    select.replaceChildren(...werte.map(([wert, text]) => el("option", { value: wert, selected: wert === gewaehlt }, text)));
  }

  function zeigeAngaben(daten) {
    bewerbung = daten.bewerbung;
    document.title = `${bewerbung.firma} – ${bewerbung.stelle}`;
    $("titel").textContent = `${bewerbung.firma} – ${bewerbung.stelle}`;
    $("untertitel").textContent = `ID ${bewerbung.id} · Status ${bewerbung.status}` +
      (bewerbung.beworben_am ? ` · beworben am ${datum(bewerbung.beworben_am)}` : "");
    optionen($("f-status"), daten.status.map(s => [s, s]), bewerbung.status);
    optionen($("f-variante"), [["", "– keine –"], ...daten.varianten.map(v => [v.id, `${v.id}${v.beschreibung ? " – " + v.beschreibung : ""}`])],
      bewerbung.variante || "");
    for (const f of FELDER) {
      if (f !== "status" && f !== "variante") $("f-" + f).value = bewerbung[f] ?? "";
    }
    $("f-rav_zuweisung").checked = !!bewerbung.rav_zuweisung;
    $("stellentext").value = daten.stellentext;
  }

  function jobroomText(key, wert) {
    if (key === "datum") return datum(wert);
    if (key === "rav_zuweisung") return wert ? "Ja" : "Nein";
    return wert;
  }

  function zeigeJobroom(j) {
    $("jobroom").replaceChildren(...JOBROOM.map(([key, text]) => {
      const wert = key in j ? jobroomText(key, j[key]) : "";
      const kopieren = wert ? el("button", { type: "button", onclick: () => kopiere(wert) }, "Kopieren") : null;
      return el("div", {}, el("span", { class: "etikett" }, text),
        el("div", { class: "kopieren" }, el("span", { class: wert ? "wert" : "wert leer" }, wert || "– fehlt –"), kopieren));
    }));
  }

  async function kopiere(text) {
    try {
      await navigator.clipboard.writeText(text);
      meldung(`Kopiert: ${text}`, "ok");
    } catch {
      meldung("Kopieren nicht möglich, bitte von Hand markieren", "hinweis");
    }
  }

  function formularWerte() {
    const werte = { ...bewerbung };
    for (const f of FELDER) werte[f] = $("f-" + f).value;
    werte.rav_zuweisung = $("f-rav_zuweisung").checked;
    return werte;
  }

  function zeigePdfs(pdfs) {
    const stand = Date.now();
    const rahmen = [["lebenslauf", "Lebenslauf"], ["anschreiben", "Anschreiben"]]
      .filter(([art]) => pdfs[art])
      .map(([art, text]) => el("figure", {}, el("figcaption", {}, text),
        el("iframe", { src: url("/api/pdf", { id: ID, art, stand }), title: text })));
    $("pdfs").replaceChildren(...(rahmen.length ? rahmen : [el("p", { class: "leer" }, "Noch keine Unterlagen erstellt.")]));
  }

  async function pruefen() {
    try {
      const { befunde } = await holen("/api/pruefung", { id: ID });
      $("befunde").replaceChildren(...befunde.map(b => el("li", { "data-stufe": b.stufe }, b.text)));
    } catch (fehler) {
      meldungOben("Prüfung fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  function zeigeVersand(b) {
    const v = b.versand;
    $("versand-form").hidden = !!v;
    if (!v) {
      $("versand-info").replaceChildren();
      return;
    }
    const links = Object.entries(v.dateien).map(([art, datei]) =>
      el("li", {}, el("a", { href: url("/api/versendet", { datei }), target: "_blank", rel: "noopener" }, `${art}: ${datei}`)));
    $("versand-info").replaceChildren(el("div", { class: "karte" },
      el("strong", {}, `Versendet am ${datum(v.datum)} (${v.art})`), el("ul", {}, links)));
  }

  // Certificates (MIN-346): without a saved choice yet, the suggestions are ticked and marked with their reason.
  async function zeigeZertifikate() {
    const { verfuegbar, vorschlag, gewaehlt } = await holen("/api/zertifikate", { id: ID });
    const gruende = new Map(vorschlag.map(v => [v.datei, v.grund]));
    const zeilen = verfuegbar.map(datei => el("li", {}, el("label", { class: "auswahl" },
      el("input", { type: "checkbox", value: datei, checked: gewaehlt ? gewaehlt.includes(datei) : gruende.has(datei) }),
      datei.split("/").pop(), gruende.has(datei) ? el("span", { class: "leise" }, ` (${gruende.get(datei)})`) : null)));
    $("zertifikate").replaceChildren(...(zeilen.length ? zeilen : [el("li", { class: "leer" }, "Keine Zertifikate unter „Meine Angaben“ hochgeladen.")]));
    $("zertifikate-speichern").hidden = !zeilen.length;
    status($("zertifikate-status"), !gewaehlt && vorschlag.length ? "Vorschlag, noch nicht gespeichert." : "");
  }

  async function speichereZertifikate() {
    const dateien = [...$("zertifikate").querySelectorAll("input:checked")].map(feld => feld.value);
    try {
      await senden("/api/zertifikate", { id: ID, dateien });
      status($("zertifikate-status"), dateien.length ? "Gespeichert." : "Gespeichert: ohne Zertifikate.", "ok");
    } catch (fehler) {
      status($("zertifikate-status"), fehler.message, "fehler");
    }
  }

  async function laden() {
    if (!ID) return meldungOben("Keine Bewerbung gewählt", "fehler");
    try {
      const daten = await holen("/api/bewerbung", { id: ID });
      zeigeAngaben(daten);
      zeigeJobroom(daten.jobroom);
      zeigeVersand(daten.bewerbung);
      zeigePdfs(daten.pdfs);
      zeigeZertifikate().catch(fehler => status($("zertifikate-status"), fehler.message, "fehler"));
      if (!daten.hat_anschreiben) meldungOben("Noch kein Anschreiben (bewerbungen/" + ID + "/anschreiben.yaml) – der Skill „bewerbung“ erstellt den Entwurf.", "hinweis");
      if (daten.pdfs.lebenslauf) pruefen();
    } catch (fehler) {
      meldungOben("Laden fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  async function speichere(werte, text) {
    try {
      bewerbung = await senden("/api/bewerbung", werte);
      meldung(text, "ok");
      await laden();
    } catch (fehler) {
      meldung("Speichern fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  $("zertifikate-speichern").addEventListener("click", speichereZertifikate);
  $("speichern").addEventListener("click", () => speichere(formularWerte(), "Angaben gespeichert"));
  $("stelle-speichern").addEventListener("click", async () => {
    try {
      await senden("/api/stellentext", { text: $("stellentext").value }, { id: ID });
      meldungOben("Stellentext gespeichert", "ok");
    } catch (fehler) {
      meldungOben("Speichern fehlgeschlagen: " + fehler.message, "fehler");
    }
  });
  $("vorschlagen").addEventListener("click", async () => {
    try {
      const { vorschlaege } = await holen("/api/varianten/vorschlag", { id: ID });
      $("vorschlaege").replaceChildren(...(vorschlaege.length ? vorschlaege.map(v => el("div", { class: "karte" },
        el("strong", {}, `${v.id}`), v.beschreibung ? ` – ${v.beschreibung}` : "",
        el("div", {}, `Passt: ${v.treffer.join(", ")}`),
        v.fehlt.length ? el("div", { class: "leise" }, `Fehlt in dieser Variante: ${v.fehlt.join(", ")}`) : null,
        el("button", { type: "button", onclick: () => { $("f-variante").value = v.id; meldungOben(`Variante ${v.id} gewählt – „Angaben speichern“ nicht vergessen`, "hinweis"); } }, "Übernehmen")))
        : [el("p", { class: "leer" }, "Keine passende Variante gefunden – neue Variante anlegen (Skill „bewerbung“).")]));
    } catch (fehler) {
      meldungOben(fehler.message, "fehler");
    }
  });
  $("erstellen").addEventListener("click", async () => {
    meldungOben("Unterlagen werden erstellt …");
    try {
      await senden("/api/unterlagen", {}, { id: ID });
      meldungOben("Unterlagen erstellt", "ok");
      zeigePdfs({ lebenslauf: true, anschreiben: true });
      await laden();
    } catch (fehler) {
      meldungOben("Erstellen fehlgeschlagen: " + fehler.message, "fehler");
    }
  });
  $("pruefen").addEventListener("click", pruefen);
  document.addEventListener("anschreiben-geaendert", laden);
  $("v-datum").value = new Date().toISOString().slice(0, 10);
  bestaetigen($("versenden"), "Wirklich erfassen? Nochmals klicken", async () => {
    try {
      const ergebnis = await senden("/api/versand", { datum: $("v-datum").value, art: $("v-art").value }, { id: ID });
      const hinweise = ergebnis.hinweise.length ? " Hinweise: " + ergebnis.hinweise.join(" · ") : "";
      meldung((ergebnis.commit ? "Versand erfasst und in Git eingefroren." : "Versand erfasst.") + hinweise,
        ergebnis.hinweise.length ? "hinweis" : "ok");
      await laden();
    } catch (fehler) {
      meldung("Versand nicht erfasst: " + fehler.message, "fehler");
    }
  });
  laden();
})();
