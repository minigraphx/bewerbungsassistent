// Cover letter of the design "Siegel" on the shared letter layout (brief.typ). Alone it carries a
// letterhead with ring, name and label; in the dossier the cover already shows the ring.
#import "../brief.typ": brief-teil
#import "../tokens.typ": space
#import "../dossier.typ": colours-for
#import "theme.typ": ring, footer, sizes, page-margin

#let letterhead(d, c, single) = {
  let name-block = {
    text(size: 18pt, weight: 700, fill: c.text-strong)[#d.person.name]
    if d.person.label != none { linebreak(); text(size: 10pt, fill: c.text-muted)[#d.person.label] }
  }
  if single {
    grid(columns: (auto, 1fr), column-gutter: space.space-3, align: horizon, ring(d.person.monogram, 40pt, c), name-block)
  } else { name-block }
  v(space.space-2, weak: true)
  text(size: 8.5pt, fill: c.text-muted)[#d.letter.absender.zeile]
}

// The strong heading: "Bewerbung als" and the position in 28 pt; without a position the subject line
#let subject(d, c) = {
  let h = d.letter.heading
  block(below: space.space-3, {
    if h.intro != none {
      text(size: 10pt, fill: c.text-muted)[#h.intro]
      linebreak()
      text(size: sizes.position, weight: 700, fill: c.text-strong)[#h.position]
    } else {
      text(size: 14pt, weight: 700, fill: c.text-strong)[#d.letter.betreff]
    }
    let details = (h.company, h.workload, if h.reference != none { "Ref. " + h.reference }).filter(x => x != none)
    if details.len() > 0 { linebreak(); text(size: 9.5pt, fill: c.text-muted)[#details.join(" · ")] }
  })
}

#let letter-part(d, single: false) = {
  let c = colours-for(d)
  brief-teil(
    d.letter,
    stil: (
      farbe-text: c.text,
      farbe-akzent: c.text-strong,
      farbe-hintergrund: c.bg,
      groesse-text: 10pt,
      rand: page-margin,
      abstand-kopf: space.space-6,
      abstand-empfaenger: space.space-5,
    ),
    kopf: letterhead(d, c, single),
    betreff-block: subject(d, c),
    fuss: footer(d, c),
  )
}
