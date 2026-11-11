// The mark of the dossier (G18, docs/design/monogramm.md): five variants from the initials, or the person's logo.
// dossier.py puts the choice into d.person.mark as (variant, logo); "passend" leaves each design its own mark.
// The initials stay real text, and a logo is only fitted: never stretched, cropped or recoloured.

#let fitting = "passend"

// The choice for this dossier; without one every design draws its own mark
#let mark-of(d) = d.person.at("mark", default: (variant: fitting, logo: none))
#let own-mark(d) = mark-of(d).variant != fitting

// Every drawn mark leaves a marker, so tests see which variant each design drew where
#let mark-marker(variant, at) = [#metadata((variant: variant, at: at))<dossier-mark>]

// Three letters take 80 % of the type size in the round and square marks
#let letters-scale(monogram) = if monogram.clusters().len() >= 3 { 0.8 } else { 1 }

// `mono`: one colour for everything, for a mark on the accent band (Raster)
#let ring-mark(monogram, size, c, mono) = box(width: size, height: size, circle(
  radius: size / 2,
  fill: if mono == none { c.surface } else { none },
  stroke: calc.max(size * 0.05, 1pt) + if mono == none { c.accent } else { mono },
  inset: 0pt,
  align(center + horizon, text(size: size * 0.34 * letters-scale(monogram), weight: 700,
    fill: if mono == none { c.text-strong } else { mono })[#monogram]),
))

#let block-mark(monogram, size, c, mono) = box(width: size, height: size, rect(
  width: size,
  height: size,
  radius: size * 0.13,
  fill: if mono == none { c.accent } else { mono },
  inset: 0pt,
  align(center + horizon, text(size: size * 0.4 * letters-scale(monogram), weight: 700,
    fill: if mono == none { c.on-accent } else { c.accent })[#monogram]),
))

// The first letter full, the second as an outline in the accent colour over it where they meet
#let interlaced-mark(monogram, size, c, mono) = {
  let (first, second) = monogram.clusters()
  let full = if mono == none { c.text-strong } else { mono }
  let outline = if mono == none { c.accent } else { mono }
  box(height: size, align(horizon, {
    box(text(size: size * 0.8, weight: 700, fill: full)[#first])
    h(-size * 0.12)
    box(text(size: size * 0.8, weight: 700, fill: rgb(0, 0, 0, 0), stroke: calc.max(size * 0.025, 0.5pt) + outline)[#second])
  }))
}

// The initials on a line in the accent colour that ends in a dot
#let line-mark(monogram, size, c, mono) = {
  let ink = if mono == none { c.accent } else { mono }
  box(height: size, stack(dir: ttb, spacing: size * 0.08,
    text(size: size * 0.55, weight: 700, fill: if mono == none { c.text-strong } else { mono })[#monogram],
    box(width: size * 1.3, height: size * 0.1, {
      place(left + horizon, line(length: 100% - size * 0.1, stroke: calc.max(size * 0.03, 0.6pt) + ink))
      place(right + horizon, circle(radius: size * 0.05, fill: ink))
    }),
  ))
}

// The dot of the status badge before the initials
#let dot-mark(monogram, size, c, mono) = box(height: size, align(horizon, stack(dir: ltr, spacing: size * 0.12,
  circle(radius: size * 0.09, fill: if mono == none { c.accent } else { mono }),
  text(size: size * 0.6, weight: 700, fill: if mono == none { c.text-strong } else { mono })[#monogram],
)))

#let variants = (
  ring: ring-mark,
  block: block-mark,
  verschraenkt: interlaced-mark,
  linie: line-mark,
  punkt: dot-mark,
)

// One of the five variants from the initials
#let mark(variant, monogram, size, c, at, mono: none) = {
  mark-marker(variant, at)
  (variants.at(variant))(monogram, size, c, mono)
}

// The logo as large as the space allows, wholly visible
#let logo-fit(path, max-w, max-h, at) = {
  mark-marker("logo", at)
  box(width: max-w, height: max-h, align(center + horizon, image(path, width: max-w, height: max-h, fit: "contain")))
}

// The chosen mark at one place: the logo in its space, a variant at its size, or none for the design's own mark
#let chosen-mark(d, c, size, logo-w, logo-h, at, mono: none) = {
  let m = mark-of(d)
  if m.variant == "logo" and m.logo != none { logo-fit(m.logo, logo-w, logo-h, at) }
  else if m.variant != fitting { mark(m.variant, d.person.monogram, size, c, at, mono: mono) }
}

// The chosen mark, or the design's own (`default`) when the person chose none
#let mark-or(d, c, size, logo-w, logo-h, at, default, mono: none) = if own-mark(d) {
  chosen-mark(d, c, size, logo-w, logo-h, at, mono: mono)
} else {
  mark-marker(fitting, at)
  default
}
