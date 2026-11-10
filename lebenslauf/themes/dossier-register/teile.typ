// Parts of the dossier "Register" besides letter and CV: the cover with the table of contents, and the
// optional pages Beilagen (only with attachments) and Referenzen (only with references in the CV).
#import "../common.typ": foto-form, datum
#import "../tokens.typ": space, radius
#import "../dossier.typ": colours-for, labels-for
#import "theme.typ": tabs, tag, footer, part-marker, sizes, page-margin, words-for, tab-parts

// Page of a part, read from its marker; empty until the layout knows it
#let page-of(part) = context {
  let found = query(<dossier-part>).filter(m => m.value.part == part)
  if found.len() > 0 [#found.first().location().page()]
}

#let contents(d, c, l, w) = {
  let h = d.letter.heading
  let attachments = d.pages.at("attachments", default: ())
  let summary = (
    anschreiben: if h.line != none { h.line } else { d.letter.betreff },
    lebenslauf: d.person.name,
    beilagen: none,
    referenzen: none,
  )
  let rows = ()
  for (i, part) in tab-parts(d).enumerate() {
    let title = if part == "anschreiben" { l.anschreiben } else if part == "lebenslauf" { l.lebenslauf } else { w.at(part) }
    rows.push(([#str(i + 1) #title], [#if summary.at(part) != none [#summary.at(part)]], page-of(part)))
    if part == "beilagen" {
      for a in attachments { rows.push(([], pad(left: space.space-3)[#a.name], [])) }
    }
  }
  block(width: 100%, stroke: 1pt + c.line, radius: radius.radius-lg, inset: space.space-4, {
    text(size: sizes.section, weight: 700, fill: c.text-strong)[#w.inhalt]
    v(space.space-3)
    grid(
      columns: (30%, 1fr, auto),
      inset: (y: space.space-2, right: space.space-3),
      stroke: (x, y) => if y > 0 { (top: 0.6pt + c.line) },
      ..(w.teil, w.inhalt, w.seite).map(x => text(weight: 500, size: 8.5pt, fill: c.text-muted)[#x]),
      ..rows.flatten(),
    )
  })
}

#let cover(d) = {
  let c = colours-for(d)
  let l = labels-for(d)
  let w = words-for(d)
  let h = d.letter.heading
  page(paper: "a4", margin: page-margin, fill: c.bg, footer: none, background: tabs(d, c, none), {
    set text(size: 10pt, fill: c.text)
    let photo = d.person.photo
    grid(columns: (1fr, auto), align: top,
      tag(d, c),
      if photo != none { foto-form(photo, 80pt, 100pt, radius.radius-md, d.person.at("photo-options", default: (:))) })
    v(space.space-6)
    text(size: 11pt, fill: c.text-muted)[#w.bewerbung]
    linebreak()
    text(size: sizes.name, weight: 700, fill: c.text-strong)[#if h.position != none { h.position } else { h.line }]
    if h.company != none { linebreak(); text(size: 13pt, fill: c.text)[#h.company] }
    if d.person.contact.len() > 0 {
      v(space.space-3, weak: true)
      text(size: 9pt, fill: c.text-muted)[#d.person.contact.join(" · ")]
    }
    v(space.space-6)
    contents(d, c, l, w)
  })
}

#let table-page(d, part, title, body) = {
  let c = colours-for(d)
  page(paper: "a4", margin: page-margin, fill: c.bg, footer: footer(d, c), background: tabs(d, c, part), {
    part-marker(part)
    set text(size: 9.5pt, fill: c.text)
    heading(level: 1, outlined: true, text(size: sizes.section, weight: 700, fill: c.text-strong)[#title])
    v(space.space-4)
    body
  })
}

// Optional page: the attachments with number, document and date
#let attachments-page(d) = {
  let items = d.pages.at("attachments", default: ())
  if items.len() == 0 { return }
  let c = colours-for(d)
  let l = labels-for(d)
  let w = words-for(d)
  table-page(d, "beilagen", w.beilagen, grid(
    columns: (32pt, 1fr, auto),
    inset: (y: space.space-2, right: space.space-3),
    stroke: (x, y) => if y > 0 { (top: 0.6pt + c.line) },
    ..(w.nr, w.dokument, w.datum).map(x => text(weight: 500, size: 8.5pt, fill: c.text-muted)[#x]),
    ..items.enumerate().map(((i, a)) => (
      [#str(i + 1)], [#a.name], [#if a.date != none [#datum(a.date, l.cv)]],
    )).flatten(),
  ))
}

// Optional page: references, only when the CV lists them
#let references-page(d) = {
  let items = d.cv.at("references", default: ())
  if items.len() == 0 { return }
  let c = colours-for(d)
  let w = words-for(d)
  table-page(d, "referenzen", w.referenzen, for r in items {
    block(below: space.space-4, {
      text(weight: 700, fill: c.text-strong)[#r.at("name", default: "")]
      let text-of = r.at("reference", default: none)
      if text-of != none { linebreak(); [#text-of] }
    })
  })
}
