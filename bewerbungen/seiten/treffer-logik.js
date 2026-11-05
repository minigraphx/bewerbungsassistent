"use strict";
// Rating hits in packages (MIN-372): what to rate, which buttons to offer, the run itself. No DOM, so it can be tested.
(function (global) {
  /** Hits that can be rated now: near the home first, then the newest, so the limit of a run takes those. */
  function zuBewerten(treffer) {
    return treffer
      .filter(t => t.zustand === "neu" && !t.bewertung && !t.ohne_text)
      .sort((a, b) => Number(Boolean(b.nah)) - Number(Boolean(a.nah))
        || (b.gefunden_am || "").localeCompare(a.gefunden_am || ""));
  }

  /** The buttons depend on how many hits are open: „Alle“ only when there are more than one package. */
  function knoepfe(offen, paket, grenze) {
    if (offen === 0) return [];
    if (offen <= paket) return [{ text: `Bewerten (${offen})`, anzahl: offen }];
    const alle = offen > grenze ? { text: `Nächste ${grenze} bewerten`, anzahl: grenze } : { text: `Alle bewerten (${offen})`, anzahl: offen };
    return [{ text: `Nächste ${paket} bewerten`, anzahl: paket }, alle];
  }

  /** True once every new hit has a grade; hits without text stay open, so the message does not claim too much. */
  function alleBewertet(treffer) {
    const neue = treffer.filter(t => t.zustand === "neu");
    return neue.length > 0 && neue.every(t => t.bewertung);
  }

  /** Own stars of the profession first, then the grade, then near the home, then the newest. Hits without a profession count as no stars. */
  function sortiert(treffer, sterne) {
    const eigene = t => sterne[t.beruf] || 0;
    return [...treffer].sort((a, b) => eigene(b) - eigene(a)
      || (b.bewertung?.note ?? 0) - (a.bewertung?.note ?? 0)
      || Number(Boolean(b.nah)) - Number(Boolean(a.nah))
      || (b.gefunden_am || "").localeCompare(a.gefunden_am || ""));
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
   * An error of connection, access or budget ends the run, what was rated stays.
   * mittel: { paket, sende(ids) → answer, angehalten() → bool, fortschritt(stand, hits) }.
   */
  async function bewerteAlle(ids, { paket, sende, angehalten, fortschritt }) {
    let stand = { bewertet: 0, ohneText: 0, kosten: 0, offen: [], fehler: "", gestoppt: false, von: ids.length };
    const runden = [...pakete(ids, paket).map(gruppe => ({ gruppe, nochmals: gruppe.length > 1 }))];
    while (runden.length) {
      if (angehalten()) return { ...stand, gestoppt: true };
      const { gruppe, nochmals } = runden.shift();
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

  /** Average cost per hit so far, from the ratings themselves; null while there are none. */
  function kostenProTreffer(treffer) {
    const kosten = treffer.map(t => t.bewertung?.kosten_usd).filter(k => typeof k === "number");
    return kosten.length ? kosten.reduce((summe, k) => summe + k, 0) / kosten.length : null;
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

  const logik = { sucheText, wahlAus, beideArten, nachArt, istSchnupperlehre, zuBewerten, knoepfe, alleBewertet, sortiert, pakete, bewerteAlle, kostenProTreffer, nachpruefungText };
  if (typeof module !== "undefined") module.exports = logik;
  else global.TrefferLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
