// DOM building blocks of the template. Values from the person or a loaded file are only ever set as
// text or form values, never as HTML.
"use strict";

/** Create an element; attrs are properties (on* handlers, dataset, aria via setAttribute). */
function el(tag, attrs, children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("aria-") || key === "role" || key === "for") node.setAttribute(key, value);
    else node[key] = value;
  }
  for (const child of [].concat(children || [])) {
    if (child === null || child === undefined || child === false) continue;
    node.append(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

let idCounter = 0;
const nextId = (prefix) => `${prefix}-${++idCounter}`;

/**
 * One field with label, hint, control and error slot.
 * ctx: { track, value, path (string), onChange(value), onBlur() }
 */
function fieldView(field, ctx) {
  const id = nextId("f");
  const hint = forTrack(field.hint, ctx.track);
  const hintId = hint ? `${id}-hint` : null;
  const errorId = `${id}-error`;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ");
  const label = forTrack(field.label, ctx.track) + (field.required ? " *" : "");
  const control = controlView(field, ctx, id, describedBy);
  const isGroup = field.type === "choice";
  return el("div", { className: `field field-${field.type}`, dataset: { path: ctx.path } }, [
    isGroup ? null : el("label", { for: id }, label),
    isGroup ? null : hint ? el("p", { className: "hint", id: hintId }, hint) : null,
    isGroup ? choiceView(field, ctx, id, label, hint, hintId, errorId) : control,
    el("p", { className: "error", id: errorId, role: "alert" }),
  ]);
}

function controlView(field, ctx, id, describedBy) {
  const common = { id, "aria-describedby": describedBy, "aria-required": field.required ? "true" : null, onblur: () => ctx.onBlur() };
  if (field.type === "textarea") {
    return el("textarea", { ...common, rows: 4, value: ctx.value || "", oninput: (e) => ctx.onChange(e.target.value) });
  }
  if (field.type === "list") {
    const text = listToLines(ctx.value);
    return el("textarea", {
      ...common, rows: Math.max(3, text.split("\n").length + 1), value: text,
      placeholder: "Eine Angabe pro Zeile", oninput: (e) => ctx.onChange(linesToList(e.target.value)),
    });
  }
  if (field.type === "select") {
    const select = el("select", { ...common, onchange: (e) => ctx.onChange(e.target.value) }, [
      el("option", { value: "" }, "– bitte wählen –"),
      ...field.options.map((o) => el("option", { value: o, selected: o === ctx.value }, o)),
    ]);
    return select;
  }
  if (field.type === "choice") return null;
  const type = field.format === "email" ? "email" : field.format === "phone" ? "tel" : "text";
  return el("input", {
    ...common, type, value: ctx.value || "", placeholder: field.placeholder || "",
    autocomplete: autocompleteFor(ctx.path), oninput: (e) => ctx.onChange(e.target.value),
  });
}

function autocompleteFor(path) {
  const map = { "person.name": "name", "person.email": "email", "person.phone": "tel", "person.address": "street-address",
    "person.postalCode": "postal-code", "person.city": "address-level2" };
  return map[path] || "off";
}

/** Radio group of suggested texts plus an own formulation. */
function choiceView(field, ctx, id, label, hint, hintId, errorId) {
  const options = forTrack(field.options, ctx.track) || [];
  const value = ctx.value || "";
  const isOwn = value !== "" && !options.includes(value);
  const ownInput = el("input", {
    type: "text", value: isOwn ? value : "", className: "own", "aria-label": "Eigene Formulierung",
    oninput: (e) => { ownRadio.checked = true; ctx.onChange(e.target.value); }, onblur: () => ctx.onBlur(),
  });
  const ownRadio = el("input", {
    type: "radio", name: id, checked: isOwn,
    onchange: () => { ownInput.focus(); ctx.onChange(ownInput.value); },
  });
  const radios = options.map((option) => el("label", { className: "option" }, [
    el("input", { type: "radio", name: id, value: option, checked: option === value, onchange: () => ctx.onChange(option), onblur: () => ctx.onBlur() }),
    el("span", {}, option),
  ]));
  return el("fieldset", {
    className: "choice", role: "radiogroup", "aria-required": field.required ? "true" : null,
    "aria-describedby": [hintId, errorId].filter(Boolean).join(" "),
  }, [
    el("legend", {}, label),
    hint ? el("p", { className: "hint", id: hintId }, hint) : null,
    ...radios,
    field.allowOwn ? el("label", { className: "option own-option" }, [ownRadio, el("span", {}, "Eigene Formulierung:"), ownInput]) : null,
  ]);
}

/** Show the given messages in the error slots of the rendered fields (matching path or sub-paths). */
function showErrors(root, messagesByPath, visiblePaths) {
  for (const node of root.querySelectorAll(".field[data-path]")) {
    const path = node.dataset.path;
    const own = Object.entries(messagesByPath)
      .filter(([p]) => p === path || p.startsWith(`${path}.`))
      .map(([, m]) => m);
    const visible = visiblePaths.has(path) && own.length > 0;
    node.querySelector(".error").textContent = visible ? own.join(" ") : "";
    node.classList.toggle("invalid", visible);
    for (const control of node.querySelectorAll("input, textarea, select")) {
      if (visible) control.setAttribute("aria-invalid", "true");
      else control.removeAttribute("aria-invalid");
    }
  }
}

if (typeof module !== "undefined") {
  module.exports = { el, fieldView, showErrors };
}
