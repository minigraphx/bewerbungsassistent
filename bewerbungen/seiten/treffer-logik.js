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
    const erste = stand.bewertet + 1;
    const welche = gruppe.length > 1 ? `Stellen ${erste} bis ${erste + gruppe.length - 1}` : `Stelle ${erste}`;
    const dauer = sekunden >= SEKUNDEN_AB ? `, seit ${seconds(sekunden)}` : "";
    return `${welche} von ${stand.von} prüfen${dauer} …`;
  }

  /** „Inserat 4 von 9 holen …“ while the extension loads the missing ads; empty before it says how many. */
  function inseratSchritt(stand) {
    return stand.von ? `Inserat ${stand.fertig + 1} von ${stand.von} holen …` : "";
  }

  // „Alle prüfen“ (G44, #209): the words around the estimate of GET /api/suche/alle-pruefen, in its currency: CHF
  // with the mediation and its budget (G46, G98), USD with an own key.
  const currencyOf = s => (s && s.waehrung) || "USD";
  // A no-break space between number and unit (#336): at 375 px «1» stood at the end of a line and «Minute» began the
  // next. Screen readers read it as a space, so the spoken words stay the same.
  const NBSP = "\u00a0";
  const money = (amount, currency) => `${currency}${NBSP}${Number(amount).toFixed(2)}`;
  const minutes = n => `${n}${NBSP}${n === 1 ? "Minute" : "Minuten"}`;
  const seconds = n => `${n}${NBSP}${n === 1 ? "Sekunde" : "Sekunden"}`;
  const jobs = (n, apprenticeship) => {
    const word = apprenticeship ? ["Lehrstelle", "Lehrstellen"] : ["Stelle", "Stellen"];
    return `${n} ${n === 1 ? word[0] : word[1]}`;
  };
  const withCredit = s => typeof s.guthaben === "number";
  const usedUp = s => withCredit(s) && s.guthaben <= 0;
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);

  // The budget of the month (G98) when the estimate names its renewal; otherwise the one-time credit of G80.
  function creditWords(s) {
    const budget = texts().budgetMonth(s);
    if (!budget) {
      return {
        pool: "Guthaben", enough: "Das Guthaben reicht", usedUpLine: "Das Guthaben ist aufgebraucht: neuen Code anfordern.",
        usedUpWarning: "Das Guthaben ist aufgebraucht. Mit einem neuen Einladungscode geht es weiter; ohne prüft die KI keine Stelle.",
        tight: left => `Das Guthaben von ${left} reicht`,
      };
    }
    return {
      pool: "Budget", enough: "Das Budget dieses Monats reicht",
      usedUpLine: `Das KI-Budget ist aufgebraucht, wieder ab ${budget.renews}.`,
      usedUpWarning: `Das KI-Budget für ${budget.month} ist aufgebraucht. Ab ${budget.renews} prüft die KI wieder; was geprüft ist, bleibt.`,
      tight: () => "Das Budget dieses Monats reicht",
    };
  }

  /** The second line of the box above the list, as in design A3; empty without an estimate. */
  function estimateLine(s, apprenticeship = false) {
    if (!s || !s.anzahl) return "";
    const currency = currencyOf(s);
    const about = `Etwa ${money(s.kosten, currency)} und ${minutes(s.dauer_minuten)}.`;
    if (!withCredit(s)) return about;
    const words = creditWords(s);
    if (usedUp(s)) return `${about} ${words.usedUpLine}`;
    if (s.reicht_fuer !== null && s.reicht_fuer !== undefined) return `${about} ${words.enough} für etwa ${jobs(s.reicht_fuer, apprenticeship)}.`;
    return `${about} Danach bleiben ${money(s.danach, currency)} im ${words.pool}.`;
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
    return { text: `${about} Im ${creditWords(estimate).pool} sind noch ${left}, das reicht vielleicht nicht.`, usedUp: used };
  }

  const estimateFailedText = reason => `Die Schätzung fehlt: ${reason}`;

  /** What the question before the run says; `withExtension`: the extension answered, so it can load missing texts. */
  function confirmation(s, apprenticeship, withExtension) {
    const currency = currencyOf(s);
    const sentences = [`Die KI prüft ${jobs(s.anzahl, apprenticeship)}, die noch keine Note haben.`,
      `Das kostet etwa ${money(s.kosten, currency)} und dauert etwa ${minutes(s.dauer_minuten)}.`];
    const words = creditWords(s);
    if (withCredit(s)) sentences.push(`Im ${words.pool} sind noch ${money(s.guthaben, currency)}, danach etwa ${money(s.danach, currency)}.`);
    const toLoad = s.laden.length;
    if (toLoad) {
      sentences.push(withExtension ? `Für ${jobs(toLoad, apprenticeship)} holt die Erweiterung zuerst den Text des Inserats.`
        : `Für ${jobs(toLoad, apprenticeship)} fehlt der Text. Ohne Erweiterung ${toLoad === 1 ? "bleibt sie" : "bleiben sie"} offen.`);
    }
    const tight = withCredit(s) && s.reicht_fuer !== null && s.reicht_fuer !== undefined;
    const warning = usedUp(s) ? words.usedUpWarning : tight ? `${words.tight(money(s.guthaben, currency))} für etwa ${s.reicht_fuer} von ${jobs(s.anzahl, apprenticeship)}. `
      + "Ist es aufgebraucht, hält die Prüfung an; was geprüft ist, bleibt." : "";
    const without = s.nicht_ladbar.length;
    return {
      title: `${jobs(s.anzahl, apprenticeship)} prüfen?`, sentences, warning,
      notLoadableTitle: without ? `${jobs(without, apprenticeship)} ohne Text ${without === 1 ? "bleibt" : "bleiben"} offen:` : "",
      notLoadable: s.nicht_ladbar.map(t => `${[t.stelle, t.firma].filter(Boolean).join(", ")}: ${t.grund}`),
    };
  }

  /** The message after a run; `rest` hits are still without a grade, also when the credit ended the run. */
  function schlussText(stand, rest, currency = "USD") {
    const teile = [`${stand.bewertet} von ${stand.von} Treffern bewertet`];
    if (stand.offen.length) teile.push(`${stand.offen.length} ohne brauchbare Antwort, die lassen sich einzeln nochmals versuchen`);
    if (stand.ohneText) teile.push(`${stand.ohneText} ohne Inseratstext`);
    if (stand.gestoppt) teile.push("angehalten");
    if (rest) teile.push(`noch ${rest} offen`);
    return `${teile.join(", ")}. Kosten: ${money(stand.kosten, currency)}.`;
  }

  /** What the details say about the second look at a good grade (MIN-389); empty when there was none. */
  function nachpruefungText(bewertung, notenText) {
    const pruefung = bewertung?.nachpruefung;
    if (!pruefung) return "";
    const paket = pruefung.im_paket ?? null;
    if (pruefung.noten.length <= (paket === null ? 1 : 0)) {
      return "Die Nachprüfung war nicht möglich, die Note kann abweichen. „Neu bewerten“ versucht es nochmals.";
    }
    const noten = pruefung.noten.map(notenText);
    const teile = { 1: `einzeln Note ${noten[0]}.`,
      2: `einzeln Noten ${noten[0]} und ${noten[1]}, es zählt die tiefere.`,
      3: `einzeln Noten ${noten[0]}, ${noten[1]} und ${noten[2]}, es zählt die mittlere.` };
    const zuerst = paket === null ? "" : ` Im Paket zuerst: Note ${notenText(paket)}.`;
    return `Nachgeprüft: ${teile[noten.length]}${zuerst}`;
  }

  const SUCHE_TEXTE = { lehrstelle: "Lehrstellen suchen", schnupperlehre: "Schnupperlehren suchen",
    beides: "Lehrstellen und Schnupperlehren suchen" };

  /** The choice on the page for the offers of the plan (MIN-373). */
  function wahlAus(angebote) {
    if (angebote.length > 1) return "beides";
    return angebote[0] || "lehrstelle";
  }

  function sucheText(angebote) {
    return SUCHE_TEXTE[wahlAus(angebote)];
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
  const KEIN_LAUF = "Die Erweiterung hat keine Suche am Laufen. Bitte nochmals „Jetzt suchen“ drücken, sonst die Seite neu laden.";

  /**
   * The run the page follows after asking the extension. `seit` is when the page began to wait: a run that ended
   * before is an older one, so this search did not start.
   */
  function laufNachStatus(antwort, seit) {
    const lauf = antwort && antwort.lauf;
    if (lauf && (lauf.zustand === "laeuft" || (lauf.beginn || "") >= seit)) return lauf;
    if (!lauf && antwort && antwort.fehler) return { zustand: "fehler", fehler: antwort.fehler };
    return { zustand: "fehler", fehler: KEIN_LAUF };
  }

  // The tabs of Stellen (G56) by the address: /treffer#gemerkt shows the saved hits, the page Firmen links there.
  const REITER = { neu: "neu", gemerkt: "uebernommen", verworfen: "verworfen" };

  /** Which hits a hash like „#gemerkt“ shows; anything else shows the new ones. */
  function reiterAus(hash) {
    const name = String(hash || "").replace(/^#/, "");
    return Object.hasOwn(REITER, name) ? REITER[name] : "neu";
  }

  /** The hash of a state of the hits, the reverse of reiterAus. */
  function reiterName(zustand) {
    return Object.keys(REITER).find(name => REITER[name] === zustand) || "neu";
  }

  /** The line above the list that names the hits without a grade (G44). */
  function offenText(anzahl, lehrstelle) {
    const wort = lehrstelle ? ["Lehrstelle", "Lehrstellen"] : ["Stelle", "Stellen"];
    return anzahl === 1 ? `1 ${wort[0]} ist noch nicht geprüft.` : `${anzahl} ${wort[1]} sind noch nicht geprüft.`;
  }

  /** Why a hit has no ad text and how to get it (G37), as the notice in the details shows it; null when it has one. */
  function fehlenderText(treffer) {
    const fehlt = treffer.ohne_text ? treffer.text_fehlt : null;
    return fehlt ? { titel: "Inseratstext fehlt", text: [fehlt.grund, fehlt.weg].filter(Boolean).join(" ") } : null;
  }

  const logik = { reiterAus, reiterName, offenText, STILLE_MS, laufNachStatus, sucheText, wahlAus, beideArten, nachArt, istSchnupperlehre, zuBewerten, alleBewertet, sortiert, gueltigeSortierung, pakete, bewerteAlle, pruefSchritt, inseratSchritt, estimateLine, costLine, estimateFailedText, confirmation, schlussText, nachpruefungText, fehlenderText, money, minutes, seconds };
  if (typeof module !== "undefined") module.exports = logik;
  else global.TrefferLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
