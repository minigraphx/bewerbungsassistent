// What a «·» line (dot-line.js) says, read from the stand-in elements of the page tests (#342): what the eye sees,
// what a screen reader hears, and its whole parts. Works with plain objects ({ attrs, children }) and with fake
// elements (attrs as a Map, className, text nodes with `data`).
"use strict";

const NBSP = String.fromCharCode(0xa0);

// A stand-in element may be a Proxy around a function, so functions count as nodes too.
const isNode = node => node !== null && (typeof node === "object" || typeof node === "function");
const attr = (node, name) => (node.attrs instanceof Map ? node.attrs.get(name) : (node.attrs || {})[name]);
const classOf = node => node.className || attr(node, "class") || "";
const kids = node => (Array.isArray(node.children) ? node.children.flat() : []);

/** The text below `node`, leaving out what `skip` says; an element without children keeps the text it was given. */
function textOf(node, skip) {
  if (!isNode(node)) return node === null || node === undefined || node === false ? "" : String(node);
  if (typeof node.data === "string" && !Array.isArray(node.children)) return node.data;
  if (skip(node)) return "";
  const children = kids(node);
  return children.length ? children.map(child => textOf(child, skip)).join("") : String(node.textContent ?? "");
}

const shown = node => textOf(node, n => classOf(n).split(" ").includes("visually-hidden"));
const heard = node => textOf(node, n => attr(n, "aria-hidden") === "true");

/** The whole parts directly below `node`, each as the eye reads it without its «·». */
const wholeParts = node => kids(node).filter(child => isNode(child) && classOf(child).split(" ").includes("whole-part"))
  .map(part => shown(part).replace(`${NBSP}·`, ""));

/** The line as the eye reads it, as `parts` joined by the helper. */
const seenLine = parts => parts.join(`${NBSP}· `);
/** The same line as a screen reader hears it. */
const heardLine = parts => parts.join(", ");

module.exports = { NBSP, shown, heard, wholeParts, seenLine, heardLine };
