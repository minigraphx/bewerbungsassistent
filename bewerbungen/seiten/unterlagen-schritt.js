"use strict";
// The DOM of the step «Unterlagen erstellen und prüfen» (#321, option A in docs/design/unterlagen-erstellen.md):
// «Dossier gestalten» and «Beilagen ändern» open in place, each built document is a tile with page 1 as a thumbnail
// and a link to where it is adapted, and the findings come with the passed checks collapsed. What to show comes from
// unterlagen-ergebnis.js; bewerbung.js decides when.
(() => {
  const { el, url } = window.App;
  const R = window.UnterlagenErgebnis;
  const W = window.UnterlagenWahl;
  const $ = id => document.getElementById(id);
  const THUMB = { width: "96", height: "136" };  // A4 upright; CSS sets the size, these keep the space while loading
  const ANCHOR = { variant: "#s-lebenslauf", letter: "#s-anschreiben", dossier: "#dossier-kurz" };

  function disclosure(buttonId) {
    const button = $(buttonId);
    const panel = $(button.getAttribute("aria-controls"));
    const set = open => {
      button.setAttribute("aria-expanded", String(open));
      panel.hidden = !open;
    };
    button.addEventListener("click", () => set(button.getAttribute("aria-expanded") !== "true"));
    return { open: () => set(true), close: () => set(false) };
  }

  const dossierPanel = disclosure("dossier-gestalten");
  disclosure("beilagen-aendern");

  function goTo(section, target) {
    $(section).scrollIntoView({ behavior: "smooth", block: "start" });
    target.focus({ preventScroll: true });
  }

  const ADAPT = {
    variant: () => goTo("s-lebenslauf", $("f-variante")),
    letter: () => goTo("s-anschreiben", $("anschreiben-titel")),
    dossier: () => {
      dossierPanel.open();
      goTo("dossier-kurz", $("d-design"));
    },
  };

  function adaptLink(adapt) {
    if (!adapt) return null;
    const attributes = { class: "btn btn--quiet doc-tile__link", href: adapt.href || ANCHOR[adapt.target] };
    if (!adapt.href) {
      attributes.onclick = event => {
        event.preventDefault();
        ADAPT[adapt.target]();
      };
    }
    return el("a", attributes, adapt.text);
  }

  /** One tile per built document; `stand` makes the browser load a rebuilt file anew. */
  function showTiles(entryId, daten, stand) {
    const entry = daten.bewerbung;
    const tiles = R.tiles(daten.pdfs, W.gewaehlt(entry), { ownCv: Boolean(daten.eigener_lebenslauf), sent: Boolean(entry.versand) });
    $("pdfs").replaceChildren(...tiles.map(tile => el("article", { class: "doc-tile" },
      el("img", { class: "doc-tile__thumb", src: url("/api/pdf/miniatur", { id: entryId, art: tile.art, stand }), alt: tile.alt, ...THUMB }),
      el("div", { class: "doc-tile__body" },
        el("h3", { class: "doc-tile__name" }, tile.name),
        el("div", { class: "doc-tile__links" },
          el("a", { class: "btn btn--sm doc-tile__link", href: url("/api/pdf", { id: entryId, art: tile.art, stand }), target: "_blank", rel: "noopener" }, tile.open),
          adaptLink(tile.adapt))))));
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

  /** The dossier line shows while the dossier is chosen and not sent; otherwise its panel closes too. */
  function showDossierLine(entry) {
    const shown = W.gewaehlt(entry) === "dossier" && !entry.versand;
    $("dossier-kurz").hidden = !shown;
    $("dossier-kurz-design").textContent = R.designLine(entry);
    if (!shown) dossierPanel.close();
  }

  window.UnterlagenSchritt = { showTiles, showFindings, focusFirstFinding, showAttachmentsLine, showDossierLine };
})();
