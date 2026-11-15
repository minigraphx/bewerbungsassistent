// Progress and result of a run as short German lines for the popup.

/** Where a search stands among all of its portal (G43): „Suche 32 von 67, Etappe 2 von 3“; empty from an older run. */
export function position(step) {
  if (!step.abfragen) return '';
  const stage = step.etappen > 1 ? `, Etappe ${step.etappe} von ${step.etappen}` : '';
  return `Suche ${step.nummer} von ${step.abfragen}${stage}`;
}

/** „ in Bern“ for the place being searched (G43); empty for a query without place or from an older run. */
export function place(step) {
  return step.ort ? ` in ${step.ort}` : '';
}

const PHASES = {
  start: () => 'Suche startet …',
  suche: (s) => [`${s.portal}: suche „${s.stichwort}“${place(s)}, Seite ${s.seite} (${s.gefunden} bisher)`, position(s)].filter(Boolean).join(' · '),
  pause: (s) => `${s.portal}: Pause vor Etappe ${s.etappe} von ${s.etappen}, noch ${s.sekunden} Sekunden`,
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
 * Before a long run it adds what the app announces (G43): searches, stages and the rough duration.
 * @param {{art?: string, portale?: string[], umfang?: {lang: boolean, text: string}}|null} plan
 * @returns {{button: string, text: string}}
 */
export function describePlan(plan) {
  if (!plan) {
    return { button: 'Suche starten', text: 'Sucht nach dem Suchprofil auf den passenden Portalen. Die Treffer gehen in die App.' };
  }
  const sites = (plan.weitere_seiten || []).map((site) => site.portal);
  const portals = [...(plan.portale || []), ...sites].join(', ').replace(/, ([^,]*)$/, ' und $1');
  const long = plan.umfang?.lang ? ` ${plan.umfang.text}` : '';
  return plan.art === 'lehrstelle'
    ? { button: OFFER_BUTTONS[(plan.angebote || []).join('+')] || OFFER_BUTTONS.lehrstelle, text: `Sucht auf ${portals} nach deinem Suchprofil. Die Treffer gehen in die App.${long}` }
    : { button: 'Stellen suchen', text: `Sucht auf ${portals} nach dem Suchprofil. Die Treffer gehen in die App.${long}` };
}
