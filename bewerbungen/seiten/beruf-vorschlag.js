"use strict";
// What to search for (MIN-375): the list of what is searched with „Entfernen“ and Rückgängig, a field for a term of the
// person's own (#216), and suggestions from the AI to add to it. The rows and their order are suchliste.js's (G87).
// Apprenticeships address the person informally and name professions, jobs formally and name search terms.
window.Suchbegriffe = (() => {
  const { holen, senden, el, status } = window.App;
  const $ = id => document.getElementById(id);
  // «Berufsbildner (nur mit Informatik, ICT)» (G110): the server took the remark, so only the words are read here
  const PFLICHT = /^(.*?)\s*\(\s*nur\s+mit\s+([^()]*)\)$/i;

  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => window.Texte.t(deutsch, werte) };

  /**
   * The message after adding a job term, naming its required words apart from the term when it has any; `satz` holds
   * the three messages of one form of address: without words, with one and with several.
   */
  function mitPflicht(name, satz) {
    const teile = PFLICHT.exec(name);
    const woerter = teile ? teile[2].split(",").map(wort => wort.trim()).filter(Boolean) : [];
    if (!woerter.length) return satz.ohne(name);
    return woerter.length === 1 ? satz.eins(teile[1], woerter[0]) : satz.mehrere(teile[1], woerter.join(", "));
  }

  // Each text through Texte.t when the page asks for it, so it comes in the app language (#424). The German says du
  // or Sie, so each form has its own texts and French follows it with tu or vous.
  const TEXTE = {
    lehrstelle: () => ({
      titel: Texte.t("Berufe von der KI vorschlagen lassen"),
      hilfe: Texte.t("Du weisst noch nicht, welchen Beruf du suchen sollst? Schreib ein paar Stichworte zu deinen Interessen und Fähigkeiten. Die KI, ein Sprachmodell, schlägt dir passende Berufe vor und nennt dir ihre Namen für die Suche. Bitte nichts zu Gesundheit oder Familie schreiben. Die KI kann sich irren: Probier Berufe in einer Schnupperlehre aus, und auch die Berufsberatung hilft dir persönlich weiter."),
      interessen: Texte.t("Was machst du gern? (Interessen)"),
      staerken: Texte.t("Was kannst du gut? (Fähigkeiten)"),
      vermeiden: Texte.t("Was möchtest du lieber nicht? (freiwillig)"),
      knopf: Texte.t("Berufe vorschlagen"),
      fertig: n => (n === 1 ? Texte.t("1 Vorschlag. Nimm auf, was dich interessiert.")
        : Texte.t("{anzahl} Vorschläge. Nimm auf, was dich interessiert.", { anzahl: n })),
      schon: Texte.t("Steht schon in deiner Suche."),
      neu: Texte.t("In deiner Suche. Die nächste Suche sucht auch danach."),
      pruefen: wert => Texte.t("In der Schnupperlehre: {pruefen}", { pruefen: wert }),
      liste: Texte.t("Danach suchst du:"),
      ordnen: Texte.t("Gesucht wird von oben nach unten; neue Berufe kommen ans Ende. Zieh die wichtigsten nach oben oder verschieb sie mit den Pfeilen."),
      entfernt: name => Texte.t("„{name}“ ist nicht mehr in deiner Suche.", { name }),
      neuLabel: Texte.t("Eigenen Beruf aufnehmen (mit EFZ oder EBA, zum Beispiel Koch/Köchin EFZ)"),
      aufgenommen: name => Texte.t("„{name}“ ist jetzt in deiner Suche.", { name }),
      zurueck: name => Texte.t("„{name}“ ist wieder in deiner Suche.", { name }),
      amEnde: name => Texte.t("„{name}“ ist wieder in deiner Suche, am Ende der Liste.", { name }),
      einwilligung: Texte.t("Bevor die KI dir Berufe vorschlägt, braucht es deine Einwilligung. Was du geschrieben hast, bleibt stehen."),
    }),
    stelle: () => ({
      titel: Texte.t("Stellen von der KI vorschlagen lassen"),
      hilfe: Texte.t("Sie wissen noch nicht genau, wonach Sie suchen sollen, vielleicht nur „etwas Administratives“? Schreiben Sie ein paar Stichworte zu Ihren Interessen und Fähigkeiten. Die KI, ein Sprachmodell, schlägt mit Blick auf Ihren Lebenslauf passende Stellen vor und nennt Begriffe für die Suche. Bitte nichts zu Gesundheit oder Familie schreiben. Die KI kann sich irren: Prüfen Sie die Vorschläge an echten Inseraten. Auch das RAV oder die Berufsberatung hilft Ihnen persönlich weiter."),
      interessen: Texte.t("Was machen Sie gern? (Interessen)"),
      staerken: Texte.t("Was können Sie gut? (Fähigkeiten)"),
      vermeiden: Texte.t("Was möchten Sie lieber nicht? (freiwillig)"),
      knopf: Texte.t("Stellen vorschlagen"),
      fertig: n => (n === 1 ? Texte.t("1 Vorschlag. Nehmen Sie auf, was Sie interessiert.")
        : Texte.t("{anzahl} Vorschläge. Nehmen Sie auf, was Sie interessiert.", { anzahl: n })),
      schon: Texte.t("Steht schon in Ihrer Suche."),
      neu: Texte.t("In Ihrer Suche. Die nächste Suche sucht auch danach."),
      pruefen: wert => Texte.t("Im Inserat: {pruefen}", { pruefen: wert }),
      liste: Texte.t("Danach suchen Sie:"),
      ordnen: Texte.t("Gesucht wird von oben nach unten; neue Begriffe kommen ans Ende. Ziehen Sie die wichtigsten nach oben oder verschieben Sie sie mit den Pfeilen."),
      entfernt: name => Texte.t("„{name}“ ist nicht mehr in Ihrer Suche.", { name }),
      neuLabel: Texte.t("Eigenen Suchbegriff aufnehmen"),
      aufgenommen: name => mitPflicht(name, {
        ohne: begriff => Texte.t("„{name}“ ist jetzt in Ihrer Suche.", { name: begriff }),
        eins: (begriff, wort) => Texte.t("„{name}“ ist jetzt in Ihrer Suche, mit Pflichtbezug: {wort}.", { name: begriff, wort }),
        mehrere: (begriff, woerter) => Texte.t("„{name}“ ist jetzt in Ihrer Suche, mit Pflichtbezug: {woerter}.", { name: begriff, woerter }),
      }),
      zurueck: name => Texte.t("„{name}“ ist wieder in Ihrer Suche.", { name }),
      amEnde: name => Texte.t("„{name}“ ist wieder in Ihrer Suche, am Ende der Liste.", { name }),
      einwilligung: Texte.t("Bevor die KI Stellen vorschlägt, braucht es Ihre Einwilligung. Was Sie geschrieben haben, bleibt stehen."),
    }),
    stelleDu: () => ({
      titel: Texte.t("Stellen von der KI vorschlagen lassen"),
      hilfe: Texte.t("Du weisst noch nicht genau, wonach du suchen sollst, vielleicht nur „etwas Administratives“? Schreib ein paar Stichworte zu deinen Interessen und Fähigkeiten. Die KI, ein Sprachmodell, schlägt mit Blick auf deinen Lebenslauf passende Stellen vor und nennt Begriffe für die Suche. Bitte nichts zu Gesundheit oder Familie schreiben. Die KI kann sich irren: Prüfe die Vorschläge an echten Inseraten. Auch das RAV oder die Berufsberatung hilft dir persönlich weiter."),
      interessen: Texte.t("Was machst du gern? (Interessen)"),
      staerken: Texte.t("Was kannst du gut? (Fähigkeiten)"),
      vermeiden: Texte.t("Was möchtest du lieber nicht? (freiwillig)"),
      knopf: Texte.t("Stellen vorschlagen"),
      fertig: n => (n === 1 ? Texte.t("1 Vorschlag. Nimm auf, was dich interessiert.")
        : Texte.t("{anzahl} Vorschläge. Nimm auf, was dich interessiert.", { anzahl: n })),
      schon: Texte.t("Steht schon in deiner Suche."),
      neu: Texte.t("In deiner Suche. Die nächste Suche sucht auch danach."),
      pruefen: wert => Texte.t("Im Inserat: {pruefen}", { pruefen: wert }),
      liste: Texte.t("Danach suchst du:"),
      ordnen: Texte.t("Gesucht wird von oben nach unten; neue Begriffe kommen ans Ende. Zieh die wichtigsten nach oben oder verschieb sie mit den Pfeilen."),
      entfernt: name => Texte.t("„{name}“ ist nicht mehr in deiner Suche.", { name }),
      neuLabel: Texte.t("Eigenen Suchbegriff aufnehmen"),
      aufgenommen: name => mitPflicht(name, {
        ohne: begriff => Texte.t("„{name}“ ist jetzt in deiner Suche.", { name: begriff }),
        eins: (begriff, wort) => Texte.t("„{name}“ ist jetzt in deiner Suche, mit Pflichtbezug: {wort}.", { name: begriff, wort }),
        mehrere: (begriff, woerter) => Texte.t("„{name}“ ist jetzt in deiner Suche, mit Pflichtbezug: {woerter}.", { name: begriff, woerter }),
      }),
      zurueck: name => Texte.t("„{name}“ ist wieder in deiner Suche.", { name }),
      amEnde: name => Texte.t("„{name}“ ist wieder in deiner Suche, am Ende der Liste.", { name }),
      einwilligung: Texte.t("Bevor die KI Stellen vorschlägt, braucht es deine Einwilligung. Was du geschrieben hast, bleibt stehen."),
    }),
  };
  const texteFuer = (art, satz) => (art === "lehrstelle" ? TEXTE.lehrstelle : satz === "stelle-du" ? TEXTE.stelleDu : TEXTE.stelle)();
  let texte = null;  // the texts of the form of address, set by zeige before anything else is shown
  let karten = [];
  let schonGeoeffnet = false;

  const geaendert = () => document.dispatchEvent(new CustomEvent("suchprofil-geaendert"));

  async function add(karte) {
    karte.button.disabled = true;
    try {
      await senden("/api/beruf/aufnehmen", { beruf: karte.beruf });
      karten = karten.map(k => (k === karte ? { ...k, eben: true } : k));
      karte.button.hidden = true;
      karte.note.textContent = texte.neu;
      karte.note.focus();
      geaendert();
    } catch (fehler) {
      status($("vorschlag-status"), fehler.message, "fehler");
    } finally {
      karte.button.disabled = false;
    }
  }

  const meldeListe = (text, art, optionen) => {
    status($("suchliste-status"), text, art, optionen);
    $("suchliste-status").focus();
  };

  async function undo(name, vorher) {
    try {
      const { am_ende: amEnde } = await senden("/api/beruf/rueckgaengig", { beruf: name, vorher });
      meldeListe(amEnde ? texte.amEnde(name) : texte.zurueck(name), "ok");
      geaendert();
    } catch (fehler) {
      meldeListe(fehler.message, "fehler");
    }
  }

  async function remove(name, button) {
    button.disabled = true;
    try {
      const { rueckgaengig } = await senden("/api/beruf/entfernen", { beruf: name });
      // the action keeps the message until it is used or closed (#215)
      const aktion = rueckgaengig ? { text: Texte.t("Rückgängig"), ausfuehren: () => undo(name, rueckgaengig) } : null;
      meldeListe(texte.entfernt(name), "ok", { aktion });
      geaendert();
    } catch (fehler) {
      meldeListe(fehler.message, "fehler");
    } finally {
      button.disabled = false;
    }
  }

  // The server says what is missing or searched already, so the field needs no rules of its own.
  async function addOwn() {
    const feld = $("suchliste-neu");
    const name = feld.value.split(/\s+/).filter(Boolean).join(" ");
    $("suchliste-aufnehmen").disabled = true;
    try {
      await senden("/api/beruf/aufnehmen", { beruf: feld.value });
      feld.value = "";
      meldeListe(texte.aufgenommen(name), "ok");
      geaendert();
    } catch (fehler) {
      meldeListe(fehler.message, "fehler", { input: window.Meldungen.isInputRejection(fehler) ? feld : null });
      feld.focus();
    } finally {
      $("suchliste-aufnehmen").disabled = false;
    }
  }

  function card(item) {
    const note = el("span", { class: "leise", tabindex: "-1" }, item.schon_gesucht ? texte.schon : "");
    const button = el("button", { type: "button", "aria-label": Texte.t("{beruf} in die Suche aufnehmen", { beruf: item.beruf }) },
      Texte.t("In die Suche aufnehmen"));
    button.hidden = item.schon_gesucht;
    const karte = { beruf: item.beruf, schluessel: item.schluessel, button, note, eben: false };
    button.addEventListener("click", () => add(karte));
    karten = [...karten, karte];
    return el("li", {},
      el("strong", {}, item.beruf),
      el("p", {}, item.warum),
      el("p", { class: "leise" }, Texte.t("Im Alltag: {alltag}", { alltag: item.alltag })),
      el("p", { class: "leise" }, texte.pruefen(item.pruefen)),
      el("div", { class: "knoepfe" }, button, note));
  }

  /** The open consent, or null; an unreadable status lets the suggestion route say what is missing. */
  async function offeneEinwilligung() {
    try {
      const { einwilligung } = await holen("/api/ki/status");
      return einwilligung && !einwilligung.erteilt ? einwilligung : null;
    } catch {
      return null;
    }
  }

  // In the box itself, so that what was typed stays and nothing of it goes out before the consent.
  function zeigeEinwilligung(stand) {
    status($("vorschlag-status"), texte.einwilligung, "");
    window.Einwilligung.zeile($("vorschlag-einwilligung"), stand, neu => {
      if (neu.einwilligung && !neu.einwilligung.erteilt) return;
      $("vorschlag-einwilligung").hidden = true;
      return vorschlagen();
    });
  }

  async function ask() {
    $("vorschlag-holen").disabled = true;
    const offen = await offeneEinwilligung();
    if (offen) {
      $("vorschlag-holen").disabled = false;
      zeigeEinwilligung(offen);
      return;
    }
    $("vorschlag-einwilligung").hidden = true;
    await vorschlagen();
  }

  async function vorschlagen() {
    $("vorschlag-holen").disabled = true;
    $("vorschlag-liste").replaceChildren();
    karten = [];
    status($("vorschlag-status"), Texte.t("Die KI überlegt, das dauert einen Moment …"), "");
    try {
      const { vorschlaege } = await senden("/api/beruf/vorschlag", {
        interessen: $("vorschlag-interessen").value, staerken: $("vorschlag-staerken").value, vermeiden: $("vorschlag-vermeiden").value,
      });
      $("vorschlag-liste").replaceChildren(...vorschlaege.map(card));
      status($("vorschlag-status"), texte.fertig(vorschlaege.length), "ok");
    } catch (fehler) {
      status($("vorschlag-status"), fehler.message, "fehler");
    } finally {
      $("vorschlag-holen").disabled = false;
    }
  }

  function zeigeListe(begriffe) {
    $("suchliste").hidden = false;
    $("suchliste-titel").hidden = !begriffe.length;
    $("suchliste-liste").hidden = !begriffe.length;
    $("suchliste-titel").textContent = texte.liste;
    $("suchliste-hinweis").textContent = texte.ordnen;
    $("suchliste-hinweis").hidden = begriffe.length < 2;
    $("suchliste-neu-label").textContent = texte.neuLabel;
    window.Suchliste.zeige($("suchliste-liste"), begriffe, { status: $("suchliste-status"), entfernen: remove, geaendert });
  }

  // The server compares forms of a name; the cards follow what it says is searched now.
  function zeigeKarten(schluessel) {
    karten.forEach(karte => {
      const gesucht = schluessel.includes(karte.schluessel);
      karte.button.hidden = gesucht;
      karte.note.textContent = !gesucht ? "" : karte.eben ? texte.neu : texte.schon;
    });
  }

  /** Called with each load of the page's data; `laenge` is what Meine Angaben takes per term (#310), the server checks it again. */
  async function zeige(art, begriffe, schluessel, laenge) {
    texte = texteFuer(art, await window.App.textsatz());
    $("vorschlag-titel").textContent = texte.titel;
    $("vorschlag-hilfe").textContent = texte.hilfe;
    $("vorschlag-label-interessen").textContent = texte.interessen;
    $("vorschlag-label-staerken").textContent = texte.staerken;
    $("vorschlag-label-vermeiden").textContent = texte.vermeiden;
    $("vorschlag-holen").textContent = texte.knopf;
    $("vorschlag").hidden = false;
    if (!begriffe.length && !schonGeoeffnet) {
      $("vorschlag").open = true;
      schonGeoeffnet = true;
    }
    if (Number.isInteger(laenge)) $("suchliste-neu").maxLength = laenge;
    zeigeListe(begriffe);
    zeigeKarten(schluessel);
  }

  $("vorschlag-holen").addEventListener("click", ask);
  $("suchliste-aufnehmen").addEventListener("click", addOwn);
  $("suchliste-neu").addEventListener("keydown", event => {
    if (event.key !== "Enter") return undefined;
    event.preventDefault();
    return addOwn();
  });
  return { zeige, texteFuer };
})();
