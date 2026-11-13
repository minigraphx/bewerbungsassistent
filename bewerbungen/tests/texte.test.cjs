// Text sets (MIN-369): every text that speaks to the person exists with Sie and with du, du is lower case.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");

test("each set picks its form, an apprenticeship falls back to du", () => {
  assert.equal(texte.text("einrichtung.ordner.frage", "stelle-sie"), "Wo sollen Ihre Unterlagen liegen?");
  assert.equal(texte.text("einrichtung.ordner.frage", "stelle-du"), "Wo sollen deine Unterlagen liegen?");
  assert.equal(texte.text("einrichtung.ordner.frage", "lehrstelle-du"), "Wo sollen deine Unterlagen liegen?");
  assert.equal(texte.text("einrichtung.ki.aufgabe", "lehrstelle-du"), "Die KI schätzt Lehrstellen ein und entwirft Anschreiben.");
});

test("an unknown set is the default, an unknown key fails loudly", () => {
  assert.equal(texte.text("einrichtung.ki.code", "irgendwas"), texte.text("einrichtung.ki.code", "stelle-sie"));
  assert.throws(() => texte.text("gibt.es.nicht", "stelle-sie"), /Unbekannter Text/);
});

test("every entry has both forms, and they really differ in the address", () => {
  for (const [schluessel, eintrag] of Object.entries(texte.TEXTE)) {
    assert.ok(eintrag.sie && eintrag.du, `${schluessel}: Sie und du`);
    for (const form of ["du", "lehrstelle"].filter(f => eintrag[f])) {
      assert.doesNotMatch(eintrag[form], /\b(Sie|Ihr|Ihre|Ihrem|Ihren|Ihrer|Ihnen)\b/, `${schluessel}.${form}: keine Sie-Form`);
      assert.doesNotMatch(eintrag[form], /[^.!?:]\s(Du|Dein|Deine|Deinem|Deinen|Deiner|Dir|Dich)\b/, `${schluessel}.${form}: du klein`);
    }
    assert.doesNotMatch(eintrag.sie, /\b(du|dein|deine|deinem|deinen|deiner|dir|dich)\b/i, `${schluessel}.sie: keine Du-Form`);
  }
});

test("values fill their places", () => {
  texte.TEXTE["test.wert"] = { sie: "Noch {anzahl} Schritte für Sie.", du: "Noch {anzahl} Schritte für dich." };
  assert.equal(texte.text("test.wert", "stelle-du", { anzahl: 3 }), "Noch 3 Schritte für dich.");
  delete texte.TEXTE["test.wert"];
});

test("for apprenticeships an interview reads as an invitation, the stored status stays", () => {
  assert.equal(texte.statusName("Gespräch", "lehrstelle-du"), "Einladung");
  assert.equal(texte.statusName("Gespräch", "stelle-du"), "Gespräch");
  assert.equal(texte.statusName("Absage", "lehrstelle-du"), "Absage");
});

test("a grade is written with a decimal point", () => {
  assert.equal(texte.notenText(5.5), "5.5");
  assert.equal(texte.notenText(4), "4");
});

test("the app is called the app, not the assistant", () => {
  const worte = Object.values(texte.TEXTE).flatMap(eintrag => Object.values(eintrag));
  assert.deepEqual(worte.filter(wort => /Assistent/.test(wort)), []);
});

// Pages whose text speaks to the person: what is left outside a data-text element must not use the address.
const SIE_FORM = /\b(Sie|Ihr|Ihre|Ihrem|Ihren|Ihrer|Ihnen)\b/;
const seite = name => fs.readFileSync(path.join(__dirname, "..", "seiten", name), "utf8");
const ohneTextElemente = html => html.replace(/<(\w+)\b[^>]*\bdata-text="[^"]*"[^>]*>[\s\S]*?<\/\1>/g, "");

test("the settings page leaves its address to the text set", () => {
  assert.doesNotMatch(ohneTextElemente(seite("einstellungen.html")), SIE_FORM);
});

test("each data-text of the settings page is known and starts as the Sie text", () => {
  const html = seite("einstellungen.html");
  const elemente = [...html.matchAll(/<(\w+)\b[^>]*\bdata-text="([^"]*)"[^>]*>([\s\S]*?)<\/\1>/g)];
  assert.ok(elemente.length > 0);
  for (const [, , schluessel, inhalt] of elemente) assert.equal(inhalt, texte.text(schluessel, "stelle-sie"));
});

test("scripts with texts of their own do not fix the address", () => {
  for (const name of ["fragen.js", "einwilligung.js", "portal-wahl.js"]) assert.doesNotMatch(seite(name), SIE_FORM, name);
  assert.doesNotMatch(seite("app.js"), /können Sie/);
  assert.doesNotMatch(seite("treffer.html").replace(/data-text="suche\.wo">[^<]*/, ""), /Wo suchen Sie/);
});

