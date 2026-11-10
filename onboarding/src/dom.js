// DOM building blocks of the template. Values from the person or a loaded file are only ever set as
// text or form values, never as HTML.
"use strict";

const MAX_TAG_OPTIONS = 50;
const DEFAULT_MAX_LINES = 20;
const TAG_PLACEHOLDER = "z.B. daten, führung";
const LANGUAGE_NAMES = { de: "Deutsch", en: "Englisch" };
const BILINGUAL_TEXT = {
  lead: "Zweisprachig, hier nicht änderbar:",
  where: "Beide Sprachen lassen sich unter „Inhalte als Text“ (Menü „Mehr“) ändern.",
  field: "Eine Eingabe hier ersetzt beide.",
  line: "Eine Eingabe in der Zeile ersetzt beide.",
};

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

/** The note under a value from cv.yaml in two languages (#167): both shown, edited elsewhere, replaced by typing. */
function bilingualNote(value, replacing) {
  const languages = Object.entries(value).map(([key, text]) => `${LANGUAGE_NAMES[key] || key} „${text.trim()}“`).join(", ");
  return el("p", { className: "hint bilingual" }, `${BILINGUAL_TEXT.lead} ${languages}. ${BILINGUAL_TEXT.where} ${replacing}`);
}

/**
 * A text control on a value that may come in two languages: it starts empty then, and emptying it again keeps the
 * two languages, so only typing replaces them.
 */
function textInput(tag, attrs, ctx) {
  const original = isBilingual(ctx.value) ? ctx.value : null;
  const input = el(tag, {
    ...attrs, value: original ? "" : ctx.value || "", oninput: (e) => ctx.onChange(original && e.target.value === "" ? original : e.target.value),
  });
  return original ? [input, bilingualNote(original, BILINGUAL_TEXT.field)] : input;
}

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
    ...[].concat(isCantons ? cantonsView(field, ctx, label, hint, hintId, errorId)
      : isGroup ? choiceView(field, ctx, id, label, hint, hintId, errorId) : control),
    el("p", { className: "error", id: errorId, role: "alert" }),
  ]);
}

function controlView(field, ctx, id, describedBy) {
  if (field.control === "cantons") return null;
  const common = { id, "aria-describedby": describedBy, "aria-required": field.required ? "true" : null, onblur: () => ctx.onBlur() };
  if (field.type === "textarea") return textInput("textarea", { ...common, rows: 4 }, ctx);
  if (field.type === "tags") {
    const onTags = (tags) => ctx.onChange(tags);
    return el("div", { className: "tags-control" }, tagsInput({ ...common, placeholder: TAG_PLACEHOLDER }, ctx.value, ctx.tagSuggestions, onTags));
  }
  if (field.type === "list" && field.tags === true) return linesView(field, ctx, id, describedBy, TAGGED_LINES);
  if (field.type === "list" && field.levels === true) return linesView(field, ctx, id, describedBy, LEVELED_LINES);
  if (field.type === "list") {
    const text = listToLines(ctx.value);
    return el("textarea", {
      ...common, rows: Math.max(3, text.split("\n").length + 1), value: text,
      placeholder: "Eine Angabe pro Zeile", oninput: (e) => ctx.onChange(linesToList(e.target.value)),
    });
  }
  if (field.type === "select") {
    // a value from cv.yaml outside the options is shown as it is and stays until the person picks another (#167)
    const own = typeof ctx.value === "string" && ctx.value !== "" && !field.options.includes(ctx.value) ? [ctx.value] : [];
    const select = el("select", { ...common, onchange: (e) => ctx.onChange(e.target.value) }, [
      el("option", { value: "" }, field.emptyLabel ?? "– bitte wählen –"),
      ...[...field.options, ...own].map((o) => el("option", { value: o, selected: o === ctx.value }, field.optionLabels?.[o] ?? o)),
    ]);
    return select;
  }
  if (field.type === "choice") return null;
  const type = field.format === "email" ? "email" : field.format === "phone" ? "tel" : "text";
  return textInput("input", { ...common, type, placeholder: field.placeholder || "", autocomplete: autocompleteFor(ctx.path) }, ctx);
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

const LEVEL_OPTIONS = ["1", "2", "3", "4", "5", "6"];
const NO_LEVEL = "ohne Stufe";

/** Lines with tags (highlights): the extra of a line is its tags, typed with commas. */
const TAGGED_LINES = {
  extraOf: (line) => (line !== null && typeof line === "object" && Array.isArray(line.tags) ? line.tags : []),
  line: (text, tags) => taggedLine(text, tags),  // looked up on use: a test sandbox may load dom.js without model.js
  controls(extra, number, ctx, onExtra, disabled) {
    const attrs = { className: "line-tags", placeholder: "Tags", "aria-label": `Tags zu Zeile ${number}`, onblur: () => ctx.onBlur(), disabled };
    return tagsInput(attrs, extra, ctx.tagSuggestions, onExtra);
  },
};

/** Lines with a level (keywords, #123): an optional level 1–6, no preset, and „ohne Stufe“ removes it. */
const LEVELED_LINES = {
  extraOf: (line) => (line !== null && typeof line === "object" && typeof line.level === "string" ? line.level : ""),
  line: (text, level) => ({ text, level }),
  controls(extra, number, ctx, onExtra, disabled) {
    return [el("select", {
      className: "line-level", "aria-label": `Stufe zu Zeile ${number}`, onblur: () => ctx.onBlur(), disabled,
      onchange: (e) => onExtra(e.target.value),
    }, [
      el("option", { value: "", selected: extra === "" }, NO_LEVEL),
      ...LEVEL_OPTIONS.map((level) => el("option", { value: level, selected: level === extra }, level)),
    ])];
  },
};

/** A list whose lines take something besides their text (tags, a level): one row per line. */
function linesView(field, ctx, id, describedBy, kind) {
  const name = forTrack(field.label, ctx.track).split(" (")[0];
  const max = field.maxItems ?? DEFAULT_MAX_LINES;
  let lines = Array.isArray(ctx.value) && ctx.value.length ? ctx.value : [""];
  const rows = el("div", { className: "tagged-lines" });
  const view = el("div", { className: "tagged-list" });
  const change = (next, focusAt) => {
    lines = next.length ? next : [""];
    ctx.onChange(lines);
    if (focusAt !== undefined) draw(focusAt);
  };
  const setLine = (index, text, extra) => change(lines.map((line, i) => (i === index ? kind.line(text, extra) : line)));
  const add = el("button", {
    type: "button", className: "add-line", onclick: () => change([...lines, ""], lines.length),
  }, "+ Zeile hinzufügen");

  // a line in two languages (#167) starts empty and keeps its tags until the person types a new text
  function row(line, index) {
    const number = index + 1;
    const original = bilingualOf(line);
    const text = el("input", {
      type: "text", id: index === 0 ? id : null, value: original ? "" : lineText(line), "aria-label": `${name}, Zeile ${number}`,
      "aria-describedby": describedBy, onblur: () => ctx.onBlur(),
      oninput: (e) => setLine(index, e.target.value, kind.extraOf(lines[index])),
    });
    const extras = kind.controls(kind.extraOf(line), number, ctx, (found) => setLine(index, lineText(lines[index]), found), Boolean(original));
    const remove = el("button", {
      type: "button", className: "remove-line", "aria-label": `Zeile ${number} entfernen`,
      onclick: () => change(lines.filter((_, i) => i !== index), Math.max(0, index - 1)),
    }, "×");
    return el("div", { className: "tagged-line" }, [text, ...extras, remove, original ? bilingualNote(original, BILINGUAL_TEXT.line) : null]);
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
