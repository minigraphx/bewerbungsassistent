"use strict";
// What the sidebar shows (#259, G54), without DOM so it can be tested: which destination a page belongs to,
// the badges and the AI budget at the bottom (G46, G98; G80 for a mediation that names no renewal).
(function (global) {
  // Pages without their own place in the sidebar belong to the destination they are reached from. The setup
  // (/einrichtung) is reached from Einstellungen but is no part of it, so it marks nothing (#279).
  const TARGET_OF_PAGE = {
    "/": "heute",
    "/bewerbungen": "bewerbungen", "/bewerbung": "bewerbungen",
    "/treffer": "stellen", "/suchbegriffe": "stellen", "/firmen": "stellen", "/suche-einstellen": "stellen",
    "/angaben": "angaben", "/inhalte": "angaben",
    "/dateien": "dateien", "/foto": "dateien", "/entwuerfe": "dateien",
    "/fragen": "fragen",
    "/einstellungen": "einstellungen",
  };
  const MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
                  "November", "Dezember"];
  // Asking for the credit reaches the mediation, so a tab asks again only after a while.
  const BUDGET_MAX_AGE_MS = 5 * 60 * 1000;
  // From this share used the sidebar warns in words (#211): a bar in another colour alone is easy to miss.
  const NEARLY_USED_SHARE = 0.8;
  // A mediation that names no renewal counts a one-time credit (G80): once used up, a new code brings a new one.
  const WARNINGS = {
    low: { long: "Guthaben fast aufgebraucht", short: "fast aufgebraucht" },
    empty: { long: "Guthaben aufgebraucht: neuen Code anfordern", short: "aufgebraucht" },
  };
  const NO_MEDIATION_CREDIT = { long: "Kein Guthaben der Vermittlung", short: "kein Guthaben der Vermittlung" };
  // With the mediation the person sees CHF (G46); one USD billed counts as one CHF (ai/usage.py CHF_PER_USD).
  const MEDIATION_CURRENCY = "CHF";
  const OWN_CURRENCY = "USD";
  // Currency and amount never part at the end of a line (#336); read aloud as a space.
  const NBSP = "\u00a0";
  // Fired on the document when a page changed which hits the list shows, so „N neu“ counts again (#303).
  const HITS_CHANGED = "treffer-geaendert";

  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);

  function activeTarget(page) {
    return TARGET_OF_PAGE[page] || null;
  }

  const count = value => (Number.isInteger(value) && value > 0 ? value : 0);

  /** Badges only where something waits: the things due today and the new hits of the search. */
  function badges({ open, newHits } = {}) {
    const due = count(open);
    const fresh = count(newHits);
    return {
      heute: due ? { long: `${due} offen`, short: String(due) } : null,
      stellen: fresh ? { long: `${fresh} neu`, short: `${fresh} neu` } : null,
    };
  }

  // A decimal point, as the design system says.
  const usd = value => value.toFixed(2);
  const NOTHING_USED = "Noch nichts verbraucht";

  /** The currency of the AI costs a page shows, from GET /api/ki/status (may be null). */
  function currencyOf(status) {
    return status && status.eingerichtet && status.vermittlung ? MEDIATION_CURRENCY : OWN_CURRENCY;
  }

  function monthName(month) {
    const found = /^\d{4}-(\d{2})$/.exec(month || "");
    const name = found ? MONTHS[Number(found[1]) - 1] : undefined;
    return name ? `im ${name}` : "in diesem Monat";
  }

  function creditState(spent, credit) {
    if (spent >= credit) return "empty";
    return spent >= credit * NEARLY_USED_SHARE ? "low" : "ok";
  }

  const chf = value => `${MEDIATION_CURRENCY}${NBSP}${usd(value)}`;

  function amounts(status) {
    const credit = status.guthaben_chf;
    const spent = Math.max(0, Number(status.verbraucht_chf) || 0);
    return { credit, spent, percent: Math.min(100, Math.round((spent / credit) * 100)),
             left: `${chf(Math.max(0, credit - spent))} frei`, state: creditState(spent, credit) };
  }

  /** The budget of this month (G98), in the words of the UI/UX review of 20.11.2026. */
  function monthlyBudget(status, { month, renews }) {
    const { credit, spent, percent, left, state } = amounts(status);
    const short = `KI-Budget: ${left}`;
    const warning = { low: `Fast aufgebraucht. Neues Budget am ${renews}.`, empty: `Aufgebraucht. Die KI geht wieder ab ${renews}.` };
    const narrow = { ok: short, low: `${short} · fast aufgebraucht`, empty: `KI-Budget: wieder ab ${renews}` };
    return {
      title: `KI-Budget ${month}`,
      text: spent > 0 ? `${chf(spent)} von ${chf(credit)} verbraucht` : `${chf(credit)} frei`,
      short,
      percent,
      label: spent > 0 ? `${percent} Prozent des KI-Budgets für ${month} verbraucht` : NOTHING_USED,
      detail: spent > 0 ? left : NOTHING_USED,
      warning: warning[state] || "",
      state,
      narrow: narrow[state],
    };
  }

  function mediationCredit(status) {
    const budget = texts().budgetMonth(status);
    if (budget) return monthlyBudget(status, budget);
    const { credit, spent, percent, left, state } = amounts(status);
    const warning = WARNINGS[state];
    const short = `KI-Guthaben: ${left}`;
    // the same words as Einstellungen and the page „KI“ (#347): the currency on both amounts, «verbraucht»
    return {
      title: "KI-Guthaben",
      text: spent > 0 ? `${chf(spent)} von ${chf(credit)} verbraucht` : `${chf(credit)} frei`,
      short,
      percent,
      label: spent > 0 ? `${percent} Prozent des Guthabens verbraucht` : NOTHING_USED,
      detail: spent > 0 ? left : NOTHING_USED,
      warning: warning ? warning.long : "",
      state,
      narrow: warning ? `${short} · ${warning.short}` : short,
    };
  }

  function ownKeyCosts(status, when) {
    const costs = usd(Math.max(0, Number(status.kosten_usd) || 0));
    const short = `KI-Kosten: ${OWN_CURRENCY}${NBSP}${costs}`;
    return {
      title: `KI-Kosten ${when}`, text: `${OWN_CURRENCY}${NBSP}${costs} mit eigenem Schlüssel`, short, percent: null, label: "",
      detail: NO_MEDIATION_CREDIT.long, warning: "", state: "own", narrow: `${short} · ${NO_MEDIATION_CREDIT.short}`,
    };
  }

  /**
   * The AI at the bottom of the sidebar, from GET /api/ki/status; null when there is nothing to show. `detail` is
   * what is left (or that no credit applies), `warning` names a credit nearly or wholly used, `narrow` is the line
   * of the header below 900 px. The budget of the mediation names its month (G98); a mediation that names no
   * renewal counts a credit once per code, which names no month (G80).
   */
  function budgetView(status) {
    if (!status || !status.eingerichtet) return null;
    if (status.vermittlung && typeof status.guthaben_chf === "number" && status.guthaben_chf > 0) {
      return mediationCredit(status);
    }
    if (!status.vermittlung && status.eigener_schluessel) return ownKeyCosts(status, monthName(status.monat));
    return null;
  }

  /** Midnight of the day the budget renews, on this computer's calendar; null when the status names no renewal. */
  function renewalTime(status) {
    const found = /^(\d{4})-(\d{2})-(\d{2})$/.exec((status && status.erneuert_am) || "");
    return found ? new Date(Number(found[1]), Number(found[2]) - 1, Number(found[3])).getTime() : null;
  }

  /**
   * A stored answer { at, status } still counts when it is younger than the limit, not from the future and not from
   * before the day the budget renews (G98), so a new month never shows the spend of the old one.
   */
  function isFresh(entry, now, maxAge = BUDGET_MAX_AGE_MS) {
    if (!entry || typeof entry.at !== "number") return false;
    const age = now - entry.at;
    const renews = renewalTime(entry.status);
    return age >= 0 && age <= maxAge && (renews === null || now < renews);
  }

  const logic = { BUDGET_MAX_AGE_MS, NEARLY_USED_SHARE, HITS_CHANGED, activeTarget, badges, budgetView, currencyOf, isFresh };
  if (typeof module !== "undefined") module.exports = logic;
  else global.SidebarLogic = logic;
})(typeof window !== "undefined" ? window : globalThis);
