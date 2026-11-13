// DOM building blocks of the template. Values from the person or a loaded file are only ever set as
// text or form values, never as HTML.
"use strict";

const MAX_TAG_OPTIONS = 50;
const DEFAULT_MAX_LINES = 20;
const TAG_PLACEHOLDER = "z.B. daten, führung";
const SWITCHED_OFF = "switchedOff"; // control of a list that names the options switched off (#291)
const LANGUAGE_NAMES = { de: "Deutsch", en: "Englisch" }; // of a value in two languages, as cv.yaml writes it
const ADD_ENGLISH = "+ Englisch";
const DROP_ENGLISH = "Englisch entfernen";

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

/** One input per language of a value { de, en }, each labelled with its language; onText(language, text). */
function languageInputs(tag, attrs, name, value, onText) {
  return Object.keys(LANGUAGE_NAMES).map((language, index) => el(tag, {
    ...attrs, id: index === 0 ? attrs.id : null, value: value[language] || "", "aria-label": `${name}, ${LANGUAGE_NAMES[language]}`,
    oninput: (e) => onText(language, e.target.value),
  }));
}

/** The inputs of languageInputs, each in a row with the name of its language. */
function languageRows(inputs) {
  const names = Object.values(LANGUAGE_NAMES);
  return inputs.map((input, index) => el("div", { className: "language-row" }, [
    el("span", { className: "language-name", "aria-hidden": "true" }, names[index]), input,
  ]));
}

/**
 * A text control on a value that may be in two languages (G30): a value { de, en } gets one input per language, and a
 * field marked "bilingual": true in form.json can add English to a plain text and drop it again. A field marked
 * "edit" (the name, the address) edits two languages it has but offers none.
 */
function textInput(tag, attrs, ctx, field, name) {
  let value = ctx.value;
  const view = el("div", { className: "text-control" });
  const list = field.suggestions ? el("datalist", { id: nextId("suggest") }, field.suggestions.map((s) => el("option", { value: s }))) : null;
  const shared = { ...attrs, list: list ? list.id : null };
  const change = (next) => { value = next; ctx.onChange(next); };
  const redraw = (next, focus) => { change(next); draw(focus); };

  function draw(focus) {
    if (!isBilingual(value)) {
      const input = el(tag, { ...shared, value: typeof value === "string" ? value : "", oninput: (e) => change(e.target.value) });
      const add = field.bilingual === true ? el("button", {
        type: "button", className: "language-toggle", "aria-label": `${name}: Englisch ergänzen`,
        onclick: () => redraw({ de: typeof value === "string" ? value : "", en: "" }, 1),
      }, ADD_ENGLISH) : null;
      view.replaceChildren(...[input, add, list].filter(Boolean));
      if (focus !== undefined) input.focus();
      return;
    }
    const inputs = languageInputs(tag, shared, name, value, (language, text) => change({ ...value, [language]: text }));
    const drop = el("button", {
      type: "button", className: "language-toggle", "aria-label": `${name}: Englisch entfernen`,
      onclick: () => redraw(value.de || value.en || "", 0),
    }, DROP_ENGLISH);
    view.replaceChildren(...languageRows(inputs), ...[drop, list].filter(Boolean));
    if (focus !== undefined) inputs[focus].focus();
  }

  draw();
  return view;
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
  const isSwitches = field.control === SWITCHED_OFF;
  const isGroup = field.type === "choice" || isCantons || isSwitches;
  return el("div", { className: `field field-${field.type}`, dataset: { path: ctx.path } }, [
    isGroup ? null : el("label", { for: id }, label),
    isGroup ? null : hint ? el("p", { className: "hint", id: hintId }, hint) : null,
    ...[].concat(isCantons ? cantonsView(field, ctx, label, hint, hintId, errorId)
      : isSwitches ? switchedOffView(field, ctx, label, hint, hintId, errorId)
        : isGroup ? choiceView(field, ctx, id, label, hint, hintId, errorId) : control),
    el("p", { className: "error", id: errorId, role: "alert" }),
  ]);
}

