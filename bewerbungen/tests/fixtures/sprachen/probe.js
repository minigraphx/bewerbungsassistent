"use strict";
// Fixture for the language check (#414): every text that speaks to the person is in the fixture catalog.
const frist = document.getElementById("frist");
frist.textContent = Texte.t("Abgabe bis {datum}", { datum: "20.11.2026" });
const label = Texte.text("fragen.label", "stelle-sie");
if (frist.dataset.status === "Gespräch") frist.className = "marke-status";
const probe = "Nur für Entwickler sichtbar"; // kein UI-Text
