"use strict";
// Page „Fragen“ (MIN-376). The conversation lives only here; the answers are shown as text. Texts come in the app
// language (#430), each read when used; the answer of the AI and refusals of the server stay as they come.
(() => {
  const { holen, senden, el, status } = window.App;
  const $ = id => document.getElementById(id);
  const ZUEGE_MIT = 12;  // the server takes no more of them; the page keeps the whole conversation
  const texte = {
    get aus() {
      return window.Texte.t("Für Fragen braucht es die KI der App: unter „Einstellungen“, „Zugang zur KI“ der Einladungscode oder ein eigener Schlüssel. Wer Claude mit dem eigenen Abo nutzt, fragt direkt dort.");
    },
    uebrig: n => (n === 1 ? window.Texte.t("Heute noch 1 Frage.") : window.Texte.t("Heute noch {anzahl} Fragen.", { anzahl: n })),
    get leer() { return window.Texte.t("Bitte zuerst die Frage schreiben."); },
    // An example goes to the AI as the person's question, in the language the page shows it
    get beispiele() {
      return [window.Texte.t("Was fehlt noch in meinen Angaben?"), window.Texte.t("Wie bereite ich mich auf ein Vorstellungsgespräch vor?"),
              window.Texte.t("Wie gehe ich im Anschreiben mit einer Lücke um?")];
    },
  };
  let satz = "stelle-sie";
  let verlauf = [];
  let wartet = false;

  function zeigeZug(zug) {
    const wer = zug.rolle === "person" ? window.Texte.text("fragen.sprecher", satz) : window.Texte.t("KI");
    $("fragen-verlauf").append(el("div", { class: `chat-zug chat-${zug.rolle}` }, el("strong", {}, wer), el("p", {}, zug.text)));
    $("fragen-verlauf").lastElementChild.scrollIntoView({ block: "nearest" });
  }

  function zeigeUebrig(uebrig) {
    $("fragen-uebrig").textContent = texte.uebrig(uebrig);
    $("fragen-senden").disabled = wartet || uebrig <= 0;
  }

  async function fragen(frage) {
    const text = frage.trim();
    if (wartet) return;
    if (!text) { status($("fragen-meldung"), texte.leer, "hinweis", { input: $("fragen-text") }); return; }
    wartet = true;
    $("fragen-senden").disabled = true;
    status($("fragen-meldung"), window.Texte.t("Die KI antwortet …"), "");
    try {
      const antwort = await senden("/api/fragen/senden", { frage: text, verlauf: verlauf.slice(-ZUEGE_MIT) });
      const neu = [{ rolle: "person", text }, { rolle: "ki", text: antwort.antwort }];
      verlauf = [...verlauf, ...neu];
      neu.forEach(zeigeZug);
      $("fragen-text").value = "";
      $("fragen-beispiele").replaceChildren();
      status($("fragen-meldung"), "", "");
      wartet = false;
      zeigeUebrig(antwort.uebrig);
    } catch (fehler) {
      wartet = false;
      $("fragen-senden").disabled = false;
      status($("fragen-meldung"), fehler.message, "fehler");  // the question stays in the field
      holen("/api/fragen/stand").then(stand => zeigeUebrig(stand.uebrig), () => {});  // an answer that could not be used still counted
    }
  }

  function zeige(stand) {
    const bereit = stand.eingerichtet && stand.erlaubt;
    $("fragen-hilfe").textContent = stand.erlaubt ? window.Texte.text("fragen.hilfe", satz) : "";
    $("fragen-label").textContent = window.Texte.text("fragen.label", satz);
    $("fragen-aus").hidden = bereit;
    $("fragen-aus").textContent = stand.erlaubt ? texte.aus : stand.hinweis;
    $("fragen-an").hidden = !bereit;
    $("fragen-beispiele").replaceChildren(...texte.beispiele.map(beispiel =>
      el("button", { type: "button", class: "chat-beispiel", onclick: () => fragen(beispiel) }, beispiel)));
    zeigeUebrig(stand.uebrig);
  }

  $("fragen-senden").addEventListener("click", () => fragen($("fragen-text").value));
  $("fragen-text").addEventListener("keydown", event => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) fragen($("fragen-text").value);
  });
  window.App.textsatz().then(gewaehlt => { satz = gewaehlt; return holen("/api/fragen/stand"); })
    .then(zeige, fehler => status($("fragen-meldung"), fehler.message, "fehler"));
})();
