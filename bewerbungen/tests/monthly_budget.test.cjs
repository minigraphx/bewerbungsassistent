// The monthly AI budget of the mediation (G98): sidebar, Einstellungen, the AI windows and the estimates name the
// month and the day the budget renews, as the mediation says them; a mediation without `erneuert_am` keeps the words
// of G80. Only invented amounts.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const texte = require("../seiten/texte.js");
const sidebar = require("../seiten/sidebar-logic.js");
const settings = require("../seiten/einstellungen-logik.js");
const treffer = require("../seiten/treffer-logik.js");

const PAGES = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(PAGES, name), "utf8");
const NOVEMBER = { monat: "2026-11", erneuert_am: "2026-12-01" };
const STATUS = { eingerichtet: true, vermittlung: true, waehrung: "CHF", guthaben_chf: 5, verbraucht_chf: 1.2, ...NOVEMBER };
const OLD_STATUS = { eingerichtet: true, vermittlung: true, waehrung: "CHF", guthaben_chf: 5, verbraucht_chf: 1.2, monat: "2026-11" };
const COSTS = { monat_usd: 1.2, gesamt_usd: 3.4, aufrufe: 12, aufgaben: { rate: { aufrufe: 8, usd: 0.9 }, draft: { aufrufe: 4, usd: 0.3 } } };
const ESTIMATE = { anzahl: 3, kosten: 0.07, dauer_minuten: 1, laden: [], nicht_ladbar: [], guthaben: 3.8, danach: 3.73,
                   reicht_fuer: null, waehrung: "CHF", ...NOVEMBER };
const RENEWS = "1.\u00a0Dezember";
const el = (tag, attrs = {}, ...children) => ({ tag, attrs, children });

// ---------- Words for month and day ----------

test("month and renewal come from the mediation, in German, day and month kept together", () => {
  assert.deepEqual(texte.budgetMonth(NOVEMBER), { month: "November", renews: RENEWS });
  assert.deepEqual(texte.budgetMonth({ monat: "2026-12", erneuert_am: "2027-01-01" }), { month: "Dezember", renews: "1.\u00a0Januar" });
  assert.deepEqual(texte.budgetMonth({ monat: "2026-02", erneuert_am: "2026-03-01" }), { month: "Februar", renews: "1.\u00a0März" });
});

test("without a readable renewal there is no month: the words of G80 stay", () => {
  for (const answer of [OLD_STATUS, { erneuert_am: "2026-12-01" }, { monat: "2026-13", erneuert_am: "2026-12-01" },
                        { monat: "2026-11", erneuert_am: "1. Dezember" }, { monat: "2026-11", erneuert_am: "2026-02-30" }, null, undefined]) {
    assert.equal(texte.budgetMonth(answer), null, JSON.stringify(answer));
  }
});

test("the pages write the no-break space as an escape, never as the raw character", () => {
  for (const name of ["texte.js", "sidebar-logic.js", "einstellungen-logik.js", "treffer-logik.js", "ki-fenster.js",
                      "ki.js", "einstellungen.js", "einstellungen.html"]) {
    assert.ok(!read(name).includes("\u00a0"), name);
  }
});

// ---------- Sidebar ----------

test("the sidebar names the month, what is used and what is left", () => {
  assert.deepEqual(sidebar.budgetView(STATUS), {
    title: "KI-Budget November", text: "CHF\u00a01.20 von CHF\u00a05.00 verbraucht", short: "KI-Budget: CHF\u00a03.80 frei",
    percent: 24, label: "24 Prozent des KI-Budgets für November verbraucht",
    detail: "CHF\u00a03.80 frei", warning: "", state: "ok", narrow: "KI-Budget: CHF\u00a03.80 frei",
  });
});

