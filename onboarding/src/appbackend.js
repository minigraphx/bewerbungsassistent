// Only in the page „Meine Angaben“ of the app: state and documents go to the data folder through the app,
// because the port of the app changes with every start and the browser's storage would be lost.
"use strict";

const BASE64_CHUNK = 0x8000;

function toBase64(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i += BASE64_CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(i, i + BASE64_CHUNK));
  }
  return btoa(binary);
}

function createAppBackend() {
  const token = document.querySelector('meta[name="token"]').content;

  async function answer(response) {
    const body = await response.json().catch(() => ({}));
    if (response.ok) return body;
    const error = new Error(body.fehler || "Die App antwortet nicht. Läuft sie noch?");
    error.status = response.status;
    error.existing = Boolean(body.vorhanden);
    throw error;
  }

  const post = (path, body) => fetch(path, {
    method: "POST", headers: { "Content-Type": "application/json", "X-Token": token }, body: JSON.stringify(body),
  }).then(answer);

  return {
    overview: () => fetch(`/api/angaben/stand?${new URLSearchParams({ t: token })}`).then(answer),
    keep: (stand) => post("/api/angaben/stand", { stand }),
    discard: () => post("/api/angaben/stand-loeschen", {}),
    addDocument: (track, category, name, bytes) => post("/api/angaben/unterlage", { track, category, name, data: toBase64(bytes) }),
    removeDocument: (datei) => post("/api/angaben/unterlage-entfernen", { datei }),
    prefill: (track, data) => post("/api/angaben/vorbefuellen", { track, data }),
    takeOver: (bundle, ersetzen) => post("/api/angaben/uebernehmen", { bundle, ersetzen }),
  };
}
