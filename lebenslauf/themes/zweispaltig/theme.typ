// Theme "zweispaltig": Kopf mit Name und rundem Foto, darunter zwei Spalten,
// die unabhängig voneinander über die Seiten laufen.
// Masse nach dem Canva-Lebenslauf (Schriftgrössen über Textbreiten, Abstände über Zeilenpositionen gemessen).
#import "../common.typ": *

#let standard-stil = (
  farbe-text: rgb("#38495d"),
  farbe-linie: rgb("#38495d"),
  farbe-hintergrund: rgb("#fdfcfa"),
  schrift-titel: "Liberation Sans",
  schrift-text: "DM Sans",
  // Schriftgrössen
  groesse-text: 8.8pt,
  groesse-kontakt: 8.95pt,
  groesse-name: 40.6pt,
  groesse-label: 11.85pt,
  groesse-titel: 13.35pt,
  // Zeilenabstände (Typst: Abstand zwischen Zeilen zusätzlich zur Schrifthöhe)
  zeilen-text: 0.665em,
  zeilen-station-kopf: 0.81em,
  zeilen-name: 0.347em,
  zeilen-label: 0.7em,
  zeilen-kontakt: 0.79em,
  // Abstände zwischen Blöcken
  abstand-absatz: 0.665em,
  abstand-station: 1.76em,
  abstand-abschnitt: 2.1em,
  abstand-titel: 2.5em,
  abstand-kopf: 4.16em,
  // Seite, Kopf und Spalten
  rand: (left: 50.5pt, right: 50.5pt, top: 2.2cm, bottom: 1.6cm),
  fusszeile-abstand: 0.22cm,
  groesse-fusszeile: 8.95pt,
  breite-label: 10cm,
  label-umbruch-nach-strich: true,
  abstand-label: 1.12em,
  foto-groesse: 4.65cm,
  spaltenbreite-links: 47.5%,
  spaltenabstand: 0.6cm,
  listen-einzug: 0.6em,
  listen-text-einzug: 0.8em,
  // Reihenfolge der Abschnitte je Spalte
  links: ("profil", "projekte", "faehigkeiten", "lehre", "sprachen", "weitere-projekte", "interessen"),
  rechts: ("erfahrung", "bildung"),
)

