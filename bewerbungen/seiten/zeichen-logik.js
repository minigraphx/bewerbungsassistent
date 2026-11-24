"use strict";
// Mark and accent colour of the dossier (G18, docs/design/monogramm.md, option B): names, sentences and the colour
// check, without DOM (tests/zeichen_logik.test.cjs). The contrast rules are those of lebenslauf/mark.py; both
// languages run the cases in lebenslauf/tests/accent_cases.json. Names and sentences come in the app language through
// Texte (#429), each read when used; values such as „ring“ or #38495d stay as they are.
(function (global) {
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte), text: (key, satz) => texts().text(key, satz) };

  const PASSEND = "passend";
  const VARIANTEN = [
    { wert: PASSEND, get name() { return Texte.t("Passend zum Design"); } },
    { wert: "ring", get name() { return Texte.t("Ring"); }, get satz() { return Texte.t("Initialen im Ring"); } },
    { wert: "block", get name() { return Texte.t("Block"); }, get satz() { return Texte.t("Initialen in einer Fläche"); } },
    { wert: "verschraenkt", get name() { return Texte.t("Verschränkt"); },
      get satz() { return Texte.t("Zwei Buchstaben ineinander"); } },
    { wert: "linie", get name() { return Texte.t("Linie"); }, get satz() { return Texte.t("Initialen auf einer Linie"); } },
    { wert: "punkt", get name() { return Texte.t("Punkt"); }, get satz() { return Texte.t("Punkt vor den Initialen"); } },
  ];
  const nurZwei = () => Texte.t("Nur mit zwei Buchstaben");
  const DESIGN_NAMEN = {
    get siegel() { return Texte.t("Siegel"); }, get raster() { return Texte.t("Raster"); },
    get register() { return Texte.t("Register"); },
  };
  // What „Passend zum Design“ draws, and the colour each design brings
  const EIGENES_ZEICHEN = { siegel: "ring", raster: "band", register: "punkt" };
  // One object per colour, so a page can tell a swatch by identity (lebenslauf-erstellen-logik.accentChoices)
  const FARBEN = [
    { get name() { return Texte.t("Schieferblau"); }, farbe: "#38495d" },
    { get name() { return Texte.t("Weinrot"); }, farbe: "#7a2e3a" },
    { get name() { return Texte.t("Tannengrün"); }, farbe: "#2f5d50" },
    { get name() { return Texte.t("Petrol"); }, farbe: "#1d5c6b" },
    { get name() { return Texte.t("Aubergine"); }, farbe: "#5b3f6b" },
    { get name() { return Texte.t("Bronze"); }, farbe: "#7a5418" },
    { get name() { return Texte.t("Graphit"); }, farbe: "#3a3d42" },
  ];
  const HAUPTFARBEN = { siegel: FARBEN[0], raster: FARBEN[1], register: FARBEN[2] };

  const PAPIER = "#fdfcfa";
  const WEISS = "#ffffff";
  const DUNKEL = "#27333f";
  const MIN_SCHRIFT = 4.5;
  const MIN_PAPIER = 3;
  const SCHRITT = 0.01;
  const FARBE = /^#[0-9a-f]{6}$/;
  const ungueltig = () => Texte.t("Bitte eine Farbe wie #38495d eingeben.");
  const zuHell = () => Texte.t("Zu hell: Ring, Linien und Punkte wären auf dem Papier kaum zu sehen. Gespeichert wird diese Farbe nicht.");
  const mittelton = () => Texte.t("Weder weisse noch dunkle Schrift ist auf dieser Farbe gut lesbar. Gespeichert wird sie nicht.");

  const kanaele = wert => [1, 3, 5].map(i => parseInt(wert.slice(i, i + 2), 16) / 255);
  const linear = v => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);

  function leuchtdichte(wert) {
    const [r, g, b] = kanaele(wert).map(linear);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  function kontrast(a, b) {
    const [la, lb] = [leuchtdichte(a), leuchtdichte(b)];
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }

  const schriftAuf = wert => (kontrast(wert, WEISS) >= kontrast(wert, DUNKEL) ? WEISS : DUNKEL);
  const lesbar = wert => kontrast(wert, schriftAuf(wert)) >= MIN_SCHRIFT && kontrast(wert, PAPIER) >= MIN_PAPIER;

  function zuHsl(wert) {
    const [r, g, b] = kanaele(wert);
    const hoch = Math.max(r, g, b);
    const tief = Math.min(r, g, b);
    const helligkeit = (hoch + tief) / 2;
    if (hoch === tief) return [0, 0, helligkeit];
    const spanne = hoch - tief;
    const saettigung = helligkeit > 0.5 ? spanne / (2 - hoch - tief) : spanne / (hoch + tief);
    let ton;
    if (hoch === r) ton = (((g - b) / spanne) % 6 + 6) % 6;
    else if (hoch === g) ton = (b - r) / spanne + 2;
    else ton = (r - g) / spanne + 4;
    return [ton / 6, saettigung, helligkeit];
  }

  function ausHsl(ton, saettigung, helligkeit) {
    const chroma = (1 - Math.abs(2 * helligkeit - 1)) * saettigung;
    const sektor = ton * 6;
    const zweite = chroma * (1 - Math.abs((sektor % 2) - 1));
    const teile = [[chroma, zweite, 0], [zweite, chroma, 0], [0, chroma, zweite], [0, zweite, chroma],
      [zweite, 0, chroma], [chroma, 0, zweite]][Math.floor(sektor) % 6];
    const basis = helligkeit - chroma / 2;
    return "#" + teile.map(v => Math.floor((v + basis) * 255 + 0.5).toString(16).padStart(2, "0")).join("");
  }

  /** The same colour, darker until text on it and the colour on the paper both read well. */
  function dunkler(wert) {
    const [ton, saettigung, start] = zuHsl(wert);
    for (let helligkeit = start; helligkeit > 0; helligkeit -= SCHRITT) {
      const kandidat = ausHsl(ton, saettigung, helligkeit);
      if (lesbar(kandidat)) return kandidat;
    }
    return ausHsl(ton, saettigung, 0);
  }

  /** The check of an own colour, as lebenslauf/mark.accent_check. */
  function pruefeFarbe(eingabe) {
    const farbe = String(eingabe || "").trim().toLowerCase();
    if (!FARBE.test(farbe)) return { farbe, ok: false, problem: "ungueltig", meldung: ungueltig(), vorschlag: null };
    const schrift = schriftAuf(farbe) === WEISS ? "weiss" : "dunkel";
    if (lesbar(farbe)) {
      const gut = schrift === "weiss"
        ? Texte.t("Gut lesbar: weisse Schrift auf der Farbe, Linien gut sichtbar auf dem Papier.")
        : Texte.t("Gut lesbar: dunkle Schrift auf der Farbe, Linien gut sichtbar auf dem Papier.");
      return { farbe, ok: true, schrift, problem: null, meldung: gut, vorschlag: null };
    }
    const problem = kontrast(farbe, PAPIER) < MIN_PAPIER ? "zu-hell" : "mittelton";
    return { farbe, ok: false, schrift, problem, meldung: problem === "zu-hell" ? zuHell() : mittelton(), vorschlag: dunkler(farbe) };
  }

  /** Why a variant cannot be chosen with these initials, or "". */
  const gesperrt = (variante, initialen) => (variante === "verschraenkt" && [...(initialen || "")].length !== 2 ? nurZwei() : "");

  const designName = design => (Object.hasOwn(DESIGN_NAMEN, design) ? DESIGN_NAMEN[design] : DESIGN_NAMEN.siegel);
  const hauptfarbe = design => HAUPTFARBEN[design] || HAUPTFARBEN.siegel;

  /** The sentence of „Passend zum Design“ in the list. */
  function passendSatz(design) {
    const name = { ring: () => Texte.t("Ring"), band: () => Texte.t("Block"), punkt: () => Texte.t("Punkt") };
    const zeichen = name[EIGENES_ZEICHEN[design] || "ring"]();
    return Texte.t("{zeichen} bei {design}, wie das Design es vorsieht", { zeichen, design: designName(design) });
  }

  /** The colour that counts and its name: the chosen one, otherwise the main colour of the cover's design. */
  function wirksameFarbe(zustand, deckblatt) {
    const akzent = zustand.akzent || PASSEND;
    if (akzent === PASSEND) return { ...hauptfarbe(deckblatt), quelle: PASSEND };
    const benannt = FARBEN.find(f => f.farbe === akzent);
    if (benannt) return { ...benannt, quelle: "benannt" };
    if (zustand.logo && zustand.logo.farbe === akzent) {
      return { name: Texte.t("Aus dem Logo ({farbe})", { farbe: akzent }), farbe: akzent, quelle: "logo" };
    }
    return { name: Texte.t("Eigene Farbe ({farbe})", { farbe: akzent }), farbe: akzent, quelle: "eigen" };
  }

  /** The mark of one design in words: „Ring mit LB“, „Initialen im Band“, „Ihr Logo“. */
  function zeichenWorte(zustand, design, du) {
    const initialen = zustand.initialen_wirksam || "";
    const variante = zustand.zeichen || PASSEND;
    if (variante === "logo" && zustand.logo) return Texte.text("lebenslauf.zeichen-logo", du ? "stelle-du" : "stelle-sie");
    const gezeichnet = variante === PASSEND || gesperrt(variante, initialen) ? EIGENES_ZEICHEN[design] || "ring" : variante;
    const werte = { initialen };
    return {
      ring: () => Texte.t("Ring mit {initialen}", werte), band: () => Texte.t("Initialen im Band"),
      punkt: () => Texte.t("Punkt mit {initialen} im Anhänger", werte), block: () => Texte.t("Block mit {initialen}", werte),
      verschraenkt: () => Texte.t("{initialen} verschränkt", werte), linie: () => Texte.t("{initialen} auf einer Linie", werte),
    }[gezeichnet]();
  }

  /** The sentence under the design choice: what counts now, and where to change it; the parts of a «·» line (#342). */
  function satzUnterDesign(zustand, seiten, du = false) {
    const deckblatt = seiten.deckblatt;
    const gemischt = new Set(Object.values(seiten)).size > 1;
    const eigenesZeichen = (zustand.zeichen || PASSEND) !== PASSEND && !(zustand.zeichen === "logo" && !zustand.logo);
    const farbe = wirksameFarbe(zustand, deckblatt);
    const name = designName(deckblatt);
    let zeichen = gemischt && !eigenesZeichen ? Texte.t("passend zum Design jeder Seite") : zeichenWorte(zustand, deckblatt, du);
    let akzent = farbe.name;
    let beides = "";
    if (gemischt) {
      if (farbe.quelle === PASSEND) akzent = Texte.t("{farbe}, passend zum Deckblatt in {design}", { farbe: akzent, design: name });
    } else if (!eigenesZeichen && farbe.quelle === PASSEND) {
      beides = Texte.t("beides passend zu {design}", { design: name });
    } else if (!eigenesZeichen) {
      zeichen = Texte.t("{zeichen}, passend zu {design}", { zeichen, design: name });
    } else if (farbe.quelle === PASSEND) {
      akzent = Texte.t("{farbe}, passend zu {design}", { farbe: akzent, design: name });
    }
    return [Texte.t("Zeichen: {zeichen}", { zeichen }), Texte.t("Akzentfarbe: {farbe}", { farbe: akzent }), beides].filter(Boolean);
  }

  /** What a screen reader hears for the preview. */
  function vorschauLabel(zustand, design, du = false) {
    return Texte.t("Vorschau Deckblatt: {design}, {zeichen}, {farbe}", { design: designName(design),
      zeichen: zeichenWorte(zustand, design, du), farbe: wirksameFarbe(zustand, design).name });
  }

  /** The variant a design draws for this choice: its own for „passend“, a missing logo or blocked letters. */
  function gezeichnet(zustand, design) {
    const variante = zustand.zeichen || PASSEND;
    if (variante === "logo") return zustand.logo ? "logo" : EIGENES_ZEICHEN[design] || "ring";
    if (variante === PASSEND || gesperrt(variante, zustand.initialen_wirksam)) return EIGENES_ZEICHEN[design] || "ring";
    return variante;
  }

  const logik = {
    PASSEND, VARIANTEN, get NUR_ZWEI() { return nurZwei(); }, DESIGN_NAMEN, HAUPTFARBEN, FARBEN, kontrast, schriftAuf, lesbar,
    dunkler, pruefeFarbe, gesperrt, designName, hauptfarbe, passendSatz, wirksameFarbe, zeichenWorte, satzUnterDesign,
    vorschauLabel, gezeichnet,
  };
  if (typeof module !== "undefined") module.exports = logik;
  else global.ZeichenLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
