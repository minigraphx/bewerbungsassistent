// Only in the page „Meine Angaben“ of the app: when the Markdown files exist already, taking over asks per file
// whether it is replaced (G26). Keeping is the default; a file chosen for replacing shows its differences first.
// The app computes them (onboarding/text_diff.py) as lines of the kinds gleich, weg, neu and luecke.
"use strict";

const KEEP = "keep";
const REPLACE = "replace";
const REPLACE_TEXT = {
  intro: "Pro Datei wählen, ob sie bleibt oder durch die neuen Angaben ersetzt wird. Der Lebenslauf (cv.yaml) nimmt die Angaben in jedem Fall auf.",
  keep: "Behalten",
  replace: "Ersetzen",
  diff: "Unterschiede zum bisherigen Stand: Zeilen mit − fallen weg, Zeilen mit + kommen dazu.",
  same: "Kein Unterschied zum bisherigen Stand.",
  gap: "…",
};
const DIFF_MARKS = { gleich: "  ", weg: "− ", neu: "+ " };

/** Every file starts as kept. */
function defaultReplaceChoices(changes) {
  return Object.fromEntries(changes.map((change) => [change.datei, KEEP]));
}

/** The files chosen for replacing, as the app expects them in `ersetzen`. */
function chosenReplacements(choices) {
  return Object.keys(choices).filter((file) => choices[file] === REPLACE);
}

/** One choice per file; onChoose(file, "keep" | "replace") hands each change back. Picking shows or hides the
 * differences in place, so the focus stays on the option. */
function replaceChoiceView({ changes, choices, onChoose }) {
  return el("div", { className: "replace-choice" }, [
    el("p", { className: "hint" }, REPLACE_TEXT.intro),
    ...changes.map((change, index) => fileChoiceView(change, choices[change.datei] || KEEP, index, onChoose)),
  ]);
}

function fileChoiceView(change, chosen, index, onChoose) {
  const name = `replace-choice-${index}`;
  const slot = el("div", { className: "replace-choice__diff", "aria-live": "polite" }, chosen === REPLACE ? diffView(change) : null);
  const pick = (value) => {
    slot.replaceChildren(...(value === REPLACE ? [diffView(change)] : []));
    onChoose(change.datei, value);
  };
  const option = (value) => el("label", { className: "option" }, [
    el("input", { type: "radio", name, value, checked: chosen === value, onchange: () => pick(value) }),
    ` ${REPLACE_TEXT[value]}`,
  ]);
  return el("fieldset", { className: "replace-choice__file" }, [
    el("legend", {}, `${change.titel} (${change.datei})`),
    el("div", { className: "choice", role: "radiogroup" }, [option(KEEP), option(REPLACE)]),
    slot,
  ]);
}

function diffView(change) {
  if (!change.zeilen.length) return el("p", { className: "hint" }, REPLACE_TEXT.same);
  return el("div", { className: "diff" }, [
    el("p", { className: "hint" }, REPLACE_TEXT.diff),
    el("pre", { className: "diff__lines" }, change.zeilen.map(diffLine)),
  ]);
}

function diffLine(line) {
  if (line.art === "luecke") return el("span", { className: "diff__line diff__line--gap" }, `${REPLACE_TEXT.gap}\n`);
  const tag = line.art === "weg" ? "del" : line.art === "neu" ? "ins" : "span";
  return el("span", { className: `diff__line diff__line--${line.art}` }, [
    DIFF_MARKS[line.art] || "  ",
    el(tag, {}, line.text),
    "\n",
  ]);
}
