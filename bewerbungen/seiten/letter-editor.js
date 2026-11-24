"use strict";
// Editing the letter paragraph by paragraph in the step Anschreiben (G94, #332, binding brief of the UI/UX review): an
// edit mode of the same card, opened by «Anschreiben ändern», by the button in the group «Längster Absatz» and by «Im
// Anschreiben kürzen». Numbers and words without DOM in letter-editor-logik.js; bewerbung.js hands over what it drew
// (update) and its reload (connect). A small stand-in DOM tests it (tests/letter_editor.test.cjs).
(() => {
  const { el, senden } = window.App;
  const L = window.LetterEditorLogik;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const READ_VIEW = ["anschreiben-text", "ki-pruefung-teil", "freigabe-zeile", "freigabe-status"];
  const LOCKED = ["ki-entwerfen", "ki-pruefen", "erstellen", "pruefen"];
  // In the app language (#429); the page's Texte has its language before any script runs
  const Texte = { t: (deutsch, werte) => window.Texte.t(deutsch, werte) };
  const SAVE = Texte.t("Speichern");
  const SAVING = Texte.t("Wird gespeichert …");
  const REBUILD = Texte.t("Unterlagen neu erstellen");
  const RELOAD = Texte.t("Neu laden");
  const LONGEST = Texte.t("Längster Absatz");
  const REMOVE = Texte.t("Entfernen");
  const NO_TEXT = Texte.t("Das Anschreiben braucht mindestens einen Absatz mit Text.");
  const MAX_PARAGRAPH_CHARS = 4000;  // letter_edit.MAX_PARAGRAPH_CHARS

  let data = null;        // what the page drew last: letter, cut (letter_cut while open), approved, shown
  let loaded = null;      // the values at open, to tell a change
  let paragraphs = [];
  let baseline = 0;       // lines at open, for the goal line
  let open = false;
  let leaving = false;    // «Neu laden» was asked for, so no question on unload
  let readView = {};
  let reload = async () => {};
  let satz = "stelle-sie";
  window.App.textsatz().then(chosen => { satz = chosen; });

  const t = key => window.Texte.text(key, satz);
  const say = (text, level = "", options = {}) => window.Meldungen.zeige($("brief-editor-status"), text, level, options);
  const charsPerLine = () => data.letter.zeichen_pro_zeile;
  const fields = () => $("brief-absaetze").querySelectorAll("textarea");
  const values = () => ({ betreff: $("brief-betreff").value, anrede: $("brief-anrede").value, absaetze: paragraphs,
                          gruss: $("brief-gruss").value });
  const dirty = () => open && L.isDirty(loaded, values());
  const editHref = () => "/inhalte?" + new URLSearchParams({ datei: `bewerbungen/${ID}/anschreiben.yaml`, ansicht: "text" });

  /** The page drew the step anew (bewerbung.js, zeigeBrief): keep what it wants shown, hidden again while open. */
  function update({ letter, findings, approval, shown }) {
    const over = (findings || []).find(b => b.letter_cut && !b.bestaetigt);
    data = { letter, cut: over ? over.letter_cut : null, approved: Boolean(approval && approval.freigegeben), shown };
    readView = Object.fromEntries(READ_VIEW.map(id => [id, $(id).hidden]));
    if (!open) return;
    lock();
    markLongest();
    showGoal();
  }

  /**
   * The page and ki.js set `disabled` on these buttons themselves, so the editor locks them with aria-disabled and
   * stops their clicks before any handler, including a click from code (the card «Nächster Schritt»).
   */
  function guard(event) {
    if (!LOCKED.some(id => event.target === $(id))) return;
    event.preventDefault();
    event.stopImmediatePropagation();
  }

  function lock() {
    READ_VIEW.forEach(id => { $(id).hidden = true; });
    LOCKED.forEach(id => {
      $(id).setAttribute("aria-disabled", "true");
      $(id).setAttribute("aria-describedby", "brief-offen-hinweis");
    });
    $("brief-offen-hinweis").hidden = false;
  }

  function unlock() {
    LOCKED.forEach(id => {
      $(id).removeAttribute("aria-disabled");
      $(id).removeAttribute("aria-describedby");
    });
    $("brief-offen-hinweis").hidden = true;
  }

  function autosize(field) {
    if (typeof CSS !== "undefined" && CSS.supports("field-sizing", "content")) return;
    field.style.height = "auto";
    field.style.height = `${field.scrollHeight + field.offsetHeight - field.clientHeight}px`;
  }

  function labelParts(place, longest) {
    return [Texte.t("Absatz {nummer}", { nummer: place + 1 }),
      ...(longest ? [" ", el("span", { class: "letter-editor__longest" }, LONGEST)] : [])];
  }

  function block(text, place) {
    const id = `brief-absatz-${place + 1}`;
    const field = el("textarea", { class: "input letter-editor__field", id, rows: "3", maxlength: String(MAX_PARAGRAPH_CHARS),
                                   "aria-describedby": `${id}-hinweis` });
    field.value = text;
    field.addEventListener("input", () => changed(place, field));
    const remove = paragraphs.length > 1 ? el("button", { type: "button", class: "btn btn--quiet btn--sm letter-editor__remove",
      "aria-label": Texte.t("Absatz {nummer} entfernen", { nummer: place + 1 }), onclick: () => removeAt(place) }, REMOVE) : null;
    return el("div", { class: "letter-editor__paragraph" },
      el("label", { class: "field__label letter-editor__label", for: id }, ...labelParts(place, false)), field,
      el("div", { class: "letter-editor__meta" },
        el("p", { class: "field__hint letter-editor__hint", id: `${id}-hinweis` }, L.lineHint(text, charsPerLine())), remove));
  }

  function render() {
    $("brief-absaetze").replaceChildren(...paragraphs.map(block));
    fields().forEach(autosize);
    markLongest();
    showGoal();
  }

  /** The mark follows the longest paragraph live, only while the check found the letter over one page. */
  function markLongest() {
    const longest = data.cut ? L.longestIndex(paragraphs) : -1;
    fields().forEach((field, place) => {
      field.parentNode.classList.toggle("letter-editor__paragraph--longest", place === longest);
      field.parentNode.querySelector("label").replaceChildren(...labelParts(place, place === longest));
    });
  }

  function showGoal() {
    const line = L.goalLine(data.cut, baseline, L.totalLines(paragraphs, charsPerLine()));
    $("brief-ziel").hidden = !line;
    $("brief-ziel").textContent = line;
  }

  function changed(place, field) {
    paragraphs = paragraphs.map((text, at) => (at === place ? field.value : text));
    hintOf(field).textContent = L.lineHint(field.value, charsPerLine());
    field.removeAttribute("aria-invalid");
    autosize(field);
    markLongest();
    showGoal();
  }

  const hintOf = field => field.parentNode.querySelector(".letter-editor__hint");

  function removeAt(place) {
    paragraphs = paragraphs.filter((_, at) => at !== place);
    render();
    fields()[L.focusAfterRemove(place, paragraphs.length)].focus();
  }

  function add() {
    paragraphs = [...paragraphs, ""];
    render();
    fields()[paragraphs.length - 1].focus();
  }

  function focusLongest() {
    const field = fields()[Math.max(L.longestIndex(paragraphs), 0)];
    field.focus({ preventScroll: true });
    field.setSelectionRange(0, 0);
    field.scrollIntoView({ block: "center" });
  }

  function focusTitle() {
    $("brief-editor-titel").focus({ preventScroll: true });
    $("brief-editor-titel").scrollIntoView({ block: "start" });
  }

  function fill() {
    const letter = data.letter;
    paragraphs = letter.absaetze.length ? [...letter.absaetze] : [""];
    $("brief-betreff").value = letter.betreff;
    $("brief-anrede").value = letter.anrede;
    $("brief-gruss").value = letter.gruss;
    loaded = { ...values(), absaetze: [...paragraphs] };
    baseline = L.totalLines(paragraphs, charsPerLine());
    $("brief-editor-intro").textContent = [t("anschreiben.editor-intro"), data.approved ? t("anschreiben.editor-freigabe") : ""]
      .filter(Boolean).join(" ");
    $("brief-als-text").setAttribute("href", editHref());
  }

  /** Opens the editor, or only moves the focus when it is open; false without a letter to edit. */
  function openEditor(atLongest) {
    if (!data || !data.shown || !data.letter) return false;
    if (!open) {
      fill();
      window.Meldungen.zeige($("brief-gespeichert"), "");
      say("");
      ask(false, false);
      open = true;
      document.addEventListener("click", guard, true);
      $("brief-editor").hidden = false;
      $("anschreiben-aendern").setAttribute("aria-expanded", "true");
      render();
      lock();
    }
    if (atLongest) focusLongest();
    else focusTitle();
    return true;
  }

  function close(focusOpener = true) {
    open = false;
    $("brief-editor").hidden = true;
    document.removeEventListener("click", guard, true);
    READ_VIEW.forEach(id => { $(id).hidden = readView[id]; });
    unlock();
    $("anschreiben-aendern").setAttribute("aria-expanded", "false");
    say("");
    if (focusOpener) $("anschreiben-aendern").focus();
  }

  function ask(shown, moveFocus = true) {
    $("brief-aktionen").hidden = shown;
    $("brief-verwerfen").hidden = !shown;
    if (moveFocus) (shown ? $("brief-weiter") : $("brief-abbrechen")).focus();
  }

  const cancel = () => (dirty() ? ask(true) : close());

  function busy(on) {
    $("brief-speichern").disabled = on;
    $("brief-speichern").textContent = on ? SAVING : SAVE;
  }

  function rebuild() {
    $("erstellen").click();
    $("s-pruefen").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function saved() {
    const line = $("brief-gespeichert");
    window.Meldungen.zeige(line, t("anschreiben.gespeichert"), "ok", { aktion: { text: REBUILD, ausfuehren: rebuild } });
    line.querySelector(".status__action")?.focus();
  }

  function failed(error) {
    const kind = L.failure(error);
    if (kind === "conflict") {
      say(t("anschreiben.geaendert"), "fehler", { aktion: { text: RELOAD, ausfuehren: () => { leaving = true; location.reload(); } } });
    } else {
      say(kind === "unreachable" ? t("anschreiben.nicht-erreichbar") : L.refusedText(error.message), "fehler");
    }
    $("brief-speichern").focus();
  }

  function refuseEmpty() {
    const first = fields()[0];
    first.setAttribute("aria-invalid", "true");
    say(NO_TEXT, "fehler", { input: $("brief-absaetze") });
    first.focus();
  }

  async function save(event) {
    event.preventDefault();
    const now = values();
    if (L.isEmpty(now)) return refuseEmpty();
    if (!L.isDirty(loaded, now)) return close();
    busy(true);
    try {
      const answer = await senden("/api/bewerbung/anschreiben", L.payload(now, data.letter.fingerabdruck), { id: ID });
      loaded = now;
      await reload();
      busy(false);
      close(answer.geaendert === false);
      if (answer.geaendert !== false) saved();
    } catch (error) {
      busy(false);
      failed(error);
    }
  }

  /** «Im Anschreiben kürzen» without a letter to edit: to the step, the focus on the marked paragraph (G94). */
  function toLongestParagraph() {
    const target = $(window.FindingRow.LONGEST_ID) || $("anschreiben-titel");
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    target.focus({ preventScroll: true });
  }

  const cut = () => openEditor(true) || toLongestParagraph();

  $("anschreiben-aendern").addEventListener("click", () => openEditor(false));
  $("brief-editor").addEventListener("submit", save);
  $("brief-abbrechen").addEventListener("click", cancel);
  $("brief-weiter").addEventListener("click", () => ask(false));
  $("brief-verwerfen-ja").addEventListener("click", () => close());
  $("brief-absatz-neu").addEventListener("click", add);
  $("erstellen").addEventListener("click", () => window.Meldungen.zeige($("brief-gespeichert"), ""));
  window.addEventListener("beforeunload", event => {
    if (leaving || !dirty()) return;
    event.preventDefault();
    event.returnValue = "";
  });

  window.LetterEditor = {
    update, cut,
    isOpen: () => open,
    connect: reloadPage => { reload = reloadPage; },
    open: () => openEditor(false),
    openAtLongest: () => openEditor(true),
  };
})();
