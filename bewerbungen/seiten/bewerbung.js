"use strict";
(() => {
  const { holen, senden, el, status, datum, url, bestaetigen } = window.App;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const FELDER = ["firma", "stelle", "firma_schluessel", "ort", "pensum", "vermittler", "portal", "link",
                  "status", "variante", "passung", "eingetragen_am", "beworben_am", "frist", "gespraech_am", "absage_am", "notiz"];
  const JOBROOM_TEXT = [["datum", "Datum der Bewerbung", "date"], ["arbeitgeber", "Arbeitgeber"],
    ["adresse", "Adresse"], ["kontaktperson", "Kontaktperson"], ["kontakt", "Telefon / E-Mail"], ["stelle", "Stelle"]];
  const JOBROOM_AUSWAHL = [["pensum", "Pensum", ["", "Vollzeit", "Teilzeit"]],
    ["art", "Art der Bewerbung", ["elektronisch", "schriftlich", "persönlich", "telefonisch"]],
    ["ergebnis", "Ergebnis", ["offen", "Absage", "Vorstellungsgespräch", "Anstellung"]]];
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
    $("stellentext").value = daten.stellentext;
  }

  function zeigeJobroom(j) {
    const felder = JOBROOM_TEXT.map(([key, text, typ]) => {
      const eingabe = el("input", { id: "j-" + key, type: typ || "text", value: j[key] || "" });
      const kopieren = el("button", { type: "button", onclick: () => kopiere(typ === "date" ? datum(eingabe.value) : eingabe.value) }, "Kopieren");
      return el("div", {}, el("label", { for: "j-" + key }, text), el("div", { class: "kopieren" }, eingabe, kopieren));
    });
    const auswahl = JOBROOM_AUSWAHL.map(([key, text, werte]) => {
      const s = el("select", { id: "j-" + key });
      optionen(s, werte.map(w => [w, w || "–"]), j[key] || "");
      return el("div", {}, el("label", { for: "j-" + key }, text), s);
    });
    const rav = el("div", {}, el("label", { class: "schalter" },
      el("input", { type: "checkbox", id: "j-rav_zuweisung", checked: !!j.rav_zuweisung }), " Bewerbung auf Zuweisung des RAV"));
    const erfasst = el("div", {}, el("label", { for: "j-erfasst_am" }, "Im Job-Room erfasst am"),
      el("input", { id: "j-erfasst_am", type: "date", value: j.erfasst_am || "" }));
    $("jobroom").replaceChildren(...felder, ...auswahl, rav, erfasst);
  }

  async function kopiere(text) {
    try {
      await navigator.clipboard.writeText(text);
      meldung(`Kopiert: ${text}`, "ok");
    } catch {
      meldung("Kopieren nicht möglich, bitte von Hand markieren", "hinweis");
    }
  }

  function jobroomWerte() {
    const werte = {};
    for (const [key] of [...JOBROOM_TEXT, ...JOBROOM_AUSWAHL, ["erfasst_am"]]) werte[key] = $("j-" + key).value;
    werte.rav_zuweisung = $("j-rav_zuweisung").checked;
    return werte;
  }

  function formularWerte() {
    const werte = { ...bewerbung };
    for (const f of FELDER) werte[f] = $("f-" + f).value;
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

  async function laden() {
    if (!ID) return meldungOben("Keine Bewerbung gewählt", "fehler");
    try {
      const daten = await holen("/api/bewerbung", { id: ID });
      zeigeAngaben(daten);
      zeigeJobroom(daten.jobroom);
      zeigeVersand(daten.bewerbung);
      zeigePdfs(daten.pdfs);
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

  $("speichern").addEventListener("click", () => speichere({ ...formularWerte(), jobroom: bewerbung.jobroom }, "Angaben gespeichert"));
  $("jobroom-speichern").addEventListener("click", () => speichere({ ...bewerbung, jobroom: jobroomWerte() }, "Job-Room-Angaben gespeichert"));
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
