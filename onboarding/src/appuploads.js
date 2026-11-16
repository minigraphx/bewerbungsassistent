// Only in the page „Meine Angaben“ of the app (G84): what the drop area does with the data folder. Adding, changing
// the kind and removing wait for each other (inTurn), and the list of the app is the truth afterwards.
// Uses the state of app.js (uploads, setUploads, inTurn, focusFirst), which is inlined after this file.
"use strict";

const ANNOUNCE_DELAY_MS = 100; // a status region that changes after it is drawn is read out
const KIND_SETTLE_MS = 500; // a new kind counts once the select has been left alone this long
let uploadNotes = {}; // datei → true when recognised by its name, false when not sure; files filed before have none
let uploadAnnouncement = "";
let kindChoices = {}; // datei → timer of a kind not yet settled
let kindMoves = {}; // datei → the move under way, resolving to where the file is afterwards
let filesArriving = 0; // drops still on their way, as against kinds being moved

/** Say what happened in the status region of the card, also when the page was just drawn anew. */
function announceUploads(text) {
  uploadAnnouncement = text;
  const region = document.getElementById("upload-status");
  if (!region) return;
  region.textContent = "";
  window.setTimeout(() => {
    const now = document.getElementById("upload-status");
    if (now && uploadAnnouncement === text) now.textContent = text;
  }, ANNOUNCE_DELAY_MS);
}

function forgetUploadAnnouncement() {
  uploadAnnouncement = "";
}

/** The person may have moved on while a large file was on its way. */
function focusInCard(...selectors) {
  if (steps()[step].kind === "start") focusFirst(...selectors, CHOOSE_SELECTOR);
}

function addDroppedFiles(fileList) {
  const chosen = Array.from(fileList);
  uploadsUnderway += 1;
  filesArriving += 1;
  const work = inTurn(async () => {
    try {
      await sendDropped(chosen);
    } finally {
      uploadsUnderway -= 1;
      filesArriving -= 1;
    }
  });
  requestEstimate(); // what the run costs is said again once the files are in (G85)
  return work;
}

async function sendDropped(chosen) {
  const { accepted, messages } = planDrop(form, state.track, uploads, chosen);
  const problems = [...messages];
  const added = [];
  let list = uploads;
  for (const entry of accepted) {
    let data;
    try {
      data = new Uint8Array(await chosen[entry.index].arrayBuffer());
    } catch (error) {
      problems.push(`${entry.name}: ${DROP_WORDS.unreadable}`);
      continue;
    }
    try {
      const before = new Set(list.map((u) => u.datei));
      list = (await backend.addDocument(state.track, entry.category, entry.name, data)).unterlagen;
      const stored = list.find((u) => !before.has(u.datei));
      if (stored) {
        uploadNotes = { ...uploadNotes, [stored.datei]: entry.sure };
        added.push(stored);
      }
    } catch (error) {
      problems.push(`${entry.name}: ${error.message}`);
    }
  }
  setUploads(list, problems);
  announceUploads(added.length ? addedStatus(form, state.track, added) : ""); // never an old „Hinzugefügt“ beside a refusal
  focusInCard();
}

/**
 * Arrow keys on a closed select fire „change“ at every step (Windows): the file moves only once the choice has
 * settled, to the kind it settled on, and only that kind is announced. Leaving the select settles it at once.
 */
function changeUploadKind(upload, category) {
  const waiting = kindChoices[upload.datei];
  if (waiting) window.clearTimeout(waiting.timer);
  const timer = window.setTimeout(() => settleUploadKind(upload.datei), KIND_SETTLE_MS);
  kindChoices = { ...kindChoices, [upload.datei]: { timer, category } };
  requestEstimate(); // the kind may change what is read; the run waits until it settled
}

/** The select lost the focus: its kind is saved now, not after the wait. */
function leaveUploadKind(upload) {
  const waiting = kindChoices[upload.datei];
  if (!waiting) return Promise.resolve();
  window.clearTimeout(waiting.timer);
  return settleUploadKind(upload.datei);
}

/** Every kind still waiting is saved now, e.g. before the prefill reads the files or the page moves on. */
function settlePendingKinds() {
  return Promise.all(Object.keys(kindChoices).map((datei) => {
    window.clearTimeout(kindChoices[datei].timer);
    return settleUploadKind(datei);
  }));
}

/** What the prefill waits for before it reads the files: uploads, removals and kinds not yet saved. */
function pendingDocumentWork() {
  settlePendingKinds();
  return uploadsUnderway ? uploadTurn : null;
}