test("a month with nothing used says so", () => {
  const shown = sidebar.budgetView({ ...STATUS, verbraucht_chf: 0 });
  assert.equal(shown.text, "CHF\u00a05.00 frei");
  assert.equal(shown.detail, "Noch nichts verbraucht");
  assert.equal(shown.label, "Noch nichts verbraucht");
  assert.equal(shown.warning, "");
});

test("from 80 percent the sidebar warns and names the day of the new budget", () => {
  for (const [spent, left] of [[4, "1.00"], [4.99, "0.01"]]) {
    const shown = sidebar.budgetView({ ...STATUS, verbraucht_chf: spent });
    assert.equal(shown.state, "low");
    assert.equal(shown.warning, `Fast aufgebraucht. Neues Budget am ${RENEWS}.`);
    assert.equal(shown.narrow, `KI-Budget: CHF\u00a0${left} frei · fast aufgebraucht`);
  }
  assert.equal(sidebar.budgetView({ ...STATUS, verbraucht_chf: 3.99 }).warning, "");
});

test("a used-up budget names the day the AI works again, with no link to a new code", () => {
  const shown = sidebar.budgetView({ ...STATUS, verbraucht_chf: 5 });
  assert.equal(shown.state, "empty");
  assert.equal(shown.warning, `Aufgebraucht. Die KI geht wieder ab ${RENEWS}.`);
  assert.equal(shown.narrow, `KI-Budget: wieder ab ${RENEWS}`);
  assert.equal(shown.percent, 100);
  assert.deepEqual(texte.withCodeRequestLink(shown.warning, el), [shown.warning]);
});

test("an old mediation without renewal keeps the credit of G80 in the sidebar", () => {
  const shown = sidebar.budgetView(OLD_STATUS);
  assert.equal(shown.title, "KI-Guthaben");
  assert.equal(shown.label, "24 Prozent des Guthabens verbraucht");
  assert.equal(sidebar.budgetView({ ...OLD_STATUS, verbraucht_chf: 5 }).warning, "Guthaben aufgebraucht: neuen Code anfordern");
});

test("the stored status of the sidebar does not outlive the day the budget renews", () => {
  const renewal = new Date(2026, 11, 1).getTime();
  const entry = at => ({ at, status: STATUS });
  assert.equal(sidebar.isFresh(entry(renewal - 60000), renewal - 1000), true);
  assert.equal(sidebar.isFresh(entry(renewal - 60000), renewal), false);
  assert.equal(sidebar.isFresh(entry(renewal - 60000), renewal + 1000), false);
  assert.equal(sidebar.isFresh({ at: renewal - 60000, status: OLD_STATUS }, renewal + 1000), true, "no renewal: the age alone counts");
});

// ---------- Einstellungen ----------

test("Einstellungen name the section «KI und Budget» and keep its anchors", () => {
  assert.equal(settings.SECTIONS[0].label, "KI und Budget");
  assert.equal(settings.sectionOf("#kosten"), "ki");
  const page = read("einstellungen.html");
  assert.match(page, /<a href="#ki">KI und Budget<\/a>/);
  assert.match(page, /id="bereich-ki" aria-label="KI und Budget"/);
});

test("the budget card names the month, the spend and the day of the new budget", () => {
  const view = settings.budgetView(STATUS, COSTS);
  assert.equal(view.title, "KI-Budget im November");
  assert.equal(view.headline, "CHF\u00a01.20 von CHF\u00a05.00 verbraucht");
  assert.equal(view.renewal, `Neues Budget am ${RENEWS}`);
  assert.equal(view.percent, 24);
  assert.equal(view.barLabel, "24 Prozent des KI-Budgets für November verbraucht");
  assert.equal(view.note, "Das Budget gilt pro Monat und erneuert sich am Monatsersten; was übrig bleibt, geht nicht in den "
    + "nächsten Monat mit. Ist es aufgebraucht, läuft die App weiter, nur ohne KI. Protokolliert werden Kosten, keine Inhalte.");
  assert.equal(view.usedUp, null);
  assert.deepEqual(view.rows.map(row => row.label), ["Stellen einschätzen", "Anschreiben entwerfen"]);
});

