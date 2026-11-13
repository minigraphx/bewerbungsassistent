"use strict";
// Page of one application (MIN-369 after MIN-261 ff.): six steps from the ad to recording it, the next step as a card,
// the facts in the side column and changed in a dialog. The steps come from bewerbung-logik.js. AI, own letter and
// the folder for uploads keep their own scripts (ki.js, eigenes-anschreiben.js, dateien-ordner.js).
(() => {
  const { holen, senden, el, status, datum, url, bestaetigen, beobachten } = window.App;
  const { fehltAnschreiben, geaenderteFelder } = window.FormularLogik;
  const L = window.BewerbungLogik;
  const W = window.UnterlagenWahl;
  const { text: textAus } = window.Texte;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const FELDER = ["firma", "stelle", "firma_schluessel", "ort", "pensum", "vermittler", "portal", "link", "formular_link",
                  "status", "variante", "passung", "eingetragen_am", "beworben_am", "frist", "gespraech_am", "absage_am",
                  "adresse", "kontaktperson", "kontakt", "notiz"];
  const JOBROOM = [["datum", "Datum"], ["arbeitgeber", "Arbeitgeber"], ["adresse", "Adresse"],
    ["kontaktperson", "Kontaktperson"], ["kontakt", "Telefon / E-Mail"], ["stelle", "Stelle"], ["pensum", "Pensum"],
    ["art", "Art"], ["ergebnis", "Ergebnis"], ["rav_zuweisung", "Zuweisung des RAV"]];
  // The own store keeps the sent files with or without Git (MIN-304), so this holds either way (#222).
  const VERSAND_GESPEICHERT = "Die verschickte Fassung bleibt gespeichert.";
  const ANDERSWO_GEAENDERT = "Diese Bewerbung wurde inzwischen auch anderswo geändert. Die Eingaben bleiben stehen, und gespeichert werden nur die geänderten Felder.";
  const FORM_FILES = { lebenslauf: "Lebenslauf", anschreiben: "Anschreiben", zertifikate: "Zertifikate", unterlagen: "Unterlagen (gemeinsames PDF)", nachweise: "Nachweise (gemeinsames PDF)" };
  const PAGE_SOURCE = "bewerbungsbegleiter-seite";
  const EXTENSION_SOURCE = "bewerbungsbegleiter-erweiterung";
  const EXTENSION_MARK = "bewerbungsbegleiterErweiterung";
  const START_ACTION = "bewerben-starten";
  const RAV_ACTION = "rav-starten";
  const NO_EXTENSION = "Zum Ausfüllen im Browser braucht es die Erweiterung (siehe Einrichtung).";
  const ANSWER_TIMEOUT_MS = 60000;
  const NACHFRAGEN_NACH_TAGEN = 14;
  const SCHRITT_NAME = { stelle: "Stelle", lebenslauf: "Lebenslauf", anschreiben: "Anschreiben", pruefen: "Prüfen", abschicken: "Abschicken", festhalten: "Festhalten" };

  let bewerbung = null;
  let daten = null;          // last answer of /api/bewerbung
  let geladenerText = "";
  let pdfStand = "";
  let befunde = null;        // null until checked
  let satz = "stelle-sie";
  let rav = false;
  let kiBereit = false;
  let answerTimer = null;
  let versandDatumGesetzt = false;

  const t = (schluessel, werte) => textAus(schluessel, satz, werte);
  const meldung = (text, stufe = "") => zeile($("status"), text, stufe);
  const meldungOben = (text, stufe = "") => zeile($("status-oben"), text, stufe);
  const pruefbar = d => d.pdfs.lebenslauf || d.pdfs.anschreiben;
  const meldeGeladen = d => document.dispatchEvent(new CustomEvent("bewerbung-geladen", { detail: d }));
  const zeile = (element, text, stufe = "", optionen = {}) => window.Meldungen.zeige(element, text, stufe, optionen);

  function optionen(select, werte, gewaehlt) {
    select.replaceChildren(...werte.map(([wert, text]) => el("option", { value: wert, selected: wert === gewaehlt }, text)));
  }

  function plusTage(iso, tage) {
    const tag = new Date(`${iso}T12:00:00Z`);
    tag.setUTCDate(tag.getUTCDate() + tage);
    return tag.toISOString().slice(0, 10);
  }

  // Head, steps and the card „Nächster Schritt“

  function notenWort(note) {
    return note >= 5.5 ? "passt sehr gut" : note >= 4.5 ? "passt gut" : note >= 4 ? "passt knapp" : "passt wenig";
  }

  function note(wert) {
    if (typeof wert !== "number") return "";
    const balken = [1, 2, 3, 4, 5, 6].map(k => el("i", { class: wert >= k ? "on" : wert >= k - 0.5 ? "half" : "" }));
    return el("span", { class: "grade-meter grade-meter--sm", "aria-label": `Note ${window.Texte.notenText(wert)} von 6, ${notenWort(wert)}` },
      el("span", { class: "grade-meter__value" }, window.Texte.notenText(wert)),
      el("span", { class: "grade-meter__bar", "aria-hidden": "true" }, balken),
      el("span", { class: "grade-meter__word", "aria-hidden": "true" }, notenWort(wert)));
  }

  function zeigeKopf() {
    const b = bewerbung;
    document.title = `${b.stelle} – ${b.firma}`;
    $("titel").textContent = b.stelle || "Bewerbung";
    $("pfad-stelle").textContent = b.stelle || "Bewerbung";
    $("untertitel").textContent = [[b.firma, b.ort].filter(Boolean).join(", "), b.frist ? `Abgabe bis ${datum(b.frist)}` : ""].filter(Boolean).join(" · ");
    $("kopf-status").hidden = false;
    $("kopf-status").dataset.status = b.status;
    $("kopf-status").textContent = window.Texte.statusName(b.status, satz);
    $("schnupper-knopf").hidden = satz !== "lehrstelle-du";
    $("kopf-note").replaceChildren(note(b.passung));
  }

  function zeigeSchritte() {
    const liste = L.schritte(daten, { befunde, rav, du: satz !== "stelle-sie" });
    const jetzt = L.aktueller(liste);
    const name = id => id === "stelle" ? t("bewerbung.feld-stelle") : SCHRITT_NAME[id];
    $("schritte").replaceChildren(...liste.map(s => {
      const punkt = el("li", { class: "steps__item", "data-state": s.id === jetzt ? "current" : s.erledigt ? "done" : "todo" },
        el("span", { class: "steps__dot" }), el("a", { class: "steps__label", href: `#s-${s.id}` }, name(s.id)),
        el("span", { class: "steps__meta" }, s.meta));
      if (s.id === jetzt) punkt.setAttribute("aria-current", "step");
      return punkt;
    }));
  }

  function knopf(text, aktion, primaer = true) {
    const k = el("button", { type: "button", class: primaer ? "btn btn--primary" : "btn btn--quiet" }, text);
    k.addEventListener("click", aktion);
    return k;
  }

  const zuAbschnitt = ziel => () => {
    const abschnitt = $(ziel);
    if (abschnitt.tagName === "DETAILS") abschnitt.open = true;
    abschnitt.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  function zeigeNaechster() {
    const n = L.naechster(daten, { befunde, rav, ki: kiBereit });
    const b = bewerbung;
    const fehlerZahl = (befunde || []).filter(x => x.stufe === "fehler").length;
    const karten = {
      inserat: ["Inseratstext einfügen", t("bewerbung.inserat"), [knopf("Zum Textfeld", zuAbschnitt("s-stelle"))]],
      variante: ["Lebenslauf-Variante wählen", "Es gibt mehrere Varianten des Lebenslaufs. «Variante vorschlagen» vergleicht sie mit dem Inserat.", [knopf("Variante wählen", zuAbschnitt("s-lebenslauf"))]],
      freigeben: ["Anschreiben lesen und freigeben", offeneAussagen().length
        ? t("bewerbung.freigeben-offen", { aussagen: offeneAussagen().length === 1 ? "Eine Aussage hat" : `${offeneAussagen().length} Aussagen haben` })
        : t("bewerbung.freigeben"), [knopf("Anschreiben lesen", zuAbschnitt("s-anschreiben"))]],
      entwerfen: ["Anschreiben entwerfen", "Die KI entwirft das Anschreiben aus dem Inserat und den Angaben. Jede Aussage nennt ihren Beleg; was sich nicht belegen lässt, kommt nicht in den Brief.", [knopf("Anschreiben entwerfen", () => $("ki-entwerfen").click()), knopf("Eigenes Anschreiben verwenden", zuAbschnitt("eigenes-anschreiben"), false)]],
      eigenes: ["Anschreiben hinzufügen", t("bewerbung.eigenes"), [knopf("Eigenes Anschreiben hochladen", () => $("anschreiben-datei").click()), knopf("KI einrichten", () => window.App.kiEinrichten(), false)]],
      erstellen: ["Unterlagen erstellen", "Lebenslauf und Anschreiben werden als PDF erstellt und danach automatisch geprüft. Die PDFs stehen dann zum Lesen bereit.", [knopf("Unterlagen erstellen", () => $("erstellen").click())]],
      pruefen: ["Unterlagen prüfen", "Die Prüfung läuft.", []],
      klaeren: ["Unterlagen prüfen", `Die Prüfung hat ${fehlerZahl === 1 ? "einen Fehler" : `${fehlerZahl} Fehler`} gefunden. ${fehlerZahl === 1 ? "Er steht" : "Sie stehen"} bei den Unterlagen.`, [knopf("Zur Prüfung", zuAbschnitt("s-pruefen"))]],
      formular: [`Formular bei ${b.firma} ausfüllen`, t("bewerbung.formular"), [knopf("Formular öffnen", e => oeffneFormular(e.currentTarget, false)), knopf("Per E-Mail beworben? Versand erfassen", zuAbschnitt("versand-titel"), false)]],
      versand: ["Abschicken und festhalten", t("bewerbung.versand"), [knopf("Versand erfassen", zuAbschnitt("versand-titel"))]],
      nachtragen: ["Versand festhalten", `Beworben am ${datum(b.beworben_am)}, aber der Versand ist noch nicht festgehalten. «Versand erfassen» legt die Fassung ab, die verschickt wurde.`, [knopf("Versand erfassen", zuAbschnitt("versand-titel"))]],
      jobroom: ["Im Job-Room eintragen", t("bewerbung.jobroom"), [knopf("Job-Room öffnen", e => oeffneJobroom(e.currentTarget))]],
      warten: ["Antwort abwarten", b.beworben_am ? t("bewerbung.warten", { datum: datum(plusTage(b.beworben_am, NACHFRAGEN_NACH_TAGEN)) }) : "Die Antwort lässt sich unten eintragen, sobald sie kommt.", [el("a", { class: "btn btn--primary", href: "/bewerbungen" }, "Zu den Bewerbungen")]],
      gespraech: [t("bewerbung.gespraech"), b.gespraech_am ? `Termin am ${datum(b.gespraech_am)}. Inserat und Anschreiben stehen auf dieser Seite.` : "Den Termin bei den Angaben eintragen, dann steht er hier und in der Übersicht.",
        [b.gespraech_am ? knopf("Inserat lesen", zuAbschnitt("s-stelle")) : knopf("Termin eintragen", () => oeffneAngaben("f-gespraech_am"))]],
      absage: ["Absage erhalten", t("bewerbung.absage"), [el("a", { class: "btn btn--primary", href: "/bewerbungen" }, "Zu den Bewerbungen")]],
      zusage: ["Zusage erhalten", "Die Unterlagen dieser Bewerbung bleiben gespeichert.", [el("a", { class: "btn btn--primary", href: "/bewerbungen" }, "Zu den Bewerbungen")]],
    };
    const [titel, text, knoepfe] = karten[n.art];
    $("naechster-zeile").textContent = n.art === "jobroom" ? "Nächster Schritt · fürs RAV" : "Nächster Schritt";
    $("naechster-titel").textContent = titel;
    $("naechster-text").textContent = text;
    $("naechster-knoepfe").replaceChildren(...knoepfe);
  }

  // Side column

  function zeigeFakten() {
    const b = bewerbung;
    const fakten = [
      [t("bewerbung.feld-firma"), b.firma], ["Ort", b.ort], ["Pensum", b.pensum],
      ["Kontakt", [b.kontaktperson, b.kontakt].filter(Boolean).join(", ")],
      ["Gefunden", [b.portal || b.vermittler, datum(b.eingetragen_am)].filter(Boolean).join(", ")],
      ["Lebenslauf", b.variante ? `Variante ${b.variante}` : daten.eigener_lebenslauf ? "eigenes PDF" : daten.varianten.length ? "noch keine Variante" : "ganzer Lebenslauf"],
      ["Frist", datum(b.frist)],
      ...(rav ? [["RAV", b.rav_zuweisung ? "Zuweisung" : "keine Zuweisung"]] : []),
    ].filter(([, wert]) => wert);
    $("fakten").replaceChildren(...fakten.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));
    $("inserat-link").hidden = !b.link;
    if (b.link) $("inserat-link").href = b.link;
    $("verlauf").replaceChildren(...L.verlauf(b).map(v => el("li", {}, el("span", { class: "num application__date" }, datum(v.datum)), " ", v.text)));
    $("rav-zuweisung-feld").hidden = !rav;
  }

  // Steps in the main column

  /** Statements the kept AI review found without evidence; only for the letter as it is now (letter_approval.py). */
  function offeneAussagen() {
    return (daten.ki_pruefung && daten.ki_pruefung.unsupported) || [];
  }

  /** A paragraph with the statements lacking evidence marked; only as text nodes, never HTML. */
  function absatz(textInhalt) {
    const stellen = offeneAussagen().map(u => u.text).filter(x => x && textInhalt.includes(x));
    if (!stellen.length) return el("p", {}, textInhalt);
    const teile = [];
    let rest = textInhalt;
    for (const stelle of stellen) {
      const i = rest.indexOf(stelle);
      if (i < 0) continue;
      teile.push(rest.slice(0, i), el("mark", {}, stelle));
      rest = rest.slice(i + stelle.length);
    }
    return el("p", {}, ...teile, rest);
  }

  function zeigeBrief() {
    const brief = daten.anschreiben_text;
    const zeigen = Boolean(brief) && !daten.eigenes_anschreiben && !bewerbung.versand;
    $("anschreiben-text").hidden = !zeigen;
    if (zeigen) {
      $("anschreiben-text").replaceChildren(
        brief.betreff ? el("p", {}, el("strong", {}, brief.betreff)) : null,
        brief.anrede ? el("p", {}, brief.anrede) : null,
        ...brief.absaetze.map(absatz),
        brief.gruss ? el("p", {}, brief.gruss) : null);
    }
    const freigabe = daten.anschreiben_freigabe || {};
    $("freigabe-zeile").hidden = !zeigen;
    $("freigeben").hidden = !freigabe.noetig || freigabe.freigegeben;
    $("anschreiben-aendern").href = "/inhalte?" + new URLSearchParams({ datei: `bewerbungen/${ID}/anschreiben.yaml`, ansicht: "text" });
    zeile($("freigabe-status"), !zeigen || !freigabe.noetig ? ""
      : freigabe.freigegeben ? `Freigegeben am ${datum(freigabe.am)}. Eine Änderung am Text hebt die Freigabe auf.`
        : "Noch nicht freigegeben. Erst mit der Freigabe öffnet die Erweiterung das Formular.", freigabe.freigegeben ? "ok" : "");
    zeigeKiPruefung(zeigen);
  }

  function zeigeKiPruefung(briefSichtbar) {
    const p = daten.ki_pruefung;
    $("ki-pruefung-teil").hidden = !briefSichtbar || !p;
    if (!p) return;
    const anforderungen = p.requirements || [];
    const abgedeckt = anforderungen.filter(r => r.status === "abgedeckt").length;
    const offen = offeneAussagen();
    $("ki-pruefung-zahl").textContent = `${abgedeckt} von ${anforderungen.length} Anforderungen belegt, ${offen.length} ${offen.length === 1 ? "Aussage" : "Aussagen"} ohne Beleg`;
    $("ki-pruefung-liste").replaceChildren(
      ...offen.map(u => el("div", { class: "claim", "data-evidence": "gap" }, el("span", { class: "claim__text" }, `«${u.text}»`),
        el("span", { class: "claim__source" }, u.problem || "Kein Beleg gefunden. Streichen oder in Meine Angaben ergänzen."))),
      ...anforderungen.filter(r => r.status !== "abgedeckt").map(r => el("div", { class: "claim", "data-evidence": "gap" },
        el("span", { class: "claim__text" }, `${r.requirement}: ${r.status}`), el("span", { class: "claim__source" }, r.note || ""))));
    $("ki-pruefung-fuss").textContent = `Prüfung der KI vom ${datum(p.am)}. Eine Einschätzung, kein Urteil: Die KI kann sich irren.`;
  }

  function zeigeAnschreibenStand() {
    const freigabe = daten.anschreiben_freigabe || {};
    $("anschreiben-stand").textContent = daten.eigenes_anschreiben ? "Für diese Bewerbung gilt das hochgeladene PDF."
      : bewerbung.versand ? "Das Anschreiben ist mit der Bewerbung versendet."
        : daten.anschreiben_text ? (freigabe.freigegeben ? "Freigegebener Entwurf:" : "Entwurf, bitte lesen:")
          : daten.hat_anschreiben ? "Ein Anschreiben ist vorhanden." : "Noch kein Anschreiben.";
    zeigeBrief();
  }

  async function freigeben() {
    $("freigeben").disabled = true;
    try {
      await senden("/api/anschreiben/freigeben", { id: ID });
      await laden();
      meldungOben("Anschreiben freigegeben", "ok");
    } catch (fehler) {
      zeile($("freigabe-status"), fehler.message, "fehler");
    } finally {
      $("freigeben").disabled = false;
    }
  }

  /** #119: „Lebenslauf anpassen“ until sent; a finished PDF gets a note instead (the own one has #eigener-cv). */
  function zeigeAnpassen(b) {
    const variante = (daten.varianten || []).find(v => v.id === b.variante) || null;
    const ziel = window.LebenslaufAnpassen.ziel({ variante, eigenesPdf: Boolean(daten.eigener_lebenslauf_da) });
    $("cv-anpassen").hidden = !ziel.href || Boolean(b.versand);
    if (ziel.href) $("cv-anpassen").href = ziel.href;
    $("cv-wie-es-ist").hidden = ziel.wieEsIst !== "variante";
  }

  function zeigeAbschnitte() {
    const b = bewerbung;
    const gesendet = L.versendet(b);
    $("formular-teil").hidden = Boolean(b.versand) || !(b.formular_link || b.link);
    $("versand-form").hidden = Boolean(b.versand);
    $("erstellen").hidden = Boolean(b.versand);
    $("pruefen").hidden = !L.erneutPruefen(befunde);
    $("unterlagen-wahl").hidden = Boolean(b.versand);
    for (const knopf of document.querySelectorAll('input[name="unterlagen"]')) knopf.checked = knopf.value === W.gewaehlt(b);
    zeigeDesign(b);
    $("antwort-teil").hidden = !gesendet;
    $("jobroom-teil").hidden = !rav || !gesendet;
    $("s-festhalten").hidden = !gesendet;
    zeigeBeenden(b);
    $("s-lebenslauf").hidden = Boolean(b.versand) && !b.variante;
    zeigeAnpassen(b);
    $("s-stelle").open = (!(daten.stellentext || "").trim() || Boolean(daten.text_fehlt)) && !gesendet;
    // Why the ad text is missing and how to get it (G37); the extension loads it at the start where the portal allows.
    $("stellentext-fehlt").textContent = daten.text_fehlt ? `${daten.text_fehlt.grund} ${daten.text_fehlt.weg}` : "";
    $("stellentext-fehlt").hidden = !daten.text_fehlt;
    if (b.beworben_am && !b.versand && !versandDatumGesetzt) {  // sent already: record it with that date
      $("v-datum").value = b.beworben_am;
      versandDatumGesetzt = true;
    }
    zeigeAnschreibenStand();
  }

  function zeigeBeenden(b) {
    const ende = L.beenden(b);
    $("beenden-teil").hidden = !ende;
    $("verwerfen").hidden = ende?.stand !== "Verworfen";
    $("zurueckziehen").hidden = ende?.stand !== "Zurückgezogen";
    $("beenden-hinweis").textContent = !ende ? ""
      : ende.stand === "Verworfen" ? "Nicht bewerben: Die Bewerbung bleibt mit dem Stand „Verworfen“ in der Liste."
        : "Die Bewerbung nicht weiterverfolgen: Sie bleibt mit dem Stand „Zurückgezogen“ in der Liste.";
  }

  function zeigeAlles() {
    zeigeKopf();
    zeigeSchritte();
    zeigeNaechster();
    zeigeFakten();
    zeigeAbschnitte();
  }

  function zeigeAngaben(d) {
    bewerbung = d.bewerbung;
    $("eigener-cv").hidden = !d.eigener_lebenslauf;
    $("vorschlagen").hidden = !d.varianten.length;  // it only picks among existing variants
    optionen($("f-status"), d.status.map(s => [s, s]), bewerbung.status);
    optionen($("f-variante"), [["", d.eigener_lebenslauf_da ? "– eigener Lebenslauf –" : d.varianten.length ? "– keine –" : "– ganzer Lebenslauf –"], ...d.varianten.map(v => [v.id, `${v.id}${v.beschreibung ? " – " + v.beschreibung : ""}`])],
      bewerbung.variante || "");
    for (const f of FELDER) {
      if (f !== "status" && f !== "variante") $("f-" + f).value = bewerbung[f] ?? "";
    }
    $("f-rav_zuweisung").checked = !!bewerbung.rav_zuweisung;
    $("stellentext").value = d.stellentext;
    geladenerText = d.stellentext;
  }

  function jobroomText(key, wert) {
    if (key === "datum") return datum(wert);
    if (key === "rav_zuweisung") return wert ? "Ja" : "Nein";
    return wert;
  }

  function zeigeJobroom(j) {
    $("jobroom").replaceChildren(...JOBROOM.map(([key, name]) => {
      const wert = key in j ? jobroomText(key, j[key]) : "";
      const kopieren = wert ? el("button", { type: "button", class: "btn btn--sm", onclick: () => kopiere(wert) }, "Kopieren") : null;
      return el("div", { class: "copy-row" }, el("dt", {}, name), el("dd", {}, el("span", { class: "copy-row__value" }, wert || ""), kopieren));
    }));
  }

  /** Entered by hand, or marked by mistake: the same mark as after saving in Job-Room (MIN-347). */
  function zeigeRav() {
    const eingetragen = bewerbung.rav_eingetragen_am;
    $("rav-stand").textContent = eingetragen ? `Im Job-Room eingetragen am ${datum(eingetragen)}.` : "Noch nicht im Job-Room eingetragen.";
    $("rav-umschalten").textContent = eingetragen ? "Zurücksetzen" : "Als eingetragen markieren";
    $("rav-umschalten").hidden = !eingetragen && !bewerbung.beworben_am;
  }

  async function schalteRav() {
    const pfad = bewerbung.rav_eingetragen_am ? "/api/rav/zuruecksetzen" : "/api/rav/eingetragen";
    try {
      const { rav_eingetragen_am } = await senden(pfad, { id: bewerbung.id });
      bewerbung = { ...bewerbung, rav_eingetragen_am };
      daten = { ...daten, bewerbung };
      zeigeRav();
      zeigeAlles();
    } catch (fehler) {
      meldung(fehler.message, "fehler");
    }
  }

  async function kopiere(inhalt) {
    try {
      await navigator.clipboard.writeText(inhalt);
      meldung(`Kopiert: ${inhalt}`, "ok");
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
    const rahmen = W.rahmen(pdfs, bewerbung ? W.gewaehlt(bewerbung) : W.VOREINSTELLUNG)
      .map(([art, name]) => el("figure", {}, el("figcaption", {}, name),
        el("iframe", { src: url("/api/pdf", { id: ID, art, stand }), title: name })));
    $("pdfs").replaceChildren(...(rahmen.length ? rahmen : [el("p", { class: "leer" }, "Noch keine Unterlagen erstellt.")]));
  }

  async function pruefen() {
    try {
      ({ befunde } = await holen("/api/pruefung", { id: ID }));
      $("befunde").replaceChildren(...befunde.map(b => window.Meldungen.listenZeile(document, b.text, b.stufe)));
      if (daten) zeigeAlles();
    } catch (fehler) {
      meldungOben("Prüfung fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  // A form keeps the file it got. Whoever sent it there and then records it here says so, the app cannot know.
  function zeigeFormularFassung(d) {
    const anders = d.formular_abweichend.map(art => FORM_FILES[art]);
    $("formular-fassung").hidden = !anders.length;
    if (!anders.length) $("v-formular").checked = false;
    $("formular-fassung-text").textContent = anders.length
      ? `Das Formular im Browser hat eine andere Fassung bekommen: ${anders.join(", ")}. Ohne Häkchen wird die aktuelle festgehalten.`
      : "";
  }

  function zeigeVersand(b) {
    const v = b.versand;
    if (!v) {
      $("versand-info").replaceChildren();
      return;
    }
    const links = Object.entries(v.dateien).map(([art, datei]) =>
      el("li", {}, el("a", { href: url("/api/versendet", { datei }), target: "_blank", rel: "noopener" }, `${art}: ${datei.split("/").pop()}`)));
    $("versand-info").replaceChildren(
      el("div", { class: "notice notice--success" }, el("span", { class: "notice__title" }, `Beworben am ${datum(v.datum)}`),
        el("p", { class: "notice__body" }, `${v.art[0].toUpperCase()}${v.art.slice(1)}. Diese Fassung ist fest gespeichert und ändert sich nicht mehr.`)),
      el("h3", {}, "Versendete Fassung"), el("ul", {}, links));
  }

  // Certificates (MIN-346): without a saved choice yet, the suggestions are ticked and marked with their reason.
  async function zeigeZertifikate() {
    const { verfuegbar, vorschlag, gewaehlt } = await holen("/api/zertifikate", { id: ID });
    const gruende = new Map(vorschlag.map(v => [v.datei, v.grund]));
    const zeilen = verfuegbar.map(datei => el("li", {}, el("label", { class: "check" },
      el("input", { type: "checkbox", value: datei, checked: gewaehlt ? gewaehlt.includes(datei) : gruende.has(datei) }),
      datei.split("/").pop(), gruende.has(datei) ? el("span", { class: "leise" }, ` (${gruende.get(datei)})`) : null)));
    $("zertifikate").replaceChildren(...(zeilen.length ? zeilen : [el("li", { class: "leer" }, "Noch keine Zertifikate hochgeladen. Das geht unter ", el("a", { href: "/dateien" }, "Lebenslauf und Dateien"), ".")]));
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

  function zeigeEintrag(d) {
    daten = d;
    zeigeAngaben(d);
    zeigeJobroom(d.jobroom);
    zeigeRav();
    zeigeVersand(d.bewerbung);
    zeigeAlles();
  }

  function hatEingaben() {
    return Object.keys(geaenderteFelder(bewerbung, formularWerte())).length > 0 || $("stellentext").value !== geladenerText;
  }

  /** Shows what Claude wrote meanwhile. What the person is typing stays: the form is only replaced when it holds nothing new. */
  async function nachsehen() {
    if (!bewerbung) return;
    let neu;
    try {
      neu = await holen("/api/bewerbung", { id: ID });
    } catch {
      return; // the app is closing or the entry is gone; the next action says so
    }
    meldeGeladen(neu);
    if (JSON.stringify(neu.pdf_stand) !== pdfStand) {
      pdfStand = JSON.stringify(neu.pdf_stand);
      daten = { ...daten, pdfs: neu.pdfs, hat_anschreiben: neu.hat_anschreiben, eigenes_anschreiben: neu.eigenes_anschreiben,
                anschreiben_text: neu.anschreiben_text, anschreiben_freigabe: neu.anschreiben_freigabe, ki_pruefung: neu.ki_pruefung };
      zeigePdfs(neu.pdfs);
      befunde = null;
      zeigeAlles();
      if (pruefbar(neu)) pruefen();
    }
    if (JSON.stringify(neu.bewerbung) === JSON.stringify(bewerbung) && neu.stellentext === geladenerText) return;
    if (hatEingaben()) meldung(ANDERSWO_GEAENDERT, "hinweis");
    else zeigeEintrag(neu);
  }

  async function laden() {
    if (!ID) return meldungOben("Keine Bewerbung gewählt", "fehler");
    try {
      const d = await holen("/api/bewerbung", { id: ID });
      befunde = null;
      zeigeEintrag(d);
      zeigePdfs(d.pdfs);
      pdfStand = JSON.stringify(d.pdf_stand);
      meldeGeladen(d);
      zeigeZertifikate().catch(fehler => status($("zertifikate-status"), fehler.message, "fehler"));
      if (pruefbar(d)) pruefen();
    } catch (fehler) {
      meldungOben("Laden fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  async function speichere(werte, meldetext) {
    try {
      bewerbung = await senden("/api/bewerbung", { id: bewerbung.id, ...geaenderteFelder(bewerbung, werte) });
      meldung(meldetext, "ok");
      await laden();
      return true;
    } catch (fehler) {
      meldung("Speichern fehlgeschlagen: " + fehler.message, "fehler");
      return false;
    }
  }

  async function waehleVariante(variante) {
    try {
      bewerbung = await senden("/api/bewerbung", { id: bewerbung.id, variante });
      daten = { ...daten, bewerbung };
      $("f-variante").value = variante;
      meldungOben(variante ? `Variante ${variante} gespeichert` : "Ohne Variante gespeichert", "ok");
      zeigeAlles();
    } catch (fehler) {
      meldungOben("Speichern fehlgeschlagen: " + fehler.message, "fehler");
    }
  }

  /** The note for the person when no letter could be drafted; the rest of the documents is still worth building. */
  async function entwirfFehlendes() {
    if (!daten || !fehltAnschreiben(daten)) return "";
    meldungOben("Anschreiben wird entworfen … das kann bis zu einer Minute dauern.");
    try {
      const ergebnis = await senden("/api/ki/anschreiben", {}, { id: ID });
      document.dispatchEvent(new CustomEvent("anschreiben-entworfen", { detail: ergebnis }));
      return "";
    } catch (fehler) {
      return `Kein Anschreiben entworfen: ${fehler.message}`;
    }
  }

  // The facts in a dialog

  function oeffneAngaben(fokus = "f-firma") {
    $("angaben-dialog").showModal();
    $(fokus)?.focus();
  }

  async function antwort(stand) {
    const heute = new Date().toISOString().slice(0, 10);
    const werte = { ...formularWerte(), status: stand };
    if (stand === "Absage" && !werte.absage_am) werte.absage_am = heute;
    if (await speichere(werte, `Stand: ${stand}`) && stand === "Gespräch" && !bewerbung.gespraech_am) oeffneAngaben("f-gespraech_am");
  }

  // Opening the form or the Job-Room through the extension (MIN-346, MIN-347)

  let laufend = null;  // { art, knopf }

  function frageErweiterung(nachricht, knopf, warten) {
    if (!document.documentElement.dataset[EXTENSION_MARK]) {
      meldungOben(NO_EXTENSION, "fehler");
      return;
    }
    laufend = { art: nachricht.art, knopf };
    if (knopf) knopf.disabled = true;
    meldungOben(warten);
    clearTimeout(answerTimer);
    answerTimer = setTimeout(() => {
      meldungOben("Die Erweiterung antwortet nicht. Bitte sie neu laden und es nochmals versuchen.", "fehler");
      if (knopf) knopf.disabled = false;
    }, ANSWER_TIMEOUT_MS);
    window.postMessage({ quelle: PAGE_SOURCE, ...nachricht }, location.origin);
  }

  function oeffneFormular(knopf, bestaetigt) {
    frageErweiterung({ art: START_ACTION, ids: [ID], bestaetigt }, knopf, "Die Unterlagen werden geprüft …");
  }

  function oeffneJobroom(knopf) {
    frageErweiterung({ art: RAV_ACTION, ids: [ID] }, knopf, "Der Job-Room wird geöffnet …");
  }

  function antwortDerErweiterung(frage, antwortDaten) {
    if (antwortDaten && antwortDaten.laeuft) return;
    clearTimeout(answerTimer);
    if (laufend?.knopf) laufend.knopf.disabled = false;
    if (!antwortDaten || antwortDaten.fehler) return meldungOben((antwortDaten && antwortDaten.fehler) || "Die Erweiterung antwortet nicht.", "fehler");
    if (antwortDaten.berechtigung) return meldungOben("Bitte im neuen Tab den Zugriff erlauben; danach geht es weiter.", "hinweis");
    if (antwortDaten.abgelehnt && antwortDaten.abgelehnt.length) return meldungOben(antwortDaten.abgelehnt.map(a => a.grund).join(" · "), "fehler");
    if (antwortDaten.doppelt && antwortDaten.doppelt.length) {
      const d = antwortDaten.doppelt[0];
      $("doppelt-titel").textContent = `Bei ${d.firma} läuft schon eine Bewerbung`;
      $("doppelt-text").replaceChildren(...antwortDaten.doppelt.map(x => el("p", {}, `${x.stelle}, Stand ${x.status}.`)), el("p", {}, t("uebersicht.doppelt")));
      meldungOben("");
      $("doppelt-dialog").showModal();
      return;
    }
    if (antwortDaten.geoeffnet) meldungOben(t(frage === RAV_ACTION ? "bewerbung.jobroom-offen" : "bewerbung.geoeffnet"), "ok");
  }

  // Wiring

  $("zertifikate-speichern").addEventListener("click", speichereZertifikate);
  $("rav-umschalten").addEventListener("click", schalteRav);
  $("angaben-aendern").addEventListener("click", () => oeffneAngaben());
  $("angaben-abbrechen").addEventListener("click", () => $("angaben-dialog").close());
  $("angaben-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (await speichere(formularWerte(), "Angaben gespeichert")) $("angaben-dialog").close();
  });
  $("notiz-speichern").addEventListener("click", () => speichere(formularWerte(), "Notiz gespeichert"));
  $("f-variante").addEventListener("change", () => waehleVariante($("f-variante").value));
  for (const k of document.querySelectorAll("[data-antwort]")) k.addEventListener("click", () => antwort(k.dataset.antwort));
  bestaetigen($("verwerfen"), "Wirklich verwerfen? Nochmals klicken", () => antwort("Verworfen"));
  bestaetigen($("zurueckziehen"), "Wirklich zurückziehen? Nochmals klicken", () => antwort("Zurückgezogen"));
  $("formular-oeffnen").addEventListener("click", e => oeffneFormular(e.currentTarget, false));
  $("jobroom-oeffnen").addEventListener("click", e => oeffneJobroom(e.currentTarget));
  $("doppelt-abbrechen").addEventListener("click", () => $("doppelt-dialog").close());
  $("doppelt-trotzdem").addEventListener("click", () => { $("doppelt-dialog").close(); oeffneFormular(laufend?.knopf, true); });
  window.addEventListener("message", event => {
    const d = event.data;
    if (event.source !== window || event.origin !== location.origin || d?.quelle !== EXTENSION_SOURCE || d.art !== "antwort") return;
    if (d.frage === START_ACTION || d.frage === RAV_ACTION) antwortDerErweiterung(d.frage, d.antwort);
  });
  $("stelle-speichern").addEventListener("click", async () => {
    try {
      await senden("/api/stellentext", { text: $("stellentext").value }, { id: ID });
      meldungOben("Stellentext gespeichert", "ok");
      await laden();
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
        el("button", { type: "button", class: "btn btn--sm", onclick: () => waehleVariante(v.id) }, "Übernehmen")))
        : [el("p", { class: "leer" }, "Keine passende Variante gefunden – neue Variante anlegen (Skill „bewerbung“).")]));
    } catch (fehler) {
      meldungOben(fehler.message, "fehler");
    }
  });
  /** G39: the design shows only with the dossier; „Erweitert“ stays closed unless a page has its own design. */
  function zeigeDesign(b) {
    $("dossier-design").hidden = W.gewaehlt(b) !== "dossier" || Boolean(b.versand);
    $("d-design").value = W.design(b);
    const seiten = W.seitenDesigns(b);
    for (const auswahl of document.querySelectorAll("select[data-seite]")) auswahl.value = seiten[auswahl.dataset.seite];
    if (W.gemischt(b)) $("d-erweitert").open = true;
  }

  /** G39, G40: each choice is saved right away; `body` gives what to save, null when nothing changed. */
  async function speichereWahl(body, gespeichert) {
    try {
      const werte = body();
      if (!werte) return;
      bewerbung = await senden("/api/bewerbung", werte);
      meldungOben(gespeichert(werte), "ok");
      await laden();
    } catch (fehler) {
      zeigeAbschnitte();
      meldungOben("Speichern fehlgeschlagen: " + fehler.message, "fehler");
    }
  }
  const NEU_ERSTELLEN = "Mit „Unterlagen erstellen“ entsteht das Dossier im neuen Design.";
  for (const knopf of document.querySelectorAll('input[name="unterlagen"]')) {
    knopf.addEventListener("change", event => speichereWahl(() => W.zuSpeichern(bewerbung, event.target.value),
      body => (body.unterlagen === "dossier" ? "Dossier gewählt" : "Anschreiben und Lebenslauf gewählt")));
  }
  $("d-design").addEventListener("change", event => speichereWahl(() => W.designSpeichern(bewerbung, event.target.value),
    () => `Design für alle Seiten gespeichert. ${NEU_ERSTELLEN}`));
  for (const auswahl of document.querySelectorAll("select[data-seite]")) {
    auswahl.addEventListener("change", () => speichereWahl(() => W.seiteSpeichern(bewerbung, auswahl.dataset.seite, auswahl.value),
      () => `Design der Seite gespeichert. ${NEU_ERSTELLEN}`));
  }
  $("erstellen").addEventListener("click", async () => {
    $("erstellen").disabled = true; // a second click would pay for a second draft
    try {
      const offen = await entwirfFehlendes();
      meldungOben("Unterlagen werden erstellt …");
      await senden("/api/unterlagen", {}, { id: ID });
      await laden();
      meldungOben(offen ? `Unterlagen erstellt. ${offen}` : "Unterlagen erstellt", offen ? "hinweis" : "ok");
    } catch (fehler) {
      meldungOben("Erstellen fehlgeschlagen: " + fehler.message, "fehler");
    } finally {
      $("erstellen").disabled = false;
    }
  });
  $("pruefen").addEventListener("click", pruefen);
  $("freigeben").addEventListener("click", freigeben);
  document.addEventListener("anschreiben-geprueft", laden);
  document.addEventListener("anschreiben-geaendert", laden);
  document.addEventListener("eigenes-anschreiben-geaendert", nachsehen);
  document.addEventListener("bewerbung-geladen", event => zeigeFormularFassung(event.detail));
  document.addEventListener("bewerbung-gespeichert", event => {
    bewerbung = event.detail;
    daten = { ...daten, bewerbung };
    $("f-passung").value = bewerbung.passung ?? "";
    zeigeAlles();
  });
  $("v-datum").value = new Date().toISOString().slice(0, 10);
  bestaetigen($("versenden"), "Wirklich erfassen? Nochmals klicken", async () => {
    try {
      const ergebnis = await senden("/api/versand", { datum: $("v-datum").value, art: $("v-art").value, fassung_formular: $("v-formular").checked }, { id: ID });
      const hinweise = ergebnis.hinweise.length ? " Hinweise: " + ergebnis.hinweise.join(" · ") : "";
      meldungOben(`Versand erfasst. ${VERSAND_GESPEICHERT}${hinweise}`,
        ergebnis.hinweise.length ? "hinweis" : "ok");
      await laden();
    } catch (fehler) {
      meldungOben("Versand nicht erfasst: " + fehler.message, "fehler");
    }
  });

  (async () => {
    const [satzJetzt, wahl, kiStatus] = await Promise.all([window.App.textsatz(), window.App.wahl(),
      holen("/api/ki/status").catch(() => null)]);
    satz = satzJetzt;
    rav = wahl ? Boolean(wahl.rav) : true;
    kiBereit = Boolean(kiStatus && kiStatus.eingerichtet && kiStatus.einwilligung?.erteilt);
    // After the window „KI einrichten“ (G60) the next step may be the draft instead of an own letter
    document.addEventListener("ki-fenster-geschlossen", event => {
      kiBereit = Boolean(event.detail?.eingerichtet && event.detail.einwilligung?.erteilt);
      if (daten) zeigeNaechster();
    });
    await laden();
    // Heute links here with #termin when an interview has no date yet (#268)
    if (location.hash === "#termin" && bewerbung) oeffneAngaben("f-gespraech_am");
    beobachten(nachsehen);
  })();
})();
