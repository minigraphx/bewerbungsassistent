// Design "Register" (docs/design/dossier.md, design C): ordered like a file. Tabs per part at the right
// edge, the cover is also the table of contents, attachments at the end. No icons: words carry meaning.
// Marks, tabs and the CV part.
#import "../common.typ": *
#import "../tokens.typ": space, radius
#import "../dossier.typ": colours-for, labels-for, level-marker, current
#import "../zeichen.typ": own-mark, chosen-mark, mark-marker

#let words = (
  de: (
    teil: "Teil",
    inhalt: "Inhalt",
    seite: "Seite",
    bewerbung: "Bewerbung",
    beilagen: "Beilagen",
    referenzen: "Referenzen",
    nr: "Nr.",
    dokument: "Dokument",
    datum: "Datum",
    zeitraum: "Zeitraum",
    dauer: "Dauer",
    station: "Station",
    pensum: "Pensum",
    unternehmen: "Unternehmen",
    referenz: "Referenz",
    auf-anfrage: "Auf Anfrage.",
    ohne-angabe: "ohne Angabe",
    stufen: ("Einstieg", "Grundlagen", "solide", "gut", "sehr gut", "Expertise"),
  ),
  en: (
    teil: "Part",
    inhalt: "Contents",
    seite: "Page",
    bewerbung: "Application",
    beilagen: "Attachments",
    referenzen: "References",
    nr: "No.",
    dokument: "Document",
    datum: "Date",
    zeitraum: "Period",
    dauer: "Duration",
    station: "Position",
    pensum: "Workload",
    unternehmen: "Company",
    referenz: "Reference",
    auf-anfrage: "On request.",
    ohne-angabe: "not stated",
    stufen: ("Entry", "Basics", "Solid", "Good", "Very good", "Expert"),
  ),
)

#let cefr = ("A1", "A2", "B1", "B2", "C1", "C2")

#let sizes = (initials: 28pt, position: 20pt, name: 26pt, section: 12pt, body: 9.5pt, small: 8pt)
#let page-margin = (left: space.space-7, right: space.space-7 + space.space-4, top: space.space-7,
  bottom: space.space-7 + space.space-3)

#let words-for(d) = words.at(d.language)

// The parts that get a tab, in order: letter, CV, and the optional pages that have content. In a dossier with a
// design per page, Beilagen and Referenzen exist only when the optional pages are those of Register.
#let own-pages(d) = d.at("designs", default: (:)).at("pages", default: "dossier-register") == "dossier-register"
#let tab-parts(d) = ("anschreiben", "lebenslauf") + (if own-pages(d) and d.pages.at("attachments", default: ()).len() > 0 { ("beilagen",) } else { () }) + (if own-pages(d) and d.cv.at("references", default: ()).len() > 0 { ("referenzen",) } else { () })

// A label drawn as glyph outlines (dossier.py renders it) and marked as a PDF artifact,
// so text extraction does not read the tabs into the text
#let outlined(path, colour) = pdf.artifact(image(bytes(read(path).replace("#010203", colour.to-hex())), format: "svg"))

// Tabs at the right edge, reaching 12 pt beyond it; the current part in the accent colour.
// `labels: false` (single files) draws only the tab of the current part, without a label.
#let tabs(d, c, current, labels: true) = {
  let parts = tab-parts(d)
  let outlined-labels = d.at("outlined", default: (:))
  for (i, part) in parts.enumerate() {
    let active = part == current
    if labels or active {
      place(top + right, dx: 12pt, dy: 140pt + i * 96pt, rect(
        width: 48pt,
        height: 84pt,
        radius: radius.radius-md,
        fill: if active { c.accent } else { c.accent-subtle },
        inset: (left: space.space-2),
        if labels and part in outlined-labels {
          [#metadata((tab: part))<dossier-tab>]
          align(left + horizon, rotate(-90deg, reflow: true,
            outlined(outlined-labels.at(part), if active { c.on-accent } else { c.text-strong })))
        },
      ))
    }
  }
}

