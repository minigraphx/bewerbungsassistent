"use strict";
// Checking the search terms (#210, G45), without DOM: the texts in Sie and du, labels that count, the marks of a change.
// Every number comes from the app; the page only words it. Jobs only for now, so there are two sets of texts. Texts in
// the app language through Texte.t (#421, tests/search_logic_languages.test.cjs); search terms, their areas' names in
// the profile («Nur …», «Nischen (ohne Ort suchen)») and hit titles are data and stay as they are.
(root => {
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : root.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte), text: (schluessel, satz, werte) => texts().text(schluessel, satz, werte) };

  /** „Die KI hat … angesehen.“: what the AI looked at, with the number of hits and since when when there are hits. */
  function gesehenSie(treffer, seit) {
    const Texte = texts();
    if (!treffer) return Texte.t("Die KI hat Ihr Suchprofil und Ihren Lebenslauf angesehen. Geändert wird nur, was eingeschaltet ist.");
    const werte = { anzahl: treffer, datum: seit ? datum(seit) : "" };
    if (treffer === 1) {
      return seit ? Texte.t("Die KI hat Ihr Suchprofil, Ihren Lebenslauf und 1 Treffer seit dem {datum} angesehen. Geändert wird nur, was eingeschaltet ist.", werte)
        : Texte.t("Die KI hat Ihr Suchprofil, Ihren Lebenslauf und 1 Treffer angesehen. Geändert wird nur, was eingeschaltet ist.");
    }
    return seit ? Texte.t("Die KI hat Ihr Suchprofil, Ihren Lebenslauf und {anzahl} Treffer seit dem {datum} angesehen. Geändert wird nur, was eingeschaltet ist.", werte)
      : Texte.t("Die KI hat Ihr Suchprofil, Ihren Lebenslauf und {anzahl} Treffer angesehen. Geändert wird nur, was eingeschaltet ist.", werte);
  }

  function gesehenDu(treffer, seit) {
    const Texte = texts();
    if (!treffer) return Texte.t("Die KI hat dein Suchprofil und deinen Lebenslauf angesehen. Geändert wird nur, was eingeschaltet ist.");
    const werte = { anzahl: treffer, datum: seit ? datum(seit) : "" };
    if (treffer === 1) {
      return seit ? Texte.t("Die KI hat dein Suchprofil, deinen Lebenslauf und 1 Treffer seit dem {datum} angesehen. Geändert wird nur, was eingeschaltet ist.", werte)
        : Texte.t("Die KI hat dein Suchprofil, deinen Lebenslauf und 1 Treffer angesehen. Geändert wird nur, was eingeschaltet ist.");
    }
    return seit ? Texte.t("Die KI hat dein Suchprofil, deinen Lebenslauf und {anzahl} Treffer seit dem {datum} angesehen. Geändert wird nur, was eingeschaltet ist.", werte)
      : Texte.t("Die KI hat dein Suchprofil, deinen Lebenslauf und {anzahl} Treffer angesehen. Geändert wird nur, was eingeschaltet ist.", werte);
  }

  function texteSie() {
    const Texte = texts();
    return {
      satz: Texte.t("Die KI schlägt vor, Sie entscheiden. Am Suchprofil ändert sich erst etwas, wenn Sie übernehmen."),
      wasGeht: Texte.t("An die KI gehen Ihr Suchprofil und Ihr Lebenslauf mit Platzhaltern für Name, Adresse und Kontakte sowie Titel und Note der eingeschätzten Treffer, Titel aussortierter Stellen und Zahlen zu jedem Suchbegriff, ohne Inseratstexte."),
      hinweisNachsatz: Texte.t("Die KI kann bessere Begriffe vorschlagen. Geändert wird nur, was Sie übernehmen."),
      warten: Texte.t("KI prüft Ihre Suchbegriffe"),
      wartenNotiz: Texte.t("Meist unter 30\u00a0Sekunden. Am Suchprofil ändert sich nichts, bis Sie etwas übernehmen."),
      gesehen: gesehenSie,
      passt: Texte.t("Ihre Suchbegriffe passen. Die KI schlägt keine Änderung vor."),
      passtNotiz: Texte.t("Kein Begriff lässt auffällig viele unpassende Treffer durch, und was in Ihrem Lebenslauf steht, wird schon gesucht."),
      fuss: Texte.t("Ein Vorschlag, kein Urteil. Die KI kann sich irren. Geändert wird nur, was Sie übernehmen."),
      andersHilfe: Texte.t("Die KI überarbeitet den Vorschlag. Ihr Text geht mit dem Vorschlag an die KI."),
      nachHinweis: Texte.t("nach Ihrem Hinweis"),
      ihrHinweis: Texte.t("Ihr Hinweis"),
      einwilligung: Texte.t("Bevor die KI Suchbegriffe vorschlägt, braucht es Ihre Einwilligung."),
      bisherige: Texte.t("Alle sind eingeschaltet. Was Sie ausschalten, entfällt beim Übernehmen."),
    };
  }

  function texteDu() {
    const Texte = texts();
    return {
      satz: Texte.t("Die KI schlägt vor, du entscheidest. Am Suchprofil ändert sich erst etwas, wenn du übernimmst."),
      wasGeht: Texte.t("An die KI gehen dein Suchprofil und dein Lebenslauf mit Platzhaltern für Name, Adresse und Kontakte sowie Titel und Note der eingeschätzten Treffer, Titel aussortierter Stellen und Zahlen zu jedem Suchbegriff, ohne Inseratstexte."),
      hinweisNachsatz: Texte.t("Die KI kann bessere Begriffe vorschlagen. Geändert wird nur, was du übernimmst."),
      warten: Texte.t("KI prüft deine Suchbegriffe"),
      wartenNotiz: Texte.t("Meist unter 30\u00a0Sekunden. Am Suchprofil ändert sich nichts, bis du etwas übernimmst."),
      gesehen: gesehenDu,
      passt: Texte.t("Deine Suchbegriffe passen. Die KI schlägt keine Änderung vor."),
      passtNotiz: Texte.t("Kein Begriff lässt auffällig viele unpassende Treffer durch, und was in deinem Lebenslauf steht, wird schon gesucht."),
      fuss: Texte.t("Ein Vorschlag, kein Urteil. Die KI kann sich irren. Geändert wird nur, was du übernimmst."),
      andersHilfe: Texte.t("Die KI überarbeitet den Vorschlag. Dein Text geht mit dem Vorschlag an die KI."),
      nachHinweis: Texte.t("nach deinem Hinweis"),
      ihrHinweis: Texte.t("Dein Hinweis"),
      einwilligung: Texte.t("Bevor die KI Suchbegriffe vorschlägt, braucht es deine Einwilligung."),
      bisherige: Texte.t("Alle sind eingeschaltet. Was du ausschaltest, entfällt beim Übernehmen."),
    };
  }
  const BELOW = 4;

  /** The texts for the set of the page in the app language; „stelle-du“ speaks informally, everything else formally. */
  const texte = satz => (satz === "stelle-du" ? texteDu() : texteSie());

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

  /** The notice above the hits: a term of the title filter that lets many poor hits in. „Titelfilter“ is the name of
   * the section in the search profile, so French and English quote it in German. */
  function hinweisText(beleg) {
    const werte = { begriff: beleg.begriff, anzahl: beleg.anzahl, alle: beleg.alle, unter: beleg.unter, note: BELOW,
                    beispiele: beleg.beispiele.join(", ") };
    return beleg.beispiele.length
      ? Texte.t("«{begriff}» im Titelfilter: {anzahl} von {alle} Treffern, {unter} davon unter Note {note}, zum Beispiel {beispiele}.", werte)
      : Texte.t("«{begriff}» im Titelfilter: {anzahl} von {alle} Treffern, {unter} davon unter Note {note}.", werte);
  }

  const belegSatz = beleg => Texte.t("{anzahl} von {alle} Treffern kamen nur über «{begriff}» herein, {unter} davon unter Note {note}.",
    { anzahl: beleg.anzahl, alle: beleg.alle, begriff: beleg.begriff, unter: beleg.unter, note: BELOW });
  const belegBeispiele = beleg => (beleg.beispiele.length ? Texte.t("Zum Beispiel: {beispiele}", { beispiele: beleg.beispiele.join(", ") }) : "");
  const belegLink = beleg => (beleg.anzahl === 1 ? Texte.t("Diese 1 Treffer ansehen")
    : Texte.t("Diese {anzahl} Treffer ansehen", { anzahl: beleg.anzahl }));
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
  const kopfTeile = anzahl => [Texte.t("Vorschlag der KI"),
    anzahl === 1 ? Texte.t("1 Änderung") : Texte.t("{anzahl} Änderungen", { anzahl })];

  // The parts of „Übernommen: …“ (#371): the first part names the terms, the ones after it only count.
  const neuTeil = n => (n === 1 ? Texte.t("1 Begriff neu") : Texte.t("{anzahl} Begriffe neu", { anzahl: n }));
  function entfallenTeil(n, mitBegriff) {
    const Texte = texts();
    if (mitBegriff) return n === 1 ? Texte.t("1 Begriff entfällt") : Texte.t("{anzahl} Begriffe entfallen", { anzahl: n });
    return n === 1 ? Texte.t("1 entfällt") : Texte.t("{anzahl} entfallen", { anzahl: n });
  }
  function verschobenTeil(n, mitBegriff) {
    const Texte = texts();
    if (mitBegriff) return n === 1 ? Texte.t("1 Begriff verschoben") : Texte.t("{anzahl} Begriffe verschoben", { anzahl: n });
    return n === 1 ? Texte.t("1 verschoben") : Texte.t("{anzahl} verschoben", { anzahl: n });
  }

  /**
   * What changed, in the words of the review (#371): new terms, those that go and those moved to the niches or onto
   * portals (G108), each only when there are some.
   */
  function uebernommen(neu, entfallen, verschoben = 0) {
    const teile = [neu ? neuTeil(neu) : "", entfallen ? entfallenTeil(entfallen, !neu) : "",
      verschoben ? verschobenTeil(verschoben, !(neu || entfallen)) : ""];
    return Texte.t("Übernommen: {teile}. Die nächste Suche sucht danach. Der bisherige Stand bleibt unter Entwürfe erhalten.",
      { teile: teile.filter(Boolean).join(", ") });
  }
  const rueckgaengigFertig = () => Texte.t("Rückgängig gemacht. Es gilt wieder der Stand vor dem Vorschlag.");

  // One switch per term (#371, G102). The state is the terms in the result per area, as the app names them; the
  // app works out order and limits again from what the page sends.
  const BEREICHE = ["suchbegriffe", "positiv", "ausschluss"];
  /** The name of an area as term_changes.AREA_NAMES says it, in the app language. */
  function bereichName(schluessel) {
    const Texte = texts();
    const namen = { suchbegriffe: () => Texte.t("Suchbegriffe"), positiv: () => Texte.t("Titel enthält eines davon"),
                    ausschluss: () => Texte.t("Titel enthält keines davon") };
    return namen[schluessel]();
  }
  const SCHLUESSEL = { keywords: "suchbegriffe", positive: "positiv", exclude: "ausschluss" };
  const frei = () => Texte.t("Die Auswahl lässt sich übernehmen.");

  // G108: moving a keyword to the niches or onto portals adds and removes nothing, so it has one chip, which stands
  // for the whole change; the page keeps those switched on under this key.
  const VERSCHOBEN = "verschoben";
  const VERSCHIEBUNGEN = ["niche", "portals"];

  /** The chips of a change: what it removes („gone“), then what it adds („new“), each in the area of the change. */
  const chips = aenderung => (VERSCHIEBUNGEN.includes(aenderung.art)
    ? [{ bereich: VERSCHOBEN, begriff: aenderung.verschoben, art: "move", wort: aenderung.verschoben_wort }]
    : [...aenderung.entfaellt.map(begriff => ({ bereich: SCHLUESSEL[aenderung.bereich], begriff, art: "gone" })),
      ...aenderung.neu.map(begriff => ({ bereich: SCHLUESSEL[aenderung.bereich], begriff, art: "new" }))]);

  /** The current terms no change touches, per area in the order of the profile; an empty area is left out. */
  const bisherigeBereiche = bisherige => BEREICHE
    .map(schluessel => ({ schluessel, name: bereichName(schluessel),
      chips: (bisherige[schluessel] || []).map(begriff => ({ bereich: schluessel, begriff, art: "kept" })) }))
    .filter(bereich => bereich.chips.length);

  const imErgebnis = (auswahl, { bereich, begriff }) => (auswahl[bereich] || []).includes(begriff);

  /** A removed term is on while it goes away; a new or current term while it is in the result, a move while it is made. */
  const chipAn = (auswahl, chip) => imErgebnis(auswahl, chip) !== (chip.art === "gone");

  function mitBegriff(auswahl, { bereich, begriff }, drin) {
    const ohne = (auswahl[bereich] || []).filter(b => b !== begriff);
    return { ...auswahl, [bereich]: drin ? [...ohne, begriff] : ohne };
  }

  const schalteChip = (auswahl, chip, an) => mitBegriff(auswahl, chip, an !== (chip.art === "gone"));

  /** The word beside a chip, which carries its state: never colour alone. */
  function chipWort(chip, an) {
    const Texte = texts();
    if (chip.art === "new") return Texte.t("neu");
    if (chip.art === "move") return an ? chip.wort : Texte.t("bleibt");
    if (chip.art === "gone") return an ? Texte.t("entfällt") : Texte.t("bleibt");
    return an ? "" : Texte.t("entfällt");
  }

  function karteStand(auswahl, aenderung) {
    const an = chips(aenderung).map(chip => chipAn(auswahl, chip));
    if (an.every(Boolean)) return "alle";
    return an.some(Boolean) ? "teilweise" : "keine";
  }

  const schalteKarte = (auswahl, aenderung, an) => chips(aenderung).reduce((stand, chip) => schalteChip(stand, chip, an), auswahl);

  /** Each area after the switches, and how many are over what it may hold (`erlaubt` from the app). */
  const zaehlung = (auswahl, erlaubt) => BEREICHE.map(schluessel => ({ schluessel, name: bereichName(schluessel),
    anzahl: auswahl[schluessel].length, zuViel: Math.max(0, auswahl[schluessel].length - erlaubt[schluessel]) }));

  /** The legend of an area as parts, which the page joins with «·» (#340). */
  function legendeTeile(z) {
    const Texte = texts();
    const werte = { anzahl: z.anzahl, zuviel: z.zuViel };
    if (z.zuViel) {
      return [z.name, z.anzahl === 1 ? Texte.t("danach 1 eingeschaltet, {zuviel} zu viel", werte)
        : Texte.t("danach {anzahl} eingeschaltet, {zuviel} zu viel", werte)];
    }
    return [z.name, z.anzahl === 1 ? Texte.t("danach 1 eingeschaltet") : Texte.t("danach {anzahl} eingeschaltet", werte)];
  }

  const entfaelltZeile = liste => (liste.length ? Texte.t("Entfällt: {begriffe}", { begriffe: liste.join(", ") }) : "");

  /** The first area over what it may hold, by the app's count, or null. */
  const zuVielBereich = grenzen => BEREICHE.find(s => grenzen.zu_viel && grenzen.zu_viel[s] > 0) || null;

  function zuVielText(grenzen) {
    const schluessel = zuVielBereich(grenzen);
    if (!schluessel) return grenzen.gesperrt || "";
    const Texte = texts();
    const anzahl = grenzen.zu_viel[schluessel];
    if (schluessel === "suchbegriffe") {
      return anzahl === 1 ? Texte.t("Noch 1 Suchbegriff zu viel") : Texte.t("Noch {anzahl} Suchbegriffe zu viel", { anzahl });
    }
    const name = bereichName(schluessel);
    return anzahl === 1 ? Texte.t("Noch 1 Begriff zu viel in «{name}»", { name })
      : Texte.t("Noch {anzahl} Begriffe zu viel in «{name}»", { anzahl, name });
  }

  /** What the polite status says after an answer: only when the choice becomes blocked or free, or what is too many changes. */
  function ansage(vorher, nachher) {
    if (!vorher) return "";
    if (!nachher.gesperrt) return vorher.gesperrt ? frei() : "";
    const jetzt = zuVielText(nachher);
    return vorher.gesperrt && zuVielText(vorher) === jetzt ? "" : jetzt;
  }

  /** The footer of the card as parts, which the page joins with «·» (#337): model, cost, date, and the rounds so far. */
  function fussTeile(vorschlag) {
    const bisher = vorschlag.runde > 1 ? Texte.t("bisher {betrag}", { betrag: geld(vorschlag.kosten_bisher, vorschlag.waehrung) }) : "";
    return [vorschlag.modell ? "Claude" : "", geld(vorschlag.kosten_usd, vorschlag.waehrung), datum(vorschlag.datum), bisher]
      .filter(Boolean);
  }

  /** The round line as parts (#340); the first proposal has none. */
  const rundeTeile = (vorschlag, satz) => (vorschlag.runde > 1
    ? [Texte.t("Vorschlag {runde}", { runde: vorschlag.runde }), texte(satz).nachHinweis] : []);

  /** The terms after the switches, as the app worked them out, each with „neu“ if it was not there before. */
  /** `nurZeilen`: a keyword limited to portals stands only in its «Nur» block (endstandZeilen), not under Suchbegriffe. */
  function endstand(jetzt, danach, nurZeilen = []) {
    const begrenzt = new Set(nurZeilen.flatMap(zeile => zeile.begriffe.map(b => b.begriff.toLowerCase())));
    const gezeigt = (schluessel, begriff) => schluessel !== "suchbegriffe" || !begrenzt.has(begriff.toLowerCase());
    return BEREICHE.map(schluessel => ({
      name: bereichName(schluessel),
      begriffe: danach[schluessel].filter(begriff => gezeigt(schluessel, begriff))
        .map(begriff => ({ begriff, neu: !jetzt[schluessel].some(b => b.toLowerCase() === begriff.toLowerCase()) })),
    }));
  }

  /** The niches and «Nur» lines after the switches (G108), as the app worked them out; a line without terms is left out. */
  // The names of the niches and «Nur» lines are lines of the search profile (vorlagen/suchprofil.md): the person finds
  // them there under these words, so they stay German in every language (docs/design/sprachen.md).
  const NISCHEN_ZEILE = "Nischen (ohne Ort suchen)";  // kein UI-Text: search profile grammar
  const nurZeile = portale => `Nur ${portale.join(", ")}`;  // kein UI-Text: search profile grammar

  /** The niches and «Nur» lines after the switches (G108), as the app worked them out; a line without terms is left out. */
  function endstandZeilen(antwort) {
    const nischen = antwort.nischen || [];
    return [...(nischen.length ? [{ name: NISCHEN_ZEILE, begriffe: nischen }] : []),
      ...(antwort.nur_zeilen || []).map(zeile => ({ name: nurZeile(zeile.portale), begriffe: zeile.begriffe }))];
  }

  // «Was die App gezählt hat» (G108, #383): the numbers come from the app, the page only words them.
  const gezaehltTitel = () => Texte.t("Was die App gezählt hat");
  const nichtsMarkiert = () => Texte.t("Jeder Suchbegriff hat in den letzten 3 Suchläufen eigene Treffer gebracht.");
  const tabelleTitel = () => Texte.t("Alle Suchbegriffe mit Zahlen");
  // „Suchen“ alone is the button „Search“ elsewhere; the column counts searches, so it is a text set of its own.
  const tabelleSpalten = () => [Texte.t("Begriff"), Texte.text("suchbegriffe.spalte-suchen", "stelle-sie"), Texte.t("Treffer"),
    Texte.t("aussortiert"), Texte.t("nur über diesen Begriff"), Texte.t("ab Note 4")];
  /** The word of a mark («ohne Ertrag», «überlappend»), or "" for a keyword without one. */
  function markenWort(marke) {
    const Texte = texts();
    if (marke === "ohne_ertrag") return Texte.t("ohne Ertrag");
    return marke === "ueberlappend" ? Texte.t("überlappend") : "";
  }
  const VERSION_DER_ZAHLEN = "0.3.3";

  const gezaehltUnterzeile = z => Texte.t("Aus den letzten {anzahl} Suchläufen, gezählt von der App, nicht von der KI. Treffer zählt sie bei jeder Suche, Stellen nur einmal.",
    { anzahl: z.noetig });
  const gezaehltFehler = grund => (/[.!?]$/.test(grund)
    ? Texte.t("Die Zahlen der App liessen sich nicht laden: {grund} Die KI schlägt darum ohne diese Zahlen vor.", { grund })
    : Texte.t("Die Zahlen der App liessen sich nicht laden: {grund}. Die KI schlägt darum ohne diese Zahlen vor.", { grund }));

  function zuWenigeLaeufe(z) {
    if (z.genug) return null;
    const Texte = texts();
    const werte = { noetig: z.noetig, version: VERSION_DER_ZAHLEN, laeufe: z.laeufe };
    if (!z.laeufe) return Texte.t("Für diese Zahlen braucht die App {noetig} Suchläufe seit Version {version}, bisher gibt es noch keinen.", werte);
    return z.laeufe === 1 ? Texte.t("Für diese Zahlen braucht die App {noetig} Suchläufe seit Version {version}, bisher sind es 1.", werte)
      : Texte.t("Für diese Zahlen braucht die App {noetig} Suchläufe seit Version {version}, bisher sind es {laeufe}.", werte);
  }

  // The reasons a hit of an «ohne Ertrag» keyword fell away, each as „alle … aussortiert“, „… aussortiert“ for a single
  // hit, and as „3 …“ in a list of several. „Titelfilter“ is the name of the section in the search profile.
  function grundText(grund, form, zahl) {
    const Texte = texts();
    const texte = {
      titel: { alle: () => Texte.t("alle vom Titelfilter aussortiert"), einer: () => Texte.t("vom Titelfilter aussortiert"),
               zahl: () => Texte.t("{anzahl} vom Titelfilter", { anzahl: zahl }) },
      bezug: { alle: () => Texte.t("alle ohne Pflichtbezug aussortiert"), einer: () => Texte.t("ohne Pflichtbezug aussortiert"),
               zahl: () => Texte.t("{anzahl} ohne Pflichtbezug", { anzahl: zahl }) },
      region: { alle: () => Texte.t("alle ausserhalb der Region aussortiert"), einer: () => Texte.t("ausserhalb der Region aussortiert"),
                zahl: () => Texte.t("{anzahl} ausserhalb der Region", { anzahl: zahl }) },
    };
    return texte[grund][form]();
  }

  /** Why every hit of an «ohne Ertrag» keyword fell away: the title filter, no required word (G110), outside the
   * region without remote work (G111), or several of them. */
  function aussortiertWie(e) {
    const ohneBezug = e.ohne_pflichtbezug || 0;
    const ausserhalb = e.ausserhalb_region || 0;
    const titel = e.aussortiert - ohneBezug - ausserhalb;  // «aussortiert» counts every reason (term_evidence.KeywordCount)
    const gruende = [[titel, "titel"], [ohneBezug, "bezug"], [ausserhalb, "region"]].filter(([zahl]) => zahl > 0);
    const form = e.treffer_portale === 1 ? "einer" : "alle";
    if (gruende.length <= 1) return grundText(gruende.length ? gruende[0][1] : "titel", form);
    return Texte.t("alle aussortiert: {gruende}", { gruende: gruende.map(([zahl, grund]) => grundText(grund, "zahl", zahl)).join(", ") });
  }

  function markeSatz(e) {
    const Texte = texts();
    if (e.marke === "ohne_ertrag") {
      // hits as Suche einstellen counts them (#383): all the portals found, the screened-out ones among them
      const suchen = e.suchen === 1 ? Texte.t("1 Suche") : Texte.t("{anzahl} Suchen", { anzahl: e.suchen });
      if (!e.treffer_portale) return Texte.t("{suchen}, kein Treffer.", { suchen });
      const treffer = e.treffer_portale === 1 ? Texte.t("1 Treffer") : Texte.t("{anzahl} Treffer", { anzahl: e.treffer_portale });
      return `${[suchen, treffer, aussortiertWie(e)].join(", ")}.`;
    }
    // the overlap counts postings, each once («Stellen»), unlike the hits of every search in the table
    const werte = { anzahl: e.treffer, begriff: e.auch_ueber };
    if (e.treffer === 1) return Texte.t("1 Stelle, auch über „{begriff}“ gefunden.", werte);
    return e.alle_ueber ? Texte.t("{anzahl} Stellen, alle auch über „{begriff}“ gefunden.", werte)
      : Texte.t("{anzahl} Stellen, alle auch über andere Begriffe gefunden, meist über „{begriff}“.", werte);
  }

  /** Only the flagged keywords, in the order of the list: name, the word of the chip, then the numbers. */
  const markiert = z => (z.genug ? z.begriffe : []).filter(e => markenWort(e.marke))
    .map(e => ({ name: Texte.t("„{begriff}“", { begriff: e.begriff }), marke: markenWort(e.marke),
                 rest: Texte.t(": {satz}", { satz: markeSatz(e) }) }));

  // as „Wo ein Begriff nichts findet“ on Suche einstellen writes it (#375)
  const mitNische = begriff => Texte.t("{begriff} (Nische)", { begriff });
  const zahlenDer = e => [e.suchen, e.treffer_portale, e.aussortiert, e.nur_hier, e.ab_note_4];

  // G111: a niche's hits outside the region are in «aussortiert»; its row names how many beside its name
  const ausserhalbZusatz = e => (e.ausserhalb_region > 0
    ? { zusatz: Texte.t("{anzahl} ausserhalb der Region", { anzahl: e.ausserhalb_region }) } : {});

  /** Every keyword, then the niches (#393), which are counted alike but never carry a mark. */
  const tabellenZeilen = z => [
    ...z.begriffe.map(e => ({ begriff: e.begriff, marke: markenWort(e.marke), zahlen: zahlenDer(e) })),
    ...(z.nischen || []).map(e => ({ begriff: mitNische(e.begriff), marke: "", zahlen: zahlenDer(e), ...ausserhalbZusatz(e) }))];

  /** The word of the chip on a card's area line: the mark of the keyword the change concerns, or nothing. */
  const kartenMarke = aenderung => markenWort(aenderung.marke);

  // The former constants are read when they are shown, so they follow the app language.
  const api = { texte, datum, geld, lockCheckLink, hinweisText, belegSatz, belegBeispiele, belegLink, belegAdresse, balken,
    belegAusAdresse, kopfTeile, uebernommen, get RUECKGAENGIG_FERTIG() { return rueckgaengigFertig(); }, fussTeile, rundeTeile,
    endstand, endstandZeilen, get GEZAEHLT_TITEL() { return gezaehltTitel(); }, get NICHTS_MARKIERT() { return nichtsMarkiert(); },
    get TABELLE_TITEL() { return tabelleTitel(); }, get TABELLE_SPALTEN() { return tabelleSpalten(); }, gezaehltUnterzeile,
    gezaehltFehler, zuWenigeLaeufe, markiert, tabellenZeilen, kartenMarke, VERSCHOBEN,
    get HAUPTKNOPF() { return Texte.t("Auswahl übernehmen"); }, get TEILWEISE() { return Texte.t("Teilweise übernommen"); },
    get BISHERIGE_OBEN() { return Texte.t("Begriffe, die eine Änderung oben betrifft, stehen dort."); },
    get ZU_DEN_BISHERIGEN() { return Texte.t("Zu den bisherigen Begriffen"); }, get FREI() { return frei(); },
    chips, bisherigeBereiche, chipAn, schalteChip, chipWort,
    karteStand, schalteKarte, zaehlung, legendeTeile, entfaelltZeile, zuVielBereich, ansage };
  if (typeof module !== "undefined") module.exports = api;
  else root.SuchbegriffeLogik = api;
})(typeof window !== "undefined" ? window : globalThis);
