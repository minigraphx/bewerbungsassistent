"use strict";
// The DOM of the step «Unterlagen erstellen und prüfen» (#321, option A in docs/design/unterlagen-erstellen.md):
// «Beilagen ändern» opens in place, «Dossier gestalten» opens the dialog (#322, dossier-dialog.js), each built
// document is a tile with page 1 as a thumbnail and a link to where it is adapted, and the findings come with the
// passed checks collapsed. After creating, the form collapses into one line beside the attachments (board A3). What
// to show comes from unterlagen-ergebnis.js; bewerbung.js decides when.
(() => {
  const { el, url } = window.App;
  const R = window.UnterlagenErgebnis;
  const W = window.UnterlagenWahl;
  const $ = id => document.getElementById(id);
  const THUMB = { width: "96", height: "136" };  // A4 upright; CSS sets the size, these keep the space while loading
  const ANCHOR = { variant: "#s-lebenslauf", letter: "#s-anschreiben" };
  let formOpen = false;  // «Form ändern» shows the tiles again until the next creating
  let shownEntry = null;
  let shownBuilt = false;

  function disclosure(buttonId) {
    const button = $(buttonId);
    const panel = $(button.getAttribute("aria-controls"));
    button.addEventListener("click", () => {
      const open = button.getAttribute("aria-expanded") !== "true";
      button.setAttribute("aria-expanded", String(open));
      panel.hidden = !open;
    });
  }

  disclosure("beilagen-aendern");

  /** The dialog gives the focus back to the button that opened it. */
  const openDialog = from => window.DossierDialog.open(from);
  for (const id of ["dossier-gestalten", "form-dossier"]) $(id).addEventListener("click", event => openDialog(event.currentTarget));

  function goTo(section, target) {
    $(section).scrollIntoView({ behavior: "smooth", block: "start" });
    target.focus({ preventScroll: true });
  }

  const ADAPT = {
    variant: () => goTo("s-lebenslauf", $("f-variante")),
    // the editor of the step (#332), looked up at click time; without a letter to edit it returns false
    letter: () => window.LetterEditor.open() || goTo("s-anschreiben", $("anschreiben-titel")),
  };

  function adaptLink(adapt) {
    if (!adapt) return null;
    if (adapt.target === "dossier") {
      // one id across redraws, so the focus finds it again after «Übernehmen» (DossierDialog.refocus)
      return el("button", { type: "button", id: "doc-dossier-gestalten", class: "btn btn--quiet doc-tile__link", "aria-haspopup": "dialog",
        onclick: event => openDialog(event.currentTarget) }, adapt.text);
    }
    const attributes = { class: "btn btn--quiet doc-tile__link", href: adapt.href || ANCHOR[adapt.target] };
    if (!adapt.href) {
      attributes.onclick = event => {
        event.preventDefault();
        ADAPT[adapt.target]();
      };
    }
    return el("a", attributes, adapt.text);
  }

  /**
   * Pages and how they were balanced (G93), in plain words without a colour. Each part breaks only as a whole and
   * carries the «·» after it (#331): a line may break beside an inline-block despite a no-break space, so a «·» of its
   * own could stand alone on a line. The plain space between two parts is the only place a line breaks. Screen readers
   * skip the «·» and hear a comma.
   */
  function noteLine(tile) {
    if (!tile.note.length) return null;
    const last = tile.note.length - 1;
    const parts = tile.note.map((part, index) => (index === last
      ? el("span", { class: "doc-tile__part" }, part)
      : el("span", { class: "doc-tile__part" },
        part, el("span", { "aria-hidden": "true" }, "\u00a0·"), el("span", { class: "visually-hidden" }, ","))));
    return el("p", { class: "doc-tile__note" }, ...parts.flatMap((part, index) => (index === 0 ? [part] : [" ", part])));
  }

  /** One tile per built document; `stand` makes the browser load a rebuilt file anew. */
  function showTiles(entryId, daten, stand) {
    const entry = daten.bewerbung;
    const tiles = R.tiles(daten.pdfs, W.gewaehlt(entry),
      { ownCv: Boolean(daten.eigener_lebenslauf), sent: Boolean(entry.versand), notes: daten.seiten });
    $("pdfs").replaceChildren(...tiles.map(tile => {
      return el("article", { class: "doc-tile", "aria-labelledby": `doc-tile-${tile.art}` },
        el("img", { class: "doc-tile__thumb", src: url("/api/pdf/miniatur", { id: entryId, art: tile.art, stand }), alt: tile.alt, ...THUMB }),
        el("div", { class: "doc-tile__body" },
          el("h3", { class: "doc-tile__name", id: `doc-tile-${tile.art}` }, tile.name),
          noteLine(tile),
          el("div", { class: "doc-tile__links" },
            el("a", { class: "btn btn--sm doc-tile__link", href: url("/api/pdf", { id: entryId, art: tile.art, stand }), target: "_blank", rel: "noopener" }, tile.open),
            adaptLink(tile.adapt))));
    }));
  }

  /** `row` draws one finding as a list line (with «So lassen» where it applies, bewerbung.js). */
  function showFindings(findings, row) {
    const groups = R.findingGroups(findings);
    $("befunde").replaceChildren(...groups.shown.map(row));
    $("befunde-ok-liste").replaceChildren(...groups.ok.map(row));
    $("befunde-ok-titel").textContent = groups.okLabel;
    $("befunde-ok").hidden = !groups.ok.length;
    $("befunde-ansage").textContent = R.announcement(findings);
  }

  /** After creating, the focus goes to what the check found first; with nothing to do, to the passed checks. */
  function focusFirstFinding() {
    const first = $("befunde").firstElementChild || ($("befunde-ok").hidden ? null : $("befunde-ok-titel"));
    if (!first) return;
    if (first.tagName === "LI") first.tabIndex = -1;
    first.focus();
  }

  function showAttachmentsLine(available, chosen, suggested) {
    $("beilagen-zeile").textContent = R.attachmentsLine(available, chosen, suggested);
  }

  /**
   * Before creating: the form as two tiles and, with the dossier, its line. Once the chosen form is `built`, both
   * collapse into one closing line until «Form ändern». Once sent, the form cannot change.
   */
  function showForm(entry, built) {
    shownEntry = entry;
    shownBuilt = built;
    const sent = Boolean(entry.versand);
    const collapsed = built && !formOpen && !sent;
    const dossier = W.gewaehlt(entry) === "dossier";
    $("unterlagen-wahl").hidden = sent || collapsed;
    $("dossier-kurz").hidden = !dossier || sent || collapsed;
    $("dossier-kurz-design").textContent = R.designLine(entry);
    $("form-zeile").hidden = !collapsed;
    $("form-zeile-text").textContent = R.formLine(entry);
    $("form-dossier").hidden = !dossier;
  }

  /** After creating anew the form collapses again. */
  function closeForm() {
    formOpen = false;
  }

  $("form-aendern").addEventListener("click", () => {
    formOpen = true;
    if (shownEntry) showForm(shownEntry, shownBuilt);
    const chosen = $("unterlagen-wahl").querySelector("input:checked");
    if (chosen) chosen.focus();
  });

  window.UnterlagenSchritt = { showTiles, showFindings, focusFirstFinding, showAttachmentsLine, showForm, closeForm };
})();
