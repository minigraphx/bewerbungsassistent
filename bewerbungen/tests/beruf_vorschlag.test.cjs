// Suggestions on the page Suche (MIN-375) ask for the AI consent in place (#140): nothing typed leaves before it.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const seite = name => fs.readFileSync(path.join(__dirname, "..", "seiten", name), "utf8");
const OPEN = { erteilt: false, fassung: "1", text: "Ich bin einverstanden …", link: null };

function element() {
  const handlers = {};
  return {
    value: "", hidden: false, disabled: false, textContent: "", open: false, children: [],
    addEventListener(type, handler) { handlers[type] = handler; },
    replaceChildren(...children) { this.children = children; },
    focus() {},
    fire(type, event = {}) { return handlers[type]({ preventDefault() {}, ...event }); },
  };
}

/** The page script in a sandbox: elements by id, a fake App that records what it sends, and a fake consent block. */
function page({ status = { einwilligung: OPEN }, antworten = {}, satz = "lehrstelle-du" } = {}) {
  const elements = new Map();
  const byId = id => {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  };
  const sent = [];
  const consent = [];
  const messages = [];
  const App = {
    el: (tag, attributes, ...children) => Object.assign(element(), { children }),
    status: (target, text, art, optionen = {}) => { target.textContent = text; messages.push({ target, text, art, optionen }); },
    textsatz: async () => satz,
    holen: async pfad => {
      assert.equal(pfad, "/api/ki/status");
      return status;
    },
    senden: async (pfad, body) => {
      sent.push({ pfad, body });
      if (antworten[pfad] instanceof Error) throw antworten[pfad];
      return antworten[pfad] || { vorschlaege: [] };
    },
  };
  const Einwilligung = { zeile: (ort, stand, fertig) => { ort.hidden = false; consent.push({ ort, stand, fertig }); } };
  // The rows and their order are suchliste.js's (tests/suchliste.test.cjs); here only what this page hands it.
  const Suchliste = { zeige(liste, begriffe, optionen) { Object.assign(this, { liste, begriffe, optionen }); } };
  const context = {
    window: { App, Einwilligung, Suchliste, Meldungen: require("../seiten/meldungen.js") },
    document: { getElementById: byId, dispatchEvent() {} },
    CustomEvent: class {},
  };
  vm.runInNewContext(seite("beruf-vorschlag.js"), context);
  return { byId, sent, consent, messages, suchliste: Suchliste, suchbegriffe: context.window.Suchbegriffe };
}

const entferne = p => p.suchliste.optionen.entfernen(p.suchliste.begriffe[0], element());

async function typeAndAsk(p) {
  await p.suchbegriffe.zeige("lehrstelle", [], []);
  p.byId("vorschlag-interessen").value = "Tiere, draussen sein";
  p.byId("vorschlag-staerken").value = "geduldig, genau";
  p.byId("vorschlag-vermeiden").value = "Büro";
  await p.byId("vorschlag-holen").fire("click");
}

test("without consent, Vorschlagen shows the consent in the suggestion box and sends nothing typed", async () => {
  const p = page();
  await typeAndAsk(p);

  assert.deepEqual(p.sent, [], "nothing typed goes out before the consent");
  assert.equal(p.consent.length, 1);
  assert.equal(p.consent[0].ort, p.byId("vorschlag-einwilligung"));
  assert.equal(p.consent[0].stand, OPEN);
  assert.doesNotMatch(p.byId("vorschlag-status").textContent, /Erweiterte Einstellungen/);
  assert.equal(p.byId("vorschlag-holen").disabled, false);
});

test("after the consent is given there, the typed answers stay and the suggestion runs", async () => {
  const p = page();
  await typeAndAsk(p);
  await p.consent[0].fertig({ einwilligung: { ...OPEN, erteilt: true } });

  assert.equal(p.byId("vorschlag-einwilligung").hidden, true);
  assert.equal(p.byId("vorschlag-interessen").value, "Tiere, draussen sein");
  assert.equal(p.byId("vorschlag-staerken").value, "geduldig, genau");
  assert.equal(p.byId("vorschlag-vermeiden").value, "Büro");
  // the body comes from the sandbox's realm, so compare it as JSON
  assert.deepEqual(JSON.parse(JSON.stringify(p.sent)), [{ pfad: "/api/beruf/vorschlag",
    body: { interessen: "Tiere, draussen sein", staerken: "geduldig, genau", vermeiden: "Büro" } }]);
});