#let lebenslauf(cv, sprache: "de", stand: none, stil: (:)) = {
  let s = standard-stil + stil
  let b = beschriftungen.at(sprache)
  let basics = cv.at("basics", default: (:))
  let name = basics.at("name", default: "")

  set document(title: name + " – " + basics.at("label", default: ""), author: name)
  set page(
    paper: "a4",
    margin: s.rand,
    fill: s.farbe-hintergrund,
    footer-descent: s.fusszeile-abstand,
    footer: align(center, {
      line(length: 6.6cm, stroke: 0.9pt + s.farbe-linie)
      v(-4pt)
      text(size: s.groesse-fusszeile, fill: s.farbe-text, font: s.schrift-text, if stand != none { name + " - " + stand } else { name })
    }),
  )
  set text(font: s.schrift-text, size: s.groesse-text, fill: s.farbe-text, lang: sprache)
  set par(leading: s.zeilen-text, spacing: s.abstand-absatz)
  // Listenpunkte im Abstand normaler Zeilen
  set list(marker: [•], indent: s.listen-einzug, body-indent: s.listen-text-einzug, spacing: s.zeilen-text)

  // Titel in voller Grösse; ist er breiter als die Spalte, wird er auf Spaltenbreite verkleinert
  let titel-block(titel) = block(below: s.abstand-titel, sticky: true, layout(platz => {
    let t(groesse) = text(font: s.schrift-titel, weight: 700, size: groesse)[#upper(titel)]
    let breite = measure(t(s.groesse-titel)).width
    t(if breite > platz.width { s.groesse-titel * (platz.width / breite) } else { s.groesse-titel })
    v(-6pt)
    line(length: 100%, stroke: 1.3pt + s.farbe-linie)
  }))

  // Ein Abschnitt besteht aus Einträgen; läuft er auf die nächste Seite, wiederholt sich der Titel mit "(Fortsetzung)".
  let abschnitt(id, titel, items, abstand) = block(breakable: true, below: s.abstand-abschnitt, {
    titel-block(titel)
    eintraege(id, items, titel-block(titel + " (" + b.fortsetzung + ")"), abstand: abstand)
  })

  let stichpunkte(e) = {
    let hs = e.at("highlights", default: ()).map(text-von).filter(t => t != "")
    if hs.len() > 0 { list(..hs.map(t => [#t])) }
  }

  // Station: Kopfzeilen (Titel, Firma, Zeitraum) etwas luftiger als die Stichpunkte
  let station(e, org-key: "name") = {
    block(spacing: s.zeilen-station-kopf, {
      set par(leading: s.zeilen-station-kopf)
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
    })
    stichpunkte(e)
  }

  let punkte(xs) = (xs.map(x => list(x)), s.zeilen-text)

  let projekte(gruppe) = {
    let ps = cv.at("projects", default: ()).filter(p => p.at("group", default: "main") == gruppe)
    ps.map(p => {
      let d = feld(p, "description")
      [#p.name#if d != none [ — #d]]
    })
  }

  // Jeder Abschnitt liefert (Einträge, Abstand); leere Einträge -> Abschnitt entfällt
  let abschnitte = (
    profil: () => {
      let t = feld(basics, "summary")
      (if t != none { ([#t],) } else { () }, s.abstand-station)
    },
    projekte: () => {
      let (items, abstand) = punkte(projekte("main"))
      if items.len() == 0 { return ((), abstand) }
      let gh = basics.at("profiles", default: ()).filter(p => lower(p.at("network", default: "")) == "github")
      if gh.len() > 0 { items.push((inhalt: [#b.projekte-auf: #gh.first().url], abstand: s.abstand-absatz)) }
      (items, abstand)
    },
    weitere-projekte: () => punkte(projekte("more")),
    faehigkeiten: () => punkte(cv.at("skills", default: ()).map(k => {
      let kw = k.at("keywords", default: ())
      if kw.len() > 0 [#k.name: #kw.join(", ")] else [#k.name]
    })),
    lehre: () => (cv.at("teaching", default: ()).map(e => station(e)), s.abstand-station),
    sprachen: () => punkte(cv.at("languages", default: ()).map(x => [#x.language – #x.at("fluency", default: "")])),
    interessen: () => punkte(cv.at("interests", default: ()).map(x => [#x.name])),
    erfahrung: () => (cv.at("work", default: ()).map(e => station(e)), s.abstand-station),
    bildung: () => punkte((cv.at("education", default: ()) + cv.at("certificates", default: ())).map(e => [#bildung-text(e, b)])),
  )

  let spalte(keys) = {
    for k in keys {
      let (items, abstand) = (abschnitte.at(k))()
      if items.len() > 0 { abschnitt(k, b.at(k), items, abstand) }
    }
  }

  // Kopf
  let foto = feld(basics, "image")
  let teile = name.split(" ")
  let kopf-links = {
    text(font: s.schrift-titel, weight: 700, size: s.groesse-name)[
      #set par(leading: s.zeilen-name)
      #teile.first() \ #teile.slice(1).join(" ")
    ]
    v(0.9em)
    if feld(basics, "label") != none {
      block(width: s.breite-label, text(weight: 700, size: s.groesse-label)[
        #set par(leading: s.zeilen-label)
        #let teile-label = basics.label.split(" – ")
        #if s.label-umbruch-nach-strich and teile-label.len() > 1 [
          #upper(teile-label.first() + " –") \ #upper(teile-label.slice(1).join(" – "))
        ] else [#upper(basics.label)]
      ])
      v(s.abstand-label)
    }
    let ort = basics.at("location", default: (:))
    let zeilen = (
      ((feld(ort, "address"), (feld(ort, "postalCode"), feld(ort, "city")).filter(x => x != none).join(" ")).filter(x => x != none and x != "").join(" · ")),
      ((feld(basics, "phone"), feld(basics, "email")).filter(x => x != none).join(" · ")),
      feld(basics, "url"),
      (basics.at("details", default: ())).join(" · "),
    ).filter(x => x != none and x != "")
    text(size: s.groesse-kontakt)[
      #set par(leading: s.zeilen-kontakt)
      #for z in zeilen [#z \ ]
    ]
  }
  grid(
    columns: (1fr, auto),
    align: (left + top, right + horizon),
    kopf-links,
    if foto != none {
      foto-rund(foto, s.foto-groesse, feld(basics, "x-image"))
    },
  )
  v(s.abstand-kopf)

  grid(
    columns: (s.spaltenbreite-links, 1fr),
    column-gutter: s.spaltenabstand,
    spalte(s.links),
    spalte(s.rechts),
  )
}
