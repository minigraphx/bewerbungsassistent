// Gemeinsame Hilfsfunktionen für alle Themes.
// Daten folgen JSON Resume (https://jsonresume.org/schema) mit wenigen Erweiterungen,
// siehe README.

#let beschriftungen = (
  de: (
    profil: "Profil",
    erfahrung: "Berufserfahrung",
    projekte: "Projekte",
    weitere-projekte: "Weitere Projekte",
    faehigkeiten: "Fähigkeiten",
    lehre: "Lehre & Training",
    sprachen: "Sprachen",
    interessen: "Interessen",
    bildung: "Bildung & Weiterbildung",
    projekte-auf: "Projekte auf",
    fortsetzung: "Fortsetzung",
    heute: "heute",
    monate: ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
             "August", "September", "Oktober", "November", "Dezember"),
  ),
  en: (
    profil: "Profile",
    erfahrung: "Experience",
    projekte: "Projects",
    weitere-projekte: "Further projects",
    faehigkeiten: "Skills",
    lehre: "Teaching & training",
    sprachen: "Languages",
    interessen: "Interests",
    bildung: "Education & training",
    projekte-auf: "Projects on",
    fortsetzung: "continued",
    heute: "present",
    monate: ("January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"),
  ),
)

// Feld lesen, fehlend oder leer -> none
#let feld(d, key) = {
  if type(d) != dictionary { return none }
  let v = d.at(key, default: none)
  if v == "" or v == () { none } else { v }
}

// Stichpunkt kann Text oder (text: ..., tags: ...) sein
#let text-von(x) = if type(x) == dictionary { x.at("text", default: "") } else { str(x) }

// "2022-06" -> "Juni 2022", "2018" -> "2018"
#let datum(d, b) = {
  if d == none or d == "" { return b.heute }
  let teile = str(d).split("-")
  if teile.len() == 1 { teile.at(0) } else {
    b.monate.at(int(teile.at(1)) - 1) + " " + teile.at(0)
  }
}

#let nur-jahre(e) = {
  let s = feld(e, "startDate")
  let en = feld(e, "endDate")
  (s == none or str(s).split("-").len() == 1) and (en == none or str(en).split("-").len() == 1)
}

#let zeitraum(e, b) = {
  let anzeige = feld(e, "x-display")
  if anzeige != none { return anzeige }
  let s = feld(e, "startDate")
  let en = feld(e, "endDate")
  if s == none { return none }
  if en != none and str(en) == str(s) { return datum(s, b) }
  datum(s, b) + " – " + datum(en, b)
}

// Bildung/Zertifikat als ein Satz; "text" überschreibt die Zusammensetzung
#let bildung-text(e, b) = {
  let t = feld(e, "text")
  if t != none { return t }
  let teile = ()
  let titel = (feld(e, "studyType"), feld(e, "area"), feld(e, "name")).filter(x => x != none).join(" ")
  if titel != none and titel != "" { teile.push(titel) }
  for k in ("institution", "issuer") { if feld(e, k) != none { teile.push(feld(e, k)) } }
  let z = zeitraum(e, b)
  if z != none { teile.push(z) } else if feld(e, "date") != none { teile.push(datum(feld(e, "date"), b)) }
  teile.join(", ")
}

// Rundes Foto. Optionen aus basics.x-image (geprüft in build.py):
// mirror – an der senkrechten Achse spiegeln; zoom – Vergrösserung ab 1;
// x, y – Bildausschnitt von 0 (links/oben) bis 1 (rechts/unten), Standard Mitte.
#let foto-rund(pfad, groesse, optionen) = {
  let o = if type(optionen) == dictionary { optionen } else { (:) }
  let zoom = o.at("zoom", default: 1)
  let x = o.at("x", default: 0.5)
  let y = o.at("y", default: 0.5)
  box(width: groesse, height: groesse, radius: 50%, clip: true, context {
    // Bild so skalieren, dass es den Kreis in beiden Richtungen mindestens füllt
    let probe = measure(image(pfad, width: groesse))
    let m = if probe.height >= groesse {
      measure(image(pfad, width: groesse * zoom))
    } else {
      measure(image(pfad, height: groesse * zoom))
    }
    // Feste Grösse und eigener Rahmen: sonst begrenzt Typst das Bild auf den Kreis,
    // und das Spiegeln dreht um die Kreismitte statt um die Bildmitte.
    let bild = image(pfad, width: m.width, height: m.height, fit: "stretch")
    let inhalt = box(width: m.width, height: m.height, if o.at("mirror", default: false) { scale(x: -100%, bild) } else { bild })
    place(top + left, dx: -(m.width - groesse) * x, dy: -(m.height - groesse) * y, inhalt)
  })
}

// Einträge eines Abschnitts, die über Seiten laufen dürfen. Landet ein Eintrag auf einer
// anderen Seite als sein Vorgänger, steht davor `fortsetzung` (z.B. "Berufserfahrung (Fortsetzung)").
// Jeder Eintrag ist ein unteilbarer Block. Ein Eintrag kann statt Inhalt auch
// (inhalt: ..., abstand: ...) sein, um den Abstand zum Vorgänger festzulegen.
// Der erste Eintrag hat oben keinen eigenen Abstand, es gilt der des Titels.
// `start`: Nummer des ersten Eintrags, wenn nur ein Teil des Abschnitts gesetzt wird (Fortsetzung);
// `pruefen: false` lässt die Seitenprüfung weg (zum Messen, wo es keine Seite gibt).
#let eintraege(id, items, fortsetzung, abstand: 0pt, start: 0, pruefen: true) = {
  for (i, item) in items.enumerate() {
    let (inhalt, oben) = if type(item) == dictionary { (item.inhalt, item.abstand) } else { (item, abstand) }
    let nr = start + i
    block(breakable: false, above: if i == 0 { 0pt } else { oben }, below: abstand, {
      [#metadata((abschnitt: id, nr: nr))<lebenslauf-eintrag>]
      if nr > 0 and pruefen {
        context {
          let vorher = query(<lebenslauf-eintrag>).filter(m => m.value == (abschnitt: id, nr: nr - 1))
          if vorher.len() > 0 and vorher.first().location().page() != here().page() { fortsetzung }
        }
      }
      inhalt
    })
  }
}
