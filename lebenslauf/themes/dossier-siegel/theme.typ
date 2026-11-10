// Design "Siegel" (docs/design/dossier.md, design A): calm, one column, the mark is the step dot of
// the design system, a ring with the initials. This file holds the marks and the CV part.
#import "../common.typ": *
#import "../tokens.typ": space, radius
#import "../dossier.typ": colours-for, labels-for, level-marker, icon, current

#let sizes = (
  name: 34pt,
  position: 28pt,
  section: 12pt,
  body: 9.5pt,
  small: 8pt,
)

#let page-margin = (x: space.space-7, top: space.space-7, bottom: space.space-7 + space.space-3)

// The mark: a ring in the accent colour on surface, initials in text-strong 700
#let ring(monogram, size, c) = box(width: size, height: size, circle(
  radius: size / 2,
  fill: c.surface,
  stroke: calc.max(size * 0.05, 1pt) + c.accent,
  inset: 0pt,
  align(center + horizon, text(size: size * 0.34, weight: 700, fill: c.text-strong)[#monogram]),
))

// Footer of every page but the cover: small ring, name and date
#let footer(d, c) = grid(
  columns: (auto, 1fr),
  column-gutter: space.space-2,
  align: horizon,
  ring(d.person.monogram, 16pt, c),
  text(size: sizes.small, fill: c.text-muted)[#d.person.name#if d.at("stand", default: none) != none [ · #d.stand]],
)

// Level 1–6 as a small path of six dots; without a level the dots and the line are dashed
#let level-path(level, c) = {
  let r = 2.6pt
  let gap = 3.4pt
  let width = 6 * 2 * r + 5 * gap
  let dashed = level == none
  let thin = 0.7pt
  level-marker(level)
  box(width: width, height: 2 * r, {
    place(left + horizon, line(length: width, stroke: if dashed {
      (paint: c.line-strong, thickness: thin, dash: "dashed")
    } else { thin + c.line-strong }))
    stack(dir: ltr, spacing: gap, ..range(6).map(i => circle(
      radius: r,
      fill: if not dashed and i < level { c.accent } else { c.surface },
      stroke: if dashed { (paint: c.line-strong, thickness: thin, dash: "densely-dotted") }
        else if i < level { none } else { thin + c.line-strong },
    )))
  })
}

// Dot of the vertical step display: ring for current stations, filled for finished ones
#let step-dot(open, c) = circle(
  radius: 4pt,
  fill: if open { c.surface } else { c.accent },
  stroke: if open { 1.4pt + c.accent } else { none },
)

// A station of the timeline: period | dot on the line | station. The period comes first in the source,
// so text extraction reads period, title, organisation and bullets in that order.
// Period column and the gap up to the station text; skills use the same edge
#let label-columns = (25%, 1fr)
#let label-gutter = 7pt + space.space-3

#let station(e, b, c, org-key: "name") = grid(
  columns: (label-columns.first(), 7pt, space.space-3, 1fr),
  inset: (bottom: space.space-4),
  text(size: 9pt, fill: c.text-muted)[#zeitraum(e, b)],
  grid.cell(stroke: (right: 0.8pt + c.line), place(top + right, dx: 4pt, dy: 1.5pt, step-dot(current(e), c))),
  [],
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
  let groups = d.skills.filter(g => g.items.len() > 0 or g.name != "")
  if groups.len() == 0 { return none }
  groups.map(g => grid(
    columns: label-columns,
    column-gutter: label-gutter,
    text(weight: 500, fill: c.text-strong)[#g.name],
    if g.graphic {
      grid(columns: (auto, 1fr), row-gutter: space.space-2, column-gutter: space.space-5, align: horizon,
        ..g.items.map(i => ([#i.name], level-path(i.level, c))).flatten())
    } else [#g.items.map(i => i.name).join(", ")],
  ))
}

#let languages-section(d, c) = {
  let group = d.languages
  if group.items.len() == 0 { return none }
  let line-of(i) = [#i.language#if i.fluency != none [ – #i.fluency]]
  if group.graphic {
    (grid(columns: (auto, 1fr), row-gutter: space.space-2, column-gutter: space.space-5, align: horizon,
      ..group.items.map(i => (line-of(i), level-path(i.level, c))).flatten()),)
  } else {
    group.items.map(line-of)
  }
}

// Interests: line icon in the accent colour above the word; without an icon only the word
#let interests-section(d, c) = {
  if d.interests.len() == 0 { return none }
  (d.interests.map(i => box(width: 64pt, inset: (bottom: space.space-2), align(center, {
    if i.icon != none { icon(i.icon, i.icon-name, c.accent, 18pt); v(space.space-1, weak: true) }
    text(size: 9pt)[#i.name]
  }))).join(h(space.space-2)),)
}

#let cv-head(d, c, single) = {
  let basics = d.cv.at("basics", default: (:))
  let name-block = {
    text(size: sizes.name, weight: 700, fill: c.text-strong)[#d.person.name]
    if d.person.label != none { v(space.space-2, weak: true); text(size: 12pt, fill: c.text-muted)[#d.person.label] }
  }
  if single {
    grid(columns: (auto, 1fr), column-gutter: space.space-4, align: horizon, ring(d.person.monogram, 56pt, c), name-block)
  } else { name-block }
  if d.person.contact.len() > 0 {
    v(space.space-3, weak: true)
    text(size: 9pt, fill: c.text-muted)[#d.person.contact.join(" · ")]
  }
  v(space.space-4)
}

// The CV as a part: sets only its own page style. `single`: the ring moves into the head of page 1.
#let cv-part(d, single: false) = {
  let c = colours-for(d)
  let l = labels-for(d)
  let b = l.cv
  let cv = d.cv
  let basics = cv.at("basics", default: (:))
  page(paper: "a4", margin: page-margin, fill: c.bg, footer: footer(d, c), {
    set text(size: sizes.body, fill: c.text)
    set par(leading: 0.6em, spacing: 0.8em)
    set list(marker: text(fill: c.text-muted)[–], indent: 0pt, body-indent: space.space-2, spacing: 0.5em)
    show heading.where(level: 1): it => block(above: space.space-5, below: space.space-3, sticky: true,
      text(size: sizes.section, weight: 700, fill: c.text-strong, it.body))

    let continued(title) = block(above: 0pt, below: space.space-3, sticky: true,
      text(size: sizes.section, weight: 700, fill: c.text-strong)[#title (#b.fortsetzung)])
    let section(key, items) = if items != none and items.len() > 0 {
      heading(level: 1, b.at(key))
      eintraege(key, items, continued(b.at(key)), abstand: space.space-2)
    }

    cv-head(d, c, single)
    let summary = feld(basics, "summary")
    if summary != none { section("profil", ([#summary],)) }
    section("erfahrung", cv.at("work", default: ()).map(e => station(e, b, c)))
    section("lehre", cv.at("teaching", default: ()).map(e => station(e, b, c)))
    let education = cv.at("education", default: ()) + cv.at("certificates", default: ())
    section("bildung", education.map(e => [#bildung-text(e, b)]))
    section("faehigkeiten", skills-section(d, c))
    section("sprachen", languages-section(d, c))
    let projects = cv.at("projects", default: ())
    section("projekte", projects.map(p => [#p.name#if feld(p, "description") != none [ – #p.description]]))
    section("interessen", interests-section(d, c))
  })
}