// Dot and initials of the tag, or the chosen mark or logo in their place (two cells of the tag's grid)
#let tag-mark(d, c, small) = if own-mark(d) {
  (grid.cell(colspan: 2, chosen-mark(d, c, if small { 18pt } else { 40pt }, if small { 72pt } else { 140pt },
    if small { 22pt } else { 44pt }, if small { "footer" } else { "cover" })),)
} else {
  (mark-marker("passend", if small { "footer" } else { "cover" }) + circle(radius: if small { 3pt } else { 5pt }, fill: c.accent),
   text(size: if small { 14pt } else { sizes.initials }, weight: 700, fill: c.text-strong)[#d.person.monogram])
}

// The mark: a tag with the filled dot of the status badge, initials, name and "Dossier · 11.2026"
#let tag(d, c, small: false) = box(
  stroke: 1pt + c.line-strong,
  radius: radius.radius-lg,
  fill: c.surface,
  inset: if small { (x: space.space-3, y: space.space-2) } else { space.space-4 },
  grid(
    columns: (auto, auto),
    column-gutter: space.space-2,
    row-gutter: space.space-2,
    align: horizon,
    ..tag-mark(d, c, small),
    grid.cell(colspan: 2, {
      text(size: if small { 8pt } else { 10pt }, weight: 500, fill: c.text-strong)[#d.person.name]
      if not small and d.at("stand", default: none) != none {
        linebreak()
        text(size: 8pt, fill: c.text-muted)[Dossier · #d.stand.slice(3)]
      }
    }),
  ),
)

#let footer(d, c) = text(size: sizes.small, fill: c.text-muted, grid(
  columns: (1fr, auto),
  [#d.person.name#if d.at("stand", default: none) != none [ · #d.stand]],
  context counter(page).display(),
))

#let part-marker(part) = [#metadata((part: part))<dossier-part>]

// Level 1–6 as a status badge whose fill grows with the level; without a level dashed, "ohne Angabe"
#let badge(level, c, w, label: none) = {
  level-marker(level)
  let word = if label != none { label } else if level != none { w.stufen.at(level - 1) } else { w.ohne-angabe }
  let (fill, stroke, colour) = if level == none {
    (none, (paint: c.line-strong, thickness: 0.6pt, dash: "dashed"), c.text-muted)
  } else if level <= 2 {
    (none, 0.6pt + c.line-strong, c.text)
  } else if level <= 4 {
    (c.accent-subtle, none, c.text-strong)
  } else {
    (c.accent, none, c.on-accent)
  }
  box(radius: 999pt, fill: fill, stroke: stroke, inset: (x: 6pt, y: 2.5pt), baseline: 2.5pt, {
    if level != none and level <= 2 {
      box(circle(radius: 2pt, stroke: 0.6pt + c.line-strong))
      h(3pt)
    }
    text(size: 8pt, fill: colour)[#word]
  })
}

#let table-head(cells, columns, c) = grid(
  columns: columns,
  inset: (bottom: space.space-2, right: space.space-3),
  ..cells.map(x => text(weight: 500, fill: c.text-muted, size: 8.5pt)[#x]),
)

// A station as a table row: period, duration, then title, organisation and bullets
#let station-columns = (24%, 12%, 1fr)
#let station(e, duration, b, c, org-key: "name") = grid(
  columns: station-columns,
  inset: (top: space.space-2, bottom: space.space-2, right: space.space-3),
  stroke: (top: 0.6pt + c.line),
  text(size: 9pt)[#zeitraum(e, b)],
  text(size: 9pt, fill: c.text-muted)[#if duration != none [#duration]],
  {
    let title = feld(e, "position")
    if title != none { text(weight: 700, fill: c.text-strong)[#title]; linebreak() }
    let org = (feld(e, org-key), feld(e, "location")).filter(x => x != none).join(", ")
    if org != none { text(fill: c.text-muted)[#org] }
    let hs = e.at("highlights", default: ()).map(text-von).filter(t => t != "")
    if hs.len() > 0 { list(..hs.map(t => [#t])) }
  },
)

// An entry with its badge on one line, so text extraction reads the word right after the name
#let with-badge(name, badge) = box[#name#h(4pt)#badge]

// Skills per group on one line each: "Sprachen  Python [ohne Angabe]   SQL [sehr gut]"
#let skills-section(d, c, w) = {
  let groups = d.skills.filter(g => g.items.len() > 0)
  if groups.len() == 0 { return none }
  groups.map(g => {
    text(weight: 500, fill: c.text-strong)[#g.name]
    h(space.space-3)
    if g.graphic {
      g.items.map(i => with-badge([#i.name], badge(i.level, c, w))).join(h(space.space-3))
    } else [#g.items.map(i => i.name).join(", ")]
  })
}

// Languages: the badge carries the level with its text, e.g. "C1 · Fliessend"
#let languages-section(d, c, w) = {
  let group = d.languages
  if group.items.len() == 0 { return none }
  let line-of(i) = [#i.language#if i.fluency != none [ – #i.fluency]]
  if group.graphic {
    group.items.map(i => if i.level != none {
      with-badge([#i.language], badge(i.level, c, w, label: cefr.at(i.level - 1) + if i.fluency != none { " · " + i.fluency }))
    } else {
      with-badge(line-of(i), badge(none, c, w))
    })
  } else {
    group.items.map(line-of)
  }
}

#let cv-head(d, c, single) = {
  if single { tag(d, c, small: true); v(space.space-4) }
  text(size: sizes.name, weight: 700, fill: c.text-strong)[#d.person.name]
  if d.person.label != none { v(space.space-2, weak: true); text(size: 11pt, fill: c.text-muted)[#d.person.label] }
  if d.person.contact.len() > 0 {
    v(space.space-3, weak: true)
    text(size: 9pt, fill: c.text-muted)[#d.person.contact.join(" · ")]
  }
  v(space.space-4)
}

// The CV as a part: sets only its own page style. `single`: the small tag above the name, no tab labels.
#let cv-part(d, single: false) = {
  let c = colours-for(d)
  let l = labels-for(d)
  let w = words-for(d)
  let b = l.cv
  let cv = d.cv
  let basics = cv.at("basics", default: (:))
  let durations = d.at("durations", default: (:))
  page(paper: "a4", margin: page-margin, fill: c.bg, footer: footer(d, c),
    background: tabs(d, c, "lebenslauf", labels: not single), {
    part-marker("lebenslauf")
    set text(size: sizes.body, fill: c.text)
    set par(leading: 0.6em, spacing: 0.8em)
    set list(marker: text(fill: c.text-muted)[–], indent: 0pt, body-indent: space.space-2, spacing: 0.5em)
    show heading.where(level: 1): it => block(above: space.space-5, below: space.space-3, sticky: true,
      text(size: sizes.section, weight: 700, fill: c.text-strong, it.body))

    let continued(title) = block(above: 0pt, below: space.space-3, sticky: true,
      text(size: sizes.section, weight: 700, fill: c.text-strong)[#title (#b.fortsetzung)])
    // Table rows touch, so their lines join; other entries keep a small gap
    let section(key, items, title: none, before: none, gap: space.space-2) = if items != none and items.len() > 0 {
      let t = if title != none { title } else { b.at(key) }
      heading(level: 1, t)
      before
      eintraege(key, items, continued(t), abstand: gap)
    }
    let stations(key, data-key) = section(key, cv.at(data-key, default: ()).enumerate().map(((i, e)) =>
      station(e, durations.at(data-key, default: ()).at(i, default: none), b, c)),
      before: table-head((w.zeitraum, w.dauer, w.station), station-columns, c), gap: 0pt)

    cv-head(d, c, single)
    let summary = feld(basics, "summary")
    if summary != none { section("profil", ([#summary],)) }
    stations("erfahrung", "work")
    stations("lehre", "teaching")
    let education = cv.at("education", default: ()) + cv.at("certificates", default: ())
    section("bildung", education.map(e => [#bildung-text(e, b)]))
    section("faehigkeiten", skills-section(d, c, w))
    section("sprachen", languages-section(d, c, w))
    let projects = cv.at("projects", default: ())
    section("projekte", projects.map(p => [#p.name#if feld(p, "description") != none [ – #p.description]]))
    let interests = d.interests.map(i => i.name)
    section("interessen", if interests.len() > 0 { ([#interests.join(", ")],) })
    if cv.at("references", default: ()).len() == 0 {
      section("referenzen", ([#w.auf-anfrage],), title: w.referenzen)
    }
  })
}
