"use strict";
// What to search for (MIN-375): the list of what is searched with „Entfernen“, and suggestions from the AI to add to it.
// Apprenticeships address the person informally and name professions, jobs formally and name search terms.
window.Suchbegriffe = (() => {
  const { senden, el, status } = window.App;
  const $ = id => document.getElementById(id);
  const TEXTE = {
    lehrstelle: {
      titel: "Welcher Beruf passt zu dir?",
      hilfe: "Du weisst noch nicht, welchen Beruf du suchen sollst? Schreib ein paar Stichworte zu deinen Interessen und Fähigkeiten. Die KI, ein Sprachmodell, schlägt dir passende Berufe vor und nennt dir ihre Namen für die Suche. Bitte nichts zu Gesundheit oder Familie schreiben. Die KI kann sich irren: Probier Berufe in einer Schnupperlehre aus, und auch die Berufsberatung hilft dir persönlich weiter.",
      interessen: "Was machst du gern? (Interessen)",
      staerken: "Was kannst du gut? (Fähigkeiten)",
      vermeiden: "Was möchtest du lieber nicht? (freiwillig)",
      knopf: "Berufe vorschlagen",
      fertig: n => `${n === 1 ? "1 Vorschlag" : `${n} Vorschläge`}. Nimm auf, was dich interessiert.`,
      schon: "Steht schon in deiner Suche.",
      neu: "In deiner Suche. Die nächste Suche sucht auch danach.",
      pruefen: "In der Schnupperlehre",
      liste: "Danach suchst du:",
      entfernt: name => `„${name}“ ist nicht mehr in deiner Suche.`,
    },
    stelle: {
      titel: "Welche Stellen passen zu Ihnen?",
      hilfe: "Sie wissen noch nicht genau, wonach Sie suchen sollen, vielleicht nur „etwas Administratives“? Schreiben Sie ein paar Stichworte zu Ihren Interessen und Fähigkeiten. Die KI, ein Sprachmodell, schlägt mit Blick auf Ihren Lebenslauf passende Stellen vor und nennt Begriffe für die Suche. Bitte nichts zu Gesundheit oder Familie schreiben. Die KI kann sich irren: Prüfen Sie die Vorschläge an echten Inseraten. Auch das RAV oder die Berufsberatung hilft Ihnen persönlich weiter.",
      interessen: "Was machen Sie gern? (Interessen)",
      staerken: "Was können Sie gut? (Fähigkeiten)",
      vermeiden: "Was möchten Sie lieber nicht? (freiwillig)",
      knopf: "Stellen vorschlagen",
      fertig: n => `${n === 1 ? "1 Vorschlag" : `${n} Vorschläge`}. Nehmen Sie auf, was Sie interessiert.`,
      schon: "Steht schon in Ihrer Suche.",
      neu: "In Ihrer Suche. Die nächste Suche sucht auch danach.",
      pruefen: "Im Inserat",
      liste: "Danach suchen Sie:",
      entfernt: name => `„${name}“ ist nicht mehr in Ihrer Suche.`,
    },
  };
  let texte = TEXTE.stelle;
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

  async function remove(name, button) {
    button.disabled = true;
    try {
      await senden("/api/beruf/entfernen", { beruf: name });
      status($("suchliste-status"), texte.entfernt(name), "ok");
      $("suchliste-status").focus();
      geaendert();
    } catch (fehler) {
      status($("suchliste-status"), fehler.message, "fehler");
    } finally {
      button.disabled = false;
    }
  }

  function card(item) {
    const note = el("span", { class: "leise", tabindex: "-1" }, item.schon_gesucht ? texte.schon : "");
    const button = el("button", { type: "button", "aria-label": `${item.beruf} in die Suche aufnehmen` }, "In die Suche aufnehmen");
    button.hidden = item.schon_gesucht;
    const karte = { beruf: item.beruf, schluessel: item.schluessel, button, note, eben: false };
    button.addEventListener("click", () => add(karte));
    karten = [...karten, karte];
    return el("li", {},
      el("strong", {}, item.beruf),
      el("p", {}, item.warum),
      el("p", { class: "leise" }, `Im Alltag: ${item.alltag}`),
      el("p", { class: "leise" }, `${texte.pruefen}: ${item.pruefen}`),
      el("div", { class: "knoepfe" }, button, note));
  }

  async function ask() {
    $("vorschlag-holen").disabled = true;
    $("vorschlag-liste").replaceChildren();
    karten = [];
    status($("vorschlag-status"), "Die KI überlegt, das dauert einen Moment …", "");
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
    $("suchliste").hidden = !begriffe.length;
    $("suchliste-titel").textContent = texte.liste;
    $("suchliste-liste").replaceChildren(...begriffe.map(name => {
      const button = el("button", { type: "button", class: "klein", "aria-label": `${name} entfernen` }, "Entfernen");
      button.addEventListener("click", () => remove(name, button));
      return el("li", {}, el("span", {}, name), button);
    }));
  }

  // The server compares forms of a name; the cards follow what it says is searched now.
  function zeigeKarten(schluessel) {
    karten.forEach(karte => {
      const gesucht = schluessel.includes(karte.schluessel);
      karte.button.hidden = gesucht;
      karte.note.textContent = !gesucht ? "" : karte.eben ? texte.neu : texte.schon;
    });
  }

  /** Called with each load of the page's data. */
  function zeige(art, begriffe, schluessel) {
    texte = TEXTE[art] || TEXTE.stelle;
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
    zeigeListe(begriffe);
    zeigeKarten(schluessel);
  }

  $("vorschlag-holen").addEventListener("click", ask);
  return { zeige };
})();
