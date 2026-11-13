"use strict";
// The pass over saved jobs (G38, #260): one job after the other with its ad, the person decides. Bewerben and
// Verwerfen change only the stage, Später leaves the job as it is. Used by Heute, reusable by the Bewerbungen page.
(() => {
  const H = window.HeuteLogic;
  const L = window.UebersichtLogik;
  const { holen, senden, el } = window.App;
  const $ = id => document.getElementById(id);
  const DIALOG = "pass-dialog";
  const STAGE = { bewerben: "Bewerben", verworfen: "Verworfen" };

  let queue = [];
  let index = 0;
  let counts = {};
  let onDone = null;

  const address = id => "/bewerbung?id=" + encodeURIComponent(id);
  const status = (content, level = "") => window.Meldungen.zeige($("pass-status"), content, level);

  function setBusy(busy) {
    for (const id of ["pass-bewerben", "pass-verwerfen", "pass-spaeter"]) $(id).disabled = busy;
  }

  function meta(b) {
    const grade = typeof b.passung === "number" ? `Note ${window.Texte.notenText(b.passung)}` : "";
    const deadline = b.frist ? `Frist ${L.datum(b.frist)}` : "";
    return [[b.firma, b.ort].filter(Boolean).join(", "), grade, deadline].filter(Boolean).join(" · ");
  }

  // The fetched ad, or why it is missing and how to get it (G37); the extension loads it at the start of the app.
  function adContent(b, text, missing) {
    const ad = H.passAd(b, text, missing);
    if (ad.text) return [ad.text];
    const link = ad.link ? el("a", { href: ad.link, target: "_blank", rel: "noopener" }, "Inserat öffnen") : null;
    const [first, ...rest] = ad.zeilen;
    return [el("p", {}, first, link ? " " : "", link), ...rest.map(line => el("p", { class: "pass__missing" }, line))];
  }

  async function show() {
    const id = queue[index];
    setBusy(true);
    status("");
    $("pass-fortschritt").textContent = H.passProgress(index, queue.length);
    $("pass-oeffnen").href = address(id);
    try {
      const { bewerbung: b, stellentext, text_fehlt: missing } = await holen("/api/bewerbung", { id });
      $("pass-titel").textContent = b.stelle || "ohne Titel";
      $("pass-firma").textContent = meta(b);
      $("pass-inserat").replaceChildren(...adContent(b, stellentext, missing));
      setBusy(false);
    } catch (error) {
      $("pass-titel").textContent = "Stelle nicht geladen";
      $("pass-firma").textContent = "";
      $("pass-inserat").replaceChildren();
      status(`Laden fehlgeschlagen: ${error.message}`, "danger");
      $("pass-spaeter").disabled = false;  // the person can still move on
    }
  }

  function finish() {
    const done = onDone;
    onDone = null;
    if ($(DIALOG).open) $(DIALOG).close();
    if (done) done({ ...counts });
  }

  function next(kind) {
    counts = { ...counts, [kind]: (counts[kind] || 0) + 1 };
    index += 1;
    if (index < queue.length) show();
    else finish();
  }

  async function decide(kind) {
    const stage = STAGE[kind];
    if (!stage) return next(kind);
    setBusy(true);
    try {
      await senden("/api/bewerbungen/stand", { ids: [queue[index]], status: stage });
      next(kind);
    } catch (error) {
      status(error.message, "danger");
      setBusy(false);
    }
  }

  /** Opens the pass over `ids`; `done` gets { bewerben, verworfen, spaeter } when it ends or is left. */
  function start(ids, done) {
    if (!ids.length) return;
    queue = [...ids];
    index = 0;
    counts = {};
    onDone = done;
    $(DIALOG).showModal();
    show();
  }

  $("pass-bewerben").addEventListener("click", () => decide("bewerben"));
  $("pass-verwerfen").addEventListener("click", () => decide("verworfen"));
  $("pass-spaeter").addEventListener("click", () => decide("spaeter"));
  $("pass-ende").addEventListener("click", finish);
  $(DIALOG).addEventListener("close", finish);  // Escape ends the pass like the button

  window.Pass = { start };
})();
