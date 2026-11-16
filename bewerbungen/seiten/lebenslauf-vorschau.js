"use strict";
// The live preview in „Lebenslauf erstellen“ (G76, #294). lebenslauf-erstellen.js sends every change of the choice
// as the event `lebenslauf-entwurf`; this script waits for a pause, lets the app build the CV into a temporary file
// (cv_preview.py, nothing is saved, nothing goes to the AI) and shows page 1 with the page count. A newer request
// wins, a failed build replaces the preview with its message, and the focus stays where the person works.
// Words and announcements: lebenslauf-vorschau-logik.js.
(() => {
  const { senden, url, el } = window.App;
  const Logic = window.LebenslaufVorschauLogik;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const ROUTE = "/api/lebenslauf/erstellen/vorschau";
  let timer = null;
  let asked = 0; // the latest request; an answer to an older one is dropped
  let shown = null; // {pages} or {failed}: what the live region compares against
  let current = null; // {key, pages} of the preview on the page

  const busy = on => $("cv-vorschau").setAttribute("aria-busy", String(on));
  const pageUrl = (page, size) => url(`${ROUTE}/seite`, { id: ID, schluessel: current.key, seite: page,
                                                          ...(size ? { groesse: size } : {}) });

  function announce(next) {
    const said = Logic.announcement(shown, next);
    shown = next;
    if (said) $("cv-vorschau-status").textContent = said;
  }

  function show(answer) {
    current = { key: answer.schluessel, pages: answer.seiten };
    const image = $("cv-vorschau-bild");
    image.src = pageUrl(1);
    image.alt = Logic.pageAlt(1, current.pages);
    image.hidden = false;
    $("cv-vorschau-titel").textContent = Logic.title(current.pages);
    $("cv-vorschau-fehler").hidden = true;
    $("cv-vorschau-fehler").textContent = "";
    $("cv-vorschau-pdf").href = url(`${ROUTE}/pdf`, { id: ID, schluessel: current.key });
    $("cv-vorschau-links").hidden = false;
    if ($("cv-vorschau-dialog").open) fillLarge();
    announce({ pages: current.pages });
  }

  function fail(reason) {
    current = null;
    const image = $("cv-vorschau-bild");
    image.hidden = true;
    image.removeAttribute("src");
    image.alt = "";
    const text = Logic.failedText(reason);
    $("cv-vorschau-titel").textContent = Logic.title(null);
    $("cv-vorschau-fehler").textContent = text;
    $("cv-vorschau-fehler").hidden = false;
    $("cv-vorschau-links").hidden = true;
    announce({ failed: text });
  }

  async function refresh(body) {
    asked += 1;
    const mine = asked;
    busy(true);
    try {
      const answer = await senden(ROUTE, body);
      if (mine === asked) show(answer);
    } catch (error) {
      if (mine === asked) fail(error.message);
    } finally {
      if (mine === asked) busy(false);
    }
  }

  function stop() {
    asked += 1; // an answer still under way belongs to a closed panel
    shown = null;
    $("cv-vorschau-status").textContent = ""; // nothing stale for a screen reader that reads the page later
    busy(false);
  }

  /** detail: {body, now} to build, {body: null, reason} when the choice cannot be sent, {closed} when it closes. */
  function onDraft({ detail = {} }) {
    clearTimeout(timer);
    timer = null;
    if (detail.closed) return stop();
    if (!detail.body) {
      asked += 1;
      busy(false);
      return fail(detail.reason);
    }
    if (detail.now) return refresh(detail.body);
    busy(true); // the preview on the page is about to change
    timer = setTimeout(() => { timer = null; refresh(detail.body); }, Logic.DELAY_MS);
    return null;
  }

  function fillLarge() {
    const { pages } = current;
    $("cv-vorschau-dialog-titel").textContent = Logic.title(pages);
    $("cv-vorschau-dialog-pdf").href = $("cv-vorschau-pdf").href;
    $("cv-vorschau-seiten").replaceChildren(...Array.from({ length: pages }, (_, i) => el("img", {
      class: "cv-preview-dialog__page", src: pageUrl(i + 1, "gross"), alt: Logic.pageAlt(i + 1, pages),
      width: "1190", height: "1683", loading: "lazy" })));
  }

  function openLarge() {
    if (!current) return;
    fillLarge();
    $("cv-vorschau-dialog").showModal();
    $("cv-vorschau-schliessen").focus();
  }

  $("cv-vorschau-bild").addEventListener("error", () => {
    if (current) fail(Logic.NOT_SHOWN);
  });
  $("cv-vorschau-gross").addEventListener("click", openLarge);
  $("cv-vorschau-schliessen").addEventListener("click", () => $("cv-vorschau-dialog").close());
  // Esc closes the dialog too; either way the focus goes back to «Gross ansehen».
  $("cv-vorschau-dialog").addEventListener("close", () => $("cv-vorschau-gross").focus());
  document.addEventListener("lebenslauf-entwurf", onDraft);
  document.addEventListener("bewerbung-geladen", event => {
    $("cv-vorschau-dossier").hidden = event.detail.bewerbung.unterlagen !== "dossier";
  });
})();
