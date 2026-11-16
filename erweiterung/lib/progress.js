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

// Number and unit never part at the end of a line (#339), as in the app's cost lines; read aloud as a space.
const seconds = (n) => `${n}\u00a0${n === 1 ? 'Sekunde' : 'Sekunden'}`;

// An older extension reports a search step without term or count, so each part stays out when it is missing.
const STEPS = {
  suche: (s) => [
    `${s.stichwort ? `suche „${s.stichwort}“${place(s)}, ` : ''}Seite ${s.seite}${s.gefunden === undefined ? '' : ` (${s.gefunden} bisher)`}`,
    position(s),
  ].filter(Boolean).join(' · '),
  pause: (s) => `Pause vor Etappe ${s.etappe} von ${s.etappen}, noch ${seconds(s.sekunden)}`,
  texte: (s) => `lese Inserat ${s.fertig + 1} von ${s.von}`,
};

/**
 * What the current portal does right now, without its name: the popup shows it in the portal's row, after the name.
 * @returns {string} empty for a step that has not reached a portal yet
 */
export function stepText(step) {
  const text = STEPS[step.phase];
  return text ? text(step) : '';
}

/**
 * @param {{zustand: string, schritt?: object, ergebnis?: object, fehler?: string}} run
 * @returns {{step: string, portals: Array<{text: string, problem: boolean}>, hints: string[]}}
 */
export function describeRun(run) {
  if (run.zustand === 'fehler') return { step: run.fehler || 'Die Suche ist abgebrochen.', portals: [], hints: [] };
  if (run.zustand === 'laeuft') {
    const step = run.schritt || { phase: 'start' };
    const text = stepText(step);
    return { step: text ? `${step.portal}: ${text}` : 'Suche startet …', portals: [], hints: [] };
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
