// DOM building blocks of the template. Values from the person or a loaded file are only ever set as
// text or form values, never as HTML.
"use strict";

const MAX_TAG_OPTIONS = 50;
const DEFAULT_MAX_LINES = 20;
const TAG_PLACEHOLDER = "z.B. daten, führung";

/** Create an element; attrs are properties (on* handlers, dataset, aria via setAttribute). */
function el(tag, attrs, children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("aria-") || key === "role" || key === "for" || key === "list") node.setAttribute(key, value);
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
 * ctx: { track, value, path (string), tagSuggestions (tags offered while typing), onChange(value), onBlur() }
 */
function fieldView(field, ctx) {
  const id = nextId("f");
  const hint = forTrack(field.hint, ctx.track);
  const hintId = hint ? `${id}-hint` : null;
  const errorId = `${id}-error`;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ");
  const label = forTrack(field.label, ctx.track) + (field.required ? " *" : "");
  const control = controlView(field, ctx, id, describedBy);
  const isCantons = field.control === "cantons";
  const isGroup = field.type === "choice" || isCantons;
  return el("div", { className: `field field-${field.type}`, dataset: { path: ctx.path } }, [
    isGroup ? null : el("label", { for: id }, label),
    isGroup ? null : hint ? el("p", { className: "hint", id: hintId }, hint) : null,
    isCantons ? cantonsView(field, ctx, label, hint, hintId, errorId)
      : isGroup ? choiceView(field, ctx, id, label, hint, hintId, errorId) : control,
    el("p", { className: "error", id: errorId, role: "alert" }),
  ]);
}

function controlView(field, ctx, id, describedBy) {
  if (field.control === "cantons") return null;
  const common = { id, "aria-describedby": describedBy, "aria-required": field.required ? "true" : null, onblur: () => ctx.onBlur() };
  if (field.type === "textarea") {
    return el("textarea", { ...common, rows: 4, value: ctx.value || "", oninput: (e) => ctx.onChange(e.target.value) });
  }
  if (field.type === "tags") {
    const onTags = (tags) => ctx.onChange(tags);
    return el("div", { className: "tags-control" }, tagsInput({ ...common, placeholder: TAG_PLACEHOLDER }, ctx.value, ctx.tagSuggestions, onTags));
  }
  if (field.type === "list" && field.tags === true) return taggedLinesView(field, ctx, id, describedBy);
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

/**
 * What the list of a tags input offers: the last tag completed, or another tag after a complete one. A datalist
 * matches the whole text of the input, so each option is the whole text with the tag in it.
 */
function tagOptions(text, suggestions) {
  const offered = Array.isArray(suggestions) ? suggestions : [];
  const parts = String(text).split(",");
  const done = parts.slice(0, -1).map((t) => t.trim()).filter((t) => t);
  const last = parts[parts.length - 1].trim();
  const free = offered.filter((t) => t !== last && !done.includes(t));
  const completed = free.filter((t) => t.toLowerCase().startsWith(last.toLowerCase())).map((t) => [...done, t].join(", "));
  const added = offered.includes(last) ? free.map((t) => [...done, last, t].join(", ")) : [];
  return [...new Set([...completed, ...added])].slice(0, MAX_TAG_OPTIONS);
}

/** A text input for tags separated by commas, with its own list of suggestions; onTags gets the tags. */
function tagsInput(attrs, tags, suggestions, onTags) {
  const listId = nextId("tags");
  const datalist = el("datalist", { id: listId });
  const offer = (text) => datalist.replaceChildren(...tagOptions(text, suggestions).map((o) => el("option", { value: o })));
  const text = tagsToText(tags);
  offer(text);
  const input = el("input", {
    ...attrs, type: "text", value: text, list: listId, autocomplete: "off", spellcheck: false,
    oninput: (e) => { offer(e.target.value); onTags(parseTags(e.target.value)); },
  });
  return [input, datalist];
}

/** A list whose lines take tags (highlights): one row per line with its text and its tags. */
function taggedLinesView(field, ctx, id, describedBy) {
  const name = forTrack(field.label, ctx.track).split(" (")[0];
  const max = field.maxItems ?? DEFAULT_MAX_LINES;
  let lines = Array.isArray(ctx.value) && ctx.value.length ? ctx.value : [""];
  const rows = el("div", { className: "tagged-lines" });
  const view = el("div", { className: "tagged-list" });
  const tagsOf = (line) => (line !== null && typeof line === "object" && Array.isArray(line.tags) ? line.tags : []);
  const change = (next, focusAt) => {
    lines = next.length ? next : [""];
    ctx.onChange(lines);
    if (focusAt !== undefined) draw(focusAt);
  };
  const setLine = (index, text, tags) => change(lines.map((line, i) => (i === index ? taggedLine(text, tags) : line)));
  const add = el("button", {
    type: "button", className: "add-line", onclick: () => change([...lines, ""], lines.length),
  }, "+ Zeile hinzufügen");

  function row(line, index) {
    const number = index + 1;
    const text = el("input", {
      type: "text", id: index === 0 ? id : null, value: lineText(line), "aria-label": `${name}, Zeile ${number}`,
      "aria-describedby": describedBy, onblur: () => ctx.onBlur(),
      oninput: (e) => setLine(index, e.target.value, tagsOf(lines[index])),
    });
    const tagAttrs = { className: "line-tags", placeholder: "Tags", "aria-label": `Tags zu Zeile ${number}`, onblur: () => ctx.onBlur() };
    const tags = tagsInput(tagAttrs, tagsOf(line), ctx.tagSuggestions, (found) => setLine(index, lineText(lines[index]), found));
    const remove = el("button", {
      type: "button", className: "remove-line", "aria-label": `Zeile ${number} entfernen`,
      onclick: () => change(lines.filter((_, i) => i !== index), Math.max(0, index - 1)),
    }, "×");
    return el("div", { className: "tagged-line" }, [text, ...tags, remove]);
  }

  function draw(focusAt) {
    rows.replaceChildren(...lines.map(row));
    view.replaceChildren(rows, ...(lines.length < max ? [add] : []));
    const target = focusAt === undefined ? null : rows.children[Math.min(focusAt, lines.length - 1)];
    if (target) target.children[0].focus();
  }

  draw();
  return view;
}

function autocompleteFor(path) {
  const map = { "person.name": "name", "person.email": "email", "person.phone": "tel", "person.address": "street-address",
    "person.postalCode": "postal-code", "person.city": "address-level2" };
  return map[path] || "off";
}

/** Radio group of suggested texts plus an own formulation. */
/** Names instead of codes: the answer stays the list of codes the search and the checks know. */
function cantonsView(field, ctx, label, hint, hintId, errorId) {
  const chosen = new Set(ctx.value || []);
  const changed = (e) => {
    const boxes = e.target.closest(".canton-list").querySelectorAll("input:checked");
    ctx.onChange([...boxes].map((box) => box.value));
  };
  return el("fieldset", { className: "choice cantons", "aria-describedby": [hintId, errorId].filter(Boolean).join(" ") }, [
    el("legend", {}, label),
    hint ? el("p", { className: "hint", id: hintId }, hint) : null,
    el("div", { className: "canton-list" }, ctx.cantons.map((canton) => el("label", { className: "option" }, [
      el("input", {
        type: "checkbox", value: canton.code, checked: chosen.has(canton.code),
        onchange: changed, onblur: () => ctx.onBlur(),
      }),
      el("span", {}, canton.name),
    ]))),
  ]);
}

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
