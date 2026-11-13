"use strict";
// What the page „Einstellungen“ shows (#265, A10), without DOM so it can be tested: its sections, which section an
// anchor opens, which way to the AI is in use and the budget of the month (G46).
(function (global) {
  const SECTIONS = [
    { id: "ki", label: "KI und Budget" },
    { id: "suche", label: "Suche und Portale" },
    { id: "erweiterung", label: "Browser-Erweiterung" },
    { id: "wahl", label: "Stelle, Lehrstelle, RAV" },
    { id: "daten", label: "Daten und Sicherung" },
    { id: "erweitert", label: "Erweitert" },
    { id: "ueber", label: "Über die App" },
  ];
  const FIRST = SECTIONS[0].id;
  // Anchors that other pages and the guide link to, from the time the page was one long list.
  const SECTION_OF_ANCHOR = {
    kosten: "ki", einwilligung: "ki", "schluessel-teil": "ki", "claude-abo": "ki", einladung: "ki", zugang: "ki",
    vorabversionen: "erweitert", seitengrenze: "erweitert", daten: "daten", "ueber-die-app": "ueber",
  };
  const WAY_OF_ANCHOR = { "schluessel-teil": "schluessel", "claude-abo": "abo", einladung: "einladung" };
  // The card under the choice that asks for what the chosen way needs.
  const WAY_CARDS = { einladung: "zugang-einladung", abo: "claude-abo", schluessel: "schluessel-teil" };
  const MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
                  "November", "Dezember"];
  // The tasks of the cost log (bewerbungen/ai/tasks.py MODELS) as the person knows them.
  const TASK_LABELS = {
    rate: "Stellen einschätzen", rate_package: "Stellen einschätzen",
    draft: "Anschreiben entwerfen", review: "Anschreiben prüfen", dossier_texts: "Texte fürs Dossier",
    chat: "Fragen an die KI", prefill: "Angaben vorbefüllen",
    form_fields: "Formulare ausfüllen", form_answers: "Formulare ausfüllen",
    career: "Suchbegriffe vorschlagen", terms: "Suchbegriffe prüfen", site_list: "Weitere Seiten lesen",
  };
  const OTHER = "Weitere";
  const MEDIATION_NOTE = "Ist das Budget aufgebraucht, läuft die App weiter, nur ohne KI. Protokolliert werden Kosten, keine Inhalte.";
  const OWN_NOTE = "Massgebend ist die Abrechnung von Anthropic. Protokolliert werden Kosten, keine Inhalte.";

  const anchor = hash => String(hash || "").replace(/^#/, "");

  /** The section an anchor belongs to; the first one for an empty or unknown anchor. */
  function sectionOf(hash) {
    const name = anchor(hash);
    if (SECTIONS.some(section => section.id === name)) return name;
    return SECTION_OF_ANCHOR[name] || FIRST;
  }

  /** The way to the AI an anchor asks for, or null. */
  function wayOf(hash) {
    return WAY_OF_ANCHOR[anchor(hash)] || null;
  }

  /** The way the app uses now, from GET /api/ki/status and GET /api/claude/stand (null outside the packaged app). */
  function currentWay(ki, abo) {
    if (ki && ki.eingerichtet && ki.eigener_schluessel) return "schluessel";
    if (ki && ki.eingerichtet && ki.vermittlung) return "einladung";
    if (abo && abo.zugang) return "abo";
    return null;
  }

  /** What the part „Einladungscode“ says: it runs, a code can be entered, the own key wins, or there is no mediation. */
  function invitationState(ki) {
    if (!ki) return "keine";
    if (ki.eingerichtet && ki.vermittlung) return "aktiv";
    if (ki.eingerichtet && ki.eigener_schluessel) return "schluessel";
    return ki.einladung ? "eingeben" : "keine";
  }

  // A decimal point, as the design system says.
  const usd = value => `USD ${Math.max(0, Number(value) || 0).toFixed(2)}`;
  const amount = value => Math.max(0, Number(value) || 0).toFixed(2);

  function monthParts(month) {
    const found = /^(\d{4})-(\d{2})$/.exec(month || "");
    if (!found || Number(found[2]) < 1 || Number(found[2]) > 12) return null;
    return { year: Number(found[1]), month: Number(found[2]) };
  }

  function renewal(month) {
    const parts = monthParts(month);
    if (!parts) return null;
    const next = parts.month === 12 ? { year: parts.year + 1, month: 1 } : { year: parts.year, month: parts.month + 1 };
    return `Neues Budget am 01.${String(next.month).padStart(2, "0")}.${next.year}`;
  }

  function rows(tasks) {
    const grouped = Object.entries(tasks || {}).reduce((sum, [task, value]) => {
      const label = TASK_LABELS[task] || OTHER;
      const before = sum[label] || { count: 0, cost: 0 };
      const count = Number.isInteger(value && value.aufrufe) ? value.aufrufe : 0;
      const cost = Number(value && value.usd) || 0;
      return { ...sum, [label]: { count: before.count + count, cost: before.cost + cost } };
    }, {});
    return Object.entries(grouped)
      .sort(([labelA, a], [labelB, b]) => (labelA === OTHER) - (labelB === OTHER) || b.cost - a.cost || b.count - a.count)
      .map(([label, value]) => ({ label, count: value.count, usd: usd(value.cost) }));
  }

  /** The card „Budget“ from GET /api/ki/status (may be null) and the costs of GET /api/schluessel. */
  function budgetView(ki, costs) {
    const parts = monthParts(ki && ki.monat);
    const when = parts ? `im ${MONTHS[parts.month - 1]}` : "in diesem Monat";
    const local = costs || {};
    const common = {
      rows: rows(local.aufgaben),
      total: `Seit Beginn ${usd(local.gesamt_usd)} in ${Number.isInteger(local.aufrufe) ? local.aufrufe : 0} Aufrufen`,
    };
    if (ki && ki.vermittlung && typeof ki.budget_usd === "number" && ki.budget_usd > 0) {
      const spent = Math.max(0, Number(ki.verbraucht_usd) || 0);
      return {
        ...common, title: `Budget ${when}`, headline: `USD ${amount(spent)} von ${amount(ki.budget_usd)} gebraucht`,
        renewal: renewal(ki.monat), percent: Math.min(100, Math.round((spent / ki.budget_usd) * 100)), note: MEDIATION_NOTE,
      };
    }
    const own = Boolean(ki && ki.eingerichtet && ki.eigener_schluessel);
    return {
      ...common, title: `Kosten ${when}`, headline: `${usd(local.monat_usd)}${own ? " mit eigenem Schlüssel" : ""}`,
      renewal: null, percent: null, note: OWN_NOTE,
    };
  }

  const logic = { SECTIONS, WAY_CARDS, sectionOf, wayOf, currentWay, invitationState, budgetView };
  if (typeof module !== "undefined") module.exports = logic;
  else global.EinstellungenLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
