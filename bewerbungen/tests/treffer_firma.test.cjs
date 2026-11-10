// kununu on Stellen suchen (G35, #190): the badge after the company name and the company line in the detail column.
// Invented companies only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/firmen-logik.js");

const HEUTE = "2026-11-09";

function firma(name, kununu = null, treffer = []) {
  return { schluessel: name.toLowerCase().replace(/\W+/g, "-"), name, ort: "Bern", treffer, bewerbungen: [], kununu,
           suche: `https://www.kununu.com/ch/search?q=${encodeURIComponent(name)}` };
}

const LINK = "https://www.kununu.com/ch/muster-industrie";
const gefunden = (wert, bewertungen, extra = {}) =>
  ({ zustand: "gefunden", wert, bewertungen, geprueft_am: "2026-11-05", seite: "ch", link: LINK, ...extra });

test("each hit finds its company by the hits the companies list", () => {
  const muster = firma("Muster Industrie AG", gefunden(3.8, 214), [{ id: "jobs-ch-1" }, { id: "jobs-ch-2" }]);
  const test = firma("Testlogistik GmbH", null, [{ id: "jobscout24-9" }]);
  const zuordnung = logik.nachTreffer([muster, test]);
  assert.equal(zuordnung.get("jobs-ch-1"), muster);
  assert.equal(zuordnung.get("jobs-ch-2"), muster);
  assert.equal(zuordnung.get("jobscout24-9"), test);
  assert.equal(zuordnung.get("unbekannt-1"), undefined);
});

test("a company with a score gets a grey badge with its value, the reviews only for screen readers", () => {
  assert.deepEqual(logik.marke(firma("Muster Industrie AG", gefunden(3.8, 214))),
    { text: "kununu 3.8 von 5", vorlesen: "kununu 3.8 von 5, 214 Bewertungen", art: "wert" });
  assert.deepEqual(logik.marke(firma("Muster Industrie AG", gefunden(4, 1312))),
    { text: "kununu 4.0 von 5", vorlesen: "kununu 4.0 von 5, 1’312 Bewertungen", art: "wert" });
});

test("few reviews make the badge dashed and say so", () => {
  assert.deepEqual(logik.marke(firma("Beispiel Bau AG", gefunden(4.6, 3))),
    { text: "kununu 4.6 von 5, wenige Bewertungen", vorlesen: "kununu 4.6 von 5, nur 3 Bewertungen", art: "wenige" });
});

test("a stale value keeps its badge", () => {
  const alt = firma("Muster Industrie AG", gefunden(3.2, 57, { geprueft_am: "2026-07-02" }));
  assert.equal(logik.veraltet(alt, HEUTE), true);
  assert.equal(logik.marke(alt).text, "kununu 3.2 von 5");
});

test("several companies or none found give a quiet word; other states give no badge", () => {
  assert.deepEqual(logik.marke(firma("Beispiel Holding AG", { zustand: "mehrere" })),
    { text: "kununu: wählen", vorlesen: "kununu: passende Firma wählen", art: "leise" });
  assert.deepEqual(logik.marke(firma("Testlogistik GmbH", { zustand: "nicht_gefunden" })),
    { text: "nicht bei kununu", vorlesen: "bei kununu nicht gefunden", art: "leise" });
  for (const kununu of [null, { zustand: "keine" }, { zustand: "fehler" }, { zustand: "zugeordnet", link: LINK }]) {
    assert.equal(logik.marke(firma("Muster AG", kununu)), null);
  }
  assert.equal(logik.marke(undefined), null);
});

test("the company line shows score, reviews, recommendation, site, date and the link to kununu", () => {
  const zeile = logik.firmenZeile(firma("Muster Industrie AG", gefunden(3.8, 214, { empfehlung: 78 })), HEUTE);
  assert.deepEqual(zeile, {
    titel: "Muster Industrie AG bei kununu", zustand: "gefunden", wert: "3.8", wenige: false,
    angaben: ["214 Bewertungen", "78 % empfehlen", "kununu.com/ch"], datum: "Geprüft am 05.11.2026",
    satz: "", aktionen: [{ art: "ansehen", text: "Bei kununu ansehen", href: LINK }],
  });
});

