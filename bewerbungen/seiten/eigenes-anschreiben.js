"use strict";
// Section „Eigenes Anschreiben“ on the page of an application (MIN-346): a finished PDF, used as it is.
// Texts in the app language through Texte (#427); file names stay as they are.
(() => {
  const { senden, el, status, url, bestaetigen, alsBase64 } = window.App;
  const Texte = window.Texte;
  const $ = id => document.getElementById(id);
  const ID = new URLSearchParams(location.search).get("id");
  const BYTES_PER_MB = 1000000;
  const formHasAnother = () => Texte.t("Ein schon geöffnetes Formular hat noch eine andere Fassung. Wird es neu geladen, bekommt es die aktuelle. Sonst gilt bei „Abgeschickt? Ja“, was es bekommen hat.");
  let maxBytes = 0;
  let shown = null;

  const message = (text, type = "") => status($("anschreiben-status"), text, type);
  // Not a full reload: the person may be typing in the fields above.
  const announceChange = () => document.dispatchEvent(new CustomEvent("eigenes-anschreiben-geaendert"));

  function report(text, { formular_abweichend: formDiffers }) {
    if (formDiffers.length) message(`${text} ${formHasAnother()}`, "hinweis");
    else message(text, "ok");
  }

  function fileRow() {
    const remove = el("button", { type: "button" }, Texte.t("Entfernen"));
    bestaetigen(remove, Texte.t("Wirklich entfernen?"), async () => {
      try {
        const answer = await senden("/api/dateien/anschreiben/entfernen", { id: ID });
        report(Texte.t("Entfernt. Ein Entwurf gilt wieder, falls es einen gibt."), answer);
        announceChange();
      } catch (error) {
        message(error.message, "fehler");
      }
    });
    return el("li", {},
      el("a", { href: url("/api/pdf", { id: ID, art: "anschreiben" }), target: "_blank", rel: "noopener" }, Texte.t("Hochgeladenes Anschreiben")),
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
    $("anschreiben-liste").replaceChildren(own ? fileRow() : el("li", { class: "leer" }, Texte.t("Noch nichts hochgeladen.")));
  }

  async function upload(file) {
    if (file.size > maxBytes) {
      throw new Error(Texte.t("{datei} ist zu gross, höchstens {mb} MB.", { datei: file.name, mb: maxBytes / BYTES_PER_MB }));
    }
    return senden("/api/dateien/anschreiben", { id: ID, name: file.name, daten: await alsBase64(file) });
  }

  document.addEventListener("bewerbung-geladen", event => show(event.detail));
  $("anschreiben-datei").addEventListener("change", async event => {
    const [file] = event.target.files;
    event.target.value = "";
    if (!file) return;
    message(Texte.t("{datei} wird hochgeladen …", { datei: file.name }));
    try {
      const answer = await upload(file);
      report(Texte.t("Hochgeladen. Für diese Bewerbung gilt jetzt diese Datei."), answer);
      announceChange();
    } catch (error) {
      message(error.message, "fehler");
    }
  });
})();
