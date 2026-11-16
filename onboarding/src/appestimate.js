// Only in the page „Meine Angaben“ of the app (G85, #271): cost and time of „Vorbefüllen“, estimated by the app without
// the AI after every add, remove and settled kind change, once the files are in the data folder. Until the estimate
// stands the run is disabled. Uses the state of app.js and appuploads.js (uploads, uploadsUnderway, uploadTurn,
// kindChoices, filesArriving, pointerReleased, backend, prefillCardContext), which are inlined around this file.
"use strict";

let prefillEstimate = { phase: "none", answer: null, problem: null };
let estimateTurn = 0; // only the answer to the latest change counts
const RUN_AREA = ".prefill-card__run";
const RUN_ACTIONS = ".prefill-card__actions";

const documentWorkPending = () => uploadsUnderway > 0 || Object.keys(kindChoices).length > 0;

/** Estimate again once the work on the documents so far is done; meanwhile the line says what it waits for. */
function requestEstimate() {
  const turn = ++estimateTurn;
  setEstimate({ phase: filesArriving > 0 ? "uploading" : "estimating", answer: null, problem: null });
  return uploadTurn.then(() => estimateWhenSettled(turn));
}

async function estimateWhenSettled(turn) {
  if (turn !== estimateTurn || documentWorkPending()) return; // the change still on its way asks again when it is done
  if (!uploads.length) {
    setEstimate({ phase: "none", answer: null, problem: null });
    return;
  }
  setEstimate({ phase: "estimating", answer: null, problem: null });
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

/**
 * The run area is drawn anew in place, not the page: a select being arrowed through stays as it is. The status keeps
 * its node, so a screen reader reads the new line; the focus stays on its control or, if that went, on the line.
 */
function drawEstimate() {
  const area = document.querySelector(RUN_AREA);
  const context = area && prefillCardContext();
  if (!context) return;
  const focused = area.contains(document.activeElement);
  const kept = focused ? controlSelector(document.activeElement) : null;
  const fresh = prefillRunArea(context);
  const status = area.querySelector(`#${STATUS_ID}`);
  const freshStatus = fresh.querySelector(`#${STATUS_ID}`);
  if (!status || !freshStatus) {
    area.replaceWith(fresh);
  } else {
    area.querySelector(RUN_ACTIONS).replaceWith(fresh.querySelector(RUN_ACTIONS));
    status.replaceChildren(...freshStatus.childNodes);
  }
  if (!focused || area.contains(document.activeElement)) return;
  const control = kept && document.querySelector(kept);
  if (control && !control.disabled) control.focus();
  else (document.getElementById(STATUS_ID) || document.getElementById("main")).focus();
}