test("with consent given, Vorschlagen asks the AI right away", async () => {
  const p = page({ status: { einwilligung: { ...OPEN, erteilt: true } } });
  await typeAndAsk(p);

  assert.equal(p.consent.length, 0);
  assert.equal(p.sent.length, 1);
  assert.equal(p.sent[0].pfad, "/api/beruf/vorschlag");
});

test("the page Suche has a place for the consent inside the suggestion box and loads its script", () => {
  const html = seite("suche-einstellen.html");
  const box = html.slice(html.indexOf('<details id="vorschlag"'), html.indexOf("</details>", html.indexOf('<details id="vorschlag"')));
  assert.match(box, /id="vorschlag-einwilligung"/);
  assert.ok(html.indexOf('src="/einwilligung.js"') > 0, "einwilligung.js is loaded");
  assert.ok(html.indexOf('src="/einwilligung.js"') < html.indexOf('src="/beruf-vorschlag.js"'));
});

// Own terms and Rückgängig (#216)

const LISTE = { berufe: ["Python", "Data Engineer"], schluessel: ["python", "data engineer"] };
const sentAs = p => JSON.parse(JSON.stringify(p.sent));

test("a term of one's own goes through the same route as a suggestion, and the field empties", async () => {
  const p = page({ antworten: { "/api/beruf/aufnehmen": LISTE } });
  await p.suchbegriffe.zeige("stelle", ["Python"], ["python"]);
  p.byId("suchliste-neu").value = "  Data   Engineer ";

  await p.byId("suchliste-aufnehmen").fire("click");

  assert.deepEqual(sentAs(p), [{ pfad: "/api/beruf/aufnehmen", body: { beruf: "  Data   Engineer " } }]);
  assert.equal(p.byId("suchliste-neu").value, "");
  assert.equal(p.messages.at(-1).text, "„Data Engineer“ ist jetzt in Ihrer Suche.");
  assert.equal(p.byId("suchliste-neu-label").textContent, "Eigenen Suchbegriff aufnehmen");
});

test("a term added with required words names them apart from the term (G110, #386)", async () => {
  for (const [satz, suche] of [["stelle-sie", "Ihrer Suche"], ["stelle-du", "deiner Suche"]]) {
    const p = page({ satz, antworten: { "/api/beruf/aufnehmen": LISTE } });
    await p.suchbegriffe.zeige("stelle", ["Python"], ["python"]);
    p.byId("suchliste-neu").value = " Ausbilder  (nur mit Informatik,Mediamatik) ";

    await p.byId("suchliste-aufnehmen").fire("click");

    assert.equal(p.messages.at(-1).text, `„Ausbilder“ ist jetzt in ${suche}, mit Pflichtbezug: Informatik, Mediamatik.`);
  }
});

test("Enter in the field adds as well, and a refusal keeps what was typed", async () => {
  const p = page({ antworten: { "/api/beruf/aufnehmen": new Error("„Python“ wird schon gesucht.") } });
  await p.suchbegriffe.zeige("stelle", ["Python"], ["python"]);
  p.byId("suchliste-neu").value = "Python";

  await p.byId("suchliste-neu").fire("keydown", { key: "Enter" });

  assert.equal(p.sent.length, 1);
  assert.equal(p.byId("suchliste-neu").value, "Python");
  assert.deepEqual([p.messages.at(-1).text, p.messages.at(-1).art], ["„Python“ wird schon gesucht.", "fehler"]);
});

test("a refused own term is an input error of the field; a failure to reach the app is not (G97)", async () => {
  const refused = Object.assign(new Error("„Python“ wird schon gesucht."), { status: 400 });
  const p = page({ antworten: { "/api/beruf/aufnehmen": refused } });
  await p.suchbegriffe.zeige("stelle", ["Python"], ["python"]);
  p.byId("suchliste-neu").value = "Python";
  await p.byId("suchliste-neu").fire("keydown", { key: "Enter" });
  assert.equal(p.messages.at(-1).optionen.input, p.byId("suchliste-neu"));

  const down = page({ antworten: { "/api/beruf/aufnehmen": new Error("Failed to fetch") } });
  await down.suchbegriffe.zeige("stelle", ["Python"], ["python"]);
  down.byId("suchliste-neu").value = "Rust";
  await down.byId("suchliste-neu").fire("keydown", { key: "Enter" });
  assert.equal(down.messages.at(-1).optionen.input, null);
});

test("the field takes a term as long as the server says Meine Angaben takes it (#310)", async () => {
  const p = page();
  await p.suchbegriffe.zeige("stelle", ["Python"], ["python"], 60);

  assert.equal(p.byId("suchliste-neu").maxLength, 60);
  assert.doesNotMatch(seite("suche-einstellen.html"), /id="suchliste-neu"[^>]*maxlength/);
  assert.match(seite("suche-einstellen.js"), /Suchbegriffe\.zeige\([^)]*daten\.begriff_laenge\)/);
});

