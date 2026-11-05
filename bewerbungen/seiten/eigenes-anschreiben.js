"use strict";
// Section „Fertiges Anschreiben“ on the page of an application (MIN-346): a finished PDF, used as it is.
(() => {
  const { senden, el, status, url, bestaetigen, alsBase64 } = window.App;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const BYTES_PER_MB = 1000000;
  const FORM_HOLDS_OLD_FILE = "Ein schon geöffnetes Formular enthält noch die bisherige Datei. Bitte dort anpassen: Als versendet gilt, was hier steht.";
  let maxBytes = 0;
  let shown = null;

  const message = (text, type = "") => status($("anschreiben-status"), text, type);
  // Not a full reload: the person may be typing in the fields above.
  const announceChange = () => document.dispatchEvent(new CustomEvent("eigenes-anschreiben-geaendert"));

  function report(text, formOpen) {
    if (formOpen) message(`${text} ${FORM_HOLDS_OLD_FILE}`, "hinweis");
    else message(text, "ok");
  }

  function fileRow() {
    const remove = el("button", { type: "button" }, "Entfernen");
    bestaetigen(remove, "Wirklich entfernen?", async () => {
      try {
        const { formular_offen: formOpen } = await senden("/api/dateien/anschreiben/entfernen", { id: ID });
        report("Entfernt. Ein Entwurf gilt wieder, falls es einen gibt.", formOpen);
        announceChange();
      } catch (error) {
        message(error.message, "fehler");
      }
    });
    return el("li", {},
      el("a", { href: url("/api/pdf", { id: ID, art: "anschreiben" }), target: "_blank", rel: "noopener" }, "Hochgeladenes Anschreiben"),
      remove);
  }

  // The page looks again every few seconds. The row stays unless something changed: „Entfernen“ may be waiting for its second click.
  function show(data) {
    const sent = !!data.bewerbung.versand;
    const own = !!data.eigenes_anschreiben;
    maxBytes = data.max_datei;
    $("eigenes-anschreiben").hidden = sent;
    $("eigener-brief").hidden = !own;
    if (own === shown) return;
    shown = own;
    $("anschreiben-liste").replaceChildren(own ? fileRow() : el("li", { class: "leer" }, "Noch nichts hochgeladen."));
  }

  async function upload(file) {
    if (file.size > maxBytes) throw new Error(`${file.name} ist zu gross, höchstens ${maxBytes / BYTES_PER_MB} MB.`);
    return senden("/api/dateien/anschreiben", { id: ID, name: file.name, daten: await alsBase64(file) });
  }

  document.addEventListener("bewerbung-geladen", event => show(event.detail));
  $("anschreiben-datei").addEventListener("change", async event => {
    const [file] = event.target.files;
    event.target.value = "";
    if (!file) return;
    message(`${file.name} wird hochgeladen …`);
    try {
      const { formular_offen: formOpen } = await upload(file);
      report("Hochgeladen. Für diese Bewerbung gilt jetzt diese Datei.", formOpen);
      announceChange();
    } catch (error) {
      message(error.message, "fehler");
    }
  });
})();
