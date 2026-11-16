// Only in the page „Meine Angaben“ of the app (G84): what the drop area does with the data folder. Adding, changing
// the kind and removing wait for each other (inTurn), and the list of the app is the truth afterwards.
// Uses the state of app.js (uploads, setUploads, inTurn, focusFirst), which is inlined after this file.
"use strict";

const ANNOUNCE_DELAY_MS = 100; // a status region that changes after it is drawn is read out
const KIND_SETTLE_MS = 500; // a new kind counts once the select has been left alone this long
let uploadNotes = {}; // datei → true when recognised by its name, false when not sure; files filed before have none
let uploadAnnouncement = "";
let kindChoices = {}; // datei → timer of a kind not yet settled

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
  return inTurn(async () => {
    try {
      await sendDropped(chosen);
    } finally {
      uploadsUnderway -= 1;
    }
  });
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
 * settled, to the kind it settled on, and only that kind is announced.
 */
function changeUploadKind(upload, category) {
  const waiting = kindChoices[upload.datei];
  if (waiting) window.clearTimeout(waiting);
  kindChoices = {
    ...kindChoices,
    [upload.datei]: window.setTimeout(() => settleUploadKind(upload, category), KIND_SETTLE_MS),
  };
}

function settleUploadKind(upload, category) {
  const { [upload.datei]: _done, ...others } = kindChoices;
  kindChoices = others;
  const current = uploads.find((u) => u.datei === upload.datei);
  if (!current || current.category === category) return Promise.resolve();
  return moveUploadKind(current, category);
}

function moveUploadKind(upload, category) {
  const problem = kindChangeProblem(form, state.track, uploads, upload, category);
  if (problem) {
    setUploads(uploads, [problem]); // drawn anew, the select shows the old kind again
    focusInCard(kindSelector(upload.datei));
    return Promise.resolve();
  }
  return inTurn(async () => {
    try {
      const answer = await backend.changeDocumentKind(state.track, upload.datei, category);
      const { [upload.datei]: _guess, ...others } = uploadNotes; // the person decided, the guess no longer counts
      uploadNotes = others;
      setUploads(answer.unterlagen, []);
      announceUploads(changedStatus(form, state.track, upload.name, category));
      focusInCard(kindSelector(answer.datei));
    } catch (error) {
      setUploads(uploads, [kindFailed(error.message)]);
      focusInCard(kindSelector(upload.datei));
    }
  });
}

/** After „Entfernen“ the focus goes to the select of the next row, else to „Dateien wählen“. */
function removeDroppedUpload(index) {
  const removed = uploads[index];
  const next = uploads[index + 1];
  return inTurn(async () => {
    try {
      setUploads((await backend.removeDocument(removed.datei)).unterlagen, []);
      announceUploads(removedStatus(removed.name));
    } catch (error) {
      setUploads(uploads, [error.message]);
    }
    focusInCard(...(next ? [kindSelector(next.datei)] : []));
  });
}
