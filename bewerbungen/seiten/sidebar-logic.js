"use strict";
// What the sidebar shows (#259, G54), without DOM so it can be tested: which destination a page belongs to,
// the badges and the AI budget at the bottom.
(function (global) {
  // Pages without their own place in the sidebar belong to the destination they are reached from.
  const TARGET_OF_PAGE = {
    "/": "heute",
    "/bewerbung": "bewerbungen",
    "/treffer": "stellen", "/suchbegriffe": "stellen", "/firmen": "stellen",
    "/angaben": "angaben", "/inhalte": "angaben",
    "/dateien": "dateien", "/foto": "dateien", "/entwuerfe": "dateien",
    "/fragen": "fragen",
    "/einstellungen": "einstellungen", "/einrichtung": "einstellungen",
  };
  const MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
                  "November", "Dezember"];
  // Asking for the budget reaches the mediation, so a tab asks again only after a while.
  const BUDGET_MAX_AGE_MS = 5 * 60 * 1000;

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

  function monthName(month) {
    const found = /^\d{4}-(\d{2})$/.exec(month || "");
    const name = found ? MONTHS[Number(found[1]) - 1] : undefined;
    return name ? `im ${name}` : "in diesem Monat";
  }

  function mediationBudget(status, when) {
    const budget = status.budget_usd;
    const spent = Math.max(0, Number(status.verbraucht_usd) || 0);
    const percent = Math.min(100, Math.round((spent / budget) * 100));
    return {
      title: `KI-Budget ${when}`,
      text: spent > 0 ? `USD ${usd(spent)} von ${usd(budget)} gebraucht` : `USD ${usd(budget)} frei`,
      short: `KI-Budget: USD ${usd(Math.max(0, budget - spent))} frei`,
      percent,
      label: spent > 0 ? `${percent} Prozent des Budgets gebraucht` : "Noch nichts gebraucht",
    };
  }

  /** The AI at the bottom of the sidebar, from GET /api/ki/status; null when there is nothing to show. */
  function budgetView(status) {
    if (!status || !status.eingerichtet) return null;
    const when = monthName(status.monat);
    if (status.vermittlung && typeof status.budget_usd === "number" && status.budget_usd > 0) {
      return mediationBudget(status, when);
    }
    if (!status.vermittlung && status.eigener_schluessel) {
      const costs = usd(Math.max(0, Number(status.kosten_usd) || 0));
      return { title: `KI-Kosten ${when}`, text: `USD ${costs} mit eigenem Schlüssel`, short: `KI-Kosten: USD ${costs}`,
               percent: null, label: "" };
    }
    return null;
  }

  /** A stored answer { at, status } still counts when it is younger than the limit and not from the future. */
  function isFresh(entry, now, maxAge = BUDGET_MAX_AGE_MS) {
    if (!entry || typeof entry.at !== "number") return false;
    const age = now - entry.at;
    return age >= 0 && age <= maxAge;
  }

  const logic = { BUDGET_MAX_AGE_MS, activeTarget, badges, budgetView, isFresh };
  if (typeof module !== "undefined") module.exports = logic;
  else global.SidebarLogic = logic;
})(typeof window !== "undefined" ? window : globalThis);
