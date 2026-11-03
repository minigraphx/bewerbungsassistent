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
    step: `Fertig: ${fresh} neue Treffer.`,
    portals: entries.map(([name, p]) => ({
      text: `${name}: ${p.treffer} gefunden, ${p.neu} neu${p.problem ? ` – ${p.problem}` : ''}`,
      problem: Boolean(p.problem),
    })),
    hints: result.hinweise || [],
  };
}