test("the field is there also when nothing is searched yet", async () => {
  const p = page();
  await p.suchbegriffe.zeige("lehrstelle", [], []);

  assert.equal(p.byId("suchliste").hidden, false);
  assert.equal(p.byId("suchliste-liste").hidden, true);
  assert.match(p.byId("suchliste-neu-label").textContent, /EFZ oder EBA/);
});

test("Entfernen offers Rückgängig, which puts the term back with its former state", async () => {
  const vorher = "a".repeat(64);
  const p = page({ antworten: {
    "/api/beruf/entfernen": { ...LISTE, berufe: ["Data Engineer"], rueckgaengig: vorher },
    "/api/beruf/rueckgaengig": { ...LISTE, am_ende: false },
  } });
  await p.suchbegriffe.zeige("stelle", ["Python", "Data Engineer"], ["python", "data engineer"]);
  await entferne(p);
  const meldung = p.messages.at(-1);
  assert.equal(meldung.text, "„Python“ ist nicht mehr in Ihrer Suche.");
  assert.equal(meldung.optionen.aktion.text, "Rückgängig");
  await meldung.optionen.aktion.ausfuehren();

  assert.deepEqual(sentAs(p).at(-1), { pfad: "/api/beruf/rueckgaengig", body: { beruf: "Python", vorher } });
  assert.equal(p.messages.at(-1).text, "„Python“ ist wieder in Ihrer Suche.");
});

test("Rückgängig after another change says the term is back at the end", async () => {
  const p = page({ antworten: {
    "/api/beruf/entfernen": { ...LISTE, rueckgaengig: "b".repeat(64) },
    "/api/beruf/rueckgaengig": { ...LISTE, am_ende: true },
  } });
  await p.suchbegriffe.zeige("stelle", ["Python"], ["python"]);
  await entferne(p);

  await p.messages.at(-1).optionen.aktion.ausfuehren();

  assert.equal(p.messages.at(-1).text, "„Python“ ist wieder in Ihrer Suche, am Ende der Liste.");
});

test("a removal that changed nothing offers nothing to undo", async () => {
  const p = page({ antworten: { "/api/beruf/entfernen": { ...LISTE, rueckgaengig: null } } });
  await p.suchbegriffe.zeige("stelle", ["Python"], ["python"]);

  await entferne(p);

  assert.equal(p.messages.at(-1).optionen.aktion, null);
});

// The order (#285, G87)

test("the list goes to suchliste.js in the order the server sends, with the message line and Entfernen", async () => {
  const p = page();
  await p.suchbegriffe.zeige("stelle", ["Data Engineer", "Python"], ["data engineer", "python"]);

  assert.equal(p.suchliste.liste, p.byId("suchliste-liste"));
  assert.deepEqual([...p.suchliste.begriffe], ["Data Engineer", "Python"]);
  assert.equal(p.suchliste.optionen.status, p.byId("suchliste-status"));
  assert.equal(typeof p.suchliste.optionen.entfernen, "function");
  assert.equal(typeof p.suchliste.optionen.geaendert, "function");
});

test("the hint says the search runs from the top, in the person's form of address, once there is something to order", async () => {
  const cases = [
    ["stelle", "stelle-sie", "Gesucht wird von oben nach unten; neue Begriffe kommen ans Ende. Ziehen Sie die wichtigsten nach oben oder verschieben Sie sie mit den Pfeilen."],
    ["stelle", "stelle-du", "Gesucht wird von oben nach unten; neue Begriffe kommen ans Ende. Zieh die wichtigsten nach oben oder verschieb sie mit den Pfeilen."],
    ["lehrstelle", "lehrstelle-du", "Gesucht wird von oben nach unten; neue Berufe kommen ans Ende. Zieh die wichtigsten nach oben oder verschieb sie mit den Pfeilen."],
  ];
  for (const [art, satz, text] of cases) {
    const p = page({ satz });
    await p.suchbegriffe.zeige(art, ["Koch/Köchin EFZ", "Maler/in EFZ"], []);
    assert.equal(p.byId("suchliste-hinweis").textContent, text);
    assert.equal(p.byId("suchliste-hinweis").hidden, false);

    await p.suchbegriffe.zeige(art, ["Koch/Köchin EFZ"], []);
    assert.equal(p.byId("suchliste-hinweis").hidden, true);
  }
});
