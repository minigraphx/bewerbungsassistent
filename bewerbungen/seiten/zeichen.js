"use strict";
// Mark and accent colour of the dossier (G18, option B of docs/design/monogramm.md) on the application page: a sentence
// under the design choice, and under „Erweitert“ the section „Zeichen und Farbe“ with a simplified preview. The
// choice is stored once per person and saved at once. Names and rules in zeichen-logik.js.
(() => {
  const { holen, senden, status, el, url, alsBase64 } = window.App;
  const Z = window.ZeichenLogik;
  const W = window.UnterlagenWahl;
  const $ = id => document.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const PAPIER = "#fdfcfa";
  const DUNKEL = "#27333f";
  const LINIE = "#d9dde3";
  const GRAU = "#c3ccd6";
  const MIT_LOGO = "logo";
  const EIGENE = "eigen";

  let zustand = null; // state of /api/dossier/zeichen, null until the section first shows
  let seiten = { deckblatt: "siegel", anschreiben: "siegel", lebenslauf: "siegel", weitere: "siegel" };
  let du = false;

  const meldung = (text, art) => status($("d-zeichen-status"), text, art);

  function s(tag, attribute = {}, ...kinder) {
    const e = document.createElementNS(NS, tag);
    for (const [name, wert] of Object.entries(attribute)) if (wert !== null && wert !== undefined) e.setAttribute(name, wert);
    for (const kind of kinder.flat(Infinity)) if (kind) e.append(typeof kind === "string" ? document.createTextNode(kind) : kind);
    return e;
  }

  // The colours of the dossier for one accent, as themes/tokens.typ derives them
  function farbenFuer(akzent) {
    const misch = (i) => Math.round(parseInt(akzent.slice(i, i + 2), 16) * 0.12 + 255 * 0.88).toString(16).padStart(2, "0");
    return { akzent, auf: Z.schriftAuf(akzent), hell: `#${misch(1)}${misch(3)}${misch(5)}` };
  }

  const logoAdresse = () => url("/api/dossier/logo", { v: zustand.logo ? zustand.logo.version : "" });

  /** One mark in a 64 × 48 box; `mono` draws it in one colour, as on the accent band of Raster. */
  function zeichenSvg(variante, initialen, f, mono = null) {
    const tinte = mono || f.akzent;
    const schrift = mono || DUNKEL;
    const klein = [...initialen].length >= 3 ? 0.8 : 1;
    const text = (x, groesse, attribute = {}) => s("text", { x, y: 24, "font-size": groesse, "font-weight": 700,
      "dominant-baseline": "central", "font-family": "DM Sans, sans-serif", ...attribute }, initialen);
    const teile = {
      ring: () => [s("circle", { cx: 32, cy: 24, r: 20, fill: mono ? "none" : "#ffffff", stroke: tinte, "stroke-width": 2.4 }),
        text(32, 14 * klein, { "text-anchor": "middle", fill: schrift })],
      block: () => [s("rect", { x: 12, y: 4, width: 40, height: 40, rx: 5, fill: tinte }),
        text(32, 16 * klein, { "text-anchor": "middle", fill: mono ? f.akzent : f.auf })],
      band: () => [s("rect", { x: 2, y: 2, width: 60, height: 44, rx: 4, fill: f.akzent }),
        text(8, 20, { y: 32, fill: f.auf })],
      verschraenkt: () => {
        const [erster, zweiter] = [...initialen];
        return [s("text", { x: 18, y: 24, "font-size": 30, "font-weight": 700, "dominant-baseline": "central", fill: schrift }, erster),
          s("text", { x: 34, y: 24, "font-size": 30, "font-weight": 700, "dominant-baseline": "central", fill: "none",
            stroke: tinte, "stroke-width": 1.2 }, zweiter || "")];
      },
      linie: () => [text(10, 17, { y: 19, fill: schrift }), s("line", { x1: 10, y1: 34, x2: 50, y2: 34, stroke: tinte, "stroke-width": 2 }),
        s("circle", { cx: 52, cy: 34, r: 2.6, fill: tinte })],
      punkt: () => [s("circle", { cx: 14, cy: 24, r: 4.2, fill: tinte }), text(23, 18, { fill: schrift })],
      logo: () => [s("image", { href: logoAdresse(), x: 2, y: 2, width: 60, height: 44, preserveAspectRatio: "xMidYMid meet" })],
    };
    return s("svg", { viewBox: "0 0 64 48", "aria-hidden": "true", focusable: "false" }, (teile[variante] || teile.ring)());
  }

  const platziert = (svg, x, y, breite, hoehe) => {
    for (const [name, wert] of Object.entries({ x, y, width: breite, height: hoehe })) svg.setAttribute(name, wert);
    return svg;
  };
  const balken = (x, y, breite, farbe = GRAU, hoehe = 3) => s("rect", { x, y, width: breite, height: hoehe, rx: 1, fill: farbe });

  /** Cover and following page of one design, simplified like the boards. */
  function vorschauSvg(design) {
    const f = farbenFuer(Z.wirksameFarbe(zustand, seiten.deckblatt).farbe);
    const variante = Z.gezeichnet(zustand, design);
    const initialen = zustand.initialen_wirksam || "";
    const eigenes = variante !== { siegel: "ring", raster: "band", register: "punkt" }[design];
    const zeichen = (x, y, b, h, mono) => platziert(zeichenSvg(variante, initialen, f, mono), x, y, b, h);
    const seite = (x, ...inhalt) => s("g", { transform: `translate(${x} 0)` },
      s("rect", { width: 105, height: 148, fill: PAPIER, stroke: LINIE }), ...inhalt);
    const text = [balken(10, 92, 60, DUNKEL, 6), balken(10, 102, 40), balken(10, 112, 50)];
    const folge = [balken(10, 22, 70, DUNKEL, 5), ...[34, 42, 50, 58, 70, 78, 86].map(y => balken(10, y, 80))];
    const deckblatt = {
      siegel: [s("line", { x1: 8, y1: 46, x2: 97, y2: 46, stroke: f.akzent, "stroke-width": 1 }),
        ...[16, 26].map(x => s("circle", { cx: x, cy: 46, r: 2, fill: f.akzent })),
        s("rect", { x: 34, y: 34, width: 36, height: 24, fill: PAPIER }), zeichen(36, 34, 32, 24),
        ...[80, 90].map(x => s("circle", { cx: x, cy: 46, r: 2, fill: PAPIER, stroke: f.akzent, "stroke-width": 0.8 })),
        ...text, s("rect", { x: 0, y: 126, width: 105, height: 22, fill: f.akzent })],
      raster: [s("rect", { x: 6, y: 6, width: 52, height: 60, rx: 3, fill: f.akzent }), s("rect", { x: 61, y: 6, width: 5, height: 60, rx: 2, fill: DUNKEL }),
        s("rect", { x: 69, y: 6, width: 30, height: 60, rx: 3, fill: f.hell }),
        variante === MIT_LOGO ? [s("rect", { x: 10, y: 40, width: 40, height: 22, rx: 2, fill: "#ffffff" }), zeichen(11, 41, 38, 20)]
          : zeichen(8, 36, 40, 28, eigenes ? f.auf : null), ...text],
      register: [s("rect", { x: 8, y: 8, width: 44, height: 30, rx: 3, fill: "#ffffff", stroke: GRAU }), zeichen(10, 10, 40, 18),
        balken(12, 31, 26, DUNKEL, 2), ...[40, 62, 84].map((y, i) => s("rect", { x: 99, y, width: 6, height: 18, rx: 1, fill: i ? f.hell : f.akzent })),
        ...text],
    }[design];
    const fuss = design === "siegel" || (design === "raster" && eigenes)
      ? [zeichen(8, 132, 12, 9), balken(22, 135, 40)] : [balken(10, 135, 40)];
    const kopf = design === "raster" ? [s("rect", { x: 6, y: 0, width: 50, height: 6, fill: f.akzent }), s("rect", { x: 58, y: 0, width: 4, height: 6, fill: DUNKEL }),
      s("rect", { x: 64, y: 0, width: 35, height: 6, fill: f.hell })] : [];
    return s("svg", { viewBox: "0 0 232 150", "aria-hidden": "true", focusable: "false" },
      seite(1, deckblatt), seite(126, ...kopf, ...folge, ...fuss));
  }

  function kachel(name, wert, satz, mark, sperre = "") {
    const id = `d-zeichen-${wert}`;
    const grund = sperre ? el("span", { class: "mark-tile__reason", id: `${id}-grund` }, sperre) : null;
    return el("label", { class: "mark-tile", for: id },
      el("input", { type: "radio", name: "d-zeichen", id, value: wert, checked: zustand.zeichen === wert, disabled: Boolean(sperre),
        "aria-describedby": sperre ? `${id}-grund` : null }),
      el("span", { class: "mark-tile__mark" }, mark),
      el("span", { class: "mark-tile__text" }, el("strong", {}, name), el("span", {}, satz), grund));
  }

  function zeigeZeichen() {
    const f = farbenFuer(Z.wirksameFarbe(zustand, seiten.deckblatt).farbe);
    const initialen = zustand.initialen_wirksam || "";
    const kacheln = Z.VARIANTEN.map(v => kachel(v.name, v.wert, v.wert === Z.PASSEND ? Z.passendSatz(seiten.deckblatt) : v.satz,
      zeichenSvg(v.wert === Z.PASSEND ? Z.gezeichnet({ ...zustand, zeichen: Z.PASSEND }, seiten.deckblatt) : v.wert, initialen, f),
      Z.gesperrt(v.wert, initialen)));
    const logoSatz = du ? "Dein Logo statt der Initialen" : "Ihr Logo statt der Initialen";
    kacheln.push(kachel("Eigenes Logo", MIT_LOGO, logoSatz, zustand.logo ? zeichenSvg(MIT_LOGO, initialen, f) : null,
      zustand.logo ? "" : "Zuerst ein Logo wählen."));
    $("d-zeichen-liste").replaceChildren(...kacheln);
  }

  function farbfeld(name, wert, farbe, zusatz = "") {
    const id = `d-akzent-${wert.replace("#", "")}`;
    const gewaehlt = wert === EIGENE ? $("d-eigene-farbe-teil").hidden === false || Z.wirksameFarbe(zustand, seiten.deckblatt).quelle === "eigen"
      : zustand.akzent === wert;
    return el("label", { class: "mark-swatch", for: id },
      el("input", { type: "radio", name: "d-akzent", id, value: wert, checked: gewaehlt }),
      farbe ? s("svg", { viewBox: "0 0 40 40", class: "mark-swatch__chip", "aria-hidden": "true" },
        s("rect", { width: 40, height: 40, rx: 6, fill: farbe })) : el("span", { class: "mark-swatch__chip mark-swatch__chip--own" }),
      el("span", {}, name, zusatz ? el("span", { class: "mark-swatch__more" }, zusatz) : null));
  }

  function zeigeFarben() {
    const haupt = Z.hauptfarbe(seiten.deckblatt);
    const felder = [farbfeld("Passend zum Design", Z.PASSEND, haupt.farbe, `${haupt.name}, Farbe von ${Z.designName(seiten.deckblatt)}`),
      ...Z.FARBEN.map(f => farbfeld(f.name, f.farbe, f.farbe))];
    if (zustand.logo && zustand.logo.farbe) felder.push(farbfeld("Aus dem Logo", zustand.logo.farbe, zustand.logo.farbe, zustand.logo.farbe));
    felder.push(farbfeld("Eigene Farbe", EIGENE, null));
    $("d-akzent-liste").replaceChildren(...felder);
    if (Z.wirksameFarbe(zustand, seiten.deckblatt).quelle === "eigen") {
      $("d-eigene-farbe-teil").hidden = false;
      zeigePruefung(zustand.akzent);
    }
  }

  function zeigeLogo() {
    const logo = zustand.logo;
    $("d-logo-aktuell").hidden = !logo;
    $("d-logo-entfernen").hidden = !logo;
    $("d-logo-waehlen").textContent = logo ? "Anderes Logo wählen" : "Logo wählen";
    if (logo) {
      $("d-logo-bild").src = logoAdresse();
      const groesse = logo.vektor ? "Vektorgrafik" : `${logo.breite} × ${logo.hoehe} Pixel`;
      $("d-logo-info").textContent = `${du ? "Dein" : "Ihr"} Logo · ${groesse}${logo.durchsichtig ? ", durchsichtig" : ""}`;
    }
    $("d-logo-hinweise").replaceChildren(...(logo ? logo.hinweise : []).map(h => el("li", {}, h)));
  }

  function zeigeVorschau() {
    const design = seiten.deckblatt;
    $("d-vorschau").replaceChildren(vorschauSvg(design));
    $("d-vorschau").setAttribute("aria-label", Z.vorschauLabel(zustand, design, du));
    $("d-vorschau-text").textContent = `Deckblatt und Folgeseite in ${Z.designName(design)}. Vereinfacht; das PDF entsteht mit «Unterlagen erstellen».`;
    const mini = vorschauSvg(design);
    mini.setAttribute("viewBox", "0 0 107 150");
    $("d-zeichen-mini").replaceChildren(mini);
    $("d-zeichen-satz").textContent = Z.satzUnterDesign(zustand, seiten, du);
  }

  function zeigeAlles() {
    $("d-initialen").value = zustand.initialen;
    $("d-initialen").placeholder = zustand.initialen ? "" : zustand.initialen_wirksam;
    zeigeZeichen();
    zeigeFarben();
    zeigeLogo();
    zeigeVorschau();
  }

  async function speichere(pfad, body) {
    try {
      zustand = await senden(pfad, body);
      zeigeAlles();
      meldung(zustand.meldung, "ok");
    } catch (fehler) {
      meldung(`Nicht gespeichert. ${fehler.message}`, "fehler");
      zeigeAlles();
    }
  }

  function zeigePruefung(wert) {
    const pruefung = Z.pruefeFarbe(wert);
    $("d-eigene-farbe-pruefung").textContent = pruefung.meldung + (pruefung.vorschlag ? ` Vorschlag ${pruefung.vorschlag}` : "");
    $("d-vorschlag").hidden = !pruefung.vorschlag;
    $("d-vorschlag").dataset.farbe = pruefung.vorschlag || "";
    $("d-eigene-farbe-speichern").disabled = !pruefung.ok;
    if (/^#[0-9a-f]{6}$/.test(pruefung.farbe)) $("d-eigene-farbe-wahl").value = pruefung.farbe;
    $("d-eigene-farbe").value = wert;
    return pruefung;
  }

  $("d-zeichen-liste").addEventListener("change", event => speichere("/api/dossier/zeichen", { zeichen: event.target.value }));
  $("d-akzent-liste").addEventListener("change", event => {
    const wert = event.target.value;
    $("d-eigene-farbe-teil").hidden = wert !== EIGENE;
    if (wert === EIGENE) {
      zeigePruefung($("d-eigene-farbe").value || Z.wirksameFarbe(zustand, seiten.deckblatt).farbe);
      $("d-eigene-farbe").focus();
    } else speichere("/api/dossier/zeichen", { akzent: wert });
  });
  $("d-eigene-farbe").addEventListener("input", event => zeigePruefung(event.target.value));
  $("d-eigene-farbe-wahl").addEventListener("input", event => zeigePruefung(event.target.value));
  $("d-vorschlag").addEventListener("click", () => zeigePruefung($("d-vorschlag").dataset.farbe));
  $("d-eigene-farbe-speichern").addEventListener("click", () => {
    if (zeigePruefung($("d-eigene-farbe").value).ok) speichere("/api/dossier/zeichen", { akzent: $("d-eigene-farbe").value.trim().toLowerCase() });
  });
  $("d-initialen").addEventListener("change", event => speichere("/api/dossier/zeichen", { initialen: event.target.value.trim() }));
  $("d-logo-datei").addEventListener("change", async event => {
    const datei = event.target.files[0];
    event.target.value = "";
    if (!datei) return;
    try {
      await speichere("/api/dossier/logo", { daten: await alsBase64(datei) });
    } catch (fehler) {
      meldung(`Nicht gespeichert. ${fehler.message}`, "fehler");
    }
  });
  $("d-logo-entfernen").addEventListener("click", () => speichere("/api/dossier/logo-entfernen", {}));
  $("d-zeichen-zuruecksetzen").addEventListener("click", () => {
    $("d-eigene-farbe-teil").hidden = true;
    speichere("/api/dossier/zeichen-zuruecksetzen", {});
  });

  /** Follows the page: with a chosen dossier until sent; the state loads once, the designs with every load. */
  async function folge(event) {
    const b = event.detail.bewerbung;
    const zeigen = W.gewaehlt(b) === "dossier" && !b.versand;
    seiten = W.seitenDesigns(b);
    if (zeigen && zustand === null) {
      try {
        zustand = await holen("/api/dossier/zeichen");
      } catch (fehler) {
        meldung(`Zeichen und Farbe nicht lesbar: ${fehler.message}`, "fehler");
        return;
      }
    }
    const bereit = zeigen && zustand !== null && zustand.lebenslauf;
    $("d-zeichen-kurz").hidden = !bereit;
    $("d-zeichen-teil").hidden = !bereit;
    if (bereit) zeigeAlles();
  }

  document.addEventListener("bewerbung-geladen", folge);
  window.App.textsatz().then(satz => { du = satz !== "stelle-sie"; });
})();