function controlView(field, ctx, id, describedBy) {
  if (field.control === "cantons" || field.control === SWITCHED_OFF) return null;
  const common = { id, "aria-describedby": describedBy, "aria-required": field.required ? "true" : null, onblur: () => ctx.onBlur() };
  const name = forTrack(field.label, ctx.track).split(" (")[0];
  if (field.type === "textarea") return textInput("textarea", { ...common, rows: 4 }, ctx, field, name);
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
  return textInput("input", { ...common, type, placeholder: field.placeholder || "", autocomplete: autocompleteFor(ctx.path) }, ctx, field, name);
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
  const valueOf = (line) => bilingualOf(line) || lineText(line); // its text, or its two languages (G30)
  const setLine = (index, text, extra) => change(lines.map((line, i) => (i === index ? kind.line(text, extra) : line)));
  const add = el("button", {
    type: "button", className: "add-line", onclick: () => change([...lines, ""], lines.length),
  }, "+ Zeile hinzufügen");
  const languages = field.bilingual === true && kind === TAGGED_LINES;
  let firstInputs = [];

  // a line in two languages (#167, G30) has an input per language; a list marked "bilingual" adds and drops English
  function row(line, index) {
    const number = index + 1;
    const both = bilingualOf(line);
    const attrs = { type: "text", id: index === 0 ? id : null, "aria-describedby": describedBy, onblur: () => ctx.onBlur() };
    const inputs = both
      ? languageInputs("input", attrs, `${name}, Zeile ${number}`, both,
        (language, text) => setLine(index, { ...bilingualOf(lines[index]), [language]: text }, kind.extraOf(lines[index])))
      : [el("input", { ...attrs, value: lineText(line), "aria-label": `${name}, Zeile ${number}`,
        oninput: (e) => setLine(index, e.target.value, kind.extraOf(lines[index])) })];
    const extras = kind.controls(kind.extraOf(line), number, ctx, (found) => setLine(index, valueOf(lines[index]), found), false);
    const toggle = languages ? el("button", {
      type: "button", className: "language-toggle",
      "aria-label": both ? `Englisch aus Zeile ${number} entfernen` : `Zeile ${number} auf Englisch ergänzen`,
      onclick: () => {
        const current = lines[index];
        const text = both ? both.de || both.en || "" : { de: lineText(current), en: "" };
        change(lines.map((l, i) => (i === index ? kind.line(text, kind.extraOf(current)) : l)), index);
      },
    }, both ? "− EN" : "+ EN") : null;
    const remove = el("button", {
      type: "button", className: "remove-line", "aria-label": `Zeile ${number} entfernen`,
      onclick: () => change(lines.filter((_, i) => i !== index), Math.max(0, index - 1)),
    }, "×");
    firstInputs = [...firstInputs, inputs[both ? 1 : 0]];
    const text = both ? el("div", { className: "line-languages" }, languageRows(inputs)) : inputs[0];
    return el("div", { className: "tagged-line" }, [text, ...extras, toggle, remove].filter(Boolean));
  }

  function draw(focusAt) {
    firstInputs = [];
    rows.replaceChildren(...lines.map(row));
    view.replaceChildren(rows, ...(lines.length < max ? [add] : []));
    const target = focusAt === undefined ? null : firstInputs[Math.min(focusAt, lines.length - 1)];
    if (target) target.focus();
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

/**
 * Boxes ticked for every option that is on, while the answer lists those switched off (#291): the portals of the
 * search, where nothing listed means every portal searches, as in the search profile.
 */
function switchedOffView(field, ctx, label, hint, hintId, errorId) {
  let off = Array.isArray(ctx.value) ? ctx.value : [];
  const changed = (e) => {
    const option = e.target.value;
    const others = off.filter((value) => value !== option);
    off = field.options.filter((value) => (value === option ? !e.target.checked : others.includes(value)));
    ctx.onChange(off);
  };
  return el("fieldset", { className: "choice switches", "aria-describedby": [hintId, errorId].filter(Boolean).join(" ") }, [
    el("legend", {}, label),
    hint ? el("p", { className: "hint", id: hintId }, hint) : null,
    el("div", { className: "canton-list" }, field.options.map((option) => el("label", { className: "option" }, [
      el("input", { type: "checkbox", value: option, checked: !off.includes(option), onchange: changed, onblur: () => ctx.onBlur() }),
      el("span", {}, field.optionLabels?.[option] ?? option),
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
