// Progress and result of a run as short German lines for the popup.

const PHASES = {
  start: () => 'Suche startet …',
  suche: (s) => `${s.portal}: suche „${s.stichwort}“, Seite ${s.seite} (${s.gefunden} bisher)`,
  texte: (s) => `${s.portal}: lese Inserate (${s.fertig} von ${s.von})`,
};

/**
 * @param {{zustand: string, schritt?: object, ergebnis?: object, fehler?: string}} run
 * @returns {{step: string, portals: Array<{text: string, problem: boolean}>, hints: string[]}}
 */
export function describeRun(run) {
  if (run.zustand === 'fehler') return { step: run.fehler || 'Die Suche ist abgebrochen.', portals: [], hints: [] };
  if (run.zustand === 'laeuft') {
    const step = run.schritt || { phase: 'start' };
    return { step: (PHASES[step.phase] || PHASES.start)(step), portals: [], hints: [] };
  }
  const result = run.ergebnis || { portale: {}, hinweise: [] };
  const entries = Object.entries(result.portale || {});
  const fresh = entries.reduce((sum, [, p]) => sum + (p.neu || 0), 0);
  return {
    step: result.abgebrochen ? `Abgebrochen: ${fresh} neue Treffer bis dahin.` : `Fertig: ${fresh} neue Treffer.`,
    portals: entries.map(([name, p]) => ({
      text: `${name}: ${p.treffer} gefunden, ${p.neu} neu${p.problem ? ` – ${p.problem}` : ''}`,
      problem: Boolean(p.problem),
    })),
    hints: result.hinweise || [],
  };
}

const OFFER_BUTTONS = {
  lehrstelle: 'Lehrstellen suchen',
  schnupperlehre: 'Schnupperlehren suchen',
  'lehrstelle+schnupperlehre': 'Lehrstellen und Schnupperlehren suchen',
};

/**
 * What the popup says about the search before it starts: the plan is known only while the app runs.
 * @param {{art?: string, portale?: string[]}|null} plan
 * @returns {{button: string, text: string}}
 */
export function describePlan(plan) {
  if (!plan) {
    return { button: 'Suche starten', text: 'Sucht nach dem Suchprofil auf den passenden Portalen. Die Treffer gehen in die App.' };
  }
  const portals = (plan.portale || []).join(', ').replace(/, ([^,]*)$/, ' und $1');
  return plan.art === 'lehrstelle'
    ? { button: OFFER_BUTTONS[(plan.angebote || []).join('+')] || OFFER_BUTTONS.lehrstelle, text: `Sucht auf ${portals} nach deinem Suchprofil. Die Treffer gehen in die App.` }
    : { button: 'Stellen suchen', text: `Sucht auf ${portals} nach Ihrem Suchprofil. Die Treffer gehen in die App.` };
}
