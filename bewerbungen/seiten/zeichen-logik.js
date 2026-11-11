"use strict";
// Mark and accent colour of the dossier (G18, docs/design/monogramm.md, option B): names, sentences and the colour
// check, without DOM (tests/zeichen_logik.test.cjs). The contrast rules are those of lebenslauf/mark.py; both
// languages run the cases in lebenslauf/tests/accent_cases.json.
(function (global) {
  const PASSEND = "passend";
  const VARIANTEN = [
    { wert: PASSEND, name: "Passend zum Design" },
    { wert: "ring", name: "Ring", satz: "Initialen im Ring" },
    { wert: "block", name: "Block", satz: "Initialen in einer Fläche" },
    { wert: "verschraenkt", name: "Verschränkt", satz: "Zwei Buchstaben ineinander" },
    { wert: "linie", name: "Linie", satz: "Initialen auf einer Linie" },
    { wert: "punkt", name: "Punkt", satz: "Punkt vor den Initialen" },
  ];
  const NUR_ZWEI = "Nur mit zwei Buchstaben";
  const DESIGN_NAMEN = { siegel: "Siegel", raster: "Raster", register: "Register" };
  // What „Passend zum Design“ draws, and the colour each design brings
  const EIGENES_ZEICHEN = { siegel: "ring", raster: "band", register: "punkt" };
  const HAUPTFARBEN = {
    siegel: { name: "Schieferblau", farbe: "#38495d" },
    raster: { name: "Weinrot", farbe: "#7a2e3a" },
    register: { name: "Tannengrün", farbe: "#2f5d50" },
  };
  const FARBEN = [
    { name: "Schieferblau", farbe: "#38495d" }, { name: "Weinrot", farbe: "#7a2e3a" },
    { name: "Tannengrün", farbe: "#2f5d50" }, { name: "Petrol", farbe: "#1d5c6b" },
    { name: "Aubergine", farbe: "#5b3f6b" }, { name: "Bronze", farbe: "#7a5418" }, { name: "Graphit", farbe: "#3a3d42" },
  ];

  const PAPIER = "#fdfcfa";
  const WEISS = "#ffffff";
  const DUNKEL = "#27333f";
  const MIN_SCHRIFT = 4.5;
  const MIN_PAPIER = 3;
  const SCHRITT = 0.01;
  const FARBE = /^#[0-9a-f]{6}$/;
  const UNGUELTIG = "Bitte eine Farbe wie #38495d eingeben.";
  const ZU_HELL = "Zu hell: Ring, Linien und Punkte wären auf dem Papier kaum zu sehen. Gespeichert wird diese Farbe nicht.";
  const MITTELTON = "Weder weisse noch dunkle Schrift ist auf dieser Farbe gut lesbar. Gespeichert wird sie nicht.";

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
    if (!FARBE.test(farbe)) return { farbe, ok: false, problem: "ungueltig", meldung: UNGUELTIG, vorschlag: null };
    const schrift = schriftAuf(farbe) === WEISS ? "weiss" : "dunkel";
    if (lesbar(farbe)) {
      const gut = `Gut lesbar: ${schrift === "weiss" ? "weisse" : "dunkle"} Schrift auf der Farbe, Linien gut sichtbar auf dem Papier.`;
      return { farbe, ok: true, schrift, problem: null, meldung: gut, vorschlag: null };
    }
    const problem = kontrast(farbe, PAPIER) < MIN_PAPIER ? "zu-hell" : "mittelton";
    return { farbe, ok: false, schrift, problem, meldung: problem === "zu-hell" ? ZU_HELL : MITTELTON, vorschlag: dunkler(farbe) };
  }

  /** Why a variant cannot be chosen with these initials, or "". */
  const gesperrt = (variante, initialen) => (variante === "verschraenkt" && [...(initialen || "")].length !== 2 ? NUR_ZWEI : "");

  const designName = design => DESIGN_NAMEN[design] || DESIGN_NAMEN.siegel;
  const hauptfarbe = design => HAUPTFARBEN[design] || HAUPTFARBEN.siegel;

  /** The sentence of „Passend zum Design“ in the list. */
  function passendSatz(design) {
    const zeichen = { ring: "Ring", band: "Block", punkt: "Punkt" }[EIGENES_ZEICHEN[design] || "ring"];
    return `${zeichen} bei ${designName(design)}, wie das Design es vorsieht`;
  }

  /** The colour that counts and its name: the chosen one, otherwise the main colour of the cover's design. */
  function wirksameFarbe(zustand, deckblatt) {
    const akzent = zustand.akzent || PASSEND;
    if (akzent === PASSEND) return { ...hauptfarbe(deckblatt), quelle: PASSEND };
    const benannt = FARBEN.find(f => f.farbe === akzent);
    if (benannt) return { ...benannt, quelle: "benannt" };
    if (zustand.logo && zustand.logo.farbe === akzent) return { name: `Aus dem Logo (${akzent})`, farbe: akzent, quelle: "logo" };
    return { name: `Eigene Farbe (${akzent})`, farbe: akzent, quelle: "eigen" };
  }

  /** The mark of one design in words: „Ring mit LB“, „Initialen im Band“, „Ihr Logo“. */
  function zeichenWorte(zustand, design, du) {
    const initialen = zustand.initialen_wirksam || "";
    const variante = zustand.zeichen || PASSEND;
    if (variante === "logo" && zustand.logo) return du ? "Dein Logo" : "Ihr Logo";
    const gezeichnet = variante === PASSEND || gesperrt(variante, initialen) ? EIGENES_ZEICHEN[design] || "ring" : variante;
    return {
      ring: `Ring mit ${initialen}`, band: "Initialen im Band", punkt: `Punkt mit ${initialen} im Anhänger`,
      block: `Block mit ${initialen}`, verschraenkt: `${initialen} verschränkt`, linie: `${initialen} auf einer Linie`,
    }[gezeichnet];
  }

  /** The sentence under the design choice: what counts now, and where to change it. */
  function satzUnterDesign(zustand, seiten, du = false) {
    const deckblatt = seiten.deckblatt;
    const gemischt = new Set(Object.values(seiten)).size > 1;
    const eigenesZeichen = (zustand.zeichen || PASSEND) !== PASSEND && !(zustand.zeichen === "logo" && !zustand.logo);
    const farbe = wirksameFarbe(zustand, deckblatt);
    const name = designName(deckblatt);
    let zeichen = gemischt && !eigenesZeichen ? "passend zum Design jeder Seite" : zeichenWorte(zustand, deckblatt, du);
    let akzent = farbe.name;
    let beides = "";
    if (gemischt) {
      if (farbe.quelle === PASSEND) akzent += `, passend zum Deckblatt in ${name}`;
    } else if (!eigenesZeichen && farbe.quelle === PASSEND) {
      beides = ` · beides passend zu ${name}`;
    } else if (!eigenesZeichen) {
      zeichen += `, passend zu ${name}`;
    } else if (farbe.quelle === PASSEND) {
      akzent += `, passend zu ${name}`;
    }
    return `Zeichen: ${zeichen} · Akzentfarbe: ${akzent}${beides} · Ändern unter «Erweitert».`;
  }

  /** What a screen reader hears for the preview. */
  function vorschauLabel(zustand, design, du = false) {
    return `Vorschau Deckblatt: ${designName(design)}, ${zeichenWorte(zustand, design, du)}, ${wirksameFarbe(zustand, design).name}`;
  }

  /** The variant a design draws for this choice: its own for „passend“, a missing logo or blocked letters. */
  function gezeichnet(zustand, design) {
    const variante = zustand.zeichen || PASSEND;
    if (variante === "logo") return zustand.logo ? "logo" : EIGENES_ZEICHEN[design] || "ring";
    if (variante === PASSEND || gesperrt(variante, zustand.initialen_wirksam)) return EIGENES_ZEICHEN[design] || "ring";
    return variante;
  }

  const logik = {
    PASSEND, VARIANTEN, NUR_ZWEI, DESIGN_NAMEN, HAUPTFARBEN, FARBEN, kontrast, schriftAuf, lesbar, dunkler, pruefeFarbe,
    gesperrt, designName, hauptfarbe, passendSatz, wirksameFarbe, zeichenWorte, satzUnterDesign, vorschauLabel, gezeichnet,
  };
  if (typeof module !== "undefined") module.exports = logik;
  else global.ZeichenLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
