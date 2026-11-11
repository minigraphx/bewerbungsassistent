// Parts of the dossier "Siegel" besides letter and CV: cover, the optional page before ("Kurz vorgestellt")
// and the optional page after ("Danke"). Each part sets only its own page style; an optional page
// without content is left out.
#import "../common.typ": foto-rund
#import "../tokens.typ": space, radius
#import "../dossier.typ": colours-for, labels-for
#import "theme.typ": ring, footer, sizes, page-margin
#import "../zeichen.typ": mark-or, mark-of, own-mark

#let open-steps = 2

// The node of the step path: ring and block are the node themselves; the other marks and a logo stand on a
// field in the paper colour where the line ends
#let node(d, c) = {
  let drawn = mark-or(d, c, 76pt, 150pt, 76pt, "cover", ring(d.person.monogram, 76pt, c))
  if mark-of(d).variant in ("passend", "ring", "block") { drawn }
  else { box(fill: c.bg, inset: (x: space.space-3), drawn) }
}

// Horizontal step path: one filled dot per past station (counted in dossier.py, at most six),
// then the mark, then open dots for what comes next
#let step-path(d, c) = {
  let done = d.person.steps
  [#metadata((done: done))<dossier-steps>]
  let dot(filled) = circle(radius: 5pt, fill: if filled { c.accent } else { c.bg },
    stroke: if filled { none } else { 1.4pt + c.accent })
  let marks = range(done).map(_ => dot(true)) + (node(d, c),) + range(open-steps).map(_ => dot(false))
  box(width: 100%, height: 76pt, {
    place(left + horizon, line(length: 100%, stroke: 1.4pt + c.accent))
    // A wider mark or logo takes the width it needs; the ring keeps the even spacing it always had
    let columns = range(marks.len()).map(i => if i == done and own-mark(d) { auto } else { 1fr })
    grid(columns: columns, align: center + horizon, rows: 76pt, ..marks)
  })
}

// Accent band at the foot of the page, cut off at the bottom edge so only its top corners are round
#let band(height, c, body) = place(bottom + center, dy: page-margin.bottom + radius.radius-lg, rect(
  width: 100% + 2 * space.space-5,
  height: height + radius.radius-lg,
  radius: radius.radius-lg,
  fill: c.accent,
  inset: (x: space.space-5, top: space.space-5),
  align(left + top, body),
))

#let cover(d) = {
  let c = colours-for(d)
  let heading = d.letter.heading
  page(paper: "a4", margin: page-margin, fill: c.bg, footer: none, {
    v(space.space-7 * 2)
    step-path(d, c)
    v(space.space-7)
    text(size: sizes.name, weight: 700, fill: c.text-strong)[#d.person.name]
    if d.person.label != none {
      v(space.space-2, weak: true)
      text(size: 13pt, fill: c.text-muted)[#d.person.label]
    }
    v(space.space-6)
    if heading.intro != none {
      text(size: 11pt, fill: c.text-muted)[#heading.intro]
      linebreak()
      text(size: 20pt, weight: 700, fill: c.text-strong)[#heading.position]
    } else if heading.line != none {
      text(size: 16pt, weight: 700, fill: c.text-strong)[#heading.line]
    }
    if heading.company != none {
      v(space.space-2, weak: true)
      text(size: 13pt, fill: c.text)[#heading.company]
    }
    band(120pt, c, {
      set text(size: 10pt, fill: c.on-accent)
      set par(leading: 0.7em, spacing: 0.7em)
      for item in d.person.contact [#item #parbreak()]
    })
  })
}

// Optional page before the letter: round photo and a card with the greeting, signed in italics
#let greeting-page(d) = {
  let text-of = d.pages.at("greeting", default: none)
  if text-of == none { return }
  let c = colours-for(d)
  let l = labels-for(d)
  page(paper: "a4", margin: page-margin, fill: c.bg, footer: footer(d, c), {
    set text(size: 10pt, fill: c.text)
    set par(leading: 0.7em, spacing: 1em)
    v(space.space-7)
    text(size: sizes.section, weight: 700, fill: c.text-strong)[#l.kurz-vorgestellt]
    v(space.space-5)
    let card = block(width: 100%, fill: c.surface-subtle, radius: radius.radius-lg, inset: space.space-5, {
      for paragraph in text-of.split("\n\n") [#paragraph.split("\n").join(" ") #parbreak()]
      v(space.space-3)
      text(style: "italic", fill: c.text-strong)[#d.person.name]
    })
    if d.person.photo != none {
      grid(columns: (auto, 1fr), column-gutter: space.space-5,
        foto-rund(d.person.photo, 120pt, d.person.at("photo-options", default: (:))), card)
    } else { card }
  })
}

// Optional page after the CV: one sentence of thanks, the ring, contact and a slim band
#let thanks-page(d) = {
  let thanks = d.pages.at("thanks", default: none)
  if thanks == none { return }
  let c = colours-for(d)
  page(paper: "a4", margin: page-margin, fill: c.bg, footer: none, {
    v(1fr)
    align(center, {
      text(size: 20pt, weight: 700, fill: c.text-strong)[#thanks]
      v(space.space-6)
      mark-or(d, c, 56pt, 110pt, 56pt, "thanks", ring(d.person.monogram, 56pt, c))
      v(space.space-4)
      text(size: 12pt, weight: 700, fill: c.text-strong)[#d.person.name]
      v(space.space-2, weak: true)
      set text(size: 9.5pt, fill: c.text-muted)
      d.person.contact.join(" · ")
    })
    v(1fr)
    band(space.space-4, c, none)
  })
}
