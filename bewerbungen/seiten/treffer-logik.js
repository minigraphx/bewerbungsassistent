"use strict";
// Rating hits in packages (MIN-372): what to rate, which buttons to offer, the run itself. No DOM, so it can be tested.
(function (global) {
  /** A hit that failed the pre-check by fixed rules (G33) goes below the others; it is never hidden. */
  const durchgefallen = t => Number(Boolean(t.vorpruefung));

  /** Hits that can be rated now: passed the pre-check, near the home first, then the newest, so the limit of a run takes those. */
  function zuBewerten(treffer) {
    return treffer
      .filter(t => t.zustand === "neu" && !t.bewertung && !t.ohne_text)
      .sort((a, b) => durchgefallen(a) - durchgefallen(b)
        || Number(Boolean(b.nah)) - Number(Boolean(a.nah))
        || (b.gefunden_am || "").localeCompare(a.gefunden_am || ""));
  }

  /** True once every new hit has a grade; hits without text stay open, so the message does not claim too much. */
  function alleBewertet(treffer) {
    const neue = treffer.filter(t => t.zustand === "neu");
    return neue.length > 0 && neue.every(t => t.bewertung);
  }

  const SORTIERUNGEN = ["note", "eigene", "datum"];

  /** A stored order of the list: a known one, else the grade. */
  function gueltigeSortierung(wert) {
    return SORTIERUNGEN.includes(wert) ? wert : "note";
  }

  /** A failed pre-check (G33) goes last in every order. By grade: own stars of the profession, the grade, near the
   * home, the newest; hits without a profession count as no stars. By own stars (G22) the hits the person rated come
   * first; by date the newest. Ties keep the order by grade. */
  function sortiert(treffer, sterne, sortierung = "note") {
    const beruf = t => sterne[t.beruf] || 0;
    const nachNote = (a, b) => beruf(b) - beruf(a)
      || (b.bewertung?.note ?? 0) - (a.bewertung?.note ?? 0)
      || Number(Boolean(b.nah)) - Number(Boolean(a.nah))
      || (b.gefunden_am || "").localeCompare(a.gefunden_am || "");
    const vorne = {
      eigene: (a, b) => (b.eigene_sterne || 0) - (a.eigene_sterne || 0),
      datum: (a, b) => (b.gefunden_am || "").localeCompare(a.gefunden_am || ""),
    }[gueltigeSortierung(sortierung)] || (() => 0);
    return [...treffer].sort((a, b) => durchgefallen(a) - durchgefallen(b) || vorne(a, b) || nachNote(a, b));
  }

  function pakete(ids, groesse) {
    const result = [];
    for (let i = 0; i < ids.length; i += groesse) result.push(ids.slice(i, i + groesse));
    return result;
  }

  const zusammen = (stand, antwort) => ({
    ...stand,
    bewertet: stand.bewertet + antwort.bewertet.length,
    ohneText: stand.ohneText + (antwort.ohne_text || []).length,
    kosten: stand.kosten + (antwort.kosten_usd || 0),
  });

  /**
   * Rate ids in packages. A package without a usable answer costs nobody else: its hits are tried again one by one.
   * An error of connection, access or credit ends the run, what was rated stays.
   * mittel: { paket, sende(ids) → answer, angehalten() → bool, fortschritt(stand, hits), beginnt?(stand, ids) }.
   */
  async function bewerteAlle(ids, { paket, sende, angehalten, fortschritt, beginnt = () => {} }) {
    let stand = { bewertet: 0, ohneText: 0, kosten: 0, offen: [], fehler: "", gestoppt: false, von: ids.length };
    const runden = [...pakete(ids, paket).map(gruppe => ({ gruppe, nochmals: gruppe.length > 1 }))];
    while (runden.length) {
      if (angehalten()) return { ...stand, gestoppt: true };
      const { gruppe, nochmals } = runden.shift();
      beginnt(stand, gruppe);
      let antwort;
      try {
        antwort = await sende(gruppe);
      } catch (fehler) {
        return { ...stand, fehler: fehler.message };
      }
      stand = zusammen(stand, antwort);
      if (nochmals) runden.push(...antwort.offen.map(id => ({ gruppe: [id], nochmals: false })));
      else stand = { ...stand, offen: [...stand.offen, ...antwort.offen] };
      fortschritt(stand, antwort.bewertet);
    }
    return stand;
  }

  // G43 (#284): a package is one call to the AI, so the line names its hits and, after a few seconds, how long it runs.
  const SEKUNDEN_AB = 3;

  /** „Stellen 11 bis 20 von 25 prüfen …“ for the package going out now; `sekunden` since it went out. */
  function pruefSchritt(stand, gruppe, sekunden) {
    const Texte = texts();
    const erste = stand.bewertet + 1;
    const werte = { erste, letzte: erste + gruppe.length - 1, von: stand.von };
    if (sekunden < SEKUNDEN_AB) {
      return gruppe.length > 1 ? Texte.t("Stellen {erste} bis {letzte} von {von} prüfen …", werte)
        : Texte.t("Stelle {erste} von {von} prüfen …", werte);
    }
    const mitDauer = { ...werte, dauer: seconds(sekunden) };
    return gruppe.length > 1 ? Texte.t("Stellen {erste} bis {letzte} von {von} prüfen, seit {dauer} …", mitDauer)
      : Texte.t("Stelle {erste} von {von} prüfen, seit {dauer} …", mitDauer);
  }

  /** „Inserat 4 von 9 holen …“ while the extension loads the missing ads; empty before it says how many. */
  function inseratSchritt(stand) {
    return stand.von ? Texte.t("Inserat {nummer} von {von} holen …", { nummer: stand.fertig + 1, von: stand.von }) : "";
  }

  // „Alle prüfen“ (G44, #209): the words around the estimate of GET /api/suche/alle-pruefen, in its currency: CHF
  // with the mediation and its budget (G46, G98), USD with an own key.
  const currencyOf = s => (s && s.waehrung) || "USD";
  // A no-break space between number and unit (#336): at 375 px «1» stood at the end of a line and «Minute» began the
  // next. Screen readers read it as a space, so the spoken words stay the same.
  const NBSP = "\u00a0";
  const money = (amount, currency) => `${currency}${NBSP}${Number(amount).toFixed(2)}`;
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const minutes = n => (n === 1 ? Texte.t("{anzahl}{nbsp}Minute", { anzahl: n, nbsp: NBSP })
    : Texte.t("{anzahl}{nbsp}Minuten", { anzahl: n, nbsp: NBSP }));
  const seconds = n => (n === 1 ? Texte.t("{anzahl}{nbsp}Sekunde", { anzahl: n, nbsp: NBSP })
    : Texte.t("{anzahl}{nbsp}Sekunden", { anzahl: n, nbsp: NBSP }));
  function jobs(n, apprenticeship) {
    const Texte = texts();
    if (apprenticeship) return n === 1 ? Texte.t("1 Lehrstelle") : Texte.t("{anzahl} Lehrstellen", { anzahl: n });
    return n === 1 ? Texte.t("1 Stelle") : Texte.t("{anzahl} Stellen", { anzahl: n });
  }
  const withCredit = s => typeof s.guthaben === "number";
  const usedUp = s => withCredit(s) && s.guthaben <= 0;

  // The budget of the month (G98) when the estimate names its renewal; otherwise the one-time credit of G80. Each
  // sentence is whole, since French and English cannot put „Guthaben“ or „Budget“ into one frame.
  function creditWords(s) {
    const Texte = texts();
    const budget = Texte.budgetMonth(s);
    if (!budget) {
      return {
        enough: stellen => Texte.t("Das Guthaben reicht für etwa {stellen}.", { stellen }),
        after: betrag => Texte.t("Danach bleiben {betrag} im Guthaben.", { betrag }),
        left: betrag => Texte.t("Im Guthaben sind noch {betrag}, das reicht vielleicht nicht.", { betrag }),
        leftThen: (guthaben, danach) => Texte.t("Im Guthaben sind noch {guthaben}, danach etwa {danach}.", { guthaben, danach }),
        usedUpLine: Texte.t("Das Guthaben ist aufgebraucht: neuen Code anfordern."),
        usedUpWarning: Texte.t("Das Guthaben ist aufgebraucht. Mit einem neuen Einladungscode geht es weiter; ohne prüft die KI keine Stelle."),
        tight: (betrag, anzahl, stellen) => Texte.t("Das Guthaben von {betrag} reicht für etwa {anzahl} von {stellen}.", { betrag, anzahl, stellen }),
      };
    }
    return {
      enough: stellen => Texte.t("Das Budget dieses Monats reicht für etwa {stellen}.", { stellen }),
      after: betrag => Texte.t("Danach bleiben {betrag} im Budget.", { betrag }),
      left: betrag => Texte.t("Im Budget sind noch {betrag}, das reicht vielleicht nicht.", { betrag }),
      leftThen: (guthaben, danach) => Texte.t("Im Budget sind noch {guthaben}, danach etwa {danach}.", { guthaben, danach }),
      usedUpLine: Texte.t("Das KI-Budget ist aufgebraucht, wieder ab {datum}.", { datum: budget.renews }),
      usedUpWarning: Texte.t("Das KI-Budget für {monat} ist aufgebraucht. Ab {datum} prüft die KI wieder; was geprüft ist, bleibt.",
        { monat: budget.month, datum: budget.renews }),
      tight: (betrag, anzahl, stellen) => Texte.t("Das Budget dieses Monats reicht für etwa {anzahl} von {stellen}.", { anzahl, stellen }),
    };
  }

  const aboutText = (s, currency) =>
    Texte.t("Etwa {kosten} und {dauer}.", { kosten: money(s.kosten, currency), dauer: minutes(s.dauer_minuten) });

  /** The second line of the box above the list, as in design A3; empty without an estimate. */
  function estimateLine(s, apprenticeship = false) {
    if (!s || !s.anzahl) return "";
    const currency = currencyOf(s);
    const about = aboutText(s, currency);
    if (!withCredit(s)) return about;
    const words = creditWords(s);
    if (usedUp(s)) return `${about} ${words.usedUpLine}`;
    if (s.reicht_fuer !== null && s.reicht_fuer !== undefined) return `${about} ${words.enough(jobs(s.reicht_fuer, apprenticeship))}`;
    return `${about} ${words.after(money(s.danach, currency))}`;
  }

  /**
   * The line beside a button that sends one request (#293, #329): `estimateLine`, but over the credit it names what is
   * left instead of what stays. `usedUp` locks the button; over the credit it stays, the mediation then says what is
   * missing.
   */
  function costLine(estimate) {
    const used = usedUp(estimate);
    const enough = !withCredit(estimate) || estimate.kosten <= estimate.guthaben;
    if (used || enough) return { text: estimateLine(estimate), usedUp: used };
    const about = estimateLine({ ...estimate, guthaben: null });
    const left = money(estimate.guthaben, currencyOf(estimate));
    return { text: `${about} ${creditWords(estimate).left(left)}`, usedUp: used };
  }

  const estimateFailedText = reason => Texte.t("Die Schätzung fehlt: {grund}", { grund: reason });

  /** The sentence about the hits whose text is missing: the extension fetches it, or they stay without a grade. */
  function toLoadSentence(toLoad, apprenticeship, withExtension) {
    const Texte = texts();
    const stellen = jobs(toLoad, apprenticeship);
    if (withExtension) return Texte.t("Für {stellen} holt die Erweiterung zuerst den Text des Inserats.", { stellen });
    return toLoad === 1 ? Texte.t("Für {stellen} fehlt der Text. Ohne Erweiterung bleibt sie offen.", { stellen })
      : Texte.t("Für {stellen} fehlt der Text. Ohne Erweiterung bleiben sie offen.", { stellen });
  }

  function confirmationWarning(s, apprenticeship, words) {
    if (usedUp(s)) return words.usedUpWarning;
    if (!withCredit(s) || s.reicht_fuer === null || s.reicht_fuer === undefined) return "";
    const tight = words.tight(money(s.guthaben, currencyOf(s)), s.reicht_fuer, jobs(s.anzahl, apprenticeship));
    return `${tight} ${Texte.t("Ist es aufgebraucht, hält die Prüfung an; was geprüft ist, bleibt.")}`;
  }

  function notLoadableTitle(without, apprenticeship) {
    if (!without) return "";
    const stellen = jobs(without, apprenticeship);
    return without === 1 ? Texte.t("{stellen} ohne Text bleibt offen:", { stellen })
      : Texte.t("{stellen} ohne Text bleiben offen:", { stellen });
  }

  /** What the question before the run says; `withExtension`: the extension answered, so it can load missing texts. */
  function confirmation(s, apprenticeship, withExtension) {
    const Texte = texts();
    const currency = currencyOf(s);
    const stellen = jobs(s.anzahl, apprenticeship);
    const sentences = [Texte.t("Die KI prüft {stellen}, die noch keine Note haben.", { stellen }),
      Texte.t("Das kostet etwa {kosten} und dauert etwa {dauer}.", { kosten: money(s.kosten, currency), dauer: minutes(s.dauer_minuten) })];
    const words = creditWords(s);
    if (withCredit(s)) sentences.push(words.leftThen(money(s.guthaben, currency), money(s.danach, currency)));
    if (s.laden.length) sentences.push(toLoadSentence(s.laden.length, apprenticeship, withExtension));
    return {
      title: Texte.t("{stellen} prüfen?", { stellen }), sentences, warning: confirmationWarning(s, apprenticeship, words),
      notLoadableTitle: notLoadableTitle(s.nicht_ladbar.length, apprenticeship),
      notLoadable: s.nicht_ladbar.map(t => Texte.t("{stelle}: {grund}", { stelle: [t.stelle, t.firma].filter(Boolean).join(", "), grund: t.grund })),
    };
  }

  /** The message after a run; `rest` hits are still without a grade, also when the credit ended the run. */
  function schlussText(stand, rest, currency = "USD") {
    const Texte = texts();
    const teile = [Texte.t("{bewertet} von {von} Treffern bewertet", { bewertet: stand.bewertet, von: stand.von })];
    if (stand.offen.length) {
      teile.push(Texte.t("{anzahl} ohne brauchbare Antwort, die lassen sich einzeln nochmals versuchen", { anzahl: stand.offen.length }));
    }
    if (stand.ohneText) teile.push(Texte.t("{anzahl} ohne Inseratstext", { anzahl: stand.ohneText }));
    if (stand.gestoppt) teile.push(Texte.t("angehalten"));
    if (rest) teile.push(Texte.t("noch {anzahl} offen", { anzahl: rest }));
    return Texte.t("{teile}. Kosten: {kosten}.", { teile: teile.join(", "), kosten: money(stand.kosten, currency) });
  }

  /** The grades of the second look, alone, as „einzeln Note 5.“ says them (one, two or three of them). */
  function einzelnText(noten) {
    const Texte = texts();
    const [eins, zwei, drei] = noten;
    if (noten.length === 1) return Texte.t("Nachgeprüft: einzeln Note {eins}.", { eins });
    if (noten.length === 2) return Texte.t("Nachgeprüft: einzeln Noten {eins} und {zwei}, es zählt die tiefere.", { eins, zwei });
    return Texte.t("Nachgeprüft: einzeln Noten {eins}, {zwei} und {drei}, es zählt die mittlere.", { eins, zwei, drei });
  }

  /** What the details say about the second look at a good grade (MIN-389); empty when there was none. */
  function nachpruefungText(bewertung, notenText) {
    const pruefung = bewertung?.nachpruefung;
    if (!pruefung) return "";
    const Texte = texts();
    const paket = pruefung.im_paket ?? null;
    if (pruefung.noten.length <= (paket === null ? 1 : 0)) {
      return Texte.t("Die Nachprüfung war nicht möglich, die Note kann abweichen. „Neu bewerten“ versucht es nochmals.");
    }
    const einzeln = einzelnText(pruefung.noten.map(notenText));
    return paket === null ? einzeln : `${einzeln} ${Texte.t("Im Paket zuerst: Note {note}.", { note: notenText(paket) })}`;
  }

  /** The choice on the page for the offers of the plan (MIN-373). */
  function wahlAus(angebote) {
    if (angebote.length > 1) return "beides";
    return angebote[0] || "lehrstelle";
  }

  /** The label of the search button for the offers of the plan. */
  function sucheText(angebote) {
    const Texte = texts();
    const texte = { lehrstelle: () => Texte.t("Lehrstellen suchen"), schnupperlehre: () => Texte.t("Schnupperlehren suchen"),
      beides: () => Texte.t("Lehrstellen und Schnupperlehren suchen") };
    return texte[wahlAus(angebote)]();
  }

  /**
   * The message on Suche einstellen after the choice changed. Suche einstellen cut „ suchen“ off sucheText before
   * (#421); a translated label has no such ending, so each choice has its own sentence.
   */
  function gesuchtText(angebote) {
    const Texte = texts();
    const texte = { lehrstelle: () => Texte.t("Gesucht wird: Lehrstellen."), schnupperlehre: () => Texte.t("Gesucht wird: Schnupperlehren."),
      beides: () => Texte.t("Gesucht wird: Lehrstellen und Schnupperlehren.") };
    return texte[wahlAus(angebote)]();
  }

  const istSchnupperlehre = t => t.art === "Schnupperlehre";

  function beideArten(treffer) {
    return treffer.some(istSchnupperlehre) && treffer.some(t => !istSchnupperlehre(t));
  }

  /** Hits of one kind; empty means all. Hits saved before MIN-373 have no kind and are apprenticeships. */
  function nachArt(treffer, art) {
    if (!art) return treffer;
    return treffer.filter(t => istSchnupperlehre(t) === (art === "Schnupperlehre"));
  }

  /** How long the page waits for word of a running search before it asks the extension for its status (#142). */
  const STILLE_MS = 20000;
  const keinLauf = () =>
    Texte.t("Die Erweiterung hat keine Suche am Laufen. Bitte nochmals „Jetzt suchen“ drücken, sonst die Seite neu laden.");

  /**
   * The run the page follows after asking the extension. `seit` is when the page began to wait: a run that ended
   * before is an older one, so this search did not start.
   */
  function laufNachStatus(antwort, seit) {
    const lauf = antwort && antwort.lauf;
    if (lauf && (lauf.zustand === "laeuft" || (lauf.beginn || "") >= seit)) return lauf;
    if (!lauf && antwort && antwort.fehler) return { zustand: "fehler", fehler: antwort.fehler };
    return { zustand: "fehler", fehler: keinLauf() };
  }

  // The tabs of Stellen (G56) by the address: /treffer#in-bewerbungen shows the hits taken over, the page Firmen links
  // there. The tab was „Gemerkt“ before #374; #gemerkt stays as an alias, so older links and bookmarks still lead there.
  const REITER = { neu: "neu", "in-bewerbungen": "uebernommen", verworfen: "verworfen" };
  const ALIAS = { gemerkt: "in-bewerbungen" };

  /** Which hits a hash like „#in-bewerbungen“ shows; anything else shows the new ones. */
  function reiterAus(hash) {
    const raw = String(hash || "").replace(/^#/, "");
    const name = Object.hasOwn(ALIAS, raw) ? ALIAS[raw] : raw;
    return Object.hasOwn(REITER, name) ? REITER[name] : "neu";
  }

  /** The hash of a state of the hits, the reverse of reiterAus. */
  function reiterName(zustand) {
    return Object.keys(REITER).find(name => REITER[name] === zustand) || "neu";
  }

  // #373: a hit taken over carries the stage of its application as `stand`, null once the application is gone.
  // Finished is what the view „Abgeschlossen“ on Bewerbungen shows, or deleted; a hit without word stays open.
  const uebersicht = () => (typeof module !== "undefined" ? require("./uebersicht-logik.js") : global.UebersichtLogik);

  function istAbgeschlossen(treffer) {
    if (treffer.zustand !== "uebernommen" || treffer.stand === undefined) return false;
    return treffer.stand === null || uebersicht().ABGESCHLOSSEN.includes(treffer.stand);
  }

  /** The number on a tab: the hits it shows without „Anzeigen“, so finished ones leave it out. */
  function reiterZahl(treffer, zustand) {
    return treffer.filter(t => t.zustand === zustand && !istAbgeschlossen(t)).length;
  }

  /** The badge of a hit taken over, { status, text } for .marke-status, or null without word from the app.
   * `statusName` is Texte.statusName, so an apprenticeship's interview reads „Einladung“. */
  function standMarke(treffer, statusName) {
    if (treffer.zustand !== "uebernommen" || treffer.stand === undefined) return null;
    if (treffer.stand === null) return { status: "geloescht", text: Texte.t("Nicht mehr unter Bewerbungen") };
    return { status: treffer.stand, text: statusName(treffer.stand) };
  }

  /** „Abgeschlossen: 1 Zusage, 3 Absagen, 2 verworfen.“ for the finished hits, in the order of Bewerbungen; "" without. */
  function abgeschlossenText(fertig) {
    const Texte = texts();
    const { ABGESCHLOSSEN_WORT, abgeschlossenTeil } = uebersicht();
    const anzahl = stand => fertig.filter(t => t.stand === stand).length;
    const teile = [
      ...Object.keys(ABGESCHLOSSEN_WORT).filter(anzahl).map(stand => abgeschlossenTeil(stand, anzahl(stand))),
      anzahl(null) ? Texte.t("{anzahl} nicht mehr unter Bewerbungen", { anzahl: anzahl(null) }) : "",
    ].filter(Boolean);
    return teile.length ? Texte.t("Abgeschlossen: {teile}.", { teile: teile.join(", ") }) : "";
  }

  /** The line above the list that names the hits without a grade (G44). */
  function offenText(anzahl, lehrstelle) {
    const Texte = texts();
    if (lehrstelle) {
      return anzahl === 1 ? Texte.t("1 Lehrstelle ist noch nicht geprüft.")
        : Texte.t("{anzahl} Lehrstellen sind noch nicht geprüft.", { anzahl });
    }
    return anzahl === 1 ? Texte.t("1 Stelle ist noch nicht geprüft.") : Texte.t("{anzahl} Stellen sind noch nicht geprüft.", { anzahl });
  }

  /** Why a hit has no ad text and how to get it (G37), as the notice in the details shows it; null when it has one.
   * Reason and way come worded from the app (missing_ads.py). */
  function fehlenderText(treffer) {
    const fehlt = treffer.ohne_text ? treffer.text_fehlt : null;
    return fehlt ? { titel: Texte.t("Inseratstext fehlt"), text: [fehlt.grund, fehlt.weg].filter(Boolean).join(" ") } : null;
  }

  const logik = { reiterAus, reiterName, istAbgeschlossen, reiterZahl, standMarke, abgeschlossenText, offenText, STILLE_MS, laufNachStatus, sucheText, gesuchtText, wahlAus, beideArten, nachArt, istSchnupperlehre, zuBewerten, alleBewertet, sortiert, gueltigeSortierung, pakete, bewerteAlle, pruefSchritt, inseratSchritt, estimateLine, costLine, estimateFailedText, confirmation, schlussText, nachpruefungText, fehlenderText, money, minutes, seconds };
  if (typeof module !== "undefined") module.exports = logik;
  else global.TrefferLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
