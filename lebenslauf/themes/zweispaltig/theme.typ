// Theme "zweispaltig": Kopf mit Name und rundem Foto, darunter zwei Spalten,
// die unabhängig voneinander über die Seiten laufen.
#import "../common.typ": *

#let standard-stil = (
  farbe-text: rgb("#38495d"),
  farbe-linie: rgb("#38495d"),
  farbe-hintergrund: rgb("#fdfcfa"),
  schrift-titel: "Liberation Sans",
  schrift-text: "DM Sans",
  groesse-text: 8.8pt,
  // Reihenfolge der Abschnitte je Spalte
  links: ("profil", "projekte", "faehigkeiten", "lehre", "sprachen", "weitere-projekte", "interessen"),
  rechts: ("erfahrung", "bildung"),
  spaltenbreite-links: 41%,
)

#let lebenslauf(cv, sprache: "de", stand: none, stil: (:)) = {
  let s = standard-stil + stil
  let b = beschriftungen.at(sprache)
  let basics = cv.at("basics", default: (:))
  let name = basics.at("name", default: "")

  set document(title: name + " – " + basics.at("label", default: ""), author: name)
  set page(
    paper: "a4",
    margin: (left: 1.6cm, right: 1.6cm, top: 1.3cm, bottom: 1.9cm),
    fill: s.farbe-hintergrund,
    footer: align(center, {
      line(length: 6.6cm, stroke: 0.9pt + s.farbe-linie)
      v(-4pt)
      text(size: 7.5pt, fill: s.farbe-text, font: s.schrift-text, if stand != none { name + " - " + stand } else { name })
    }),
  )
  set text(font: s.schrift-text, size: s.groesse-text, fill: s.farbe-text, lang: sprache)
  set par(leading: 0.5em, spacing: 0.65em)
  set list(marker: [•], indent: 0.5em, body-indent: 0.5em, spacing: 0.42em)

  let abschnitt(titel, inhalt) = block(breakable: true, below: 1.7em, {
    block(below: 0.9em, sticky: true, {
      text(font: s.schrift-titel, weight: 700, size: 12.5pt)[#upper(titel)]
      v(-6pt)
      line(length: 100%, stroke: 1.3pt + s.farbe-linie)
    })
    inhalt
  })

  let stichpunkte(e) = {
    let hs = e.at("highlights", default: ()).map(text-von).filter(t => t != "")
    if hs.len() > 0 { list(..hs.map(t => [#t])) }
  }

  let station(e, org-key: "name") = block(breakable: false, below: 1em, {
    let titel = feld(e, "position")
    if titel != none { text(weight: 700)[#titel]; linebreak() }
    let org = (feld(e, org-key), feld(e, "location")).filter(x => x != none).join(", ")
    let z = zeitraum(e, b)
    if nur-jahre(e) and z != none {
      [#org · #z]
    } else {
      [#org]
      if z != none { linebreak(); [#z] }
    }
    let hs = e.at("highlights", default: ())
    if hs.len() > 0 { v(0.15em); stichpunkte(e) }
  })

  let projekte(gruppe) = {
    let ps = cv.at("projects", default: ()).filter(p => p.at("group", default: "main") == gruppe)
    if ps.len() == 0 { return none }
    list(..ps.map(p => {
      let d = feld(p, "description")
      [#p.name#if d != none [ — #d]]
    }))
  }

  let abschnitte = (
    profil: () => {
      let t = feld(basics, "summary")
      if t != none { [#t] }
    },
    projekte: () => {
      let l = projekte("main")
      if l == none { return none }
      l
      let gh = basics.at("profiles", default: ()).filter(p => lower(p.at("network", default: "")) == "github")
      if gh.len() > 0 { [#b.projekte-auf: #gh.first().url] }
    },
    weitere-projekte: () => projekte("more"),
    faehigkeiten: () => {
      let sk = cv.at("skills", default: ())
      if sk.len() == 0 { return none }
      list(..sk.map(k => {
        let kw = k.at("keywords", default: ())
        if kw.len() > 0 [#k.name: #kw.join(", ")] else [#k.name]
      }))
    },
    lehre: () => {
      let t = cv.at("teaching", default: ())
      if t.len() == 0 { return none }
      for e in t { station(e) }
    },
    sprachen: () => {
      let l = cv.at("languages", default: ())
      if l.len() == 0 { return none }
      list(..l.map(x => [#x.language – #x.at("fluency", default: "")]))
    },
    interessen: () => {
      let l = cv.at("interests", default: ())
      if l.len() == 0 { return none }
      list(..l.map(x => [#x.name]))
    },
    erfahrung: () => {
      let w = cv.at("work", default: ())
      if w.len() == 0 { return none }
      for e in w { station(e) }
    },
    bildung: () => {
      let l = cv.at("education", default: ()) + cv.at("certificates", default: ())
      if l.len() == 0 { return none }
      list(..l.map(e => [#bildung-text(e, b)]))
    },
  )

  let spalte(keys) = {
    for k in keys {
      let inhalt = (abschnitte.at(k))()
      if inhalt != none { abschnitt(b.at(k), inhalt) }
    }
  }

  // Kopf
  let foto = feld(basics, "image")
  let teile = name.split(" ")
  let kopf-links = {
    text(font: s.schrift-titel, weight: 700, size: 34pt)[
      #set par(leading: 0.15em)
      #teile.first() \ #teile.slice(1).join(" ")
    ]
    v(0.9em)
    if feld(basics, "label") != none {
      block(width: 9cm, text(weight: 700, size: 10pt)[#upper(basics.label)])
      v(0.5em)
    }
    let ort = basics.at("location", default: (:))
    let zeilen = (
      ((feld(ort, "address"), (feld(ort, "postalCode"), feld(ort, "city")).filter(x => x != none).join(" ")).filter(x => x != none and x != "").join(" · ")),
      ((feld(basics, "phone"), feld(basics, "email")).filter(x => x != none).join(" · ")),
      feld(basics, "url"),
      (basics.at("details", default: ())).join(" · "),
    ).filter(x => x != none and x != "")
    set par(leading: 0.55em)
    for z in zeilen [#z \ ]
  }
  grid(
    columns: (1fr, auto),
    align: (left + top, right + horizon),
    kopf-links,
    if foto != none {
      box(width: 4.1cm, height: 4.1cm, radius: 50%, clip: true, image(foto, width: 100%, height: 100%, fit: "cover"))
    },
  )
  v(1.6em)

  grid(
    columns: (s.spaltenbreite-links, 1fr),
    column-gutter: 1.1cm,
    spalte(s.links),
    spalte(s.rechts),
  )
}