test("the company line says where the value came from and marks few reviews and stale values", () => {
  const de = logik.firmenZeile(firma("Beispiel Bau AG", gefunden(4.6, 3, { seite: "de", geprueft_am: "2026-07-02",
    link: "https://www.kununu.com/de/beispiel-bau" })), HEUTE);
  assert.equal(de.wenige, true);
  assert.deepEqual(de.angaben, ["Nur 3 Bewertungen, wenig aussagekräftig.", "kununu.com/de"]);
  assert.equal(de.datum, "Stand 02.07.2026");
  assert.deepEqual(de.aktionen.map(a => a.text), ["Neu prüfen", "Bei kununu ansehen"]);
});

test("for apprenticeships the apprentices' reviews come along when kununu lists them", () => {
  const lehrbetrieb = firma("Muster Industrie AG", gefunden(3.8, 214, { lernende: { wert: 4.2, bewertungen: 12 } }));
  assert.ok(logik.firmenZeile(lehrbetrieb, HEUTE, { lehrstelle: true }).angaben.includes("Lernende: 4.2 von 5, 12 Bewertungen"));
  assert.ok(!logik.firmenZeile(lehrbetrieb, HEUTE).angaben.some(a => a.startsWith("Lernende")));
});

test("without a value the company line says what is known and offers to check", () => {
  const ungeprueft = logik.firmenZeile(firma("Muster AG"), HEUTE);
  assert.equal(ungeprueft.satz, "Noch nicht bei kununu geprüft.");
  assert.deepEqual(ungeprueft.aktionen, [{ art: "pruefen", text: "Jetzt prüfen", href: "https://www.kununu.com/ch/search?q=Muster%20AG" }]);
  assert.equal(ungeprueft.wert, null);

  const zugeordnet = logik.firmenZeile(firma("Muster AG", { zustand: "zugeordnet", link: LINK, seite: "ch" }), HEUTE);
  assert.equal(zugeordnet.satz, "Seite zugeordnet, noch nicht geprüft.");
  assert.deepEqual(zugeordnet.aktionen.map(a => [a.art, a.href]), [["pruefen", LINK], ["ansehen", LINK]]);

  const keine = logik.firmenZeile(firma("Muster AG", { zustand: "keine", link: LINK, geprueft_am: "2026-11-05" }), HEUTE);
  assert.equal(keine.satz, "Noch keine Bewertungen.");
  assert.equal(keine.datum, "Geprüft am 05.11.2026");

  const fehler = logik.firmenZeile(firma("Muster AG", { zustand: "fehler" }), HEUTE);
  assert.equal(fehler.satz, "Nicht geprüft. kununu war nicht erreichbar. Bitte später nochmals prüfen.");
  assert.deepEqual(fehler.aktionen.map(a => a.text), ["Nochmals prüfen"]);

  const nicht = logik.firmenZeile(firma("Testlogistik GmbH", { zustand: "nicht_gefunden", geprueft_am: "2026-11-05" }), HEUTE);
  assert.equal(nicht.satz, "Bei kununu nicht gefunden.");
  assert.deepEqual(nicht.aktionen.map(a => [a.art, a.text]), [["suchen", "Bei kununu suchen"]]);

  const mehrere = logik.firmenZeile(firma("Beispiel Holding AG", { zustand: "mehrere" }), HEUTE);
  assert.equal(mehrere.satz, "Mehrere Firmen bei kununu.");
  assert.deepEqual(mehrere.aktionen, []);
  assert.equal(logik.firmenZeile(firma("Beispiel Holding AG", { zustand: "mehrere" }), HEUTE, { lehrstelle: true }).satz,
    "Mehrere Lehrbetriebe bei kununu.");
});

test("the badge and the company line never borrow the words of the fit grade", () => {
  const alle = [gefunden(3.8, 214), gefunden(1.2, 40), gefunden(4.6, 3), { zustand: "mehrere" }, { zustand: "nicht_gefunden" }];
  for (const kununu of alle) {
    const texte = JSON.stringify([logik.marke(firma("Muster AG", kununu)), logik.firmenZeile(firma("Muster AG", kununu), HEUTE)]);
    assert.doesNotMatch(texte, /Note|passt gut|★/);
  }
});
