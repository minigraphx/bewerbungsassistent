"use strict";
const TOKEN = document.querySelector('meta[name="token"]').content;
const MIN_ABSTAND_MS = 50;           // höchstens ein Vorschaubild pro 50 ms
const STANDARD = { mirror: false, zoom: 1, x: 0.5, y: 0.5 };
const el = id => document.getElementById(id);

let stand = { ...STANDARD };          // aktuelle Werte im Editor
let gespeichert = { ...STANDARD };    // Werte in der Datei
let seitenverhaeltnis = 1;            // Höhe / Breite des Originalfotos

const gerundet = o => ({ mirror: o.mirror, zoom: +o.zoom.toFixed(3), x: +o.x.toFixed(3), y: +o.y.toFixed(3) });
const gleich = (a, b) => JSON.stringify(gerundet(a)) === JSON.stringify(gerundet(b));
const begrenzt = (wert, unten, oben) => Math.min(oben, Math.max(unten, wert));

function status(text, art = "") {
  const s = el("status");
  s.textContent = text;
  s.className = "status " + art;
}

// Überstand des Bildes über den Kreis, in Kreisdurchmessern (wie foto-rund in common.typ)
function ueberstand(zoom) {
  const breite = seitenverhaeltnis >= 1 ? zoom : zoom / seitenverhaeltnis;
  const hoehe = seitenverhaeltnis >= 1 ? zoom * seitenverhaeltnis : zoom;
  return { x: breite - 1, y: hoehe - 1 };
}

function setze(neu) {
  stand = {
    mirror: !!neu.mirror,
    zoom: begrenzt(neu.zoom, 1, 4),
    x: begrenzt(neu.x, 0, 1),
    y: begrenzt(neu.y, 0, 1),
  };
  zeige();
  vorschauAnfordern();
}

function zeige() {
  const g = gerundet(stand);
  el("mirror").checked = g.mirror;
  for (const k of ["zoom", "x", "y"]) {
    el(k).value = g[k];
    el(k + "-wert").textContent = k === "zoom" ? g[k].toFixed(2) + "×" : g[k].toFixed(3);
  }
  el("yaml").textContent = `x-image: {mirror: ${g.mirror}, zoom: ${g.zoom}, x: ${g.x}, y: ${g.y}}`;
  const ungespeichert = !gleich(stand, gespeichert);
  el("speichern").disabled = !ungespeichert;
  el("zuruecksetzen").disabled = !ungespeichert;
  if (ungespeichert) status("Nicht gespeichert", "hinweis");
  else if (el("status").className === "status hinweis") status("");
}

// Vorschau: immer nur eine Anfrage gleichzeitig; Änderungen währenddessen holt die nächste Runde
let laeuft = false, wartet = false, letzteUrl = null;
async function vorschauAnfordern() {
  if (laeuft) { wartet = true; return; }
  laeuft = true;
  const start = performance.now();
  try {
    const g = gerundet(stand);
    const q = new URLSearchParams({ t: TOKEN, mirror: g.mirror, zoom: g.zoom, x: g.x, y: g.y });
    const antwort = await fetch("/api/foto/vorschau.png?" + q);
    if (!antwort.ok) throw new Error((await antwort.json()).fehler);
    const url = URL.createObjectURL(await antwort.blob());
    el("gross").src = url;
    el("klein").src = url;
    if (letzteUrl) URL.revokeObjectURL(letzteUrl);
    letzteUrl = url;
  } catch (fehler) {
    status("Vorschau fehlgeschlagen: " + fehler.message, "fehler");
  }
  const rest = MIN_ABSTAND_MS - (performance.now() - start);
  if (rest > 0) await new Promise(r => setTimeout(r, rest));
  laeuft = false;
  if (wartet) { wartet = false; vorschauAnfordern(); }
}

// Ziehen
const kreis = el("kreis");
let ziehen = null;
kreis.addEventListener("pointerdown", e => {
  kreis.setPointerCapture(e.pointerId);
  kreis.classList.add("zieht");
  ziehen = { px: e.clientX, py: e.clientY, x: stand.x, y: stand.y };
});
kreis.addEventListener("pointermove", e => {
  if (!ziehen) return;
  const d = kreis.clientWidth;
  const u = ueberstand(stand.zoom);
  // Bild folgt der Maus: nach rechts ziehen zeigt mehr vom linken Bildrand
  setze({
    ...stand,
    x: u.x > 0 ? ziehen.x - (e.clientX - ziehen.px) / d / u.x : stand.x,
    y: u.y > 0 ? ziehen.y - (e.clientY - ziehen.py) / d / u.y : stand.y,
  });
});
const loslassen = () => { ziehen = null; kreis.classList.remove("zieht"); };
kreis.addEventListener("pointerup", loslassen);
kreis.addEventListener("pointercancel", loslassen);
kreis.addEventListener("wheel", e => {
  e.preventDefault();
  setze({ ...stand, zoom: stand.zoom * Math.exp(-e.deltaY * 0.0015) });
}, { passive: false });
kreis.addEventListener("keydown", e => {
  const schritt = e.shiftKey ? 0.05 : 0.01;
  const aktionen = {
    ArrowLeft: () => ({ x: stand.x - schritt }), ArrowRight: () => ({ x: stand.x + schritt }),
    ArrowUp: () => ({ y: stand.y - schritt }), ArrowDown: () => ({ y: stand.y + schritt }),
    "+": () => ({ zoom: stand.zoom + 0.05 }), "-": () => ({ zoom: stand.zoom - 0.05 }),
    m: () => ({ mirror: !stand.mirror }), M: () => ({ mirror: !stand.mirror }),
  };
  if (!aktionen[e.key]) return;
  e.preventDefault();
  setze({ ...stand, ...aktionen[e.key]() });
});

// Regler und Knöpfe
el("mirror").addEventListener("change", e => setze({ ...stand, mirror: e.target.checked }));
for (const k of ["zoom", "x", "y"]) {
  el(k).addEventListener("input", e => setze({ ...stand, [k]: parseFloat(e.target.value) }));
}
el("zuruecksetzen").addEventListener("click", () => { setze(gespeichert); status(""); });
el("standard").addEventListener("click", () => setze(STANDARD));
el("speichern").addEventListener("click", async () => {
  el("speichern").disabled = true;
  try {
    const antwort = await fetch("/api/foto/speichern", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Token": TOKEN },
      body: JSON.stringify(gerundet(stand)),
    });
    const daten = await antwort.json();
    if (!antwort.ok) throw new Error(daten.fehler);
    gespeichert = { ...daten };
    zeige();
    status("Gespeichert. Der Stand davor liegt unter Entwürfe.", "ok");
  } catch (fehler) {
    zeige();
    status("Speichern fehlgeschlagen: " + fehler.message, "fehler");
  }
});
window.addEventListener("beforeunload", e => { if (!gleich(stand, gespeichert)) e.preventDefault(); });

// Start: Werte aus der Datei und Seitenverhältnis des Originalfotos
async function start() {
  try {
    const antwort = await fetch("/api/foto/optionen?t=" + encodeURIComponent(TOKEN));
    const daten = await antwort.json();
    if (!antwort.ok) throw new Error(daten.fehler);
    gespeichert = { ...daten };
    const bild = new Image();
    bild.src = "/api/foto/bild?t=" + encodeURIComponent(TOKEN);
    await bild.decode();
    seitenverhaeltnis = bild.naturalHeight / bild.naturalWidth;
    setze(gespeichert);
  } catch (fehler) {
    status("Laden fehlgeschlagen: " + fehler.message, "fehler");
  }
}
start();
