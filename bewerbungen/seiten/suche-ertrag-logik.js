"use strict";
// What the search brings on Suche einstellen (G103, #375), without DOM: the words of the yield line under each term,
// the caption under the list, the empty searches and the places. Every number comes from the app (search_yield.py);
// a «·» line is a list of parts that the page joins with dot-line.js. Texts in the app language through Texte (#425);
// terms, portals and places are data and stay as they are.
(global => {
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Under its own name, so each lookup reads Texte.t for the scanner; the page's Texte is found when a text is made.
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const VERSION_VORHER = "0.3.3";  // the first version that keeps the query behind each hit

  // Each count with its singular apart, since French and English need it (#425); written out, so the scanner reads each.
  const suchen = n => (n === 1 ? Texte.t("1 Suche") : Texte.t("{anzahl} Suchen", { anzahl: n }));
  const suchlaeufe = n => (n === 1 ? Texte.t("1 Suchlauf") : Texte.t("{anzahl} Suchläufen", { anzahl: n }));
  const treffer = n => (n === 1 ? Texte.t("1 Treffer") : Texte.t("{anzahl} Treffer", { anzahl: n }));
  const neu = n => (n === 1 ? Texte.t("1 neu") : Texte.t("{anzahl} neu", { anzahl: n }));
  const gut = n => (n === 1 ? Texte.t("1 ab Note 4") : Texte.t("{anzahl} ab Note 4", { anzahl: n }));
  const aussortiert = n => (n === 1 ? Texte.t("1 aussortiert") : Texte.t("{anzahl} aussortiert", { anzahl: n }));
  const ohnePflicht = n => (n === 1 ? Texte.t("1 ohne Pflichtbezug") : Texte.t("{anzahl} ohne Pflichtbezug", { anzahl: n }));
  const ausserhalb = n => (n === 1 ? Texte.t("1 ausserhalb der Region") : Texte.t("{anzahl} ausserhalb der Region", { anzahl: n }));
  const andere = n => (n === 1 ? Texte.t("andere 1") : Texte.t("andere {anzahl}", { anzahl: n }));

  /** The parts of the yield line of a term or place. One no run has searched yet has none before the first run and
   * says so once there are `laeufe`, e.g. a term added since. */
  function teile(eintrag, laeufe = 0) {
    if (!eintrag || !eintrag.suchen) return laeufe > 0 ? [Texte.t("noch nicht gesucht")] : [];
    const raus = eintrag.aussortiert > 0 ? aussortiert(eintrag.aussortiert) : "";
    if (!eintrag.treffer) return [suchen(eintrag.suchen), Texte.t("keine Treffer"), raus].filter(Boolean);
    const pflicht = eintrag.ohne_pflichtbezug > 0 ? ohnePflicht(eintrag.ohne_pflichtbezug) : "";  // G110
    const region = eintrag.ausserhalb_region > 0 ? ausserhalb(eintrag.ausserhalb_region) : "";  // G111
    return [suchen(eintrag.suchen), treffer(eintrag.treffer), neu(eintrag.neu), gut(eintrag.ab_note_4), raus, pflicht, region]
      .filter(Boolean);
  }

  /** What a hit counts like: per occupation for apprenticeships, per term with the title filter for jobs; with
   * `pflicht` (some hit had no required word, G110) also what that reason means. */
  function zaehlen(lehrstelle, pflicht) {
    if (lehrstelle) return Texte.t("Findet die Suche eine Lehrstelle über mehrere Berufe, zählt sie bei jedem.");
    return pflicht
      ? Texte.t("Findet die Suche eine Stelle über mehrere Begriffe, zählt sie bei jedem. „Aussortiert“ heisst: Der Titelfilter hat den Titel nicht durchgelassen. „Ohne Pflichtbezug“: Titel und Inserat nennen keines der Pflichtwörter des Begriffs.")
      : Texte.t("Findet die Suche eine Stelle über mehrere Begriffe, zählt sie bei jedem. „Aussortiert“ heisst: Der Titelfilter hat den Titel nicht durchgelassen.");
  }

  /** The one caption on the numbers under the list: from how many runs they come and how a hit counts. */
  function hinweis(laeufe, lehrstelle, pflicht = false) {
    if (!laeufe) {
      return lehrstelle ? Texte.t("Nach dem nächsten Suchlauf steht hier bei jedem Beruf, was er bringt.")
        : Texte.t("Nach dem nächsten Suchlauf steht hier bei jedem Begriff, was er bringt.");
    }
    const werte = { anzahl: laeufe, zaehlen: zaehlen(lehrstelle, pflicht) };
    return laeufe === 1 ? Texte.t("Die Zahlen stammen aus dem letzten Suchlauf. {zaehlen}", werte)
      : Texte.t("Die Zahlen stammen aus den letzten {anzahl} Suchläufen. {zaehlen}", werte);
  }

  /** The summary of the details on hits without a required word (G110): how many there were in all. */
  function pflichtTitel(eintraege) {
    const summe = eintraege.reduce((bisher, e) => bisher + e.anzahl, 0);
    return summe === 1 ? Texte.t("Ohne Pflichtbezug aussortiert (1)") : Texte.t("Ohne Pflichtbezug aussortiert ({anzahl})", { anzahl: summe });
  }

  const zitiert = titel => Texte.t("„{begriff}“", { begriff: titel });

  /** One term of those details, with up to three titles of its own last run. */
  function pflichtZeile(eintrag) {
    const beispiele = (eintrag.beispiele || []).slice(0, 3).map(zitiert);
    // hits of every search over the runs, not postings counted once («Stellen» since #383)
    const werte = { begriff: eintrag.begriff, anzahl: eintrag.anzahl, beispiel: beispiele[0], beispiele: beispiele.join(", ") };
    if (eintrag.anzahl === 1) {
      return beispiele.length ? Texte.t("„{begriff}“: 1 Treffer, {beispiel}", werte) : Texte.t("„{begriff}“: 1 Treffer", werte);
    }
    return beispiele.length ? Texte.t("„{begriff}“: {anzahl} Treffer, zum Beispiel {beispiele}", werte)
      : Texte.t("„{begriff}“: {anzahl} Treffer", werte);
  }

  /** What outside the region means, in the person's form of address (G111). */
  const ausserhalbSatz = (satz, du) => (du
    ? Texte.t("{satz} „Ausserhalb der Region“: Die Stelle liegt ausserhalb deiner Kantone und Orte, und das Inserat nennt kein Remote.", { satz })
    : Texte.t("{satz} „Ausserhalb der Region“: Die Stelle liegt ausserhalb Ihrer Kantone und Orte, und das Inserat nennt kein Remote.", { satz }));

  /** The first line of «Was die Orte bringen»: where the numbers come from and what a place-less search is; with
   * `ausserhalb` (a niche hit lay outside the region, G111) also what that means. */
  function ortHinweis(laeufe, ausserhalb = false, du = false) {
    const satz = laeufe === 1
      ? Texte.t("Aus dem letzten Suchlauf, gezählt wie bei den Suchbegriffen. „Ohne Ort“ sind Suchen ohne Ortsangabe, etwa für die Nischen.")
      : Texte.t("Aus den letzten {anzahl} Suchläufen, gezählt wie bei den Suchbegriffen. „Ohne Ort“ sind Suchen ohne Ortsangabe, etwa für die Nischen.", { anzahl: laeufe });
    return ausserhalb ? ausserhalbSatz(satz, du) : satz;
  }

  const MAX_ORTE_AUSSERHALB = 3;

  /** The caption under the niche row (G111): where its hits outside the region lay, at most three places; '' without. */
  function ausserhalbOrte(eintrag) {
    const orte = ((eintrag && eintrag.ausserhalb_orte) || []).slice(0, MAX_ORTE_AUSSERHALB).map(o => `${o.ort} ${o.anzahl}`);
    if (!orte.length) return "";
    const rest = eintrag.ausserhalb_andere > 0 ? [andere(eintrag.ausserhalb_andere)] : [];
    return Texte.t("Ausserhalb der Region, ohne Remote: {orte}", { orte: [...orte, ...rest].join(", ") });
  }

  /** Hits from runs before the app kept the query; '' when there are none. */
  function ohneAngabe(zahl, lehrstelle) {
    if (!zahl) return "";
    const werte = { anzahl: zahl, version: VERSION_VORHER };
    if (zahl === 1) {
      return lehrstelle
        ? Texte.t("Ohne Angabe: 1 Treffer aus Suchläufen vor Version {version}. Über welchen Beruf sie kamen, hat die App damals nicht festgehalten.", werte)
        : Texte.t("Ohne Angabe: 1 Treffer aus Suchläufen vor Version {version}. Über welchen Begriff sie kamen, hat die App damals nicht festgehalten.", werte);
    }
    return lehrstelle
      ? Texte.t("Ohne Angabe: {anzahl} Treffer aus Suchläufen vor Version {version}. Über welchen Beruf sie kamen, hat die App damals nicht festgehalten.", werte)
      : Texte.t("Ohne Angabe: {anzahl} Treffer aus Suchläufen vor Version {version}. Über welchen Begriff sie kamen, hat die App damals nicht festgehalten.", werte);
  }

  const leerTitel = (zahl, lehrstelle) => (lehrstelle ? Texte.t("Wo ein Beruf nichts findet ({anzahl})", { anzahl: zahl })
    : Texte.t("Wo ein Begriff nichts findet ({anzahl})", { anzahl: zahl }));

  function leerZeile(eintrag) {
    const werte = { begriff: eintrag.begriff, portal: eintrag.portal, suchen: suchen(eintrag.suchen), laeufe: suchlaeufe(eintrag.laeufe) };
    return eintrag.nische ? Texte.t("„{begriff}“ (Nische) auf {portal}: {suchen} in {laeufe}, kein Treffer.", werte)
      : Texte.t("„{begriff}“ auf {portal}: {suchen} in {laeufe}, kein Treffer.", werte);
  }

  /** A place the way its portal searches it: a town, a postcode, a region of ictjobs or the cantons of job-room. */
  function ortName(eintrag) {
    const { portal, ort } = eintrag;
    if (eintrag.nischen) return Texte.t("Ohne Ort (Nischen)");  // every portal's niche searches in one row (G111)
    if (!ort) return Texte.t("{portal}, ohne Ort", { portal });
    if (portal === "jobscout24") return Texte.t("{portal}, PLZ {ort}", { portal, ort });
    if (portal === "job-room") {
      return ort.includes(",") ? Texte.t("{portal}, Kantone {ort}", { portal, ort }) : Texte.t("{portal}, Kanton {ort}", { portal, ort });
    }
    return `${portal}, ${eintrag.ort_name || ort}`;
  }

  /** The yield of each term by its name as the term list shows it. */
  const nachBegriff = ertrag => new Map(((ertrag && ertrag.begriffe) || []).map(eintrag => [eintrag.begriff, eintrag]));

  const logik = { get OHNE_ERTRAG() { return Texte.t("ohne Ertrag"); }, teile, hinweis, ortHinweis, ohneAngabe, leerTitel,
    leerZeile, ortName, nachBegriff, pflichtTitel, pflichtZeile, ausserhalbOrte };
  if (typeof module !== "undefined") module.exports = logik;
  else global.SucheErtragLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
