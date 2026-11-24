"use strict";
// Page of one application (MIN-369 after MIN-261 ff.): six steps from the ad to recording it, the next step as a card,
// the facts in the side column and changed in a dialog. The steps come from bewerbung-logik.js. AI, own letter and
// the folder for uploads keep their own scripts (ki.js, eigenes-anschreiben.js, dateien-ordner.js).
// Texts in the app language through Texte and bewerbung-texte.js (#427); data and the AI's own words stay as they come.
(() => {
  const { holen, senden, el, status, datum, url, bestaetigen, beobachten } = window.App;
  /** A «·» line of whole parts (#342, dot-line.js): never starts with «·», screen readers hear commas. */
  const dotLine = parts => window.DotLine.render(parts, el);
  const { fehltAnschreiben, geaenderteFelder } = window.FormularLogik;
  const L = window.BewerbungLogik;
  const W = window.UnterlagenWahl;
  const R = window.UnterlagenErgebnis;
  const S = window.UnterlagenSchritt;
  const K = window.KuerzenLogik;
  const KU = window.Kuerzen;
  const E = window.LetterEditor;
  const BT = window.BewerbungTexte;
  const Texte = window.Texte;
  const { text: textAus } = Texte;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const FELDER = ["firma", "stelle", "firma_schluessel", "ort", "pensum", "vermittler", "portal", "link", "formular_link",
                  "status", "variante", "passung", "eingetragen_am", "beworben_am", "frist", "gespraech_am", "absage_am",
                  "adresse", "kontaktperson", "kontakt", "notiz"];
  const PAGE_SOURCE = "bewerbungsbegleiter-seite";
  const EXTENSION_SOURCE = "bewerbungsbegleiter-erweiterung";
  const EXTENSION_MARK = "bewerbungsbegleiterErweiterung";
  const START_ACTION = "bewerben-starten";
  const RAV_ACTION = "rav-starten";
  const ANSWER_TIMEOUT_MS = 60000;
  const NACHFRAGEN_NACH_TAGEN = 14;

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
  let zertifikateDa = [];    // the certificates offered, for the line under «Beilagen ändern»

  const t = (schluessel, werte) => textAus(schluessel, satz, werte);
  const meldung = (text, stufe = "") => zeile($("status"), text, stufe);
  const meldungOben = (text, stufe = "") => zeile($("status-oben"), text, stufe);
  const pruefbar = d => d.pdfs.lebenslauf || d.pdfs.anschreiben;
  const meldeGeladen = d => document.dispatchEvent(new CustomEvent("bewerbung-geladen", { detail: d }));
  const zeile = (element, text, stufe = "", optionen = {}) => window.Meldungen.zeige(element, text, stufe, optionen);
  // A stored stage by its name; for an apprenticeship too „Gespräch“ here, as the head alone says „Einladung“.
  const standName = stand => Texte.statusName(stand, satz === "lehrstelle-du" ? "stelle-du" : satz);

  function optionen(select, werte, gewaehlt) {
    select.replaceChildren(...werte.map(([wert, text]) => el("option", { value: wert, selected: wert === gewaehlt }, text)));
  }

  function plusTage(iso, tage) {
    const tag = new Date(`${iso}T12:00:00Z`);
    tag.setUTCDate(tag.getUTCDate() + tage);
    return tag.toISOString().slice(0, 10);
  }

  // Head, steps and the card „Nächster Schritt“

  function note(wert) {
    if (typeof wert !== "number") return "";
    const balken = [1, 2, 3, 4, 5, 6].map(k => el("i", { class: wert >= k ? "on" : wert >= k - 0.5 ? "half" : "" }));
    const label = Texte.t("Note {wert} von 6, {wort}", { wert: Texte.notenText(wert), wort: BT.gradeWord(wert) });
    return el("span", { class: "grade-meter grade-meter--sm", "aria-label": label },
      el("span", { class: "grade-meter__value" }, Texte.notenText(wert)),
      el("span", { class: "grade-meter__bar", "aria-hidden": "true" }, balken),
      el("span", { class: "grade-meter__word", "aria-hidden": "true" }, BT.gradeWord(wert)));
  }

  function zeigeKopf() {
    const b = bewerbung;
    document.title = `${b.stelle} – ${b.firma}`;
    $("titel").textContent = b.stelle || Texte.t("Bewerbung");
    $("pfad-stelle").textContent = b.stelle || Texte.t("Bewerbung");
    $("untertitel").replaceChildren(...dotLine([[b.firma, b.ort].filter(Boolean).join(", "),
      b.frist ? Texte.t("Abgabe bis {datum}", { datum: datum(b.frist) }) : ""]));
    $("kopf-status").hidden = false;
    $("kopf-status").dataset.status = b.status;
    $("kopf-status").textContent = Texte.statusName(b.status, satz);
    $("schnupper-knopf").hidden = satz !== "lehrstelle-du";
    $("kopf-note").replaceChildren(note(b.passung));
    window.BewerbungWieder.zeige(b);  // G109: the job came again with a new ad
  }

  function zeigeSchritte() {
    const liste = L.schritte(daten, { befunde, rav, du: satz !== "stelle-sie" });
    const jetzt = L.aktueller(liste);
    const name = id => id === "stelle" ? t("bewerbung.feld-stelle") : BT.stepName(id);
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
  // G92: the card about a CV over its limit leads to the cuts, so the focus goes there too
  const zuBefund = () => {
    zuAbschnitt("s-pruefen")();
    S.focusFirstFinding();
  };
  const zuDenBewerbungen = () => el("a", { class: "btn btn--primary", href: "/bewerbungen" }, Texte.t("Zu den Bewerbungen"));

  // Title and text of most cards come from bewerbung-texte.js, with the dates as this page writes them.
  function karten(b, fehlerZahl) {
    const c = { t, firma: b.firma, offen: offeneAussagen().length, beworben: datum(b.beworben_am), gespraech: datum(b.gespraech_am),
      nachfragen: b.beworben_am ? datum(plusTage(b.beworben_am, NACHFRAGEN_NACH_TAGEN)) : "" };
    const karte = (art, ...knoepfe) => [...BT.card(art, c), knoepfe];
    const versandErfassen = () => knopf(Texte.t("Versand erfassen"), zuAbschnitt("versand-titel"));
    const zurPruefung = () => knopf(Texte.t("Zur Prüfung"), zuAbschnitt("s-pruefen"));
    return {
      inserat: () => karte("inserat", knopf(Texte.t("Zum Textfeld"), zuAbschnitt("s-stelle"))),
      variante: () => karte("variante", knopf(t("bewerbung.variante-waehlen"), zuAbschnitt("s-lebenslauf"))),
      freigeben: () => karte("freigeben", knopf(Texte.t("Anschreiben lesen"), zuAbschnitt("s-anschreiben"))),
      entwerfen: () => karte("entwerfen", knopf(t("bewerbung.ki-entwerfen"), () => $("ki-entwerfen").click()),
        knopf(Texte.t("Eigenes Anschreiben verwenden"), zuAbschnitt("eigenes-anschreiben"), false)),
      eigenes: () => karte("eigenes", knopf(Texte.t("Eigenes Anschreiben hochladen"), () => $("anschreiben-datei").click()),
        knopf(Texte.t("KI einrichten"), () => window.App.kiEinrichten(), false)),
      erstellen: () => [Texte.t("Unterlagen erstellen"), R.NEXT_CREATE, [knopf(Texte.t("Unterlagen erstellen"), () => $("erstellen").click())]],
      pruefen: () => [R.STEP_TITLE, Texte.t("Die Prüfung läuft."), []],
      klaeren: () => [R.STEP_TITLE, R.nextClarify(fehlerZahl), [zurPruefung()]],
      kuerzen: () => [K.NEXT_TITLE, t("bewerbung.kuerzen"), [knopf(Texte.t("Zur Prüfung"), zuBefund)]],
      bestaetigen: () => karte("bestaetigen", zurPruefung()),
      formular: () => karte("formular", knopf(Texte.t("Formular öffnen"), e => oeffneFormular(e.currentTarget, false)),
        knopf(Texte.t("Per E-Mail beworben? Versand erfassen"), zuAbschnitt("versand-titel"), false)),
      versand: () => karte("versand", versandErfassen()),
      nachtragen: () => karte("nachtragen", versandErfassen()),
      jobroom: () => karte("jobroom", knopf(Texte.t("Job-Room öffnen"), e => oeffneJobroom(e.currentTarget))),
      warten: () => karte("warten", zuDenBewerbungen()),
      gespraech: () => karte("gespraech", b.gespraech_am ? knopf(Texte.t("Inserat lesen"), zuAbschnitt("s-stelle"))
        : knopf(Texte.t("Termin eintragen"), () => oeffneAngaben("f-gespraech_am"))),
      absage: () => karte("absage", zuDenBewerbungen()),
      zusage: () => karte("zusage", zuDenBewerbungen()),
    };
  }

  function zeigeNaechster() {
    const n = L.naechster(daten, { befunde, rav, ki: kiBereit });
    const fehlerZahl = (befunde || []).filter(x => x.stufe === "fehler").length;
    const [titel, text, knoepfe] = karten(bewerbung, fehlerZahl)[n.art]();
    $("naechster-zeile").replaceChildren(...dotLine([Texte.t("Nächster Schritt"), n.art === "jobroom" ? Texte.t("fürs RAV") : ""]));
    $("naechster-titel").textContent = titel;
    $("naechster-text").textContent = text;
    $("naechster-knoepfe").replaceChildren(...knoepfe);
  }

  // Side column

  function zeigeFakten() {
    const b = bewerbung;
    const fakten = [
      [t("bewerbung.feld-firma"), b.firma], [Texte.t("Ort"), b.ort], [Texte.t("Pensum"), b.pensum],
      [Texte.t("Kontakt"), [b.kontaktperson, b.kontakt].filter(Boolean).join(", ")],
      [Texte.t("Gefunden"), [b.portal || b.vermittler, datum(b.eingetragen_am)].filter(Boolean).join(", ")],
      [Texte.t("Lebenslauf"), BT.cvFact(b, daten)],
      [Texte.t("Frist"), datum(b.frist)],
      ...(rav ? [[Texte.t("RAV"), b.rav_zuweisung ? Texte.t("Zuweisung") : Texte.t("keine Zuweisung")]] : []),
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
    const marked = L.longestParagraph(befunde);
    $("anschreiben-text").hidden = !zeigen;
    if (zeigen) {
      $("anschreiben-text").replaceChildren(
        brief.betreff ? el("p", {}, el("strong", {}, brief.betreff)) : null,
        brief.anrede ? el("p", {}, brief.anrede) : null,
        ...brief.absaetze.map((text, place) => (place === marked ? FindingRow.longest(absatz(text), E.openAtLongest) : absatz(text))),
        brief.gruss ? el("p", {}, brief.gruss) : null);
    }
    const freigabe = daten.anschreiben_freigabe || {};
    $("freigabe-zeile").hidden = !zeigen;
    $("freigeben").hidden = !freigabe.noetig || freigabe.freigegeben;
    // the page draws this again after each load and check; a live region would say an unchanged line again
    const stand = zeigen && freigabe.noetig ? BT.approvalState(freigabe, datum(freigabe.am)) : "";
    window.Meldungen.zeigeNeu($("freigabe-status"), stand, freigabe.freigegeben ? "ok" : "");
    zeigeKiPruefung(zeigen);
    E.update({ letter: brief, findings: befunde, approval: freigabe, shown: zeigen });  // hidden again while editing (#332)
  }

  function zeigeKiPruefung(briefSichtbar) {
    const p = daten.ki_pruefung;
    $("ki-pruefung-teil").hidden = !briefSichtbar || !p;
    if (!p) return;
    const anforderungen = p.requirements || [];
    const abgedeckt = anforderungen.filter(r => r.status === "abgedeckt").length;
    const offen = offeneAussagen();
    $("ki-pruefung-zahl").textContent = BT.reviewCount(abgedeckt, anforderungen.length, offen.length);
    $("ki-pruefung-liste").replaceChildren(
      ...offen.map(u => el("div", { class: "claim", "data-evidence": "gap" }, el("span", { class: "claim__text" }, Texte.t("«{wert}»", { wert: u.text })),
        el("span", { class: "claim__source" }, u.problem || Texte.t("Kein Beleg gefunden. Streichen oder in Meine Angaben ergänzen.")))),
      ...anforderungen.filter(r => r.status !== "abgedeckt").map(r => el("div", { class: "claim", "data-evidence": "gap" },
        el("span", { class: "claim__text" }, BT.requirementLine(r)),
        el("span", { class: "claim__source" }, r.note || ""))));
    $("ki-pruefung-fuss").textContent = BT.reviewFoot(datum(p.am));
  }

  function zeigeAnschreibenStand() {
    $("anschreiben-stand").textContent = BT.letterState(daten, bewerbung);
    zeigeBrief();
  }

  async function freigeben() {
    $("freigeben").disabled = true;
    try {
      await senden("/api/anschreiben/freigeben", { id: ID });
      await laden();
      meldungOben(Texte.t("Anschreiben freigegeben"), "ok");
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
    for (const knopf of document.querySelectorAll('input[name="unterlagen"]')) knopf.checked = knopf.value === W.gewaehlt(b);
    S.showForm(b, R.built(daten.pdfs, W.gewaehlt(b)));
    $("antwort-teil").hidden = !gesendet;
    $("jobroom-teil").hidden = !rav || !gesendet;
    $("s-festhalten").hidden = !gesendet;
    zeigeBeenden(b);
    $("s-lebenslauf").hidden = Boolean(b.versand) && !b.variante;
    KU.showLeftOut(daten.kuerzungen, { entryId: ID, sent: Boolean(b.versand), after: nachKuerzen });
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
    $("beenden-hinweis").textContent = BT.endingHint(ende);
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
    optionen($("f-status"), d.status.map(s => [s, standName(s)]), bewerbung.status);
    optionen($("f-variante"), [["", BT.withoutVariant(d)], ...d.varianten.map(v => [v.id, `${v.id}${v.beschreibung ? " – " + v.beschreibung : ""}`])],
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
    if (key === "rav_zuweisung") return wert ? Texte.t("Ja") : Texte.t("Nein");
    return wert;
  }

  function zeigeJobroom(j) {
    $("jobroom").replaceChildren(...BT.jobroomFields().map(([key, name]) => {
      const wert = key in j ? jobroomText(key, j[key]) : "";
      const kopieren = wert ? el("button", { type: "button", class: "btn btn--sm", onclick: () => kopiere(wert) }, Texte.t("Kopieren")) : null;
      return el("div", { class: "copy-row" }, el("dt", {}, name), el("dd", {}, el("span", { class: "copy-row__value" }, wert || ""), kopieren));
    }));
  }

  /** Entered by hand, or marked by mistake: the same mark as after saving in Job-Room (MIN-347). */
  function zeigeRav() {
    const eingetragen = bewerbung.rav_eingetragen_am;
    $("rav-stand").textContent = BT.ravState(datum(eingetragen));
    $("rav-umschalten").textContent = BT.ravButton(eingetragen);
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
      meldung(Texte.t("Kopiert: {inhalt}", { inhalt }), "ok");
    } catch {
      meldung(Texte.t("Kopieren nicht möglich, bitte von Hand markieren"), "hinweis");
    }
  }

  function formularWerte() {
    const werte = { ...bewerbung };
    for (const f of FELDER) werte[f] = $("f-" + f).value;
    werte.rav_zuweisung = $("f-rav_zuweisung").checked;
    return werte;
  }

  /** #321: a tile per document with page 1, instead of the embedded PDFs. */
  function zeigePdfs(d) {
    S.showTiles(ID, d, Date.now());
  }

  function befundZeile(b) {
    const zeile = L.befundZeile(b);
    if (zeile.kuerzen) {  // G92: the cuts to tick instead of «So lassen»
      const chooser = KU.chooser(zeile.kuerzen, { entryId: ID, note: t("kuerzen.hinweis"), after: nachKuerzen });
      const satz = el("span", { id: K.SENTENCE_ID }, zeile.text);
      const li = window.Meldungen.listenZeile(document, el("span", { class: "cut-finding" }, satz, chooser), zeile.stufe, { schliessbar: false });
      li.setAttribute("aria-labelledby", K.SENTENCE_ID);
      return window.FindingRow.keyed(li, b);
    }
    return window.FindingRow.row(b, zeile, { onCut: E.cut, onKeep: knopf => soLassen(knopf, b.schluessel) });
  }

  function zeigeBefunde() {
    S.showFindings(befunde, befundZeile);
  }

  let laufendePruefung = Promise.resolve();  // the check started by the last load; creating waits for it

  function pruefen() {
    laufendePruefung = pruefenJetzt();
    return laufendePruefung;
  }

  async function pruefenJetzt() {
    try {
      ({ befunde } = await holen("/api/pruefung", { id: ID }));
      zeigeBefunde();
      if (daten) zeigeAlles();
    } catch (fehler) {
      meldungOben(Texte.t("Prüfung fehlgeschlagen: {fehler}", { fehler: fehler.message }), "fehler");
    }
  }

  // G92: the choice is stored and the documents are built anew; the focus goes to the new result of the check
  async function nachKuerzen(aktion, antwort) {
    await laden();
    await laufendePruefung;
    const over = K.stillOver(befunde);
    const noneLeft = K.noCutLeft(befunde);
    meldungOben(K.doneMessage(aktion, antwort, over, noneLeft), K.doneLevel(aktion, antwort, over, noneLeft));
    if (aktion !== "zurueck") S.focusFirstFinding();
  }

  // G52: the person has looked at the PDF and sends it as it is; only then does a form open
  async function soLassen(knopf, schluessel) {
    knopf.disabled = true;
    try {
      ({ befunde } = await senden("/api/pruefung/bestaetigen", { id: ID, schluessel }));
      zeigeBefunde();
      if (daten) zeigeAlles();
      FindingRow.focusAfterConfirm($("befunde"), schluessel);
    } catch (fehler) {
      knopf.disabled = false;
      meldungOben(Texte.t("Meldung der Prüfung nicht bestätigt: {fehler}", { fehler: fehler.message }), "fehler");
    }
  }

  // A form keeps the file it got. Whoever sent it there and then records it here says so, the app cannot know.
  function zeigeFormularFassung(d) {
    const anders = d.formular_abweichend;
    $("formular-fassung").hidden = !anders.length;
    if (!anders.length) $("v-formular").checked = false;
    $("formular-fassung-text").textContent = BT.formVersion(anders);
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
      el("div", { class: "notice notice--success" }, el("span", { class: "notice__title" }, Texte.t("Beworben am {datum}", { datum: datum(v.datum) })),
        el("p", { class: "notice__body" }, BT.sentVersion(v.art))),
      el("h3", {}, Texte.t("Versendete Fassung")), el("ul", {}, links));
  }

  /** The empty list leads to the page of files; the sentence is split around its link and ends with its full stop in every language. */
  function keineZertifikate() {
    return el("li", { class: "leer" }, Texte.t("Noch keine Zertifikate hochgeladen. Das geht unter "),
      el("a", { href: "/dateien" }, Texte.t("Lebenslauf und Dateien")), ".");
  }

  // Certificates (MIN-346): without a saved choice yet, the suggestions are ticked and marked with their reason.
  async function zeigeZertifikate() {
    const { verfuegbar, vorschlag, gewaehlt } = await holen("/api/zertifikate", { id: ID });
    const gruende = new Map(vorschlag.map(v => [v.datei, v.grund]));
    const zeilen = verfuegbar.map(datei => el("li", {}, el("label", { class: "check" },
      el("input", { type: "checkbox", value: datei, checked: gewaehlt ? gewaehlt.includes(datei) : gruende.has(datei) }),
      datei.split("/").pop(), gruende.has(datei) ? el("span", { class: "leise" }, ` (${gruende.get(datei)})`) : null)));
    $("zertifikate").replaceChildren(...(zeilen.length ? zeilen : [keineZertifikate()]));
    $("zertifikate-speichern").hidden = !zeilen.length;
    status($("zertifikate-status"), !gewaehlt && vorschlag.length ? Texte.t("Vorschlag, noch nicht gespeichert.") : "");
    zertifikateDa = verfuegbar;
    S.showAttachmentsLine(verfuegbar, gewaehlt, vorschlag.map(v => v.datei));
  }

  async function speichereZertifikate() {
    const dateien = [...$("zertifikate").querySelectorAll("input:checked")].map(feld => feld.value);
    try {
      await senden("/api/zertifikate", { id: ID, dateien });
      S.showAttachmentsLine(zertifikateDa, dateien, []);
      status($("zertifikate-status"), dateien.length ? Texte.t("Gespeichert.") : Texte.t("Gespeichert: ohne Zertifikate."), "ok");
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
                anschreiben_text: neu.anschreiben_text, anschreiben_freigabe: neu.anschreiben_freigabe, ki_pruefung: neu.ki_pruefung,
                kuerzungen: neu.kuerzungen };
      zeigePdfs(neu);
      befunde = null;
      zeigeAlles();
      if (pruefbar(neu)) pruefen();
    }
    if (JSON.stringify(neu.bewerbung) === JSON.stringify(bewerbung) && neu.stellentext === geladenerText) return;
    if (hatEingaben()) meldung(BT.changedElsewhere(), "hinweis");
    else zeigeEintrag(neu);
  }

  async function laden() {
    if (!ID) return meldungOben(Texte.t("Keine Bewerbung gewählt"), "fehler");
    try {
      const d = await holen("/api/bewerbung", { id: ID });
      befunde = null;
      zeigeEintrag(d);
      zeigePdfs(d);
      pdfStand = JSON.stringify(d.pdf_stand);
      meldeGeladen(d);
      zeigeZertifikate().catch(fehler => status($("zertifikate-status"), fehler.message, "fehler"));
      if (pruefbar(d)) pruefen();
    } catch (fehler) {
      meldungOben(Texte.t("Laden fehlgeschlagen: {fehler}", { fehler: fehler.message }), "fehler");
    }
  }

  const speichernFehlgeschlagen = fehler => Texte.t("Speichern fehlgeschlagen: {fehler}", { fehler: fehler.message });

  async function speichere(werte, meldetext) {
    try {
      bewerbung = await senden("/api/bewerbung", { id: bewerbung.id, ...geaenderteFelder(bewerbung, werte) });
      meldung(meldetext, "ok");
      await laden();
      return true;
    } catch (fehler) {
      meldung(speichernFehlgeschlagen(fehler), "fehler");
      return false;
    }
  }

  async function waehleVariante(variante) {
    try {
      bewerbung = await senden("/api/bewerbung", { id: bewerbung.id, variante });
      daten = { ...daten, bewerbung };
      $("f-variante").value = variante;
      meldungOben(variante ? Texte.t("Variante {variante} gespeichert", { variante }) : Texte.t("Ohne Variante gespeichert"), "ok");
      zeigeAlles();
    } catch (fehler) {
      meldungOben(speichernFehlgeschlagen(fehler), "fehler");
    }
  }

  /** The note for the person when no letter could be drafted; the rest of the documents is still worth building. */
  async function entwirfFehlendes() {
    if (!daten || !fehltAnschreiben(daten)) return "";
    meldungOben(Texte.t("Anschreiben wird entworfen … das kann bis zu einer Minute dauern."));
    try {
      const ergebnis = await senden("/api/ki/anschreiben", {}, { id: ID });
      document.dispatchEvent(new CustomEvent("anschreiben-entworfen", { detail: ergebnis }));
      return "";
    } catch (fehler) {
      return Texte.t("Kein Anschreiben entworfen: {fehler}", { fehler: fehler.message });
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
    const gespeichert = await speichere(werte, Texte.t("Stand: {stand}", { stand: standName(stand) }));
    if (gespeichert && stand === "Gespräch" && !bewerbung.gespraech_am) oeffneAngaben("f-gespraech_am");
  }

  // Opening the form or the Job-Room through the extension (MIN-346, MIN-347)

  let laufend = null;  // { art, knopf }

  function frageErweiterung(nachricht, knopf, warten) {
    if (!document.documentElement.dataset[EXTENSION_MARK]) {
      meldungOben(Texte.t("Zum Ausfüllen im Browser braucht es die Erweiterung (siehe Einrichtung)."), "fehler");
      return;
    }
    laufend = { art: nachricht.art, knopf };
    if (knopf) knopf.disabled = true;
    meldungOben(warten);
    clearTimeout(answerTimer);
    answerTimer = setTimeout(() => {
      meldungOben(Texte.t("Die Erweiterung antwortet nicht. Bitte sie neu laden und es nochmals versuchen."), "fehler");
      if (knopf) knopf.disabled = false;
    }, ANSWER_TIMEOUT_MS);
    window.postMessage({ quelle: PAGE_SOURCE, ...nachricht }, location.origin);
  }

  function oeffneFormular(knopf, bestaetigt) {
    frageErweiterung({ art: START_ACTION, ids: [ID], bestaetigt }, knopf, Texte.t("Die Unterlagen werden geprüft …"));
  }

  function oeffneJobroom(knopf) {
    frageErweiterung({ art: RAV_ACTION, ids: [ID] }, knopf, Texte.t("Der Job-Room wird geöffnet …"));
  }

  function antwortDerErweiterung(frage, antwortDaten) {
    if (antwortDaten && antwortDaten.laeuft) return;
    clearTimeout(answerTimer);
    if (laufend?.knopf) laufend.knopf.disabled = false;
    if (!antwortDaten || antwortDaten.fehler) return meldungOben((antwortDaten && antwortDaten.fehler) || Texte.t("Die Erweiterung antwortet nicht."), "fehler");
    if (antwortDaten.berechtigung) return meldungOben(Texte.t("Bitte im neuen Tab den Zugriff erlauben; danach geht es weiter."), "hinweis");
    if (antwortDaten.abgelehnt && antwortDaten.abgelehnt.length) return meldungOben(antwortDaten.abgelehnt.map(a => a.grund).join(" · "), "fehler");
    if (antwortDaten.doppelt && antwortDaten.doppelt.length) {
      const d = antwortDaten.doppelt[0];
      $("doppelt-titel").textContent = Texte.t("Bei {firma} läuft schon eine Bewerbung", { firma: d.firma });
      $("doppelt-text").replaceChildren(...antwortDaten.doppelt.map(x => el("p", {}, Texte.t("{stelle}, Stand {stand}.", { stelle: x.stelle, stand: standName(x.status) }))), el("p", {}, t("uebersicht.doppelt")));
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
    if (await speichere(formularWerte(), Texte.t("Angaben gespeichert"))) $("angaben-dialog").close();
  });
  $("notiz-speichern").addEventListener("click", () => speichere(formularWerte(), Texte.t("Notiz gespeichert")));
  $("f-variante").addEventListener("change", () => waehleVariante($("f-variante").value));
  for (const k of document.querySelectorAll("[data-antwort]")) k.addEventListener("click", () => antwort(k.dataset.antwort));
  bestaetigen($("verwerfen"), Texte.t("Wirklich verwerfen? Nochmals klicken"), () => antwort("Verworfen"));
  bestaetigen($("zurueckziehen"), Texte.t("Wirklich zurückziehen? Nochmals klicken"), () => antwort("Zurückgezogen"));
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
      meldungOben(Texte.t("Stellentext gespeichert"), "ok");
      await laden();
    } catch (fehler) {
      meldungOben(speichernFehlgeschlagen(fehler), "fehler");
    }
  });
  $("vorschlagen").addEventListener("click", async () => {
    try {
      const { vorschlaege } = await holen("/api/varianten/vorschlag", { id: ID });
      $("vorschlaege").replaceChildren(...(vorschlaege.length ? vorschlaege.map(v => el("div", { class: "karte" },
        el("strong", {}, `${v.id}`), v.beschreibung ? ` – ${v.beschreibung}` : "",
        el("div", {}, Texte.t("Passt: {liste}", { liste: v.treffer.join(", ") })),
        v.fehlt.length ? el("div", { class: "leise" }, Texte.t("Fehlt in dieser Variante: {liste}", { liste: v.fehlt.join(", ") })) : null,
        el("button", { type: "button", class: "btn btn--sm", onclick: () => waehleVariante(v.id) }, Texte.t("Übernehmen"))))
        : [el("p", { class: "leer" }, Texte.t("Keine passende Variante gefunden. Mit «Lebenslauf erstellen» entsteht eine für diese Stelle."))]));
    } catch (fehler) {
      meldungOben(fehler.message, "fehler");
    }
  });
  /** G40: the form is saved right away; `body` gives what to save, null when nothing changed. */
  async function speichereWahl(body, gespeichert) {
    try {
      const werte = body();
      if (!werte) return;
      bewerbung = await senden("/api/bewerbung", werte);
      meldungOben(gespeichert(werte), "ok");
      await laden();
    } catch (fehler) {
      zeigeAbschnitte();
      meldungOben(speichernFehlgeschlagen(fehler), "fehler");
    }
  }
  for (const knopf of document.querySelectorAll('input[name="unterlagen"]')) {
    knopf.addEventListener("change", event => speichereWahl(() => W.zuSpeichern(bewerbung, event.target.value),
      body => (body.unterlagen === "dossier" ? Texte.t("Dossier gewählt") : Texte.t("Anschreiben und Lebenslauf gewählt"))));
  }
  // #322: the dialog «Dossier gestalten» saved the design or the texts; an empty message only reloads
  document.addEventListener("dossier-uebernommen", async event => {
    await laden();
    window.DossierDialog.refocus();
    if (event.detail.meldung) status($("dossier-meldung"), event.detail.meldung, "ok");
  });
  $("erstellen").addEventListener("click", async () => {
    $("erstellen").disabled = true; // a second click would pay for a second draft
    try {
      const offen = await entwirfFehlendes();
      meldungOben(Texte.t("Unterlagen werden erstellt …"));
      await senden("/api/unterlagen", {}, { id: ID });
      S.closeForm();
      await laden();
      await laufendePruefung;
      meldungOben(offen ? Texte.t("Unterlagen erstellt. {offen}", { offen }) : Texte.t("Unterlagen erstellt"), offen ? "hinweis" : "ok");
      S.focusFirstFinding();
    } catch (fehler) {
      meldungOben(Texte.t("Erstellen fehlgeschlagen: {fehler}", { fehler: fehler.message }), "fehler");
    } finally {
      $("erstellen").disabled = false;
    }
  });
  $("pruefen").addEventListener("click", pruefen);
  $("freigeben").addEventListener("click", freigeben);
  E.connect(laden);
  document.addEventListener("anschreiben-geprueft", laden);
  document.addEventListener("anschreiben-geaendert", laden);
  document.addEventListener("eigenes-anschreiben-geaendert", nachsehen);
  document.addEventListener("lebenslauf-erstellt", laden);  // G17: the new variant is chosen
  document.addEventListener("bewerbung-geladen", event => zeigeFormularFassung(event.detail));
  document.addEventListener("bewerbung-gespeichert", event => {
    bewerbung = event.detail;
    daten = { ...daten, bewerbung };
    $("f-passung").value = bewerbung.passung ?? "";
    zeigeAlles();
  });
  $("v-datum").value = new Date().toISOString().slice(0, 10);
  bestaetigen($("versenden"), Texte.t("Wirklich erfassen? Nochmals klicken"), async () => {
    try {
      const ergebnis = await senden("/api/versand", { datum: $("v-datum").value, art: $("v-art").value, fassung_formular: $("v-formular").checked }, { id: ID });
      meldungOben(BT.recorded(ergebnis.hinweise, t),ergebnis.hinweise.length ? "hinweis" : "ok");
      await laden();
    } catch (fehler) {
      meldungOben(Texte.t("Versand nicht erfasst: {fehler}", { fehler: fehler.message }), "fehler");
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