test("the questions page speaks in the form of the set", () => {
  assert.equal(texte.text("fragen.label", "stelle-sie"), "Ihre Frage");
  assert.equal(texte.text("fragen.label", "stelle-du"), "Deine Frage");
  assert.equal(texte.text("fragen.sprecher", "lehrstelle-du"), "Du");
  assert.match(texte.text("fragen.hilfe", "lehrstelle-du"), /zur Lehrstellensuche und zu deiner Bewerbung/);
});

test("a job with du gets the search suggestions with du", () => {
  const context = { window: { App: { senden() {}, el() {}, status() {} } }, document: { getElementById: () => ({ addEventListener() {} }), dispatchEvent() {} }, CustomEvent: class {} };
  vm.runInNewContext(seite("beruf-vorschlag.js"), context);
  const { texteFuer } = context.window.Suchbegriffe;
  assert.match(texteFuer("stelle", "stelle-sie").titel, /zu Ihnen/);
  assert.match(texteFuer("stelle", "stelle-du").titel, /zu dir/);
  assert.match(texteFuer("lehrstelle", "lehrstelle-du").titel, /Beruf/);
  for (const [name, wert] of Object.entries(texteFuer("stelle", "stelle-du"))) {
    assert.doesNotMatch(typeof wert === "function" ? wert("Muster") : wert, SIE_FORM, name);
  }
});

test("the consent says what the app replaces before text goes to the AI, in the form of the set (G14)", () => {
  const sie = texte.text("einwilligung.ersetzt", "stelle-sie");
  const du = texte.text("einwilligung.ersetzt", "stelle-du");
  const lehrstelle = texte.text("einwilligung.ersetzt", "lehrstelle-du");
  for (const satz of [sie, du, lehrstelle]) {
    assert.match(satz, /Platzhalter/);
    assert.match(satz, /Name.*Adresse.*Telefon.*E-Mail/);
    assert.match(satz, /Jahreszahlen bleiben/);
    assert.match(satz, /richtig eingetragen/);
  }
  assert.match(sie, /\bIhre\b/);
  assert.match(du, /\bdeine\b/);
  assert.match(lehrstelle, /Schulen/);
  assert.match(seite("einwilligung.js"), /"einwilligung\.ersetzt"/);
});

test("the ictjobs line says why it is on or off and how to change it, in the form of the set (#107)", () => {
  const begriff = { begriff: "Software" };
  assert.equal(texte.text("suche.ictjobs.aus", "stelle-sie"), "Aus, weil keiner Ihrer Suchbegriffe nach Informatik klingt. Mit dem Häkchen einschalten.");
  assert.equal(texte.text("suche.ictjobs.aus", "stelle-du"), "Aus, weil keiner deiner Suchbegriffe nach Informatik klingt. Mit dem Häkchen einschalten.");
  assert.equal(texte.text("suche.ictjobs.passt", "stelle-sie", begriff), "An, weil Ihr Suchbegriff «Software» nach Informatik klingt. Mit dem Häkchen ausschalten.");
  assert.equal(texte.text("suche.ictjobs.passt", "stelle-du", begriff), "An, weil dein Suchbegriff «Software» nach Informatik klingt. Mit dem Häkchen ausschalten.");
  assert.match(texte.text("suche.ictjobs.gewaehlt", "stelle-sie"), /^Ihre Wahl\. .*Häkchen/);
  assert.match(texte.text("suche.ictjobs.gewaehlt", "stelle-du"), /^Deine Wahl\. .*Häkchen/);
  for (const satz of ["stelle-sie", "stelle-du"]) assert.match(texte.text("suche.ictjobs.keine", satz), /^An, bis Suchbegriffe da sind\. .*Häkchen/);
});

test("the portal choice shows the reason of ictjobs from the text set", () => {
  const script = seite("portal-wahl.js");
  assert.match(script, /`suche\.ictjobs\.\$\{portal\.grund\}`/);
  assert.match(script, /begriff: portal\.begriff/);
});

test("the empty overview names Merken like the search page does since #220 (#229)", () => {
  const erwartet = {
    "stelle-sie": "Noch keine Bewerbungen. Klicken Sie in der Suche bei einer Stelle auf «Merken» oder erfassen Sie eine von Hand.",
    "stelle-du": "Noch keine Bewerbungen. Klicke in der Suche bei einer Stelle auf «Merken» oder erfasse eine von Hand.",
    "lehrstelle-du": "Noch keine Bewerbungen. Klicke in der Suche bei einer Lehrstelle auf «Merken» oder erfasse eine von Hand.",
  };
  for (const [satz, text] of Object.entries(erwartet)) assert.equal(texte.text("uebersicht.liste-leer", satz), text, satz);
  const html = seite("bewerbungen.html");
  assert.ok(html.includes(`data-text="uebersicht.liste-leer" hidden>${erwartet["stelle-sie"]}</p>`));
  for (const alt of ["Übernehmen Sie eine Stelle aus der Suche", "Übernimm eine"]) {
    assert.ok(!html.includes(alt) && !JSON.stringify(texte.TEXTE["uebersicht.liste-leer"]).includes(alt), alt);
  }
});
