"use strict";
// The words of the application page (#427, G10): what bewerbung.js says about one application, in the app language
// through Texte. No DOM; loaded before bewerbung.js and required in the tests. Data such as firm, job, file names and
// the AI's own words stay as they come; stored values (kinds of dispatch, states of a requirement) are looked up by
// their stored German name, and an unknown one shows as stored. Dates come formatted by the page.
(function (global) {
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const aus = (namen, wert) => (namen[wert] ? namen[wert]() : wert);

  const STEP_NAMES = {
    lebenslauf: () => Texte.t("Lebenslauf"), anschreiben: () => Texte.t("Anschreiben"), pruefen: () => Texte.t("Prüfen"),
    abschicken: () => Texte.t("Abschicken"), festhalten: () => Texte.t("Festhalten"),
  };
  const FORM_FILES = {
    lebenslauf: () => Texte.t("Lebenslauf"), anschreiben: () => Texte.t("Anschreiben"), zertifikate: () => Texte.t("Zertifikate"),
    unterlagen: () => Texte.t("Unterlagen (gemeinsames PDF)"), nachweise: () => Texte.t("Nachweise (gemeinsames PDF)"),
  };
  // A file kept with the dispatch, by the part it went out as (versand.py). German has always shown the stored part,
  // so each key is the line as German wrote it, and French and English name the part as form_copy.LABELS does.
  const SENT_FILES = {
    lebenslauf: datei => Texte.t("lebenslauf: {datei}", { datei }), anschreiben: datei => Texte.t("anschreiben: {datei}", { datei }),
    dossier: datei => Texte.t("dossier: {datei}", { datei }), zertifikate: datei => Texte.t("zertifikate: {datei}", { datei }),
    unterlagen: datei => Texte.t("unterlagen: {datei}", { datei }), nachweise: datei => Texte.t("nachweise: {datei}", { datei }),
  };
  // The kinds of dispatch as stored (register.JOBROOM_ART), capitalised at the start of a sentence.
  const KIND_SENTENCE = {
    "elektronisch": () => Texte.t("Elektronisch"), "schriftlich": () => Texte.t("Schriftlich"),
    "persönlich": () => Texte.t("Persönlich"), "telefonisch": () => Texte.t("Telefonisch"),
  };
  // The state of a requirement as the AI review stores it (ai/letter_review.py).
  const REQUIREMENT_STATES = {
    "abgedeckt": () => Texte.t("abgedeckt"), "fehlt": () => Texte.t("fehlt"), "überdehnt": () => Texte.t("überdehnt"),
  };

  const jobroomFields = () => [["datum", Texte.t("Datum")], ["arbeitgeber", Texte.t("Arbeitgeber")], ["adresse", Texte.t("Adresse")],
    ["kontaktperson", Texte.t("Kontaktperson")], ["kontakt", Texte.t("Telefon / E-Mail")], ["stelle", Texte.t("Stelle")],
    ["pensum", Texte.t("Pensum")], ["art", Texte.t("Art")], ["ergebnis", Texte.t("Ergebnis")],
    ["rav_zuweisung", Texte.t("Zuweisung des RAV")]];

  function gradeWord(note) {
    return note >= 5.5 ? Texte.t("passt sehr gut") : note >= 4.5 ? Texte.t("passt gut") : note >= 4 ? Texte.t("passt knapp")
      : Texte.t("passt wenig");
  }

  /** A draft: one statement without evidence and more have sets of their own, for the verb in French and English. */
  function approvalText(c) {
    if (!c.offen) return c.t("bewerbung.freigeben");
    return c.offen === 1 ? c.t("bewerbung.freigeben-offen-eins") : c.t("bewerbung.freigeben-offen", { anzahl: c.offen });
  }

  // Title and text of the card „Nächster Schritt“ by its kind; `c` holds the page's text sets (`t`), the firm, the
  // number of open statements and the dates as the page writes them. Kinds that other modules word are not here.
  const CARDS = {
    inserat: c => [Texte.t("Inseratstext einfügen"), c.t("bewerbung.inserat")],
    variante: () => [Texte.t("Lebenslauf-Variante wählen"),
      Texte.t("Es gibt mehrere Varianten des Lebenslaufs. «Variante vorschlagen» vergleicht sie mit dem Inserat.")],
    freigeben: c => [Texte.t("Anschreiben lesen und freigeben"), approvalText(c)],
    entwerfen: c => [c.t("bewerbung.ki-entwerfen"),
      Texte.t("Die KI entwirft das Anschreiben aus dem Inserat und den Angaben. Jede Aussage nennt ihren Beleg; was sich nicht belegen lässt, kommt nicht in den Brief.")],
    eigenes: c => [Texte.t("Anschreiben hinzufügen"), c.t("bewerbung.eigenes")],
    bestaetigen: () => [Texte.t("Unterlagen ansehen"),
      Texte.t("Die Prüfung meldet etwas am Satz der PDFs, mit Dokument und Seite. Erst nach «So lassen» öffnet sich ein Formular.")],
    formular: c => [Texte.t("Formular bei {firma} ausfüllen", { firma: c.firma }), c.t("bewerbung.formular")],
    versand: c => [Texte.t("Abschicken und festhalten"), c.t("bewerbung.versand")],
    nachtragen: c => [Texte.t("Versand festhalten"),
      Texte.t("Beworben am {datum}, aber der Versand ist noch nicht festgehalten. «Versand erfassen» legt die Fassung ab, die verschickt wurde.",
        { datum: c.beworben })],
    jobroom: c => [Texte.t("Im Job-Room eintragen"), c.t("bewerbung.jobroom")],
    warten: c => [Texte.t("Antwort abwarten"), c.nachfragen ? c.t("bewerbung.warten", { datum: c.nachfragen })
      : Texte.t("Die Antwort lässt sich unten eintragen, sobald sie kommt.")],
    gespraech: c => [c.t("bewerbung.gespraech"), c.gespraech
      ? Texte.t("Termin am {datum}. Inserat und Anschreiben stehen auf dieser Seite.", { datum: c.gespraech })
      : Texte.t("Den Termin bei den Angaben eintragen, dann steht er hier und in der Übersicht.")],
    absage: c => [Texte.t("Absage erhalten"), c.t("bewerbung.absage")],
    zusage: () => [Texte.t("Zusage erhalten"), Texte.t("Die Unterlagen dieser Bewerbung bleiben gespeichert.")],
  };

  function cvFact(b, daten) {
    if (b.variante) return Texte.t("Variante {name}", { name: b.variante });
    if (daten.eigener_lebenslauf) return Texte.t("eigenes PDF");
    return daten.varianten.length ? Texte.t("noch keine Variante") : Texte.t("ganzer Lebenslauf");
  }

  function approvalState(freigabe, am) {
    return freigabe.freigegeben ? Texte.t("Freigegeben am {datum}. Eine Änderung am Text hebt die Freigabe auf.", { datum: am })
      : Texte.t("Noch nicht freigegeben. Erst mit der Freigabe öffnet die Erweiterung das Formular.");
  }

  /** „1 von 2 Anforderungen belegt, 1 Aussage ohne Beleg“: a count of 1 has keys of its own for French and English. */
  function reviewCount(belegt, anzahl, offen) {
    const anforderungen = anzahl === 1 ? (belegt ? Texte.t("1 von 1 Anforderungen belegt") : Texte.t("0 von 1 Anforderungen belegt"))
      : belegt === 1 ? Texte.t("1 von {anzahl} Anforderungen belegt", { anzahl })
        : Texte.t("{belegt} von {anzahl} Anforderungen belegt", { belegt, anzahl });
    const aussagen = offen === 1 ? Texte.t("1 Aussage ohne Beleg") : Texte.t("{anzahl} Aussagen ohne Beleg", { anzahl: offen });
    return `${anforderungen}, ${aussagen}`;
  }

  const reviewFoot = am => Texte.t("Prüfung der KI vom {datum}. Eine Einschätzung, kein Urteil: Die KI kann sich irren.", { datum: am });
  const changedElsewhere = () => Texte.t("Diese Bewerbung wurde inzwischen auch anderswo geändert. Die Eingaben bleiben stehen, und gespeichert werden nur die geänderten Felder.");
  const requirementLine = r => Texte.t("{anforderung}: {stand}", { anforderung: r.requirement, stand: aus(REQUIREMENT_STATES, r.status) });

  function letterState(daten, b) {
    const freigabe = daten.anschreiben_freigabe || {};
    if (daten.eigenes_anschreiben) return Texte.t("Für diese Bewerbung gilt das hochgeladene PDF.");
    if (b.versand) return Texte.t("Das Anschreiben ist mit der Bewerbung versendet.");
    if (daten.anschreiben_text) return freigabe.freigegeben ? Texte.t("Freigegebener Entwurf:") : Texte.t("Entwurf, bitte lesen:");
    return daten.hat_anschreiben ? Texte.t("Ein Anschreiben ist vorhanden.") : Texte.t("Noch kein Anschreiben.");
  }

  function endingHint(ende) {
    if (!ende) return "";
    return ende.stand === "Verworfen" ? Texte.t("Nicht bewerben: Die Bewerbung bleibt mit dem Stand „Verworfen“ in der Liste.")
      : Texte.t("Die Bewerbung nicht weiterverfolgen: Sie bleibt mit dem Stand „Zurückgezogen“ in der Liste.");
  }

  function withoutVariant(d) {
    if (d.eigener_lebenslauf_da) return Texte.t("– eigener Lebenslauf –");
    return d.varianten.length ? Texte.t("– keine –") : Texte.t("– ganzer Lebenslauf –");
  }

  const ravState = am => (am ? Texte.t("Im Job-Room eingetragen am {datum}.", { datum: am }) : Texte.t("Noch nicht im Job-Room eingetragen."));
  const ravButton = eingetragen => (eingetragen ? Texte.t("Zurücksetzen") : Texte.t("Als eingetragen markieren"));

  /** The files a form got in another version, or "" when it got the current ones. */
  function formVersion(arten) {
    if (!arten.length) return "";
    return Texte.t("Das Formular im Browser hat eine andere Fassung bekommen: {dateien}. Ohne Häkchen wird die aktuelle festgehalten.",
      { dateien: arten.map(art => aus(FORM_FILES, art)).join(", ") });
  }

  /** „Elektronisch. Diese Fassung …“; a kind the page does not know, capitalised as stored. */
  function sentVersion(art) {
    const satz = KIND_SENTENCE[art] ? KIND_SENTENCE[art]() : `${art[0].toUpperCase()}${art.slice(1)}`;
    return Texte.t("{art}. Diese Fassung ist fest gespeichert und ändert sich nicht mehr.", { art: satz });
  }

  /** After recording: one remark from the server and more have sets of their own; the remarks come as the server words them. */
  function recorded(hinweise, t) {
    if (!hinweise.length) return Texte.t("Versand erfasst. Die verschickte Fassung bleibt gespeichert.");
    return t(hinweise.length === 1 ? "versand.erfasst-hinweis" : "versand.erfasst-hinweise", { hinweise: hinweise.join(" · ") });
  }

  const texte = {
    jobroomFields, gradeWord, cvFact, approvalState, reviewCount, reviewFoot, changedElsewhere, requirementLine, letterState, endingHint, withoutVariant,
    ravState, ravButton, formVersion, sentVersion, recorded,
    stepName: id => aus(STEP_NAMES, id),
    // A part the page does not know shows as stored.
    sentFile: (art, datei) => (SENT_FILES[art] ? SENT_FILES[art](datei) : `${art}: ${datei}`),
    card: (art, c) => CARDS[art](c),
  };
  if (typeof module !== "undefined") module.exports = texte;
  else global.BewerbungTexte = texte;
})(typeof window !== "undefined" ? window : globalThis);