test("a used-up budget says so in Einstellungen and the code field stays", () => {
  const usedUp = { ...STATUS, verbraucht_chf: 5 };
  assert.equal(settings.budgetView(usedUp, COSTS).usedUp,
    `Das KI-Budget für November ist aufgebraucht. Die KI geht wieder ab ${RENEWS}; alles andere funktioniert weiterhin.`);
  assert.equal(settings.invitationState(usedUp), "aufgebraucht");
  assert.equal(settings.invitationUsedUp(usedUp), `Das KI-Budget für November ist aufgebraucht. Die KI geht wieder ab ${RENEWS}.`);
  assert.match(read("einstellungen.js"), /\$\("einladung-eingeben"\)\.hidden = !\["eingeben", "aufgebraucht"\]\.includes\(state\)/);
});

test("Einstellungen ask for the costs of the budget month with the token still in the address", async () => {
  // as app.js builds it: the path, «?», then the token and the parameters
  const address = (where, parameters = {}) => new URL(`${where}?${new URLSearchParams({ t: "token", ...parameters })}`, "http://127.0.0.1");
  const page = read("einstellungen.js");
  const loadCosts = ["loadCosts\\(\\)", "reportCostsProblem\\(fehler\\)"]
    .map(head => page.match(new RegExp(`\\n  function ${head} \\{[\\s\\S]*?\\n  \\}\\n`))[0]).join("");
  const asked = [];
  const holen = (where, parameters) => { asked.push(address(where, parameters)); return Promise.resolve({}); };
  const run = new Function("holen", "L", "ki", "zeige", "status", "$", `${loadCosts}; return loadCosts();`);
  for (const month of ["2026-11", null]) {
    await run(holen, { costMonth: () => month }, STATUS, () => {}, () => {}, () => null);
  }
  assert.deepEqual(asked.map(url => [url.pathname, url.searchParams.get("t"), url.searchParams.get("monat")]),
    [["/api/schluessel", "token", "2026-11"], ["/api/schluessel", "token", null]]);
  // a failure says what could not be read, not only the bare reason, on the line of the budget card
  const shown = [];
  await run(() => Promise.reject(new Error("Zeitüberschreitung")), { costMonth: () => "2026-11" }, STATUS, () => {},
    (line, text, level) => shown.push([line.id, text, level]), id => ({ id }));
  assert.deepEqual(shown, [["budget-meldung", "Die Kosten liessen sich nicht laden: Zeitüberschreitung", "fehler"]]);
});

test("the costs' failure line stays visible while the key section is hidden", () => {
  // with the invitation code as the way, #schluessel-teil is hidden and so is every line inside it
  const page = read("einstellungen.html");
  const section = id => page.match(new RegExp(`<section class="card" id="${id}"[^>]*>[\\s\\S]*?\\n  </section>\\n`))[0];
  assert.match(section("schluessel-teil"), /^<section class="card" id="schluessel-teil"[^>]* hidden>/);
  assert.doesNotMatch(section("schluessel-teil"), /id="budget-meldung"/);
  assert.match(section("kosten"), /<div id="budget-meldung" class="status" role="status" aria-live="polite"><\/div>/);
  assert.doesNotMatch(section("kosten"), /^<section[^>]* hidden>/);
});

const ACTIVE_MONTHLY = "Die KI läuft über die Vermittlung des Pilots, mit einem Budget pro Monat. Was davon verbraucht ist, "
  + "steht unter KI-Budget.";
const ACTIVE_ONCE = "Die KI läuft über die Vermittlung des Pilots, mit dem einmaligen Guthaben des Einladungscodes. Was davon "
  + "verbraucht ist, steht unter Guthaben.";

