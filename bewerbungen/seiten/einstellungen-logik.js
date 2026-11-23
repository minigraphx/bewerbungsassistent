"use strict";
// What the page „Einstellungen“ shows (#265, A10), without DOM so it can be tested: its sections, which section an
// anchor opens, which way to the AI is in use, the monthly budget of the code (G46, G98) or the costs of the month.
(function (global) {
  const SECTIONS = [
    { id: "ki", label: "KI, Budget und Sprache" },
    { id: "suche", label: "Suche und Portale" },
    { id: "erweiterung", label: "Browser und Erweiterung" },
    { id: "wahl", label: "Stelle, Lehrstelle, RAV" },
    { id: "daten", label: "Daten und Sicherung" },
    { id: "erweitert", label: "Erweitert" },
    { id: "ueber", label: "Über die App" },
  ];
  const FIRST = SECTIONS[0].id;
  // Anchors that other pages and the guide link to, from the time the page was one long list.
  const SECTION_OF_ANCHOR = {
    kosten: "ki", einwilligung: "ki", sprache: "ki", "schluessel-teil": "ki", "claude-abo": "ki", einladung: "ki", zugang: "ki",
    vorabversionen: "erweitert", seitengrenze: "erweitert", daten: "daten", "ueber-die-app": "ueber",
    browser: "erweiterung",
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
    exclusions: "Ausschlüsse vorschlagen", cv_suggestions: "Lebenslauf für eine Stelle",
  };
  const OTHER = "Weitere";
  const MEDIATION_NOTE = "Das Budget gilt pro Monat und erneuert sich am Monatsersten; was übrig bleibt, geht nicht in "
    + "den nächsten Monat mit. Ist es aufgebraucht, läuft die App weiter, nur ohne KI. Protokolliert werden Kosten, keine Inhalte.";
  // A mediation that names no renewal still counts a one-time credit (G80).
  const MEDIATION_NOTE_ONCE = "Das Guthaben gilt einmal und erneuert sich nicht. Ist es aufgebraucht, läuft die App weiter, "
    + "nur ohne KI, bis ein neuer Einladungscode eingelöst ist. Protokolliert werden Kosten, keine Inhalte.";
  // With the mediation the person sees CHF (G46); one USD billed counts as one CHF (ai/usage.py CHF_PER_USD).
  const MEDIATION_CURRENCY = "CHF";
  const OWN_CURRENCY = "USD";
  const OWN_NOTE = "Massgebend ist die Abrechnung von Anthropic. Protokolliert werden Kosten, keine Inhalte.";

  // Loaded before this file on the page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);

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

  const viaMediation = ki => Boolean(ki && ki.eingerichtet && ki.vermittlung);
  const hasCredit = ki => viaMediation(ki) && typeof ki.guthaben_chf === "number" && ki.guthaben_chf > 0;
  const creditUsedUp = ki => hasCredit(ki) && (Number(ki.verbraucht_chf) || 0) >= ki.guthaben_chf;

  /**
   * What the part „Einladungscode“ says: it runs, its budget is used up (the field for a code stays, G98),
   * a code can be entered, the own key wins, or there is no mediation.
   */
  function invitationState(ki) {
    if (!ki) return "keine";
    if (creditUsedUp(ki)) return "aufgebraucht";
    if (viaMediation(ki)) return "aktiv";
    if (ki.eingerichtet && ki.eigener_schluessel) return "schluessel";
    return ki.einladung ? "eingeben" : "keine";
  }

  // A decimal point, as the design system says.
  const money = (value, currency) => `${currency}\u00a0${Math.max(0, Number(value) || 0).toFixed(2)}`;

  function monthParts(month) {
    const found = /^(\d{4})-(\d{2})$/.exec(month || "");
    if (!found || Number(found[2]) < 1 || Number(found[2]) > 12) return null;
    return { year: Number(found[1]), month: Number(found[2]) };
  }

  function rows(tasks, currency) {
    const grouped = Object.entries(tasks || {}).reduce((sum, [task, value]) => {
      const label = TASK_LABELS[task] || OTHER;
      const before = sum[label] || { count: 0, cost: 0 };
      const count = Number.isInteger(value && value.aufrufe) ? value.aufrufe : 0;
      const cost = Number(value && value.usd) || 0;
      return { ...sum, [label]: { count: before.count + count, cost: before.cost + cost } };
    }, {});
    return Object.entries(grouped)
      .sort(([labelA, a], [labelB, b]) => (labelA === OTHER) - (labelB === OTHER) || b.cost - a.cost || b.count - a.count)
      .map(([label, value]) => ({ label, count: value.count, usd: money(value.cost, currency) }));
  }

  /** The month of the budget and its renewal as the mediation names them (G98); null for a one-time credit. */
  const budgetMonth = ki => (hasCredit(ki) ? texts().budgetMonth(ki) : null);

  /**
   * The sentence of „Einladungscode“ while the code works; null keeps the page's own sentence of G80, so an app that
   * ships before the mediation's monthly budget still says what is true.
   */
  const invitationActive = ki => (budgetMonth(ki)
    ? "Die KI läuft über die Vermittlung des Pilots, mit einem Budget pro Monat. Was davon verbraucht ist, steht unter KI-Budget."
    : null);

  /** The sentence of „Einladungscode“ once the budget is used up; null keeps the page's own sentence of G80. */
  function invitationUsedUp(ki) {
    const budget = creditUsedUp(ki) && budgetMonth(ki);
    return budget ? `Das KI-Budget für ${budget.month} ist aufgebraucht. Die KI geht wieder ab ${budget.renews}.` : null;
  }

  function mediationBudget(ki, common) {
    const spent = Math.max(0, Number(ki.verbraucht_chf) || 0);
    const percent = Math.min(100, Math.round((spent / ki.guthaben_chf) * 100));
    const headline = `${money(spent, MEDIATION_CURRENCY)} von ${money(ki.guthaben_chf, MEDIATION_CURRENCY)} verbraucht`;
    const budget = budgetMonth(ki);
    if (!budget) {
      return { ...common, title: "Guthaben", headline, percent, barLabel: `${percent} Prozent des Guthabens verbraucht`,
               note: MEDIATION_NOTE_ONCE };
    }
    return {
      ...common, title: `KI-Budget im ${budget.month}`, headline, percent,
      barLabel: `${percent} Prozent des KI-Budgets für ${budget.month} verbraucht`,
      renewal: `Neues Budget am ${budget.renews}`, note: MEDIATION_NOTE,
      usedUp: creditUsedUp(ki)
        ? `Das KI-Budget für ${budget.month} ist aufgebraucht. Die KI geht wieder ab ${budget.renews}; alles andere funktioniert weiterhin.`
        : null,
    };
  }

  /**
   * The card „KI-Budget“ from GET /api/ki/status (may be null) and the costs of GET /api/schluessel: with the mediation
   * the budget of its month in CHF (G98), or a one-time credit when it names no renewal (G80); otherwise the costs of
   * the month in USD. The costs of the log count 1:1.
   */
  function budgetView(ki, costs) {
    const local = costs || {};
    const currency = viaMediation(ki) ? MEDIATION_CURRENCY : OWN_CURRENCY;
    const common = {
      rows: rows(local.aufgaben, currency),
      total: `Seit Beginn ${money(local.gesamt_usd, currency)} in ${Number.isInteger(local.aufrufe) ? local.aufrufe : 0} Aufrufen`,
      renewal: null,
      usedUp: null,
    };
    if (hasCredit(ki)) return mediationBudget(ki, common);
    const parts = monthParts(ki && ki.monat);
    const when = parts ? `im ${MONTHS[parts.month - 1]}` : "in diesem Monat";
    const own = Boolean(ki && ki.eingerichtet && ki.eigener_schluessel);
    return {
      ...common, title: `Kosten ${when}`, headline: `${money(local.monat_usd, currency)}${own ? " mit eigenem Schlüssel" : ""}`,
      percent: null, barLabel: "", note: OWN_NOTE,
    };
  }

  /** The month whose rows per task the card shows: the mediation's month of the budget, or null for this clock's. */
  const costMonth = ki => (budgetMonth(ki) ? ki.monat : null);

  const logic = { SECTIONS, WAY_CARDS, sectionOf, wayOf, currentWay, invitationState, invitationActive, invitationUsedUp,
                  budgetView, costMonth };
  if (typeof module !== "undefined") module.exports = logic;
  else global.EinstellungenLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
