// Design "Raster" (docs/design/dossier.md, design B): bold and data-like. The bands of the design-system
// cover carry the dossier; the career shows as a numbered horizontal axis. Marks and the CV part.
#import "../common.typ": *
#import "../page-fill.typ": spacing, leading, body-size, part-start, part-end
#import "../tokens.typ": space, radius
#import "../dossier.typ": colours-for, labels-for, level-marker, icon, current
#import "../zeichen.typ": own-mark, chosen-mark

#let sizes = (
  initials: 96pt,
  name: 38pt,
  figure: 64pt,
  company: 26pt,
  section: 12pt,
  body: 10pt,
  small: 8pt,
)

#let page-margin = (x: space.space-7, top: space.space-7 + space.space-3, bottom: space.space-7 + space.space-3)
#let side-column = 26%
#let cut = radius.radius-lg

// The three bands of the cover: accent, a slim one in text-strong, accent-subtle
#let bands(height, c, first: none, last: none) = grid(
  columns: (52%, 18pt, 1fr),
  column-gutter: space.space-2,
  rect(width: 100%, height: height, radius: radius.radius-lg, fill: c.accent, inset: space.space-5, first),
  rect(width: 100%, height: height, radius: radius.radius-lg, fill: c.text-strong),
  rect(width: 100%, height: height, radius: radius.radius-lg, fill: c.accent-subtle, inset: space.space-5, last),
)

// Bands at the top of the content area, cut off at the page edge; returns the space they take
#let top-bands(visible, c, first: none, last: none) = {
  place(top + left, dy: -page-margin.top - cut, bands(visible + cut, c, first: first, last: last))
  v(visible - page-margin.top + space.space-5)
}

// The mark on following pages: a slim strip of the same three bands, cut off at the top
#let strip(c) = place(top + left, dx: page-margin.x, dy: -cut,
  block(width: 100% - 2 * page-margin.x, bands(14pt + cut, c)))

// Footer of following pages; a chosen mark or logo stands small before the name (new with G18)
#let footer(d, c) = {
  let words = text(size: sizes.small, fill: c.text-muted)[#d.person.name#if d.at("stand", default: none) != none [ · #d.stand]]
  if own-mark(d) {
    grid(columns: (auto, 1fr), column-gutter: space.space-2, align: horizon,
      chosen-mark(d, c, 14pt, 44pt, 14pt, "footer"), words)
  } else { words }
}

// Level 1–6 as the grade bar of six fields; without a level the fields are dashed
#let grade-bar(level, c) = {
  level-marker(level)
  box(stack(dir: ltr, spacing: 2pt, ..range(6).map(i => rect(
    width: 9pt,
    height: 6pt,
    radius: 1.5pt,
    fill: if level == none { none } else if i < level { c.accent } else { c.line },
    stroke: if level == none { (paint: c.line-strong, thickness: 0.6pt, dash: "dashed") } else { none },
  ))))
}

