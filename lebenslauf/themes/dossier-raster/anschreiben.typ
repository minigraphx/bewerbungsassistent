// Cover letter of the design "Raster" on the shared letter layout (brief.typ). The accent band with the
// company and the position is the letterhead, alone and in the dossier alike.
#import "../brief.typ": brief-teil
#import "../tokens.typ": space
#import "../dossier.typ": colours-for
#import "theme.typ": bands, strip, footer, sizes, page-margin, cut

#let band-height = 140pt

#let letterhead(d, c) = {
  let h = d.letter.heading
  place(top + left, dy: -page-margin.top - cut, rect(
    width: 100%,
    height: band-height + cut,
    radius: 10pt,
    fill: c.accent,
    inset: (x: space.space-5, bottom: space.space-5),
    align(bottom + left, {
      if h.company != none { text(size: sizes.company, weight: 700, fill: c.on-accent)[#h.company]; linebreak() }
      if h.intro != none {
        text(size: 12pt, fill: c.on-accent)[#h.intro #h.position]
      } else if h.line != none {
        text(size: 12pt, fill: c.on-accent)[#h.line]
      }
    }),
  ))
  v(band-height - page-margin.top + space.space-5)
  text(size: 12pt, weight: 700, fill: c.text-strong)[#d.letter.absender.name]
  linebreak()
  text(size: 8.5pt, fill: c.text-muted)[#d.letter.absender.zeile]
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
    kopf: letterhead(d, c),
    fuss: footer(d, c),
  )
}