test("„Einladungscode“ names the monthly budget only when the mediation names its renewal", () => {
  assert.equal(settings.invitationActive(STATUS), ACTIVE_MONTHLY);
  assert.equal(settings.invitationActive(OLD_STATUS), null, "the page keeps its sentence of G80");
  assert.equal(settings.invitationActive(null), null);
  // the page holds the sentence of G80, so an app ahead of the mediation's deploy still says what is true
  assert.match(read("einstellungen.html"), new RegExp(`<p id="einladung-aktiv" hidden>${ACTIVE_ONCE}</p>`));
});

test("the page sets the sentence of „Einladungscode“ from the status, as written", () => {
  const page = read("einstellungen.js");
  const show = page.match(/\n  function showInvitation\(\) \{[\s\S]*?\n  \}\n/)[0];
  const once = page.match(/\n  const ACTIVE_ONCE = [^\n]*\n/);
  assert.ok(once, "the page keeps its own sentence of G80 before the status arrives");
  const run = ki => {
    const elements = new Map();
    const $ = id => {
      if (!elements.has(id)) elements.set(id, { id, hidden: true, textContent: id === "einladung-aktiv" ? ACTIVE_ONCE : "", replaceChildren() {} });
      return elements.get(id);
    };
    const window = { Texte: texte };
    new Function("$", "L", "ki", "window", "el", "USED_UP_ONCE", `${once[0]}${show}; showInvitation();`)(
      $, settings, ki, window, el, "used up");
    return $("einladung-aktiv");
  };
  for (const [ki, sentence] of [[STATUS, ACTIVE_MONTHLY], [OLD_STATUS, ACTIVE_ONCE]]) {
    const line = run(ki);
    assert.equal(line.hidden, false);
    assert.equal(line.textContent, sentence);
  }
});

test("Einstellungen of an old mediation keep the words of G80", () => {
  const view = settings.budgetView(OLD_STATUS, COSTS);
  assert.equal(view.title, "Guthaben");
  assert.equal(view.renewal, null);
  assert.equal(view.barLabel, "24 Prozent des Guthabens verbraucht");
  assert.equal(settings.invitationUsedUp({ ...OLD_STATUS, verbraucht_chf: 5 }), null, "the page keeps its sentence with «anfordern»");
});

test("the texts of the code name a budget per month, in the Sie and the du form", () => {
  const page = read("einstellungen.html");
  assert.equal(settings.invitationActive(STATUS), ACTIVE_MONTHLY);
  assert.match(page, /<p class="notice notice--warning" id="budget-aufgebraucht" hidden>/);
  assert.match(read("ki-zugang.js"), /text: "Kostenlos im Pilot, mit einem Budget von CHF 5 pro Monat\."/);
  assert.equal(texte.text("einrichtung.ki.code", "stelle-sie"),
    "Haben Sie einen Einladungscode? Er bringt ein Budget von CHF 5 pro Monat für die KI.");
  assert.equal(texte.text("einrichtung.ki.code", "stelle-du"),
    "Hast du einen Einladungscode? Er bringt ein Budget von CHF 5 pro Monat für die KI.");
  assert.equal(texte.text("einrichtung.ki.code", "lehrstelle-du"),
    "Hast du einen Einladungscode? Er bringt ein Budget von CHF 5 pro Monat für die KI.");
  // the one exception is the page's sentence of G80, shown only while the mediation names no renewal
  const fallback = `<p id="einladung-aktiv" hidden>${ACTIVE_ONCE}</p>`;
  assert.equal(page.split(fallback).length, 2, "the sentence of G80 stands once, in #einladung-aktiv");
  const texts = { "ki-zugang.js": read("ki-zugang.js"), "texte.js": read("texte.js"), "einstellungen.html": page.replace(fallback, ""),
                  "einstellungen-logik.js": read("einstellungen-logik.js") };
  for (const [name, text] of Object.entries(texts)) assert.ok(!text.includes("einmalig"), name);
});

