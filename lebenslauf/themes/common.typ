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
