// Minimal ZIP writer and reader for the template: einstieg.json plus uploaded documents in one file.
// Writes stored or deflated entries with UTF-8 names; reads stored and deflated entries, checks sizes
// and CRCs and stops at the given limits. No encryption, no ZIP64, no multi-disk archives.
"use strict";

const SIG_LOCAL = 0x04034b50;
const SIG_CENTRAL = 0x02014b50;
const SIG_END = 0x06054b50;
const LOCAL_HEADER = 30;
const CENTRAL_HEADER = 46;
const END_RECORD = 22;
const MAX_COMMENT = 0xffff;
const FLAG_ENCRYPTED = 0x0001;
const FLAG_UTF8 = 0x0800;
const METHOD_STORED = 0;
const METHOD_DEFLATE = 8;
const ZIP_VERSION = 20;

class ZipError extends Error {}

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(data) {
  let crc = 0xffffffff;
  for (let i = 0; i < data.length; i++) crc = CRC_TABLE[(crc ^ data[i]) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

async function streamThrough(data, transform, limit) {
  const reader = new Blob([data]).stream().pipeThrough(transform).getReader();
  const chunks = [];
  let length = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    length += value.length;
    if (limit !== undefined && length > limit) {
      await reader.cancel();
      throw new ZipError("Die Datei ist beschädigt (ein Eintrag ist grösser als angegeben).");
    }
    chunks.push(value);
  }
  const out = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { out.set(chunk, offset); offset += chunk.length; }
  return out;
}

function dosDateTime(date) {
  const time = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2);
  const day = ((Math.max(date.getFullYear(), 1980) - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  return { time, day };
}

/** ZIP bytes for entries [{ name, data: Uint8Array }]; with compress, entries are deflated where that is smaller. */
async function createZip(entries, { date = new Date(), compress = false } = {}) {
  const { time, day } = dosDateTime(date);
  const encoder = new TextEncoder();
  const locals = [];
  const centrals = [];
  let offset = 0;
  for (const entry of entries) {
    const name = encoder.encode(entry.name);
    const crc = crc32(entry.data);
    let method = METHOD_STORED;
    let body = entry.data;
    if (compress) {
      const deflated = await streamThrough(entry.data, new CompressionStream("deflate-raw"));
      if (deflated.length < entry.data.length) { method = METHOD_DEFLATE; body = deflated; }
    }
    const fields = { method, time, day, crc, compressed: body.length, size: entry.data.length, name };
    const local = header(LOCAL_HEADER, SIG_LOCAL, fields);
    locals.push(local, body);
    centrals.push(header(CENTRAL_HEADER, SIG_CENTRAL, fields, offset));
    offset += local.length + body.length;
  }
  const centralSize = centrals.reduce((sum, c) => sum + c.length, 0);
  const end = new Uint8Array(END_RECORD);
  const view = new DataView(end.buffer);
  view.setUint32(0, SIG_END, true);
  view.setUint16(8, entries.length, true);
  view.setUint16(10, entries.length, true);
  view.setUint32(12, centralSize, true);
  view.setUint32(16, offset, true);
  return concat([...locals, ...centrals, end]);
}

function header(size, signature, f, offset) {
  const out = new Uint8Array(size + f.name.length);
  const v = new DataView(out.buffer);
  v.setUint32(0, signature, true);
  const central = signature === SIG_CENTRAL;
  const base = central ? 2 : 0; // the central header has "version made by" before the common fields
  if (central) v.setUint16(4, ZIP_VERSION, true);
  v.setUint16(4 + base, ZIP_VERSION, true);
  v.setUint16(6 + base, FLAG_UTF8, true);
  v.setUint16(8 + base, f.method, true);
  v.setUint16(10 + base, f.time, true);
  v.setUint16(12 + base, f.day, true);
  v.setUint32(14 + base, f.crc, true);
  v.setUint32(18 + base, f.compressed, true);
  v.setUint32(22 + base, f.size, true);
  v.setUint16(26 + base, f.name.length, true);
  if (central) v.setUint32(42, offset, true);
  out.set(f.name, size);
  return out;
}

function concat(parts) {
  const out = new Uint8Array(parts.reduce((sum, p) => sum + p.length, 0));
  let offset = 0;
  for (const part of parts) { out.set(part, offset); offset += part.length; }
  return out;
}

/** Entries [{ name, data }] of a ZIP; throws ZipError (German message) if it is damaged or exceeds the limits. */
async function readZip(bytes, { maxEntries, maxTotalBytes }) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const end = findEnd(bytes, view);
  const count = view.getUint16(end + 10, true);
  if (view.getUint16(end + 4, true) !== 0 || view.getUint16(end + 8, true) !== count) {
    throw new ZipError("ZIP-Dateien über mehrere Teile gehen nicht.");
  }
  if (count > maxEntries) throw new ZipError(`Die Datei enthält zu viele Einträge (höchstens ${maxEntries}).`);
  const decoder = new TextDecoder("utf-8", { fatal: true });
  const entries = [];
  let total = 0;
  let position = view.getUint32(end + 16, true);
  for (let i = 0; i < count; i++) {
    const entry = centralEntry(bytes, view, position, decoder);
    position = entry.next;
    if (entry.name.endsWith("/")) continue;
    total += entry.size;
    if (total > maxTotalBytes) throw new ZipError(`Der Inhalt ist zu gross (höchstens ${Math.floor(maxTotalBytes / 1000000)} MB).`);
    entries.push({ name: entry.name, data: await entryData(bytes, view, entry) });
  }
  return entries;
}

function findEnd(bytes, view) {
  const lowest = Math.max(0, bytes.length - END_RECORD - MAX_COMMENT);
  for (let i = bytes.length - END_RECORD; i >= lowest; i--) {
    if (view.getUint32(i, true) === SIG_END) return i;
  }
  throw new ZipError("Die Datei ist keine ZIP-Datei.");
}

function centralEntry(bytes, view, at, decoder) {
  if (at + CENTRAL_HEADER > bytes.length || view.getUint32(at, true) !== SIG_CENTRAL) {
    throw new ZipError("Die Datei ist beschädigt (Inhaltsverzeichnis).");
  }
  const flags = view.getUint16(at + 8, true);
  if (flags & FLAG_ENCRYPTED) throw new ZipError("Verschlüsselte ZIP-Dateien gehen nicht.");
  const nameLength = view.getUint16(at + 28, true);
  const next = at + CENTRAL_HEADER + nameLength + view.getUint16(at + 30, true) + view.getUint16(at + 32, true);
  if (next > bytes.length) throw new ZipError("Die Datei ist beschädigt (Inhaltsverzeichnis).");
  let name;
  try {
    name = decoder.decode(bytes.subarray(at + CENTRAL_HEADER, at + CENTRAL_HEADER + nameLength));
  } catch (error) {
    throw new ZipError("Ein Dateiname in der ZIP-Datei ist ungültig.");
  }
  return {
    name, next, method: view.getUint16(at + 10, true), crc: view.getUint32(at + 16, true),
    compressed: view.getUint32(at + 20, true), size: view.getUint32(at + 24, true), offset: view.getUint32(at + 42, true),
  };
}

async function entryData(bytes, view, entry) {
  const at = entry.offset;
  if (at + LOCAL_HEADER > bytes.length || view.getUint32(at, true) !== SIG_LOCAL) {
    throw new ZipError("Die Datei ist beschädigt (Eintrag nicht gefunden).");
  }
  const start = at + LOCAL_HEADER + view.getUint16(at + 26, true) + view.getUint16(at + 28, true);
  if (start + entry.compressed > bytes.length) throw new ZipError("Die Datei ist beschädigt (Eintrag abgeschnitten).");
  const raw = bytes.subarray(start, start + entry.compressed);
  let data;
  if (entry.method === METHOD_STORED) data = raw.slice();
  else if (entry.method === METHOD_DEFLATE) {
    try {
      data = await streamThrough(raw, new DecompressionStream("deflate-raw"), entry.size);
    } catch (error) {
      if (error instanceof ZipError) throw error;
      throw new ZipError(`Die Datei ist beschädigt (${entry.name}).`);
    }
  } else throw new ZipError(`Diese Art der Komprimierung geht nicht (${entry.name}).`);
  if (data.length !== entry.size || crc32(data) !== entry.crc) throw new ZipError(`Die Datei ist beschädigt (${entry.name}).`);
  return data;
}

if (typeof module !== "undefined") {
  module.exports = { crc32, createZip, readZip, ZipError };
}
