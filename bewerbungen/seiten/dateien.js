"use strict";
// Page „Lebenslauf und Dateien“ (#264, A9, G55): the choice between the CV of the app and an own PDF, certificates
// and references in one list, the photos (G21) with „Im Lebenslauf zeigen“ (G62) and the way to earlier versions.
// What it shows: dateien-logik.js.
(() => {
  const { holen, senden, el, status, url, bestaetigen, alsBase64 } = App;
  const Logic = window.DateienLogik;
  const $ = id => document.getElementById(id);
  let maxBytes = 0;
  let maxPhotoBytes = 0;
  let found = { lebenslauf: [], zertifikat: [], zeugnis: [] };
  let wantsOwn = false;

  const cvMessage = (text, type = "") => status($("cv-status"), text, type);
  const proofMessage = (text, type = "") => status($("nachweise-status"), text, type);
  const photoMessage = (text, type = "") => status($("fotos-status"), text, type);

  function fileLink(file) {
    return el("a", { href: url("/api/dateien/ansehen", { datei: file.datei }), target: "_blank", rel: "noopener" }, file.name);
  }

  function removeButton(file, done) {
    const remove = el("button", { type: "button", class: "btn btn--quiet btn--sm" }, "Entfernen");
    bestaetigen(remove, "Wirklich entfernen?", async () => {
      try {
        showFiles(await senden("/api/dateien/entfernen", { datei: file.datei }));
        done(`${file.name} entfernt.`, "ok");
      } catch (error) {
        done(error.message, "fehler");
      }
    });
    return remove;
  }

  function showCv() {
    const own = found.lebenslauf[0] || null;
    const chosen = Logic.cvChoice({ ownPdf: Boolean(own), wantsOwn });
    for (const card of document.querySelectorAll("[data-cv]")) card.setAttribute("aria-pressed", String(card.dataset.cv === chosen));
    $("cv-app").hidden = chosen !== "app";
    $("cv-eigen").hidden = chosen !== "eigen";
    $("cv-wie-es-ist").hidden = !own;
    $("cv-waehlen").firstChild.textContent = own ? "Anderes PDF wählen" : "PDF wählen";
    const row = own ? el("li", {}, fileLink(own), el("span", { class: "leise" }, Logic.sizeText(own.groesse)),
                         removeButton(own, cvMessage))
      : el("li", { class: "leer" }, "Noch kein PDF. Bis eines da ist, erstellt die App den Lebenslauf.");
    $("cv-datei").replaceChildren(row);
  }

  function kindSelect(file) {
    const select = el("select", { class: "input files__kind", "aria-label": `Art von ${file.name}` },
      Logic.KINDS.map(kind => el("option", { value: kind, selected: kind === file.art }, Logic.KIND_LABELS[kind])));
    select.addEventListener("change", async () => {
      try {
        showFiles(await senden("/api/dateien/art", { datei: file.datei, art: select.value }));
        proofMessage(`${file.name} ist jetzt als ${Logic.KIND_LABELS[select.value]} eingeordnet.`, "ok");
      } catch (error) {
        select.value = file.art;
        proofMessage(error.message, "fehler");
      }
    });
    return select;
  }

  function showProofs() {
    const rows = Logic.oneList(found).map(file => el("li", {},
      el("span", { class: "files__name" }, fileLink(file), el("span", { class: "leise" }, Logic.sizeText(file.groesse))),
      el("span", { class: "files__actions" }, kindSelect(file), removeButton(file, proofMessage))));
    $("nachweise").replaceChildren(...(rows.length ? rows : [el("li", { class: "leer" }, "Noch nichts hochgeladen.")]));
  }

  function showFiles(listing) {
    found = listing;
    showCv();
    showProofs();
  }

  async function uploadOne(kind, file) {
    if (file.size > maxBytes) throw new Error(`${file.name} ist zu gross, höchstens ${maxBytes / 1000000} MB.`);
    return senden("/api/dateien/hochladen", { art: kind, name: file.name, daten: await alsBase64(file) });
  }

  // One after the other: a refused file says why and does not stop the others.
  async function upload(files, kindOf, message) {
    const problems = [];
    let done = 0;
    for (const file of files) {
      message(`${file.name} wird hochgeladen …`);
      try {
        showFiles(await uploadOne(kindOf(file), file));
        done += 1;
      } catch (error) {
        problems.push(`${file.name}: ${error.message}`);
      }
    }
    if (problems.length) message(problems.join(" "), "fehler");
    else message(done === 1 ? "Hochgeladen." : `${done} Dateien hochgeladen.`, "ok");
  }

  const uploadProofs = files => upload(files, file => Logic.guessKind(file.name), proofMessage);

  function chooseCv(chosen) {
    if (Logic.needsRemoval({ ownPdf: found.lebenslauf.length > 0, chosen })) {
      $("cv-dialog").showModal();
      return;
    }
    wantsOwn = chosen === "eigen";
    showCv();
  }

  async function removeOwnCv() {
    $("cv-dialog").close();
    try {
      wantsOwn = false;
      showFiles(await senden("/api/dateien/entfernen", { datei: found.lebenslauf[0].datei }));
      cvMessage("Die App erstellt den Lebenslauf wieder.", "ok");
    } catch (error) {
      cvMessage(error.message, "fehler");
    }
  }

  function photoButton(photo) {
    const picture = el("img", { src: url("/api/foto/bild", { datei: photo.datei }), alt: "" });
    const button = el("button", { type: "button", class: "files__photo", "aria-pressed": String(photo.aktiv),
                                  "aria-label": photo.aktiv ? "Aktives Foto" : "Dieses Foto verwenden" }, picture);
    if (!photo.aktiv) button.addEventListener("click", () => usePhoto(photo.datei));
    return el("li", {}, button);
  }

  function showPhotos(photos, shown) {
    const toggle = Logic.photoSwitch(photos, shown);
    $("fotos").replaceChildren(...photos.map(photoButton));
    $("fotos-text").textContent = Logic.photoSummary(photos, toggle.checked);
    $("foto-ausschnitt").hidden = !photos.length;
    $("foto-zeigen-zeile").hidden = !toggle.visible;
    $("foto-zeigen").checked = toggle.checked;
  }

  async function loadPhotos() {
    const listing = await holen("/api/foto/liste");
    maxPhotoBytes = listing.max_groesse;
    showPhotos(listing.fotos, listing.zeigen);
  }

  // Only new documents follow the switch (G62); what is built or sent keeps its photo.
  async function showInCv() {
    const shown = $("foto-zeigen").checked;
    try {
      await senden("/api/foto/zeigen", { zeigen: shown });
      await loadPhotos();
      photoMessage(shown ? "Neue Unterlagen zeigen das Foto. Was schon erstellt ist, bleibt, wie es ist."
        : "Neue Unterlagen entstehen ohne Foto. Was schon erstellt ist, bleibt, wie es ist.", "ok");
    } catch (error) {
      photoMessage(`Foto im Lebenslauf nicht geändert: ${error.message}`, "fehler");
      $("foto-zeigen").checked = !shown;
    }
  }

  async function usePhoto(file) {
    try {
      await senden("/api/foto/aktiv", { datei: file });
      await loadPhotos();
      photoMessage("Neue Unterlagen nutzen jetzt dieses Foto. Was schon erstellt ist, behält seines.", "ok");
    } catch (error) {
      photoMessage(error.message, "fehler");
    }
  }

  async function addPhoto(file) {
    try {
      if (file.size > maxPhotoBytes) throw new Error(`Das Foto ist zu gross, höchstens ${maxPhotoBytes / 1000000} MB.`);
      photoMessage(`${file.name} wird hochgeladen …`);
      await senden("/api/foto/hochladen", { name: file.name, daten: await alsBase64(file) });
      await loadPhotos();
      photoMessage("Hochgeladen. Es ist jetzt das aktive Foto.", "ok");
    } catch (error) {
      photoMessage(error.message, "fehler");
    }
  }

  function onFiles(input, handle) {
    input.addEventListener("change", async () => {
      const files = [...input.files];
      input.value = "";
      await handle(files);
    });
  }

  function dropZone(zone) {
    zone.addEventListener("dragover", event => { event.preventDefault(); zone.dataset.ueber = ""; });
    zone.addEventListener("dragleave", () => delete zone.dataset.ueber);
    zone.addEventListener("drop", async event => {
      event.preventDefault();
      delete zone.dataset.ueber;
      await uploadProofs([...event.dataTransfer.files]);
    });
  }

  function wire() {
    for (const card of document.querySelectorAll("[data-cv]")) card.addEventListener("click", () => chooseCv(card.dataset.cv));
    $("cv-dialog-nein").addEventListener("click", () => $("cv-dialog").close());
    $("cv-dialog-ja").addEventListener("click", removeOwnCv);
    onFiles($("cv-input"), files => upload(files, () => "lebenslauf", cvMessage));
    onFiles($("nachweise-input"), uploadProofs);
    onFiles($("foto-input"), files => (files[0] ? addPhoto(files[0]) : null));
    $("foto-zeigen").addEventListener("change", showInCv);
    dropZone($("ablage-zone"));
  }

  async function start() {
    wire();
    const withVariant = await holen("/api/bewerbungen")
      .then(d => d.bewerbungen.filter(b => b.variante && !b.versand).length, () => 0);
    const note = Logic.variantNote(withVariant);
    $("cv-varianten").textContent = note;
    $("cv-varianten").hidden = !note;
    const listing = await holen("/api/dateien");
    maxBytes = listing.max_groesse;
    showFiles(listing);
    await loadPhotos().catch(error => photoMessage(error.message, "fehler"));
  }

  start().catch(error => cvMessage(error.message, "fehler"));
})();
