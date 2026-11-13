"use strict";
// The sidebar of every page (#259, G54): marks where the page belongs, opens „Menü“ below 900 px, fills the badges,
// the AI budget and the state of the extension. Every part stays hidden when its question fails.
(() => {
  const S = window.SidebarLogic;
  const L = window.UebersichtLogik;
  const nav = document.querySelector(".app-nav");
  if (!nav || !S || !window.App) return;
  const { holen } = window.App;
  const $ = id => document.getElementById(id);
  const BUDGET_KEY = "bewerbungsbegleiter.ki-status";
  // The content script of the extension announces itself at document_idle; after that it is not coming.
  const EXTENSION_WAIT_MS = 3000;
  const EXTENSION_SOURCE = "bewerbungsbegleiter-erweiterung";

  function markCurrent() {
    const target = S.activeTarget(location.pathname);
    const link = target && nav.querySelector(`.app-nav__link[data-target="${target}"]`);
    if (link) link.setAttribute("aria-current", "page");
  }

  function menu() {
    const button = $("nav-menu");
    const setOpen = open => {
      button.setAttribute("aria-expanded", String(open));
      nav.toggleAttribute("data-open", open);
    };
    button.addEventListener("click", () => setOpen(button.getAttribute("aria-expanded") !== "true"));
    document.addEventListener("click", event => { if (!nav.contains(event.target)) setOpen(false); });
    document.addEventListener("keydown", event => {
      if (event.key !== "Escape" || button.getAttribute("aria-expanded") !== "true") return;
      setOpen(false);
      button.focus();
    });
  }

  function showBadge(id, badge) {
    const element = $(id);
    element.hidden = !badge;
    element.querySelector(".app-nav__count-long").textContent = badge ? badge.long : "";
    element.querySelector(".app-nav__count-short").textContent = badge ? badge.short : "";
  }

  async function dueCount() {
    const [register, choice, rav] = await Promise.all([
      holen("/api/bewerbungen"), holen("/api/bewerben/auswahl"), holen("/api/rav/auswahl")]);
    const reasons = new Map(choice.bewerbungen.map(row => [row.id, row.grund]));
    const ravReasons = new Map(rav.sichtbar ? rav.bewerbungen.map(row => [row.id, row.grund]) : []);
    return L.stehtAn(L.mitSchritten(register.bewerbungen, reasons, ravReasons), Infinity).length;
  }

  async function newHits() {
    const list = await holen("/api/suche/liste");
    return list.treffer.filter(hit => hit.zustand === "neu").length;
  }

  async function fillBadges() {
    const [open, fresh] = await Promise.all([dueCount().catch(() => 0), newHits().catch(() => 0)]);
    const shown = S.badges({ open, newHits: fresh });
    showBadge("badge-heute", shown.heute);
    showBadge("badge-stellen", shown.stellen);
  }

  function storedStatus() {
    try {
      const entry = JSON.parse(sessionStorage.getItem(BUDGET_KEY) || "null");
      return S.isFresh(entry, Date.now()) ? entry.status : null;
    } catch {
      return null;  // storage blocked or garbled: ask the app
    }
  }

  async function aiStatus() {
    const stored = storedStatus();
    if (stored) return stored;
    const status = await holen("/api/ki/status");
    try { sessionStorage.setItem(BUDGET_KEY, JSON.stringify({ at: Date.now(), status })); } catch { /* asked again next page */ }
    return status;
  }

  // Asked once per page; Heute reads the same answers for its first step (#260).
  const aiAnswer = aiStatus().catch(() => null);  // the app is closing: no budget, and the first step stays open
  let reportExtension = () => {};
  const extensionAnswer = new Promise(resolve => { reportExtension = resolve; });

  async function fillBudget() {
    const view = S.budgetView(await aiAnswer);
    $("nav-budget").hidden = $("nav-budget-short").hidden = !view;
    if (!view) return;
    $("nav-budget-title").textContent = view.title;
    $("nav-budget-text").textContent = view.text;
    $("nav-budget-short").textContent = view.short;
    const bar = $("nav-budget-bar");
    bar.hidden = view.percent === null;
    bar.setAttribute("aria-label", view.label);
    $("nav-budget-fill").style.width = `${view.percent || 0}%`;
  }

  function showExtension(connected) {
    const line = $("nav-extension");
    line.dataset.state = connected ? "connected" : "missing";
    $("nav-extension-text").textContent = connected ? "Erweiterung verbunden" : "Erweiterung nicht verbunden";
    $("nav-extension-setup").hidden = connected;
    line.hidden = false;
    reportExtension(connected);
  }

  function watchExtension() {
    let announced = Boolean(document.documentElement.dataset.bewerbungsbegleiterErweiterung);
    if (announced) return showExtension(true);
    window.addEventListener("message", event => {
      if (event.source !== window || event.origin !== location.origin || event.data?.quelle !== EXTENSION_SOURCE) return;
      announced = true;
      showExtension(true);
    });
    setTimeout(() => {
      if (!announced && !document.documentElement.dataset.bewerbungsbegleiterErweiterung) showExtension(false);
    }, EXTENSION_WAIT_MS);
  }

  window.Sidebar = { aiStatus: aiAnswer, extension: extensionAnswer };
  markCurrent();
  menu();
  watchExtension();
  fillBudget();
  if (L) fillBadges();
  document.addEventListener("visibilitychange", () => { if (!document.hidden && L) fillBadges(); });
})();
