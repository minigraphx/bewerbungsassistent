// Theme "einspaltig": schlicht, eine Spalte, kein Foto. Gut für Bewerbungssoftware (ATS).
#import "../common.typ": *
#import "../page-fill.typ": spacing, leading, body-size, part-start, part-end

#let standard-stil = (
  farbe-akzent: rgb("#2f5d4a"),
  schrift: "DM Sans",
  groesse-text: 9.5pt,
  reihenfolge: ("profil", "erfahrung", "lehre", "projekte", "faehigkeiten", "bildung", "sprachen", "interessen"),
)

#let lebenslauf(cv, sprache: "de", stand: none, stil: (:)) = {
  let s = standard-stil + stil
  let b = beschriftungen-fuer(cv, sprache)
  let basics = cv.at("basics", default: (:))
  let name = basics.at("name", default: "")
  let (f, lf) = (spacing("cv"), leading("cv"))

  set document(title: name, author: name)
  set page(paper: "a4", margin: 2cm, footer: align(right, text(size: 7.5pt, if stand != none { name + ", " + stand } else { name })))
  set text(font: s.schrift, size: body-size(s.groesse-text, "cv"), lang: sprache)
  set par(leading: 0.55em * lf, spacing: 0.7em * f)
  set list(marker: [–], indent: 0.3em, spacing: 0.45em * f)

  let titel(t) = block(above: 1.3em * f, below: 0.6em * f, sticky: true,
    text(weight: 700, size: 11pt, fill: s.farbe-akzent)[#upper(t)])

  let station(e) = block(breakable: false, below: 0.8em * f, {
    grid(columns: (1fr, auto),
      text(weight: 700)[#feld(e, "position") · #(feld(e, "name"), feld(e, "location")).filter(x => x != none).join(", ")],
      [#zeitraum(e, b)])
    let hs = e.at("highlights", default: ()).map(text-von)
    if hs.len() > 0 { list(..hs.map(t => [#t])) }
  })

  let abschnitte = (
    profil: () => { let t = feld(basics, "summary"); if t != none [#t] },
    erfahrung: () => { let w = cv.at("work", default: ()); if w.len() > 0 { for e in w { station(e) } } },
    lehre: () => { let w = cv.at("teaching", default: ()); if w.len() > 0 { for e in w { station(e) } } },
    projekte: () => {
      let ps = cv.at("projects", default: ())
      if ps.len() > 0 { list(..ps.map(p => [#p.name#if feld(p, "description") != none { " – " + p.description }])) }
    },
    faehigkeiten: () => {
      let sk = cv.at("skills", default: ())
      if sk.len() > 0 { list(..sk.map(k => [#k.name: #k.at("keywords", default: ()).map(stichwort).join(", ")])) }
    },
    bildung: () => {
      let l = cv.at("education", default: ()) + cv.at("certificates", default: ())
      if l.len() > 0 { list(..l.map(e => [#bildung-text(e, b)])) }
    },
    sprachen: () => {
      let l = cv.at("languages", default: ())
      if l.len() > 0 [#l.map(x => x.language + " (" + x.at("fluency", default: "") + ")").join(", ")]
    },
    interessen: () => {
      let l = cv.at("interests", default: ())
      if l.len() > 0 [#l.map(x => x.name).join(", ")]
    },
  )

  part-start("cv")
  text(size: 22pt, weight: 700)[#name]
  linebreak()
  if feld(basics, "label") != none { text(size: 11pt, fill: s.farbe-akzent)[#basics.label]; linebreak() }
  let ort = basics.at("location", default: (:))
  text(size: 8.5pt, (
    (feld(ort, "address"), feld(ort, "postalCode"), feld(ort, "city")).filter(x => x != none).join(" "),
    feld(basics, "phone"), feld(basics, "email"), feld(basics, "url"),
  ).filter(x => x != none and x != "").join(" · "))

  // Sections without stations are short lists or a paragraph: up to five lines they stay together (G50)
  let zeilen(k) = (
    projekte: cv.at("projects", default: ()).len(),
    faehigkeiten: cv.at("skills", default: ()).len(),
    bildung: (cv.at("education", default: ()) + cv.at("certificates", default: ())).len(),
  ).at(k, default: 1)
  let kurz = k => k in ("projekte", "faehigkeiten", "bildung", "sprachen", "interessen") and zeilen(k) <= 5
  for k in s.reihenfolge {
    let inhalt = (abschnitte.at(k))()
    if inhalt != none {
      // The block takes the title's space above, which a title at the start of a block would lose
      if kurz(k) { block(breakable: false, above: 1.3em * f, { titel(b.at(k)); inhalt }) } else { titel(b.at(k)); inhalt }
    }
  }
  part-end("cv")
}
