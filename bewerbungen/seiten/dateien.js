"use strict";
// Page „Meine Dateien“ (MIN-346): upload finished documents and use them as they are.
(() => {
  const { holen, senden, el, status, url, bestaetigen, alsBase64 } = App;
  const BYTES_PER_MB = 1000000;
  const BYTES_PER_KB = 1000;
  let maxBytes = 0;

  const section = kind => document.querySelector(`.eigene-dateien[data-art="${kind}"]`);
  const sections = () => [...document.querySelectorAll(".eigene-dateien")];
  const message = (kind, text, type = "") => status(section(kind).querySelector(".status"), text, type);

  function sizeText(bytes) {
    if (bytes >= BYTES_PER_MB) return `${(bytes / BYTES_PER_MB).toFixed(1)} MB`;
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

  let withVariant = 0;  // applications that chose a variant: there the variant counts (MIN-369)

  /** Which CV counts: a chosen variant, else the own PDF, else the one built from „Meine Angaben“. */
  function showRank(found) {
    const own = found.lebenslauf.length > 0;
    document.getElementById("rang-variante").textContent = withVariant === 1 ? "1 Bewerbung hat eine Variante" : `${withVariant} Bewerbungen haben eine Variante`;
    document.getElementById("rang-eigen").textContent = own ? `Wird verwendet: ${found.lebenslauf[0].name}` : "Noch kein PDF hochgeladen";
    document.getElementById("rang-gebaut").textContent = own ? "Wird nicht verwendet, solange ein PDF da ist" : "Wird verwendet";
    document.querySelector('[data-rang="eigen"]').toggleAttribute("data-aktiv", own);
    document.querySelector('[data-rang="gebaut"]').toggleAttribute("data-aktiv", !own);
    const adjust = LebenslaufAnpassen.ziel({ eigenesPdf: own });  // #119; a variant belongs to one application
    document.getElementById("cv-wie-es-ist").hidden = !adjust.wieEsIst;
    document.getElementById("cv-anpassen").hidden = !adjust.href;
    if (adjust.href) document.getElementById("cv-anpassen").href = adjust.href;
  }

  function show(found) {
    for (const part of sections()) {
      const kind = part.dataset.art;
      const rows = found[kind].map(file => fileRow(kind, file));
      part.querySelector(".datei-liste").replaceChildren(...(rows.length ? rows : [el("li", { class: "leer" }, "Noch nichts hochgeladen.")]));
    }
    showRank(found);
  }

  async function uploadOne(kind, file) {
    if (file.size > maxBytes) throw new Error(`${file.name} ist zu gross, höchstens ${maxBytes / BYTES_PER_MB} MB.`);
    return senden("/api/dateien/hochladen", { art: kind, name: file.name, daten: await alsBase64(file) });
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
    withVariant = await holen("/api/bewerbungen").then(d => d.bewerbungen.filter(b => b.variante && !b.versand).length, () => 0);
    const found = await holen("/api/dateien");
    maxBytes = found.max_groesse;
    show(found);
  }

  start().catch(error => message("lebenslauf", error.message, "fehler"));
})();