// Horizontal axis from the first year to today (dossier_data.timeline): one bar per station,
// proportional to its duration, carrying only its number. Current stations in the accent colour.
#let axis(t, c, l) = {
  if t.bars.len() == 0 { return }
  [#metadata((bars: t.bars.len()))<dossier-axis>]
  let lane = 12pt
  let earlier-width = if t.earlier { 36pt } else { 0pt }
  block(width: 100%, above: 0pt, below: space.space-4, grid(
    columns: (earlier-width, 1fr),
    column-gutter: if t.earlier { space.space-1 } else { 0pt },
    if t.earlier {
      rect(width: 100%, height: t.lanes * lane - 3pt, radius: 4pt, stroke: (paint: c.line-strong, thickness: 0.6pt, dash: "dashed"),
        inset: 0pt, align(center + horizon, text(size: 6.5pt, fill: c.text-muted)[#l.frueher]))
    },
    {
      box(width: 100%, height: t.lanes * lane, for bar in t.bars {
        place(top + left, dx: bar.from * 100%, dy: bar.lane * lane, rect(
          width: (bar.to - bar.from) * 100%,
          height: lane - 3pt,
          radius: 4pt,
          fill: if bar.current { c.accent } else { c.line },
          inset: 0pt,
          align(center + horizon, text(size: 6.5pt, weight: 700,
            fill: if bar.current { c.on-accent } else { c.text-strong })[#str(bar.number)]),
        ))
      })
      box(width: 100%, height: 12pt, {
        place(top + left, line(length: 100%, stroke: 0.6pt + c.line-strong))
        for tick in t.ticks {
          place(top + left, dx: tick.at * 100%, dy: 3pt, text(size: 7pt, fill: c.text-muted)[#str(tick.year)])
        }
      })
    },
  ))
}

#let number-badge(n, c) = box(fill: c.accent-subtle, radius: 4pt, inset: (x: 4pt, y: 2pt),
  text(size: 8pt, weight: 700, fill: c.text-strong)[#str(n)])

// A station: side column first (number, period), then title, organisation and bullets
#let station(e, b, c, number: none, org-key: "name") = grid(
  columns: (side-column, 1fr),
  column-gutter: space.space-3,
  {
    // Number and period on the title's line, so text extraction reads them before the station
    if number != none { number-badge(number, c); h(space.space-2) }
    text(size: 9pt, fill: c.text-muted)[#zeitraum(e, b)]
  },
  {
    let title = feld(e, "position")
    if title != none { text(weight: 700, fill: c.text-strong)[#title]; linebreak() }
    let org = (feld(e, org-key), feld(e, "location")).filter(x => x != none).join(", ")
    if org != none { text(fill: c.text-muted)[#org] }
    let hs = e.at("highlights", default: ()).map(text-von).filter(t => t != "")
    if hs.len() > 0 { list(..hs.map(t => [#t])) }
  },
)

#let skills-section(d, c) = {
  let groups = d.skills.filter(g => g.items.len() > 0)
  if groups.len() == 0 { return none }
  groups.map(g => grid(
    columns: (side-column, 1fr),
    column-gutter: space.space-3,
    text(weight: 500, fill: c.text-strong)[#g.name],
    if g.graphic {
      grid(columns: (auto, 1fr), row-gutter: space.space-2, column-gutter: space.space-5, align: horizon,
        ..g.items.map(i => ([#i.name], grade-bar(i.level, c))).flatten())
    } else [#g.items.map(i => i.name).join(", ")],
  ))
}

#let languages-section(d, c) = {
  let group = d.languages
  if group.items.len() == 0 { return none }
  let line-of(i) = [#i.language#if i.fluency != none [ – #i.fluency]]
  if group.graphic {
    (grid(columns: (auto, 1fr), row-gutter: space.space-2, column-gutter: space.space-5, align: horizon,
      ..group.items.map(i => (line-of(i), grade-bar(i.level, c))).flatten()),)
  } else {
    group.items.map(line-of)
  }
}

// Interests: icon in text-strong on a field in accent-subtle, the word below; without an icon only the word
#let interests-section(d, c) = {
  if d.interests.len() == 0 { return none }
  (d.interests.map(i => box(width: 64pt, inset: (bottom: space.space-2), align(center, {
    if i.icon != none {
      box(fill: c.accent-subtle, radius: radius.radius-md, inset: space.space-2, icon(i.icon, i.icon-name, c.text-strong, 18pt))
      v(space.space-1, weak: true)
    }
    text(size: 9pt)[#i.name]
  }))).join(h(space.space-2)),)
}

// Head of the CV: alone it starts with a taller band (name in on-accent, photo in the light band)
#let cv-head(d, c, single) = {
  if single {
    let photo = d.person.photo
    top-bands(150pt, c,
      first: align(bottom + left, {
        text(size: 28pt, weight: 700, fill: c.on-accent)[#d.person.name]
        if d.person.label != none { linebreak(); text(size: 11pt, fill: c.on-accent)[#d.person.label] }
      }),
      last: if photo != none {
        align(bottom + center, foto-form(photo, 84pt, 100pt, radius.radius-lg, d.person.at("photo-options", default: (:))))
      })
  } else {
    text(size: 26pt, weight: 700, fill: c.text-strong)[#d.person.name]
    if d.person.label != none { v(space.space-2, weak: true); text(size: 11pt, fill: c.text-muted)[#d.person.label] }
  }
  if d.person.contact.len() > 0 {
    v(space.space-3, weak: true)
    text(size: 9pt, fill: c.text-muted)[#d.person.contact.join(" · ")]
  }
  v(space.space-4)
}

// The CV as a part: sets only its own page style. `single`: the band head replaces the strip on page 1.
#let cv-part(d, single: false) = {
  let c = colours-for(d)
  let l = labels-for(d)
  let b = l.cv
  let cv = d.cv
  let basics = cv.at("basics", default: (:))
  let with-axis = d.at("style", default: (:)).at("zeitachse", default: true)
  page(paper: "a4", margin: page-margin, fill: c.bg, footer: footer(d, c),
    background: context { if not (single and here().page() == 1) { strip(c) } }, {
    let (f, lf) = (spacing("cv"), leading("cv"))
    set text(size: body-size(sizes.body, "cv"), fill: c.text)
    set par(leading: 0.6em * lf, spacing: 0.8em * f)
    set list(marker: text(fill: c.text-muted)[–], indent: 0pt, body-indent: space.space-2, spacing: 0.5em * f)
    show heading.where(level: 1): it => block(above: space.space-5 * f, below: space.space-3 * f, sticky: true,
      text(size: sizes.section, weight: 700, fill: c.text-strong, it.body))

    let continued(title) = block(above: 0pt, below: space.space-3 * f, sticky: true,
      text(size: sizes.section, weight: 700, fill: c.text-strong)[#title (#b.fortsetzung)])
    // Sections of one-line entries: up to five they stay together with their heading, longer ones never
    // leave their last entry alone (G50)
    let short-keys = ("bildung", "faehigkeiten", "sprachen", "projekte", "interessen")
    // The block takes the heading's space above, which a heading at the start of a block would lose
    let together(key, items, body) = if key in short-keys and items.len() <= 5 {
      block(breakable: false, above: space.space-5 * f, body)
    } else { body }
    let section(key, items, before: none) = if items != none and items.len() > 0 { together(key, items, {
      heading(level: 1, b.at(key))
      before
      eintraege(key, items, continued(b.at(key)), abstand: space.space-3 * f, einzeilig: key in short-keys)
    }) }

    part-start("cv")
    cv-head(d, c, single)
    let summary = feld(basics, "summary")
    if summary != none { section("profil", ([#summary],)) }
    let work = cv.at("work", default: ())
    section("erfahrung", work.enumerate().map(((i, e)) => station(e, b, c, number: i + 1)),
      before: if with-axis { axis(d.timeline, c, l) })
    section("lehre", cv.at("teaching", default: ()).map(e => station(e, b, c)))
    let education = cv.at("education", default: ()) + cv.at("certificates", default: ())
    section("bildung", education.map(e => [#bildung-text(e, b)]))
    section("faehigkeiten", skills-section(d, c))
    section("sprachen", languages-section(d, c))
    let projects = cv.at("projects", default: ())
    section("projekte", projects.map(p => [#p.name#if feld(p, "description") != none [ – #p.description]]))
    section("interessen", interests-section(d, c))
    part-end("cv")
  })
}
