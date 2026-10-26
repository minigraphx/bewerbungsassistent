// Theme "zweispaltig": Kopf mit Name und rundem Foto, darunter zwei Spalten,
// die unabhängig voneinander über die Seiten laufen. Ab Seite 2 steht die Fortsetzung der
// Hauptspalte links (gedruckt liest man nach Seite 1 unten rechts oben links weiter).
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
  // Ab Seite 2 die rechte Spalte (Berufserfahrung, Bildung) links setzen; false = Spalten bleiben, wo sie sind
  fortsetzung-links: true,
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
  // `von`/`bis` setzen nur einen Teil der Einträge (Aufteilung auf Seiten); ab `von` > 0 ohne eigenen Titel.
  let abschnitt(a, von: 0, bis: none, pruefen: true) = {
    let bis = if bis == none { a.items.len() } else { bis }
    let titel = b.at(a.key)
    if bis > von {
      block(breakable: true, below: s.abstand-abschnitt, {
        if von == 0 { titel-block(titel) }
        eintraege(a.key, a.items.slice(von, bis), titel-block(titel + " (" + b.fortsetzung + ")"),
          abstand: a.abstand, start: von, pruefen: pruefen)
      })
    }
  }

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

  // Abschnitte einer Spalte mit ihren Einträgen; leere entfallen
  let spalten-daten(keys) = keys.map(k => {
    let (items, abstand) = (abschnitte.at(k))()
    (key: k, items: items, abstand: abstand)
  }).filter(a => a.items.len() > 0)

  // Teile einer Spalte: (Abschnitt, von, bis)
  let spalte(teile, pruefen: true) = for (a, von, bis) in teile { abschnitt(a, von: von, bis: bis, pruefen: pruefen) }
  let ganz(abschnitte) = abschnitte.map(a => (a, 0, a.items.len()))

  // Die ersten k Einträge einer Spalte (über alle Abschnitte gezählt) und der Rest
  let aufteilen(abschnitte, k) = {
    let (vorne, hinten, rest) = ((), (), k)
    for a in abschnitte {
      let n = a.items.len()
      let hier = calc.max(0, calc.min(n, rest))
      if hier > 0 { vorne.push((a, 0, hier)) }
      if hier < n { hinten.push((a, hier, n)) }
      rest -= hier
    }
    (vorne, hinten)
  }

  // Wie viele Einträge passen in die Höhe? Einträge sind unteilbar, das Messen ist also exakt.
  let passend(abschnitte, breite, hoehe) = {
    let k = abschnitte.map(a => a.items.len()).sum(default: 0)
    while k > 0 and measure(block(width: breite, spalte(aufteilen(abschnitte, k).first(), pruefen: false))).height > hoehe {
      k -= 1
    }
    k
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
  let kopf = grid(
    columns: (1fr, auto),
    align: (left + top, right + horizon),
    kopf-links,
    if foto != none {
      foto-rund(foto, s.foto-groesse, feld(basics, "x-image"))
    },
  )
  kopf
  v(s.abstand-kopf)

  let links = spalten-daten(s.links)
  let rechts = spalten-daten(s.rechts)
  if not s.fortsetzung-links {
    grid(columns: (s.spaltenbreite-links, 1fr), column-gutter: s.spaltenabstand, spalte(ganz(links)), spalte(ganz(rechts)))
    return
  }

  // Seite 1 ausmessen: was passt, bleibt; der Rest kommt ab Seite 2 mit vertauschten Spalten.
  context {
    let breite = page.width - s.rand.left - s.rand.right
    let frei = (page.height - s.rand.top - s.rand.bottom - measure(block(width: breite, kopf)).height
      - measure(block(height: s.abstand-kopf)).height - 1pt)
    let breite-links = breite * s.spaltenbreite-links
    let breite-rechts = breite - breite-links - s.spaltenabstand
    let (links-1, links-2) = aufteilen(links, passend(links, breite-links, frei))
    let (rechts-1, rechts-2) = aufteilen(rechts, passend(rechts, breite-rechts, frei))
    grid(columns: (breite-links, breite-rechts), column-gutter: s.spaltenabstand, spalte(links-1), spalte(rechts-1))
    if rechts-2.len() > 0 {
      pagebreak(weak: true)
      grid(columns: (breite-rechts, breite-links), column-gutter: s.spaltenabstand, spalte(rechts-2), spalte(links-2))
    } else if links-2.len() > 0 {
      pagebreak(weak: true)
      grid(columns: (breite-links, breite-rechts), column-gutter: s.spaltenabstand, spalte(links-2), [])
    }
  }
}
