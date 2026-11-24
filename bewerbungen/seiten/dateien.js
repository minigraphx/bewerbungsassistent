"use strict";
// Page „Lebenslauf und Dateien“ (#264, A9, G55): the choice between the CV of the app and an own PDF, certificates
// and references in one list, the photos (G21) with „Im Lebenslauf zeigen“ (G62), the design of the CV (G61,
// „Aussehen wählen“) and the way to earlier versions. What it shows: dateien-logik.js. Texts come in the app language
// (#430); file names and what the server says stay as they come.
(() => {
  const { holen, senden, el, status, url, bestaetigen, alsBase64 } = App;
  const MB = 1000000;
  const Logic = window.DateienLogik;
  const $ = id => document.getElementById(id);
  let maxBytes = 0;
  let maxPhotoBytes = 0;
  let found = { lebenslauf: [], zeugnis: [], diplom: [], zertifikat: [] };
  let wantsOwn = false;
  let design = Logic.PRESET_DESIGN;

  const cvMessage = (text, type = "") => status($("cv-status"), text, type);
  const proofMessage = (text, type = "") => status($("nachweise-status"), text, type);
  const photoMessage = (text, type = "") => status($("fotos-status"), text, type);

  function fileLink(file) {
    return el("a", { href: url("/api/dateien/ansehen", { datei: file.datei }), target: "_blank", rel: "noopener" }, file.name);
  }

  function removeButton(file, done) {
    const remove = el("button", { type: "button", class: "btn btn--quiet btn--sm" }, window.Texte.t("Entfernen"));
    bestaetigen(remove, window.Texte.t("Wirklich entfernen?"), async () => {
      try {
        showFiles(await senden("/api/dateien/entfernen", { datei: file.datei }));
        done(window.Texte.t("{datei} entfernt.", { datei: file.name }), "ok");
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
    $("cv-waehlen").firstChild.textContent = own ? window.Texte.t("Anderes PDF wählen") : window.Texte.t("PDF wählen");
    const row = own ? el("li", {}, fileLink(own), el("span", { class: "leise" }, Logic.sizeText(own.groesse)),
                         removeButton(own, cvMessage))
      : el("li", { class: "leer" }, window.Texte.t("Noch kein PDF. Bis eines da ist, erstellt die App den Lebenslauf."));
    $("cv-datei").replaceChildren(row);
  }

  function kindSelect(file) {
    const select = el("select", { class: "input files__kind", "aria-label": window.Texte.t("Art von {datei}", { datei: file.name }) },
      Logic.KINDS.map(kind => el("option", { value: kind, selected: kind === file.art }, Logic.KIND_LABELS[kind])));
    select.addEventListener("change", async () => {
      try {
        showFiles(await senden("/api/dateien/art", { datei: file.datei, art: select.value }));
        proofMessage(window.Texte.t("{datei} ist jetzt als {art} eingeordnet.",
                                    { datei: file.name, art: Logic.KIND_LABELS[select.value] }), "ok");
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
    $("nachweise").replaceChildren(...(rows.length ? rows : [el("li", { class: "leer" }, window.Texte.t("Noch nichts hochgeladen."))]));
  }

  function showFiles(listing) {
    found = listing;
    showCv();
    showProofs();
  }

  async function uploadOne(kind, file) {
    if (file.size > maxBytes) {
      throw new Error(window.Texte.t("{datei} ist zu gross, höchstens {mb} MB.", { datei: file.name, mb: maxBytes / MB }));
    }
    return senden("/api/dateien/hochladen", { art: kind, name: file.name, daten: await alsBase64(file) });
  }

  // One after the other: a refused file says why and does not stop the others.
  async function upload(files, kindOf, message) {
    const problems = [];
    let done = 0;
    for (const file of files) {
      message(window.Texte.t("{datei} wird hochgeladen …", { datei: file.name }));
      try {
        showFiles(await uploadOne(kindOf(file), file));
        done += 1;
      } catch (error) {
        problems.push(window.Texte.t("{datei}: {fehler}", { datei: file.name, fehler: error.message }));
      }
    }
    if (problems.length) message(problems.join(" "), "fehler");
    else message(done === 1 ? window.Texte.t("Hochgeladen.") : window.Texte.t("{anzahl} Dateien hochgeladen.", { anzahl: done }), "ok");
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
      cvMessage(window.Texte.t("Die App erstellt den Lebenslauf wieder."), "ok");
    } catch (error) {
      cvMessage(error.message, "fehler");
    }
  }

  function photoButton(photo) {
    const picture = el("img", { src: url("/api/foto/bild", { datei: photo.datei }), alt: "" });
    const button = el("button", { type: "button", class: "files__photo", "aria-pressed": String(photo.aktiv),
                                  "aria-label": photo.aktiv ? window.Texte.t("Aktives Foto") : window.Texte.t("Dieses Foto verwenden") },
                        picture);
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
      photoMessage(shown ? window.Texte.t("Neue Unterlagen zeigen das Foto. Was schon erstellt ist, bleibt, wie es ist.")
        : window.Texte.t("Neue Unterlagen entstehen ohne Foto. Was schon erstellt ist, bleibt, wie es ist."), "ok");
    } catch (error) {
      photoMessage(window.Texte.t("Foto im Lebenslauf nicht geändert: {fehler}", { fehler: error.message }), "fehler");
      $("foto-zeigen").checked = !shown;
    }
  }

  async function usePhoto(file) {
    try {
      await senden("/api/foto/aktiv", { datei: file });
      await loadPhotos();
      photoMessage(window.Texte.t("Neue Unterlagen nutzen jetzt dieses Foto. Was schon erstellt ist, behält seines."), "ok");
    } catch (error) {
      photoMessage(error.message, "fehler");
    }
  }

  async function addPhoto(file) {
    try {
      if (file.size > maxPhotoBytes) {
        throw new Error(window.Texte.t("Das Foto ist zu gross, höchstens {mb} MB.", { mb: maxPhotoBytes / MB }));
      }
      photoMessage(window.Texte.t("{datei} wird hochgeladen …", { datei: file.name }));
      await senden("/api/foto/hochladen", { name: file.name, daten: await alsBase64(file) });
      await loadPhotos();
      photoMessage(window.Texte.t("Hochgeladen. Es ist jetzt das aktive Foto."), "ok");
    } catch (error) {
      photoMessage(error.message, "fehler");
    }
  }

  function showDesign() {
    $("cv-design").textContent = window.Texte.t("Design: {name}", { name: Logic.designName(design) });
  }

  function designTile(choice) {
    const radio = el("input", { type: "radio", name: "aussehen", value: choice.id, checked: choice.id === design });
    return el("label", { class: "design-tile" },
      el("span", { class: `design-tile__sheet design-tile__sheet--${choice.id}`, "aria-hidden": "true" }),
      el("span", { class: "design-tile__name" }, radio, choice.name),
      el("span", { class: "design-tile__text" }, choice.text));
  }

  function openDesigns() {
    $("aussehen-liste").replaceChildren(...Logic.DESIGNS.map(designTile));
    $("aussehen-dialog").showModal();
    $("aussehen-liste").querySelector("input:checked")?.focus();
  }

  async function chooseDesign() {
    const chosen = $("aussehen-liste").querySelector("input:checked")?.value;
    try {
      const body = Logic.designToSave(design, chosen);
      $("aussehen-dialog").close();
      if (!body) return;
      design = (await senden("/api/dateien/aussehen", body)).design;
      showDesign();
      cvMessage(Logic.designSaved(design), "ok");
    } catch (error) {
      $("aussehen-dialog").close();
      cvMessage(window.Texte.t("Aussehen nicht gespeichert: {fehler}", { fehler: error.message }), "fehler");
    }
  }

  async function loadDesign() {
    design = (await holen("/api/dateien/aussehen")).design;
    showDesign();
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
    $("cv-aussehen").addEventListener("click", openDesigns);
    $("aussehen-nein").addEventListener("click", () => $("aussehen-dialog").close());
    $("aussehen-ja").addEventListener("click", chooseDesign);
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
    await loadDesign().catch(error => cvMessage(window.Texte.t("Aussehen nicht geladen: {fehler}", { fehler: error.message }), "fehler"));
    await loadPhotos().catch(error => photoMessage(error.message, "fehler"));
  }

  start().catch(error => cvMessage(error.message, "fehler"));
})();
