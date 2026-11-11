// Parts of the dossier "Raster" besides letter and CV: cover, the optional page before ("Auf einen Blick",
// only with figures) and the optional back page (only with thanks). Each part sets only its own page style.
#import "../common.typ": foto-form
#import "../tokens.typ": space, radius
#import "../dossier.typ": colours-for, labels-for
#import "theme.typ": bands, top-bands, strip, footer, sizes, page-margin, cut
#import "../zeichen.typ": mark-or, mark-of

// The mark in the accent band: the initials, a chosen variant in on-accent, or the logo on a white field
#let band-mark(d, c) = if mark-of(d).variant == "logo" {
  rect(fill: c.surface, radius: 6pt, inset: 8pt, mark-or(d, c, 100pt, 190pt, 90pt, "cover", none))
} else {
  mark-or(d, c, 100pt, 190pt, 90pt, "cover", mono: c.on-accent,
    text(size: sizes.initials, weight: 700, fill: c.on-accent)[#d.person.monogram])
}

// Three punched dots in the accent band, in the paper colour
#let punched(c) = stack(dir: ltr, spacing: space.space-2, ..range(3).map(_ => circle(radius: 6pt, fill: c.bg)))

// Step path in the light band: one filled dot per past station (at most six), then open dots
#let step-path(done, c) = {
  [#metadata((done: done))<dossier-steps>]
  let dot(filled) = circle(radius: 4pt, fill: if filled { c.accent } else { c.accent-subtle },
    stroke: if filled { none } else { 1.2pt + c.accent })
  box(width: 100%, height: 8pt, {
    place(left + horizon, line(length: 100%, stroke: 1.2pt + c.accent))
    stack(dir: ltr, spacing: 1fr, ..(range(done).map(_ => dot(true)) + range(2).map(_ => dot(false))))
  })
}

#let detail-rows(rows, c) = grid(
  columns: (90pt, 1fr),
  row-gutter: space.space-3,
  ..rows.filter(r => r.at(1) != none).map(((label, value)) => (
    text(size: 9pt, fill: c.text-muted)[#label],
    text(size: 11pt, fill: c.text-strong)[#value],
  )).flatten(),
)

#let cover(d) = {
  let c = colours-for(d)
  let l = labels-for(d)
  let h = d.letter.heading
  page(paper: "a4", margin: page-margin, fill: c.bg, footer: none, {
    top-bands(300pt, c,
      first: {
        place(top + right, punched(c))
        align(bottom + left, band-mark(d, c))
      },
      last: align(bottom, step-path(d.person.steps, c)))
    text(size: sizes.name, weight: 700, fill: c.text-strong)[#d.person.name]
    if d.person.label != none {
      v(space.space-2, weak: true)
      text(size: 13pt, fill: c.text-muted)[#d.person.label]
    }
    v(space.space-6)
    let rows = (
      (l.stelle, if h.position != none { h.position } else { h.line }),
      (l.unternehmen, h.company),
      (l.inhalt, (l.anschreiben, l.lebenslauf).join(", ")),
      (l.datum, d.letter.ort_datum),
      (l.kontakt, if d.person.contact.len() > 0 { d.person.contact.join("\n") }),
    )
    let photo = d.person.photo
    if photo != none {
      grid(columns: (1fr, auto), column-gutter: space.space-5, detail-rows(rows, c),
        foto-form(photo, 110pt, 132pt, radius.radius-lg, d.person.at("photo-options", default: (:))))
    } else { detail-rows(rows, c) }
  })
}

// Optional page before the letter: the figures the person entered, large with tabular figures
#let glance-page(d) = {
  let figures = d.pages.at("figures", default: ())
  if figures.len() == 0 { return }
  let c = colours-for(d)
  let l = labels-for(d)
  page(paper: "a4", margin: page-margin, fill: c.bg, footer: footer(d, c), background: strip(c), {
    v(space.space-6)
    text(size: sizes.section, weight: 700, fill: c.text-strong)[#l.auf-einen-blick]
    v(space.space-6)
    grid(columns: (1fr,) * calc.min(figures.len(), 3), column-gutter: space.space-5, row-gutter: space.space-6,
      ..figures.map(f => {
        text(size: sizes.figure, weight: 700, fill: c.text-strong)[#f.value]
        v(space.space-2, weak: true)
        text(size: 10pt, fill: c.text-muted)[#f.text]
      }))
  })
}

// Optional back page: contact and the thanks above the bands, which are cut off at the bottom
#let back-page(d) = {
  let thanks = d.pages.at("thanks", default: none)
  if thanks == none { return }
  let c = colours-for(d)
  page(paper: "a4", margin: page-margin, fill: c.bg, footer: none, {
    v(1fr)
    text(size: 22pt, weight: 700, fill: c.text-strong)[#thanks]
    v(space.space-4)
    text(size: 12pt, weight: 700, fill: c.text-strong)[#d.person.name]
    linebreak()
    set text(size: 9.5pt, fill: c.text-muted)
    d.person.contact.join(" · ")
    v(220pt)
    place(bottom + left, dy: page-margin.bottom + cut, bands(180pt + cut, c))
  })
}
