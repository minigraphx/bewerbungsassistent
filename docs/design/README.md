# Neugestaltung (MIN-369): Vorgaben für die Umsetzung

Hier liegen die Ergebnisse der Neugestaltung, damit die Umsetzung ohne Zugang zu den Claude-Artefakten möglich ist: Design System, Seiten mit ihren Zuständen, Textkatalog und die Entscheide. Wo `beschreibung.md` und die Entscheide in `texte.md` voneinander abweichen, gelten die Entscheide.

## Was hier liegt

| Pfad | Inhalt |
| --- | --- |
| `beschreibung.md`, `bilder/` | Der Auftrag an die Gestaltung und Bilder des heutigen Stands. |
| `system/README.md` | Regeln des Design Systems: Grundsätze, Ton, Farbe, Schrift, Abstände, Noten, Bewerbungsstand, Erweiterung, Zugänglichkeit. |
| `system/tokens.json` | Alle Werte (Farben hell und dunkel, Schrift, Abstände, Radien, Schatten, Breiten). Die Quelle für jeden Wert. |
| `system/tokens.css` | Dieselben Werte als CSS-Variablen, aus `tokens.json` erzeugt. |
| `system/components.css` | Die Bausteine als CSS-Klassen, nur mit Variablen aus `tokens.css`. |
| `system/bausteine/<Name>/` | Pro Baustein eine Anleitung (`README.md`) und das Markup als Beispiel (`vorschau.html`). |
| `texte.md` | Alle sichtbaren Texte in Sie- und Du-Form, Regeln für die Anrede, Entscheide für die Umsetzung. |
| `abgleich.md` | Wo die App vom Design abweicht und was davon auf einen Entscheid wartet. |
| `entwurf/*.jpg` | Bilder aller Zeichenflächen, gerendert am 05.11.2026 (Tabelle unten). |
| `seiten/*.dc.html` | Quellen der Zeichenflächen. Sie laufen nur in der Zeichenfläche (Format von Claude Design) und dienen als Referenz für Aufbau, Zustände und Texte. |

