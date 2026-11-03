// Keeps uploaded documents in this browser (IndexedDB), so they are still there after closing the page.
// localStorage is too small for documents (about 5 MB). Everything stays on the device; "Alles löschen"
// removes it. Without IndexedDB (e.g. some private windows) the functions report failure and the page
// keeps the files in memory only.
"use strict";

const UPLOAD_DB_NAME = "bewerbungsassistent.einstieg";
const UPLOAD_DB_VERSION = 1;
const UPLOAD_DB_STORE = "uploads";
const UPLOAD_DB_KEY = "current";

function openUploadDb() {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB not available"));
      return;
    }
    const request = indexedDB.open(UPLOAD_DB_NAME, UPLOAD_DB_VERSION);
    request.onupgradeneeded = () => request.result.createObjectStore(UPLOAD_DB_STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error("IndexedDB blocked"));
  });
}

/** Run one request in a transaction and resolve with its result once the transaction is done. */
async function withUploadStore(mode, makeRequest) {
  const db = await openUploadDb();
  try {
    return await new Promise((resolve, reject) => {
      const transaction = db.transaction(UPLOAD_DB_STORE, mode);
      const request = makeRequest(transaction.objectStore(UPLOAD_DB_STORE));
      transaction.oncomplete = () => resolve(request.result);
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error || new Error("IndexedDB aborted"));
    });
  } finally {
    db.close();
  }
}

/** Store the uploads ({ category, name, size, data }); true if they are kept in this browser. */
async function keepUploads(list) {
  try {
    const copy = list.map(({ category, name, size, data }) => ({ category, name, size, data }));
    await withUploadStore("readwrite", (store) => (copy.length ? store.put(copy, UPLOAD_DB_KEY) : store.delete(UPLOAD_DB_KEY)));
    return true;
  } catch (error) {
    return false;
  }
}

/** Uploads kept in this browser, or [] if there are none or they cannot be read. */
async function keptUploads() {
  try {
    const stored = await withUploadStore("readonly", (store) => store.get(UPLOAD_DB_KEY));
    return Array.isArray(stored) ? stored.filter(isKeptUpload) : [];
  } catch (error) {
    return [];
  }
}

function isKeptUpload(u) {
  return u !== null && typeof u === "object" && typeof u.category === "string" && typeof u.name === "string"
    && u.data instanceof Uint8Array && u.size === u.data.length;
}
