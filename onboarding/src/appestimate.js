// Only in the page „Meine Angaben“ of the app (G85, #271): cost and time of „Vorbefüllen“, estimated by the app without
// the AI after every add, remove and settled kind change, once the files are in the data folder. Until the estimate
// stands the run is disabled. Uses the state of app.js and appuploads.js (uploads, uploadsUnderway, uploadTurn,
// kindChoices, filesArriving, pointerReleased, backend, prefillCardContext), which are inlined around this file.
"use strict";

let prefillEstimate = { phase: "none", answer: null, problem: null };
let estimateTurn = 0; // only the answer to the latest change counts
let estimateRetried = false; // „Neu schätzen“ was pressed: once the answer is there the focus goes on to the run
const RUN_AREA = ".prefill-card__run";
const RUN_ACTIONS = ".prefill-card__actions";
const SLOW_ESTIMATE_MS = 400; // a quicker answer replaces the old figures at once, without a line in between
const HELD_PHASES = ["ready", "failed"]; // what stays shown for that moment; „uploading“ would no longer be true

const documentWorkPending = () => uploadsUnderway > 0 || Object.keys(kindChoices).length > 0;

/** Estimate again once the work on the documents so far is done; meanwhile the line says what it waits for. */
function requestEstimate() {
  const turn = ++estimateTurn;
  if (filesArriving > 0) setEstimate({ phase: "uploading", answer: null, problem: null });
  else startEstimating();
  return uploadTurn.then(() => estimateWhenSettled(turn));
}

/** „Neu schätzen“ after a failed estimate. */
function retryEstimate() {
  estimateRetried = true;
  return requestEstimate();
}

/** The estimate shown before stays for a moment; only an answer slower than that says that it estimates. */
function startEstimating() {
  if (prefillEstimate.phase === "estimating") return;
  const held = HELD_PHASES.includes(prefillEstimate.phase) ? prefillEstimate : null;
  const next = { phase: "estimating", answer: null, problem: null, held, slow: false };
  setEstimate(next);
  window.setTimeout(() => {
    if (prefillEstimate === next) setEstimate({ ...next, slow: true });
  }, SLOW_ESTIMATE_MS);
}

async function estimateWhenSettled(turn) {
  if (turn !== estimateTurn || documentWorkPending()) return; // the change still on its way asks again when it is done
  if (!uploads.length) {
    setEstimate({ phase: "none", answer: null, problem: null });
    return;
  }
  startEstimating();
  let next;
  try {
    next = { phase: "ready", answer: await backend.estimatePrefill(state.track), problem: null };
  } catch (error) {
    next = { phase: "failed", answer: null, problem: error.message };
  }
  if (turn === estimateTurn) setEstimate(next);
}

/** Drawn after a press on the page is released, so a button is not replaced between press and click (#270). */
function setEstimate(next) {
  prefillEstimate = next;
  pointerReleased().then(() => {
    if (prefillEstimate === next) drawEstimate();
  });
}

/** The run area is drawn anew in place, not the page: a select being arrowed through stays as it is. */
function drawEstimate() {
  const area = document.querySelector(RUN_AREA);
  const context = area && prefillCardContext();
  if (!context) return;
  const focused = area.contains(document.activeElement);
  const kept = focused ? controlSelector(document.activeElement) : null;
  const fresh = prefillRunArea(context);
  if (!drawInPlace(area, fresh)) area.replaceWith(fresh);
  focusAfterEstimate(focused, kept);
}

/** The status keeps its node and only takes the new lines and busy state, so a screen reader reads the new line. */
function drawInPlace(area, fresh) {
  const status = area.querySelector(`#${STATUS_ID}`);
  const freshStatus = fresh.querySelector(`#${STATUS_ID}`);
  if (!status || !freshStatus) return false;
  area.querySelector(RUN_ACTIONS).replaceWith(fresh.querySelector(RUN_ACTIONS));
  status.replaceChildren(...freshStatus.childNodes);
  const busy = freshStatus.getAttribute("aria-busy");
  if (busy) status.setAttribute("aria-busy", busy);
  else status.removeAttribute("aria-busy");
  const files = area.querySelector(`#${FILES_ID}`);
  const freshFiles = fresh.querySelector(`#${FILES_ID}`);
  if (files) files.replaceWith(freshFiles);
  else status.after(freshFiles);
  return true;
}

const usableControl = (selector) => {
  const node = document.querySelector(selector);
  return Boolean(node) && !node.disabled;
};

function focusAfterEstimate(focused, kept) {
  const settled = !estimatePending(prefillEstimate);
  const target = estimateFocus({ focused, kept, retried: estimateRetried, settled, usable: usableControl });
  if (settled || !focused) estimateRetried = false;
  const node = target && document.querySelector(target);
  if (node && node !== document.activeElement) node.focus();
}

/**
 * Where the focus goes after the run area is drawn anew; never away from elsewhere on the page. After „Neu schätzen“
 * and its answer to „Vorbefüllen“ if it can run, else back to „Neu schätzen“; otherwise it stays on its control or,
 * if that went, on the line. usable(selector) says whether that control is there and enabled.
 */
function estimateFocus({ focused, kept, retried, settled, usable }) {
  if (!focused) return null;
  const order = retried && settled ? ["#prefill", `#${RETRY_ID}`, `#${STATUS_ID}`] : [kept, `#${STATUS_ID}`];
  return [...order, "#main"].find((selector) => selector && usable(selector)) || null;
}
