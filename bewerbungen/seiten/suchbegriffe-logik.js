"use strict";
// Checking the search terms (#210, G45), without DOM: the texts in Sie and du, labels that count, the marks of a change.
// Every number comes from the app; the page only words it. Jobs only for now, so there are two sets of texts.
(root => {
  const TEXTE = {
    sie: {
      satz: "Die KI schlägt vor, Sie entscheiden. Am Suchprofil ändert sich erst etwas, wenn Sie übernehmen.",
      wasGeht: "An die KI gehen Ihr Suchprofil und Ihr Lebenslauf mit Platzhaltern für Name, Adresse und Kontakte sowie Titel und Note der eingeschätzten Treffer, ohne Inseratstexte.",
      hinweisNachsatz: "Die KI kann bessere Begriffe vorschlagen. Geändert wird nur, was Sie übernehmen.",
      warten: "KI prüft Ihre Suchbegriffe",
      wartenNotiz: "Meist unter 30\u00a0Sekunden. Am Suchprofil ändert sich nichts, bis Sie etwas übernehmen.",
      gesehen: (treffer, seit) => `Die KI hat Ihr Suchprofil, Ihren Lebenslauf${treffer ? ` und ${treffer} Treffer${seit ? ` seit dem ${datum(seit)}` : ""}` : ""} angesehen. Geändert wird nur, was angehakt ist.`,
      passt: "Ihre Suchbegriffe passen. Die KI schlägt keine Änderung vor.",
      passtNotiz: "Kein Begriff lässt auffällig viele unpassende Treffer durch, und was in Ihrem Lebenslauf steht, wird schon gesucht.",
      fuss: "Ein Vorschlag, kein Urteil. Die KI kann sich irren. Geändert wird nur, was Sie übernehmen.",
      andersHilfe: "Die KI überarbeitet den Vorschlag. Ihr Text geht mit dem Vorschlag an die KI.",
      nachHinweis: "nach Ihrem Hinweis",
      ihrHinweis: "Ihr Hinweis",
      einwilligung: "Bevor die KI Suchbegriffe vorschlägt, braucht es Ihre Einwilligung.",
      bisherige: "Alle sind eingeschaltet. Was Sie ausschalten, entfällt beim Übernehmen.",
    },
    du: {
      satz: "Die KI schlägt vor, du entscheidest. Am Suchprofil ändert sich erst etwas, wenn du übernimmst.",
      wasGeht: "An die KI gehen dein Suchprofil und dein Lebenslauf mit Platzhaltern für Name, Adresse und Kontakte sowie Titel und Note der eingeschätzten Treffer, ohne Inseratstexte.",
      hinweisNachsatz: "Die KI kann bessere Begriffe vorschlagen. Geändert wird nur, was du übernimmst.",
      warten: "KI prüft deine Suchbegriffe",
      wartenNotiz: "Meist unter 30\u00a0Sekunden. Am Suchprofil ändert sich nichts, bis du etwas übernimmst.",
      gesehen: (treffer, seit) => `Die KI hat dein Suchprofil, deinen Lebenslauf${treffer ? ` und ${treffer} Treffer${seit ? ` seit dem ${datum(seit)}` : ""}` : ""} angesehen. Geändert wird nur, was angehakt ist.`,
      passt: "Deine Suchbegriffe passen. Die KI schlägt keine Änderung vor.",
      passtNotiz: "Kein Begriff lässt auffällig viele unpassende Treffer durch, und was in deinem Lebenslauf steht, wird schon gesucht.",
      fuss: "Ein Vorschlag, kein Urteil. Die KI kann sich irren. Geändert wird nur, was du übernimmst.",
      andersHilfe: "Die KI überarbeitet den Vorschlag. Dein Text geht mit dem Vorschlag an die KI.",
      nachHinweis: "nach deinem Hinweis",
      ihrHinweis: "Dein Hinweis",
      einwilligung: "Bevor die KI Suchbegriffe vorschlägt, braucht es deine Einwilligung.",
      bisherige: "Alle sind eingeschaltet. Was du ausschaltest, entfällt beim Übernehmen.",
    },
  };
  const BELOW = 4;

  /** The texts for the set of the page; „stelle-du“ speaks informally, everything else formally. */
  const texte = satz => (satz === "stelle-du" ? TEXTE.du : TEXTE.sie);

  function datum(iso) {
    const [jahr, monat, tag] = String(iso).split("-");
    return tag ? `${Number(tag)}.${Number(monat)}.${jahr}` : String(iso);
  }

  /** Never less than a cent: a call that costs less is still not free. CHF with the mediation (G46), counted 1:1. */
  const geld = (betrag, waehrung = "USD") => `${waehrung}\u00a0${Math.max(Number(betrag) || 0, 0.01).toFixed(2)}`;

  const CHECK_PAGE = "/suchbegriffe";

  /**
   * The link to the check, locked while the credit is used up (#329, #334): opening the check sends at once. Locked, it
   * keeps tabindex 0, since a link without href leaves the tab order and its reason would go unheard. Only the given
   * element changes; `describedBy` names the line with the reason where the page does not already.
   */
  function lockCheckLink(link, locked, describedBy) {
    const lock = { role: "link", "aria-disabled": "true", tabindex: "0",
      ...(describedBy ? { "aria-describedby": describedBy } : {}) };
    if (locked) {
      link.removeAttribute("href");
      for (const [name, value] of Object.entries(lock)) link.setAttribute(name, value);
      return;
    }
    link.setAttribute("href", CHECK_PAGE);
    for (const name of Object.keys(lock)) link.removeAttribute(name);
  }

  function hinweisText(beleg) {
    const beispiele = beleg.beispiele.length ? `, zum Beispiel ${beleg.beispiele.join(", ")}` : "";
    return `«${beleg.begriff}» im Titelfilter: ${beleg.anzahl} von ${beleg.alle} Treffern, ${beleg.unter} davon unter Note ${BELOW}${beispiele}.`;
  }

  const belegSatz = beleg => `${beleg.anzahl} von ${beleg.alle} Treffern kamen nur über «${beleg.begriff}» herein, ${beleg.unter} davon unter Note ${BELOW}.`;
  const belegBeispiele = beleg => (beleg.beispiele.length ? `Zum Beispiel: ${beleg.beispiele.join(", ")}` : "");
  const belegLink = beleg => `Diese ${beleg.anzahl} Treffer ansehen`;
  const belegAdresse = beleg => `/treffer#beleg=${encodeURIComponent(beleg.begriff)}`;
  /** Share of the bar, in per cent: all hits through the term, and those below 4 within them. */
  const balken = beleg => ({ anteil: beleg.alle ? Math.round((100 * beleg.anzahl) / beleg.alle) : 0,
    unter: beleg.anzahl ? Math.round((100 * beleg.unter) / beleg.anzahl) : 0 });

  /** The term from a link such as „#beleg=Engineer“, or null. */
  function belegAusAdresse(hash) {
    const gefunden = /^#beleg=(.+)$/.exec(hash || "");
    if (!gefunden) return null;
    try {
      return decodeURIComponent(gefunden[1]);
    } catch {
      return null;
    }
  }

  /** The heading as parts, which the page joins with «·» (#340); its accessible name then reads with a comma. */
  const kopfTeile = anzahl => ["Vorschlag der KI", anzahl === 1 ? "1 Änderung" : `${anzahl} Änderungen`];

  const viele = (anzahl, eins, mehr) => `${anzahl} ${anzahl === 1 ? eins : mehr}`;

  /** What changed, in the words of the review (#371): new terms and those that go, each only when there are some. */
  function uebernommen(neu, entfallen) {
    const teile = [neu ? `${viele(neu, "Begriff", "Begriffe")} neu` : "",
      entfallen ? `${neu ? entfallen : viele(entfallen, "Begriff", "Begriffe")} ${entfallen === 1 ? "entfällt" : "entfallen"}` : ""];
    return `Übernommen: ${teile.filter(Boolean).join(", ")}. Die nächste Suche sucht danach. Der bisherige Stand bleibt unter Entwürfe erhalten.`;
  }
  const RUECKGAENGIG_FERTIG = "Rückgängig gemacht. Es gilt wieder der Stand vor dem Vorschlag.";

  // One switch per term (#371, G102). The state is the terms in the result per area, as the app names them; the
  // app works out order and limits again from what the page sends.
  const BEREICHE = [["suchbegriffe", "Suchbegriffe"], ["positiv", "Titel enthält eines davon"], ["ausschluss", "Titel enthält keines davon"]];
  const SCHLUESSEL = { keywords: "suchbegriffe", positive: "positiv", exclude: "ausschluss" };
  const HAUPTKNOPF = "Auswahl übernehmen";
  const TEILWEISE = "Teilweise übernommen";
  const BISHERIGE_OBEN = "Begriffe, die eine Änderung oben betrifft, stehen dort.";
  const ZU_DEN_BISHERIGEN = "Zu den bisherigen Begriffen";
  const FREI = "Die Auswahl lässt sich übernehmen.";

  /** The chips of a change: what it removes („gone“), then what it adds („new“), each in the area of the change. */
  const chips = aenderung => [
    ...aenderung.entfaellt.map(begriff => ({ bereich: SCHLUESSEL[aenderung.bereich], begriff, art: "gone" })),
    ...aenderung.neu.map(begriff => ({ bereich: SCHLUESSEL[aenderung.bereich], begriff, art: "new" })),
  ];

  /** The current terms no change touches, per area in the order of the profile; an empty area is left out. */
  const bisherigeBereiche = bisherige => BEREICHE
    .map(([schluessel, name]) => ({ schluessel, name,
      chips: (bisherige[schluessel] || []).map(begriff => ({ bereich: schluessel, begriff, art: "kept" })) }))
    .filter(bereich => bereich.chips.length);

  const imErgebnis = (auswahl, { bereich, begriff }) => auswahl[bereich].includes(begriff);

  /** A removed term is on while it goes away; a new or current term while it is in the result. */
  const chipAn = (auswahl, chip) => imErgebnis(auswahl, chip) !== (chip.art === "gone");

  function mitBegriff(auswahl, { bereich, begriff }, drin) {
    const ohne = auswahl[bereich].filter(b => b !== begriff);
    return { ...auswahl, [bereich]: drin ? [...ohne, begriff] : ohne };
  }

  const schalteChip = (auswahl, chip, an) => mitBegriff(auswahl, chip, an !== (chip.art === "gone"));

  /** The word beside a chip, which carries its state: never colour alone. */
  function chipWort(chip, an) {
    if (chip.art === "new") return "neu";
    if (chip.art === "gone") return an ? "entfällt" : "bleibt";
    return an ? "" : "entfällt";
  }

  function karteStand(auswahl, aenderung) {
    const an = chips(aenderung).map(chip => chipAn(auswahl, chip));
    if (an.every(Boolean)) return "alle";
    return an.some(Boolean) ? "teilweise" : "keine";
  }

  const schalteKarte = (auswahl, aenderung, an) => chips(aenderung).reduce((stand, chip) => schalteChip(stand, chip, an), auswahl);

  /** Each area after the switches, and how many are over what it may hold (`erlaubt` from the app). */
  const zaehlung = (auswahl, erlaubt) => BEREICHE.map(([schluessel, name]) => ({ schluessel, name,
    anzahl: auswahl[schluessel].length, zuViel: Math.max(0, auswahl[schluessel].length - erlaubt[schluessel]) }));

  /** The legend of an area as parts, which the page joins with «·» (#340). */
  const legendeTeile = z => [z.name, `danach ${z.anzahl} eingeschaltet${z.zuViel ? `, ${z.zuViel} zu viel` : ""}`];

  const entfaelltZeile = liste => (liste.length ? `Entfällt: ${liste.join(", ")}` : "");

  /** The first area over what it may hold, by the app's count, or null. */
  const zuVielBereich = grenzen => (BEREICHE.find(([s]) => grenzen.zu_viel && grenzen.zu_viel[s] > 0) || [null])[0];

  function zuVielText(grenzen) {
    const schluessel = zuVielBereich(grenzen);
    if (!schluessel) return grenzen.gesperrt || "";
    const name = BEREICHE.find(([s]) => s === schluessel)[1];
    const anzahl = grenzen.zu_viel[schluessel];
    return schluessel === "suchbegriffe" ? `Noch ${viele(anzahl, "Suchbegriff", "Suchbegriffe")} zu viel`
      : `Noch ${viele(anzahl, "Begriff", "Begriffe")} zu viel in «${name}»`;
  }

  /** What the polite status says after an answer: only when the choice becomes blocked or free, or what is too many changes. */
  function ansage(vorher, nachher) {
    if (!vorher) return "";
    if (!nachher.gesperrt) return vorher.gesperrt ? FREI : "";
    const jetzt = zuVielText(nachher);
    return vorher.gesperrt && zuVielText(vorher) === jetzt ? "" : jetzt;
  }

  /** Roving focus within a group of chips: the index to move to, or null for a key the browser keeps. */
  function rovingZiel(taste, index, anzahl) {
    const ziele = { ArrowRight: index + 1, ArrowDown: index + 1, ArrowLeft: index - 1, ArrowUp: index - 1, Home: 0, End: anzahl - 1 };
    return taste in ziele ? Math.min(Math.max(ziele[taste], 0), anzahl - 1) : null;
  }

  /** The footer of the card as parts, which the page joins with «·» (#337): model, cost, date, and the rounds so far. */
  function fussTeile(vorschlag) {
    const bisher = vorschlag.runde > 1 ? `bisher ${geld(vorschlag.kosten_bisher, vorschlag.waehrung)}` : "";
    return [vorschlag.modell ? "Claude" : "", geld(vorschlag.kosten_usd, vorschlag.waehrung), datum(vorschlag.datum), bisher]
      .filter(Boolean);
  }

  /** The round line as parts (#340); the first proposal has none. */
  const rundeTeile = (vorschlag, satz) => (vorschlag.runde > 1 ? [`Vorschlag ${vorschlag.runde}`, texte(satz).nachHinweis] : []);

  /** The terms after the switches, as the app worked them out, each with „neu“ if it was not there before. */
  function endstand(jetzt, danach) {
    return BEREICHE.map(([schluessel, name]) => ({
      name,
      begriffe: danach[schluessel].map(begriff => ({ begriff, neu: !jetzt[schluessel].some(b => b.toLowerCase() === begriff.toLowerCase()) })),
    }));
  }

  const api = { texte, datum, geld, lockCheckLink, hinweisText, belegSatz, belegBeispiele, belegLink, belegAdresse, balken,
    belegAusAdresse, kopfTeile, uebernommen, RUECKGAENGIG_FERTIG, fussTeile, rundeTeile, endstand,
    HAUPTKNOPF, TEILWEISE, BISHERIGE_OBEN, ZU_DEN_BISHERIGEN, FREI, chips, bisherigeBereiche, chipAn, schalteChip, chipWort,
    karteStand, schalteKarte, zaehlung, legendeTeile, entfaelltZeile, zuVielBereich, ansage, rovingZiel };
  if (typeof module !== "undefined") module.exports = api;
  else root.SuchbegriffeLogik = api;
})(typeof window !== "undefined" ? window : globalThis);
