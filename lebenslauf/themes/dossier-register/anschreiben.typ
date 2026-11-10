// Cover letter of the design "Register" on the shared letter layout (brief.typ): the small tag in the head,
// and a box on surface-subtle with position, workload, company and reference instead of the subject.
#import "../brief.typ": brief-teil
#import "../tokens.typ": space, radius
#import "../dossier.typ": colours-for
#import "theme.typ": tabs, tag, footer, part-marker, sizes, page-margin, words-for

#let letterhead(d, c) = {
  part-marker("anschreiben")
  tag(d, c, small: true)
  v(space.space-2, weak: true)
  text(size: 8.5pt, fill: c.text-muted)[#d.letter.absender.zeile]
}

#let subject(d, c) = {
  let hd = d.letter.heading
  let w = words-for(d)
  block(width: 100%, fill: c.surface-subtle, radius: radius.radius-md, inset: space.space-4, below: space.space-3, {
    if hd.position != none {
      text(size: sizes.position, weight: 700, fill: c.text-strong)[#hd.position]
    } else {
      text(size: 14pt, weight: 700, fill: c.text-strong)[#d.letter.betreff]
    }
    let details = ((w.pensum, hd.workload), (w.unternehmen, hd.company), (w.referenz, hd.reference))
      .filter(x => x.at(1) != none)
    if details.len() > 0 {
      v(space.space-2, weak: true)
      set text(size: 9pt)
      details.map(((label, value)) => [#text(fill: c.text-muted)[#label] #value]).join(h(space.space-4))
    }
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
    kopf: letterhead(d, c),
    betreff-block: subject(d, c),
    fuss: footer(d, c),
    hintergrund: tabs(d, c, "anschreiben", labels: not single),
  )
}
