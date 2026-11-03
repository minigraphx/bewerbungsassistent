// ZIP container of the template: einstieg.json plus uploaded documents, written and read in the browser.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const zlib = require("node:zlib");
const { crc32, createZip, readZip, ZipError } = require("../src/zip.js");

const DATE = new Date(2026, 10, 3, 10, 30, 0);
const LIMITS = { maxEntries: 10, maxTotalBytes: 1000000 };
const bytes = (text) => new TextEncoder().encode(text);

test("crc32 matches the standard check value", () => {
  assert.equal(crc32(bytes("123456789")), 0xcbf43926);
});

test("written entries read back unchanged, also with umlauts and compression", async () => {
  const pdf = new Uint8Array(5000).map((_, i) => (i * 7) % 256);
  const entries = [
    { name: "einstieg.json", data: bytes('{"format":"x"}') },
    { name: "dokumente/zeugnisse/2023 Müller AG Arbeitszeugnis.pdf", data: pdf },
    { name: "dokumente/zertifikate/leer-ähnlich.txt", data: bytes("a".repeat(2000)) },
  ];
  for (const compress of [false, true]) {
    const zip = await createZip(entries, { date: DATE, compress });
    const read = await readZip(zip, LIMITS);
    assert.deepEqual(read.map((e) => e.name), entries.map((e) => e.name));
    read.forEach((e, i) => assert.deepEqual(e.data, entries[i].data));
  }
});

test("compression is used only where it helps", async () => {
  const text = bytes("Zeugnis ".repeat(1000));
  const zip = await createZip([{ name: "a.txt", data: text }], { date: DATE, compress: true });
  assert.ok(zip.length < text.length / 4);
});

test("reads deflated entries written by other tools", async () => {
  const data = bytes("Arbeitszeugnis ".repeat(200));
  const zip = await createZip([{ name: "a.txt", data }], { date: DATE });
  const deflated = zlib.deflateRawSync(data);
  const rebuilt = rebuildWithDeflate(zip, data, deflated);
  const [entry] = await readZip(rebuilt, LIMITS);
  assert.deepEqual(entry.data, data);
});

test("rejects data that is no ZIP", async () => {
  await assert.rejects(readZip(bytes("kein zip"), LIMITS), ZipError);
});

test("rejects a damaged entry", async () => {
  const zip = await createZip([{ name: "a.txt", data: bytes("hallo welt") }], { date: DATE });
  const damaged = zip.slice();
  damaged[30 + "a.txt".length] ^= 0xff;
  await assert.rejects(readZip(damaged, LIMITS), /beschädigt/);
});

test("rejects too many entries and too much content", async () => {
  const many = Array.from({ length: 11 }, (_, i) => ({ name: `f${i}.txt`, data: bytes("x") }));
  await assert.rejects(readZip(await createZip(many, { date: DATE }), LIMITS), /zu viele/i);
  const big = [{ name: "a.txt", data: new Uint8Array(1000001) }];
  await assert.rejects(readZip(await createZip(big, { date: DATE }), LIMITS), /zu gross/i);
});

test("rejects entries that claim a wrong size", async () => {
  const zip = await createZip([{ name: "a.txt", data: bytes("hallo") }], { date: DATE });
  const view = new DataView(zip.buffer, zip.byteOffset, zip.byteLength);
  const central = findCentral(zip);
  view.setUint32(central + 24, 3, true); // uncompressed size in the central directory
  await assert.rejects(readZip(zip, LIMITS), ZipError);
});

function findCentral(zip) {
  for (let i = zip.length - 22; i >= 0; i--) {
    if (zip[i] === 0x50 && zip[i + 1] === 0x4b && zip[i + 2] === 0x01 && zip[i + 3] === 0x02) return i;
  }
  throw new Error("no central directory");
}

// Replace the single stored entry by a deflated one (method 8), keeping the layout simple.
function rebuildWithDeflate(zip, data, deflated) {
  const nameLength = new DataView(zip.buffer).getUint16(26, true);
  const name = zip.slice(30, 30 + nameLength);
  const crc = crc32(data);
  const local = new Uint8Array(30 + nameLength + deflated.length);
  const lv = new DataView(local.buffer);
  lv.setUint32(0, 0x04034b50, true); lv.setUint16(4, 20, true); lv.setUint16(8, 8, true);
  lv.setUint32(14, crc, true); lv.setUint32(18, deflated.length, true); lv.setUint32(22, data.length, true);
  lv.setUint16(26, nameLength, true); local.set(name, 30); local.set(deflated, 30 + nameLength);
  const central = new Uint8Array(46 + nameLength);
  const cv = new DataView(central.buffer);
  cv.setUint32(0, 0x02014b50, true); cv.setUint16(4, 20, true); cv.setUint16(6, 20, true); cv.setUint16(10, 8, true);
  cv.setUint32(16, crc, true); cv.setUint32(20, deflated.length, true); cv.setUint32(24, data.length, true);
  cv.setUint16(28, nameLength, true); central.set(name, 46);
  const end = new Uint8Array(22);
  const ev = new DataView(end.buffer);
  ev.setUint32(0, 0x06054b50, true); ev.setUint16(8, 1, true); ev.setUint16(10, 1, true);
  ev.setUint32(12, central.length, true); ev.setUint32(16, local.length, true);
  const out = new Uint8Array(local.length + central.length + end.length);
  out.set(local, 0); out.set(central, local.length); out.set(end, local.length + central.length);
  return out;
}
