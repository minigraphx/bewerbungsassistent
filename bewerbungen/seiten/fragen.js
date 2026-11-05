"use strict";
// Page „Fragen“ (MIN-376). The conversation lives only here; the answers are shown as text.
(() => {
  const { holen, senden, el, status } = window.App;
  const $ = id => document.getElementById(id);
  const ZUEGE_MIT = 12;  // the server takes no more of them; the page keeps the whole conversation
  const texte = {
    hilfe: "Fragen Sie hier zur Stellensuche und zu Ihrer Bewerbung. Die KI kennt Ihre Angaben, nicht Ihre Liste der Bewerbungen, und sie ändert nichts. Das Gespräch bleibt nur auf dieser Seite. Prüfen Sie wichtige Antworten, auch eine KI irrt sich.",
    label: "Ihre Frage",
    aus: "Für Fragen braucht es die KI der App: unter „Einrichtung“ der Einladungscode oder unter „Erweiterte Einstellungen“ ein eigener Schlüssel. Wer Claude mit dem eigenen Abo nutzt, fragt direkt dort.",
    du: "Sie",
    uebrig: n => `Heute noch ${n === 1 ? "1 Frage" : `${n} Fragen`}.`,
    leer: "Bitte zuerst die Frage schreiben.",
    beispiele: ["Was fehlt noch in meinen Angaben?", "Wie bereite ich mich auf ein Vorstellungsgespräch vor?", "Wie gehe ich im Anschreiben mit einer Lücke um?"],
  };
  let verlauf = [];
  let wartet = false;

  function zeigeZug(zug) {
    const wer = zug.rolle === "person" ? texte.du : "KI";
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
    if (!text) { status($("fragen-meldung"), texte.leer, "hinweis"); return; }
    wartet = true;
    $("fragen-senden").disabled = true;
    status($("fragen-meldung"), "Die KI antwortet …", "");
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
    $("fragen-hilfe").textContent = stand.erlaubt ? texte.hilfe : "";
    $("fragen-label").textContent = texte.label;
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
  holen("/api/fragen/stand").then(zeige, fehler => status($("fragen-meldung"), fehler.message, "fehler"));
})();
