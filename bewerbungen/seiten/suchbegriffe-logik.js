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
      wartenNotiz: "Meist unter 30 Sekunden. Am Suchprofil ändert sich nichts, bis Sie etwas übernehmen.",
      gesehen: (treffer, seit) => `Die KI hat Ihr Suchprofil, Ihren Lebenslauf${treffer ? ` und ${treffer} Treffer${seit ? ` seit dem ${datum(seit)}` : ""}` : ""} angesehen. Geändert wird nur, was angehakt ist.`,
      passt: "Ihre Suchbegriffe passen. Die KI schlägt keine Änderung vor.",
      passtNotiz: "Kein Begriff lässt auffällig viele unpassende Treffer durch, und was in Ihrem Lebenslauf steht, wird schon gesucht.",
      fuss: "Ein Vorschlag, kein Urteil. Die KI kann sich irren. Geändert wird nur, was Sie übernehmen.",
      andersHilfe: "Die KI überarbeitet den Vorschlag. Ihr Text geht mit dem Vorschlag an die KI.",
      nachHinweis: "nach Ihrem Hinweis",
      ihrHinweis: "Ihr Hinweis",
      einwilligung: "Bevor die KI Suchbegriffe vorschlägt, braucht es Ihre Einwilligung.",
    },
    du: {
      satz: "Die KI schlägt vor, du entscheidest. Am Suchprofil ändert sich erst etwas, wenn du übernimmst.",
      wasGeht: "An die KI gehen dein Suchprofil und dein Lebenslauf mit Platzhaltern für Name, Adresse und Kontakte sowie Titel und Note der eingeschätzten Treffer, ohne Inseratstexte.",
      hinweisNachsatz: "Die KI kann bessere Begriffe vorschlagen. Geändert wird nur, was du übernimmst.",
      warten: "KI prüft deine Suchbegriffe",
      wartenNotiz: "Meist unter 30 Sekunden. Am Suchprofil ändert sich nichts, bis du etwas übernimmst.",
      gesehen: (treffer, seit) => `Die KI hat dein Suchprofil, deinen Lebenslauf${treffer ? ` und ${treffer} Treffer${seit ? ` seit dem ${datum(seit)}` : ""}` : ""} angesehen. Geändert wird nur, was angehakt ist.`,
      passt: "Deine Suchbegriffe passen. Die KI schlägt keine Änderung vor.",
      passtNotiz: "Kein Begriff lässt auffällig viele unpassende Treffer durch, und was in deinem Lebenslauf steht, wird schon gesucht.",
      fuss: "Ein Vorschlag, kein Urteil. Die KI kann sich irren. Geändert wird nur, was du übernimmst.",
      andersHilfe: "Die KI überarbeitet den Vorschlag. Dein Text geht mit dem Vorschlag an die KI.",
      nachHinweis: "nach deinem Hinweis",
      ihrHinweis: "Dein Hinweis",
      einwilligung: "Bevor die KI Suchbegriffe vorschlägt, braucht es deine Einwilligung.",
    },
  };
  const BELOW = 4;

  /** The texts for the set of the page; „stelle-du“ speaks informally, everything else formally. */
  const texte = satz => (satz === "stelle-du" ? TEXTE.du : TEXTE.sie);

  function datum(iso) {
    const [jahr, monat, tag] = String(iso).split("-");
    return tag ? `${Number(tag)}.${Number(monat)}.${jahr}` : String(iso);
  }

  /** Never less than a cent: a call that costs less is still not free. */
  const geld = usd => `${Math.max(Number(usd) || 0, 0.01).toFixed(2)} USD`;
  const schaetzung = usd => `Etwa ${geld(usd)}`;

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

  function hauptknopf(gewaehlt, alle) {
    if (gewaehlt === 0) return "Übernehmen";
    if (gewaehlt === alle) return alle === 1 ? "Änderung übernehmen" : `Alle ${alle} übernehmen`;
    return `${gewaehlt} von ${alle} übernehmen`;
  }

  const kopf = anzahl => `Vorschlag der KI · ${anzahl === 1 ? "1 Änderung" : `${anzahl} Änderungen`}`;

  /** The marks of a change: what goes with „entfällt“, what comes with „neu“; the word carries the meaning, not the colour. */
  const marken = aenderung => [
    ...aenderung.entfaellt.map(begriff => ({ begriff, wort: "entfällt", art: "gone" })),
    ...aenderung.neu.map(begriff => ({ begriff, wort: "neu", art: "new" })),
  ];

  const uebernommen = anzahl => `Übernommen: ${anzahl === 1 ? "1 Änderung" : `${anzahl} Änderungen`}. Die nächste Suche sucht danach. Der bisherige Stand bleibt unter Entwürfe erhalten.`;
  const RUECKGAENGIG_FERTIG = "Rückgängig gemacht. Es gilt wieder der Stand vor dem Vorschlag.";

  function fuss(vorschlag) {
    const teile = [vorschlag.modell ? "Claude" : "", geld(vorschlag.kosten_usd), datum(vorschlag.datum)];
    if (vorschlag.runde > 1) teile.push(`bisher ${geld(vorschlag.kosten_bisher)}`);
    return teile.filter(Boolean).join(" · ");
  }

  const runde = (vorschlag, satz) => (vorschlag.runde > 1 ? `Vorschlag ${vorschlag.runde} · ${texte(satz).nachHinweis}` : "");

  /** The terms after the ticked changes, each with „neu“ if it was not there before. */
  function endstand(jetzt, danach) {
    const bereiche = [["suchbegriffe", "Suchbegriffe"], ["positiv", "Titel enthält eines davon"], ["ausschluss", "Titel enthält keines davon"]];
    return bereiche.map(([schluessel, name]) => ({
      name,
      begriffe: danach[schluessel].map(begriff => ({ begriff, neu: !jetzt[schluessel].some(b => b.toLowerCase() === begriff.toLowerCase()) })),
    }));
  }

  const api = { texte, datum, geld, schaetzung, hinweisText, belegSatz, belegBeispiele, belegLink, belegAdresse, balken,
    belegAusAdresse, hauptknopf, kopf, marken, uebernommen, RUECKGAENGIG_FERTIG, fuss, runde, endstand };
  if (typeof module !== "undefined") module.exports = api;
  else root.SuchbegriffeLogik = api;
})(typeof window !== "undefined" ? window : globalThis);
