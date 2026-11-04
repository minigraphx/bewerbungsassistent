// The page of the app talks to the app only through createAppBackend.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function load(fetchStub) {
  const context = vm.createContext({
    document: { querySelector: () => ({ content: "geheim" }) },
    fetch: fetchStub, btoa, URLSearchParams, Error, String, JSON,
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../src/appbackend.js"), "utf8"), context);
  return context;
}

const respond = (status, body) => ({ ok: status < 400, status, json: async () => body });

test("large files survive the conversion to base64", () => {
  const { toBase64 } = load();
  const bytes = Uint8Array.from({ length: 200000 }, (_, i) => i % 251);

  assert.deepStrictEqual(Buffer.from(toBase64(bytes), "base64"), Buffer.from(bytes));
});

test("requests carry the token and the upload carries its track", async () => {
  const calls = [];
  const { createAppBackend } = load(async (url, options) => { calls.push([url, options]); return respond(200, { unterlagen: [] }); });

  await createAppBackend().addDocument("apprenticeship", "lebenslauf-bisher", "cv.pdf", new Uint8Array([1, 2, 3]));

  assert.strictEqual(calls[0][0], "/api/angaben/unterlage");
  assert.strictEqual(calls[0][1].headers["X-Token"], "geheim");
  assert.deepStrictEqual(JSON.parse(calls[0][1].body), { track: "apprenticeship", category: "lebenslauf-bisher", name: "cv.pdf", data: "AQID" });
});

test("errors tell the message of the app and whether files already exist", async () => {
  const { createAppBackend } = load(async () => respond(409, { fehler: "Es gibt schon Dateien.", vorhanden: ["cv.yaml"] }));

  await assert.rejects(createAppBackend().takeOver({}, false), (error) => {
    assert.strictEqual(error.message, "Es gibt schon Dateien.");
    assert.strictEqual(error.status, 409);
    assert.strictEqual(error.existing, true);
    return true;
  });
});

test("a broken answer still gives a message for people", async () => {
  const { createAppBackend } = load(async () => ({ ok: false, status: 500, json: async () => { throw new SyntaxError("x"); } }));

  await assert.rejects(createAppBackend().overview(), /Die App antwortet nicht/);
});

test("prefill posts the track and the answers so far", async () => {
  const calls = [];
  const { createAppBackend } = load(async (url, options) => { calls.push([url, options]); return respond(200, { suggestions: {} }); });

  await createAppBackend().prefill("job", { person: { name: "Erika" } });

  assert.strictEqual(calls[0][0], "/api/angaben/vorbefuellen");
  assert.deepStrictEqual(JSON.parse(calls[0][1].body), { track: "job", data: { person: { name: "Erika" } } });
});