// ---------- The AI windows ----------

test("the window and the page «KI» name the month and, once used up, the day the AI works again", () => {
  assert.equal(texte.budgetPart(STATUS), " KI-Budget im November: CHF\u00a01.20 von CHF\u00a05.00 verbraucht.");
  assert.equal(texte.budgetPart({ ...STATUS, verbraucht_chf: 5 }),
    ` KI-Budget im November: CHF\u00a05.00 von CHF\u00a05.00 verbraucht. Es ist aufgebraucht; die KI geht wieder ab ${RENEWS}.`);
  assert.match(read("ki.js"), /window\.Texte\.budgetPart\(s\)/);
  assert.match(read("ki-fenster.js"), /window\.Texte\.budgetPart\(ki\)/);
});

test("the window of an old mediation keeps the way to a new code", () => {
  assert.equal(texte.budgetPart({ ...OLD_STATUS, verbraucht_chf: 5 }),
    " Guthaben: CHF\u00a05.00 von CHF\u00a05.00 verbraucht. Das Guthaben ist aufgebraucht: einen neuen Code anfordern "
    + "und unter Einstellungen, KI und Budget einlösen.");
  assert.equal(texte.budgetPart({ eingerichtet: true, vermittlung: true }), "");
});

// ---------- Estimates before a run ----------

test("the estimates speak of the budget of this month", () => {
  assert.equal(treffer.estimateLine(ESTIMATE), "Etwa CHF\u00a00.07 und 1\u00a0Minute. Danach bleiben CHF\u00a03.73 im Budget.");
  assert.equal(treffer.estimateLine({ ...ESTIMATE, reicht_fuer: 2 }),
    "Etwa CHF\u00a00.07 und 1\u00a0Minute. Das Budget dieses Monats reicht für etwa 2 Stellen.");
  assert.equal(treffer.costLine({ ...ESTIMATE, guthaben: 0.05 }).text,
    "Etwa CHF\u00a00.07 und 1\u00a0Minute. Im Budget sind noch CHF\u00a00.05, das reicht vielleicht nicht.");
  assert.equal(treffer.confirmation({ ...ESTIMATE, anzahl: 20, guthaben: 0.1, reicht_fuer: 4 }, false, true).warning,
    "Das Budget dieses Monats reicht f\u00fcr etwa 4 von 20 Stellen. Ist es aufgebraucht, h\u00e4lt die Pr\u00fcfung an; was gepr\u00fcft ist, bleibt.");
});

test("a used-up budget locks the run and names the day, without a link to a new code", () => {
  const usedUp = { ...ESTIMATE, guthaben: 0, danach: 0, reicht_fuer: 0 };
  const line = treffer.costLine(usedUp);
  assert.equal(line.usedUp, true);
  assert.equal(line.text, `Etwa CHF\u00a00.07 und 1\u00a0Minute. Das KI-Budget ist aufgebraucht, wieder ab ${RENEWS}.`);
  assert.deepEqual(texte.withCodeRequestLink(line.text, el), [line.text]);
  assert.equal(treffer.confirmation(usedUp, false, true).warning,
    `Das KI-Budget für November ist aufgebraucht. Ab ${RENEWS} prüft die KI wieder; was geprüft ist, bleibt.`);
});

test("the estimates of an old mediation keep the credit of G80", () => {
  const old = { ...ESTIMATE, monat: undefined, erneuert_am: undefined };
  assert.equal(treffer.estimateLine(old), "Etwa CHF\u00a00.07 und 1\u00a0Minute. Danach bleiben CHF\u00a03.73 im Guthaben.");
  assert.equal(treffer.estimateLine({ ...old, guthaben: 0, danach: 0, reicht_fuer: 0 }),
    "Etwa CHF\u00a00.07 und 1\u00a0Minute. Das Guthaben ist aufgebraucht: neuen Code anfordern.");
});