Originale, privat für das Konto des Projekts: [Design System](https://claude.ai/artifact/YRZfoh86amQ1SiGFZopzBs), [Zeichenflächen](https://claude.ai/artifact/9XMb7JTKoWzuyngdwyzemR), [Textkatalog](https://claude.ai/artifact/2vVWbr5YyJ56psyLa1Zjda).

## Entscheide in Kürze

Ausführlich in `texte.md`, Abschnitt «Entscheide für die Umsetzung».

1. Der erste Schritt der Einrichtung fragt: Stelle oder Lehrstelle, bei Stellen die Anrede (Sie als Vorgabe, oder du), und ob die Person beim RAV gemeldet ist. Meine Angaben zeigt die Wahl und lässt sie ändern.
2. Drei Textsätze: Stelle mit Sie, Stelle mit du, Lehrstelle mit du. Das Anschreiben an die Firma bleibt immer in der Sie-Form. Die Anweisungen an die KI übernehmen die gewählte Anrede.
3. Job-Room, RAV-Erinnerung und RAV-Zeile erscheinen nur bei «RAV: ja», in beiden Zweigen. Ohne RAV folgt nach dem Versand «Antwort abwarten».
4. Eigener API-Schlüssel und Claude-Abo gibt es in beiden Zweigen.
5. Bei Lehrstellen heisst es «Lehrbetrieb» statt «Firma».
6. «du» wird klein geschrieben, ausser am Satzanfang.
7. Die Formularleiste der Erweiterung ist immer dunkel. Sie liegt unten und lässt sich nach oben setzen; die Seite rückt dabei, nichts wird verdeckt.

## Umsetzung in Schritten

Jeder Schritt ein eigener Pull Request.

1. **Gestaltungsgrundlage:** `bewerbungen/seiten/stil.css` aus `system/tokens.css` und `system/components.css` neu aufbauen; DM Sans aus `lebenslauf/fonts/` mit der App ausliefern; `onboarding/src/style.css` und `erweiterung/popup.css` auf dieselben Werte bringen.
2. **Einrichtung:** Schritt «Gesucht» mit Stelle oder Lehrstelle, Anrede und RAV; die drei Textsätze anlegen.
3. **Navigation und Übersicht:** «Das steht an» mit dem nächsten Schritt, Bewerbungsliste mit fünf Spalten.
4. **Bewerbung:** in sechs Schritten, die Angaben zur Stelle in der Seitenspalte.
5. **Suche:** Liste und Detailspalte, «Suche einstellen».
6. **Übrige Seiten:** Meine Angaben, Meine Dateien, Entwürfe, Inhalte, Foto, Fragen, Einstellungen.
7. **Browser-Erweiterung:** Formularleiste, Feldmarken, Popup, Erlaubnis-Seite.

## Hinweise für die Umsetzung

- **Hell und dunkel:** `tokens.css` schaltet über `[data-theme="dark"]`. Die App folgt der Systemeinstellung, also dieselben Werte unter `@media (prefers-color-scheme: dark)` setzen.
- **Schriften:** `tokens.css` lädt `fonts/DMSans-*.ttf` relativ zur CSS-Datei. Die Dateien liegen in `lebenslauf/fonts/` und müssen vom lokalen Server ausgeliefert werden; nichts von einem CDN (CSP).
- **Klassen:** Englisch, wie in `components.css`. Die Werte von `data-status` bleiben deutsch wie im Register.
- **Zeichenflächen:** `seiten/*.dc.html` nutzen für das Mockup Inline-Styles und eine Laufzeit der Zeichenfläche. In der App gehört das Layout in Klassen in `stil.css`, das Verhalten in eigene Skriptdateien (keine Inline-Skripte).
- **Erweiterung:** Die Formularleiste liegt in einem Shadow DOM und kann `tokens.css` nicht laden. Sie braucht die aufgelösten Werte als eigenes Stylesheet.
- **Daten:** Alle Namen, Firmen und Dokumente in Bildern und Seiten sind erfunden.

## Bilder der Zeichenflächen

| Bild | Seite und Zustand | Breite | Quelle |
| --- | --- | --- | --- |
| [main.jpg](entwurf/main.jpg) | Übersicht (Startseite) | 1280 px | [Main.dc.html](seiten/Main.dc.html) |
| [uebersicht-760.jpg](entwurf/uebersicht-760.jpg) | Übersicht · 760px | 760 px | [Uebersicht-760.dc.html](seiten/Uebersicht-760.dc.html) |
| [uebersicht-erststart.jpg](entwurf/uebersicht-erststart.jpg) | Übersicht · noch keine Angaben | 1280 px | [Uebersicht-Erststart.dc.html](seiten/Uebersicht-Erststart.dc.html) |
| [uebersicht-dunkel.jpg](entwurf/uebersicht-dunkel.jpg) | Übersicht · dunkel, Doppelbewerbung | 1280 px | [Uebersicht-Dunkel.dc.html](seiten/Uebersicht-Dunkel.dc.html) |
| [suche.jpg](entwurf/suche.jpg) | Stellen suchen | 1280 px | [Suche.dc.html](seiten/Suche.dc.html) |
| [suche-760.jpg](entwurf/suche-760.jpg) | Stellen suchen · 760px, ohne Erweiterung | 760 px | [Suche-760.dc.html](seiten/Suche-760.dc.html) |
| [suche-lehrstellen.jpg](entwurf/suche-lehrstellen.jpg) | Lehrstellen suchen (Du-Form), Suche läuft | 1280 px | [Suche-Lehrstellen.dc.html](seiten/Suche-Lehrstellen.dc.html) |
| [bewerbung.jpg](entwurf/bewerbung.jpg) | Bewerbung · Anschreiben | 1280 px | [Bewerbung.dc.html](seiten/Bewerbung.dc.html) |
| [bewerbung-760.jpg](entwurf/bewerbung-760.jpg) | Bewerbung · 760px, Prüfen | 760 px | [Bewerbung-760.dc.html](seiten/Bewerbung-760.dc.html) |
| [bewerbung-abschicken.jpg](entwurf/bewerbung-abschicken.jpg) | Bewerbung · Abschicken | 1280 px | [Bewerbung-Abschicken.dc.html](seiten/Bewerbung-Abschicken.dc.html) |
| [bewerbung-versendet.jpg](entwurf/bewerbung-versendet.jpg) | Bewerbung · nach dem Versand | 1280 px | [Bewerbung-Versendet.dc.html](seiten/Bewerbung-Versendet.dc.html) |
| [bewerbung-lehrstelle.jpg](entwurf/bewerbung-lehrstelle.jpg) | Bewerbung · Lehrstelle, Anschreiben | 1280 px | [Bewerbung-Lehrstelle.dc.html](seiten/Bewerbung-Lehrstelle.dc.html) |
| [bewerbung-lehrstelle-versendet.jpg](entwurf/bewerbung-lehrstelle-versendet.jpg) | Bewerbung · Lehrstelle ohne RAV, nach dem Versand | 1280 px | [Bewerbung-Lehrstelle-Versendet.dc.html](seiten/Bewerbung-Lehrstelle-Versendet.dc.html) |
| [angaben.jpg](entwurf/angaben.jpg) | Meine Angaben | 1280 px | [Angaben.dc.html](seiten/Angaben.dc.html) |
| [einrichtung-wahl.jpg](entwurf/einrichtung-wahl.jpg) | Einrichtung · Stelle oder Lehrstelle, Anrede, RAV | 1280 px | [Einrichtung-Wahl.dc.html](seiten/Einrichtung-Wahl.dc.html) |
| [einrichtung.jpg](entwurf/einrichtung.jpg) | Einrichtung · KI | 1280 px | [Einrichtung.dc.html](seiten/Einrichtung.dc.html) |
| [einrichtung-erweiterung.jpg](entwurf/einrichtung-erweiterung.jpg) | Einrichtung · Erweiterung | 1280 px | [Einrichtung-Erweiterung.dc.html](seiten/Einrichtung-Erweiterung.dc.html) |
| [dateien.jpg](entwurf/dateien.jpg) | Meine Dateien | 1280 px | [Dateien.dc.html](seiten/Dateien.dc.html) |
| [inhalte.jpg](entwurf/inhalte.jpg) | Inhalte als Text (für Geübte) | 1280 px | [Inhalte.dc.html](seiten/Inhalte.dc.html) |
| [entwuerfe.jpg](entwurf/entwuerfe.jpg) | Entwürfe und Versionen | 1280 px | [Entwuerfe.dc.html](seiten/Entwuerfe.dc.html) |
| [entwuerfe-vergleich.jpg](entwurf/entwuerfe-vergleich.jpg) | Entwürfe · Vergleich | 1280 px | [Entwuerfe-Vergleich.dc.html](seiten/Entwuerfe-Vergleich.dc.html) |
| [foto.jpg](entwurf/foto.jpg) | Foto | 1280 px | [Foto.dc.html](seiten/Foto.dc.html) |
| [fragen.jpg](entwurf/fragen.jpg) | Fragen an die KI | 1280 px | [Fragen.dc.html](seiten/Fragen.dc.html) |
| [einstellungen.jpg](entwurf/einstellungen.jpg) | Erweiterte Einstellungen | 1280 px | [Einstellungen.dc.html](seiten/Einstellungen.dc.html) |
| [erweiterung-popups.jpg](entwurf/erweiterung-popups.jpg) | Erweiterung · Popup in vier Zuständen | 1460 px | [Erweiterung-Popups.dc.html](seiten/Erweiterung-Popups.dc.html) |
| [erweiterung-formular.jpg](entwurf/erweiterung-formular.jpg) | Erweiterung · Formular einer Firma, ausgefüllt | 1280 px | [Erweiterung-Formular.dc.html](seiten/Erweiterung-Formular.dc.html) |
| [erweiterung-formular-oben.jpg](entwurf/erweiterung-formular-oben.jpg) | Erweiterung · Leiste oben | 1280 px | [Erweiterung-Formular-Oben.dc.html](seiten/Erweiterung-Formular-Oben.dc.html) |
| [erweiterung-leisten.jpg](entwurf/erweiterung-leisten.jpg) | Formularleiste · alle Zustände | 1280 px | [Erweiterung-Leisten.dc.html](seiten/Erweiterung-Leisten.dc.html) |
| [erweiterung-jobroom.jpg](entwurf/erweiterung-jobroom.jpg) | Erweiterung · Arbeitsbemühungen eintragen | 1280 px | [Erweiterung-JobRoom.dc.html](seiten/Erweiterung-JobRoom.dc.html) |
| [erweiterung-erlauben.jpg](entwurf/erweiterung-erlauben.jpg) | Erweiterung · Erlaubnis für eine weitere Seite | 1280 px | [Erweiterung-Erlauben.dc.html](seiten/Erweiterung-Erlauben.dc.html) |
| [webseite.jpg](entwurf/webseite.jpg) | Webseite der App, Startseite | 1280 px | [Webseite.dc.html](seiten/Webseite.dc.html) |

Weitere Zustände der Seiten (etwa leer, ohne KI, dunkel) sind in den Zeichenflächen über die Einstellungen jeder Seite wählbar und in `texte.md` beschrieben.

## Webseite

Entwurf der Webseite, von Andy am 7.11.2026 freigegeben (Original privat: [Zeichenfläche](https://claude.ai/artifact/H6U4oZS6efH9w3gDghpX2Q)). Die Seite stellt die App vor und führt zum Download, für Stellensuchende und Eltern von Lehrstellensuchenden.

- **Sprachwahl:** DE, EN und FR sind gestaltet, aber vorerst mit `display: none` ausgeblendet, bis die App weitere Sprachen kann.
- **Bilder:** dieselben wie im README, aus `docs/bilder/`, mit erfundenen Daten.
- **Logo:** `bewerbungen/seiten/as-logo.svg`, dieselbe Datei wie in der App, einfarbig, hell und dunkel nach der Systemeinstellung. Es ist von der AGPL ausgenommen (`docs/NOTICE`).
- **Anleitung:** Die Knöpfe „Anleitung“ zeigen in der fertigen Seite auf eine eigene Seite, gebaut aus `docs/installation.md`.
