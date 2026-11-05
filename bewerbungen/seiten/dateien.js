"use strict";
// Page „Meine Dateien“ (MIN-346): upload finished documents and use them as they are.
(() => {
  const { holen, senden, el, status, url, bestaetigen } = App;
  const BYTES_PER_MB = 1000000;
  const BYTES_PER_KB = 1000;
  let maxBytes = 0;

  const section = kind => document.querySelector(`.eigene-dateien[data-art="${kind}"]`);
  const sections = () => [...document.querySelectorAll(".eigene-dateien")];
  const message = (kind, text, type = "") => status(section(kind).querySelector(".status"), text, type);

  function sizeText(bytes) {
    if (bytes >= BYTES_PER_MB) return `${(bytes / BYTES_PER_MB).toFixed(1).replace(".", ",")} MB`;
    return `${Math.max(1, Math.round(bytes / BYTES_PER_KB))} KB`;
  }

  function fileRow(kind, file) {
    const remove = el("button", { type: "button" }, "Entfernen");
    bestaetigen(remove, "Wirklich entfernen?", async () => {
      try {
        show(await senden("/api/dateien/entfernen", { datei: file.datei }));
        message(kind, `${file.name} entfernt.`, "ok");
      } catch (error) {
        message(kind, error.message, "fehler");
      }
    });
    return el("li", {},
      el("a", { href: url("/api/dateien/ansehen", { datei: file.datei }), target: "_blank", rel: "noopener" }, file.name),
      el("span", { class: "leise" }, sizeText(file.groesse)), remove);
  }

  function show(found) {
    for (const part of sections()) {
      const kind = part.dataset.art;
      const rows = found[kind].map(file => fileRow(kind, file));
      part.querySelector(".datei-liste").replaceChildren(...(rows.length ? rows : [el("li", { class: "leer" }, "Noch nichts hochgeladen.")]));
    }
  }

  function asBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(",")[1] || "");
      reader.onerror = () => reject(new Error(`${file.name} liess sich nicht lesen.`));
      reader.readAsDataURL(file);
    });
  }

  async function uploadOne(kind, file) {
    if (file.size > maxBytes) throw new Error(`${file.name} ist zu gross, höchstens ${maxBytes / BYTES_PER_MB} MB.`);
    return senden("/api/dateien/hochladen", { art: kind, name: file.name, daten: await asBase64(file) });
  }

  // One after the other: a refused file says why and does not stop the others.
  async function upload(kind, files) {
    const problems = [];
    let done = 0;
    for (const file of files) {
      message(kind, `${file.name} wird hochgeladen …`);
      try {
        show(await uploadOne(kind, file));
        done += 1;
      } catch (error) {
        problems.push(`${file.name}: ${error.message}`);
      }
    }
    if (problems.length) message(kind, problems.join(" "), "fehler");
    else message(kind, done === 1 ? "Hochgeladen." : `${done} Dateien hochgeladen.`, "ok");
  }

  async function start() {
    for (const part of sections()) {
      const input = part.querySelector("input[type=file]");
      input.addEventListener("change", async () => {
        const files = [...input.files];
        input.value = "";
        await upload(part.dataset.art, files);
      });
    }
    const found = await holen("/api/dateien");
    maxBytes = found.max_groesse;
    show(found);
  }

  start().catch(error => message("lebenslauf", error.message, "fehler"));
})();