/** Resolves to the path of the file once its kind is saved. */
function settleUploadKind(datei) {
  const { [datei]: waiting, ...others } = kindChoices;
  kindChoices = others;
  const current = uploads.find((u) => u.datei === datei);
  const moved = !waiting || !current || current.category === waiting.category
    ? Promise.resolve(datei) : moveUploadKind(current, waiting.category);
  if (waiting) requestEstimate(); // also when it settled on the kind it had: the run must not stay disabled
  return moved;
}

/**
 * Where the file is once a kind picked just before is saved: one still waiting is saved now, one on its way is
 * waited for. The list may still show the old path until the move is drawn (#328).
 */
function settledUploadPath(datei) {
  if (kindChoices[datei]) return leaveUploadKind({ datei });
  return kindMoves[datei] || Promise.resolve(datei);
}

/** Resolves to the path of the file afterwards: the new one, or the old one when the kind could not be changed. */
function moveUploadKind(upload, category) {
  const problem = kindChangeProblem(form, state.track, uploads, upload, category);
  uploadsUnderway += 1;
  const move = inTurn(async () => {
    try {
      const answer = problem ? null : await backend.changeDocumentKind(state.track, upload.datei, category);
      await pointerReleased(); // drawn anew under a pressed button, the click would get lost
      if (problem) {
        redrawKinds(uploads, [problem], upload.datei); // the select shows the old kind again
        return upload.datei;
      }
      const { [upload.datei]: _guess, ...others } = uploadNotes; // the person decided, the guess no longer counts
      uploadNotes = others;
      redrawKinds(answer.unterlagen, [], answer.datei);
      announceUploads(changedStatus(form, state.track, upload.name, category));
      return answer.datei;
    } catch (error) {
      await pointerReleased();
      redrawKinds(uploads, [kindFailed(error.message)], upload.datei);
      return upload.datei;
    } finally {
      uploadsUnderway -= 1;
      if (kindMoves[upload.datei] === move) {
        const { [upload.datei]: _done, ...others } = kindMoves;
        kindMoves = others;
      }
    }
  });
  kindMoves = { ...kindMoves, [upload.datei]: move };
  return move;
}

/** Draw the list anew; the focus stays on the control the person went on to, else it goes back to the select. */
function redrawKinds(list, messages, datei) {
  const kept = controlSelector(document.activeElement);
  setUploads(list, messages);
  if (kept) focusFirst(kept, kindSelector(datei));
  else focusInCard(kindSelector(datei));
}

/** A selector that finds a control again after the page is drawn anew: by its id or its label; null for none. */
function controlSelector(node) {
  if (!node || typeof node.closest !== "function" || !node.closest(DROP_CARD)) return null;
  if (node.id) return `#${node.id}`;
  const label = node.getAttribute("aria-label");
  return label ? `[aria-label="${label.replace(/["\\]/g, "\\$&")}"]` : null;
}

let pointerPressed = false;
let pointerWaiters = [];

/** A press on the page is followed to its release, so nothing is drawn anew between the two (trackPointer). */
function trackPointer(doc) {
  doc.addEventListener("pointerdown", () => { pointerPressed = true; }, true);
  const release = () => {
    pointerPressed = false;
    const waiting = pointerWaiters;
    pointerWaiters = [];
    window.setTimeout(() => waiting.forEach((resolve) => resolve()), 0); // after the click of this press
  };
  doc.addEventListener("pointerup", release, true);
  doc.addEventListener("pointercancel", release, true);
}

function pointerReleased() {
  return pointerPressed ? new Promise((resolve) => { pointerWaiters = [...pointerWaiters, resolve]; }) : Promise.resolve();
}

/**
 * After „Entfernen“ the focus goes to the select of the next row, else to „Dateien wählen“. A kind picked on the
 * row just before moves the file first, and the file is removed under its new path (#328).
 */
function removeDroppedUpload(index) {
  const clicked = uploads[index];
  const settled = settledUploadPath(clicked.datei); // queued before the removal, so it is done when the removal runs
  const work = inTurn(async () => {
    const datei = await settled;
    const at = uploads.findIndex((u) => u.datei === datei);
    const removed = at >= 0 ? uploads[at] : { ...clicked, datei };
    const next = at >= 0 ? uploads[at + 1] : null;
    try {
      setUploads((await backend.removeDocument(removed.datei)).unterlagen, []);
      announceUploads(removedStatus(removed.name));
    } catch (error) {
      setUploads(uploads, [error.message]);
    }
    focusInCard(...(next ? [kindSelector(next.datei)] : []));
  });
  requestEstimate();
  return work;
}
